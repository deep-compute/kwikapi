import socket
from urllib.parse import urljoin, urlparse, urlencode
import urllib.request
from requests.structures import CaseInsensitiveDict

from deeputil import Dummy, ExpiringCache

from .protocols import PROTOCOLS
from .exception import NonKeywordArgumentsError, ResponseError
from .api import PROTOCOL_HEADER, REQUEST_ID_HEADER
from .utils import get_loggable_params

DUMMY_LOG = Dummy()


class DNSCache:
    CACHE_SIZE = 2048
    CACHE_TIMEOUT = 600

    def __init__(self):
        self._cache = ExpiringCache(self.CACHE_SIZE, self.CACHE_TIMEOUT)

    def map_url(self, url):
        scheme, netloc, path, _, query, _ = urlparse(url)
        _netloc = netloc.split(":", 1)
        if len(_netloc) > 1:
            host, port = _netloc
        else:
            host, port = _netloc[0], 80

        _host = self._cache.get(host, None)
        if _host is None:
            _host = socket.gethostbyname(host)
            self._cache.put(host, _host)

        if query:
            path = "{}?{}".format(path, query)

        if port:
            return "{}://{}:{}{}".format(scheme, _host, port, path)
        else:
            return "{}://{}{}".format(scheme, _host, path)


class Client:
    DEFAULT_PROTOCOL = "pickle"

    def __init__(
        self,
        url,
        version=None,
        protocol=DEFAULT_PROTOCOL,
        path=None,
        request="",
        timeout=None,
        dnscache=None,
        headers=None,
        auth=None,
        stream=False,
        log=DUMMY_LOG,
        raise_exception=True,
    ):

        headers = headers or {}

        self._url = url
        self._version = version
        self._protocol = protocol  # FIXME: check validity

        self._path = path or []
        self._request = request
        self._timeout = timeout
        self._dnscache = dnscache
        self._headers = CaseInsensitiveDict(headers)
        self._auth = auth
        self._stream = stream
        self._log = log
        self._raise_exception = raise_exception

        if not self._dnscache:
            self._dnscache = DNSCache()

    def _get_state(self):
        return dict(
            url=self._url,
            version=self._version,
            protocol=self._protocol,
            path=self._path,
            request=self._request,
            timeout=self._timeout,
            dnscache=self._dnscache,
            headers=self._headers,
            auth=self._auth,
            stream=self._stream,
            log=self._log,
            raise_exception=self._raise_exception,
        )

    def _copy(self, **kwargs):
        _kwargs = self._get_state()
        _kwargs.update(kwargs)
        return Client(**_kwargs)

    def _prepare_request(self, post_body, get_params=None):
        headers = self._headers.copy()

        if self._request:
            for hk, hv in self._request.headers.items():
                if not hk.lower().startswith("x-kwikapi-"):
                    continue
                headers[hk] = hv

            headers[REQUEST_ID_HEADER] = self._request.id

        headers[PROTOCOL_HEADER] = self._protocol

        upath = [self._version] + self._path
        upath = "/".join(x for x in upath if x)
        url = urljoin(self._url, upath)

        if get_params:
            url = "{}?{}".format(url, urlencode(get_params))

        url = self._dnscache.map_url(url)
        if self._auth:
            self._auth.sign(url, headers, post_body)

        return url, post_body, headers

    def _make_request(self, url, post_body, headers):
        req = urllib.request.Request(url, data=post_body, headers=headers)
        res = urllib.request.urlopen(req)

        proto = PROTOCOLS[res.headers.get("X-KwikAPI-Protocol", self._protocol)]

        if self._stream:
            res = proto.deserialize_stream(res)
            res = Client._extract_stream_response(res, self._raise_exception)
        else:
            res = self._deserialize_response(res.read(), proto, self._raise_exception)

        return res

    @staticmethod
    def _deserialize_response(data, proto, raise_exception=True):
        r = proto.deserialize(data)
        return Client._extract_response(r, raise_exception)

    @staticmethod
    def _extract_response(r, raise_exception=True):
        success = r["success"]
        if not success:
            r.pop("success")
            r = ResponseError(r)
            if raise_exception:
                raise r
        else:
            r = r["result"]

        return r

    @staticmethod
    def _extract_stream_response(res, raise_exception=True):
        for r in res:
            yield Client._extract_response(r, raise_exception)

    @staticmethod
    def _serialize_params(params, protocol):
        proto = PROTOCOLS[protocol]
        data = proto.serialize(params)
        return data

    def __call__(self, *args, **kwargs):
        if args:
            raise NonKeywordArgumentsError(args)

        if self._path:
            # FIXME: support streaming in both directions
            _kwargs = get_loggable_params(kwargs or {})

            self._log.debug(
                "kwikapi.client.__call__",
                path=self._path,
                kwargs=_kwargs,
                url=self._url,
                version=self._version,
                protocol=self._protocol,
            )

            post_body = self._serialize_params(kwargs, self._protocol)
            url, post_body, headers = self._prepare_request(post_body)
            res = self._make_request(url, post_body, headers)

            return res

        else:
            return self._copy(**kwargs)

    def __getattr__(self, attr):
        return self._copy(path=self._path + [attr])
