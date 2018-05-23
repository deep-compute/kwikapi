import socket
from urllib.parse import urljoin, urlparse, urlencode
import urllib.request

from deeputil import Dummy, ExpiringCache

from .protocols import PROTOCOLS
from .exception import APICallFailed
from .api import PROTOCOL_HEADER, NETPATH_HEADER
from .utils import get_loggable_params

DUMMY_LOG = Dummy()

class DNSCache:
    CACHE_SIZE = 2048
    CACHE_TIMEOUT = 600

    def __init__(self):
        self._cache = ExpiringCache(self.CACHE_SIZE,
                self.CACHE_TIMEOUT)

    def map_url(self, url):
        scheme, netloc, path, _, query, _ = urlparse(url)
        _netloc = netloc.split(':', 1)
        if len(_netloc) > 1:
            host, port = _netloc
        else:
            host, port = _netloc[0], 80

        _host = self._cache.get(host, None)
        if _host is None:
            _host = socket.gethostbyname(host)
            self._cache.put(host, _host)

        if query:
            path = '{}?{}'.format(path, query)

        if port:
            return '{}://{}:{}{}'.format(scheme, host, port, path)
        else:
            return '{}://{}{}'.format(scheme, host, path)

class Client:
    DEFAULT_PROTOCOL = 'pickle'

    def __init__(self, url, version=None, protocol=DEFAULT_PROTOCOL,
            path=None, netpath='', timeout=None, dnscache=None,
            log=DUMMY_LOG):

        self._url = url
        self._version = version
        self._protocol = protocol # FIXME: check validity

        self._path = path or []
        self._netpath = netpath
        self._timeout = timeout
        self._dnscache = dnscache
        self._log = log

        if not self._dnscache:
            self._dnscache = DNSCache()

    def _get_state(self):
        return dict(url=self._url, version=self._version,
            protocol=self._protocol, path=self._path,
            netpath=self._netpath, timeout=self._timeout,
            dnscache=self._dnscache, log=self._log)

    def _copy(self, **kwargs):
        _kwargs = self._get_state()
        _kwargs.update(kwargs)
        return Client(**_kwargs)

    def _prepare_request(self, post_body, get_params=None):
        headers = {}
        headers[PROTOCOL_HEADER] = self._protocol
        headers[NETPATH_HEADER] = self._netpath

        upath = [self._version] + self._path
        upath = '/'.join(x for x in upath if x)
        url = urljoin(self._url, upath)

        if get_params:
            url = '{}?{}'.format(url, urlencode(get_params))

        url = self._dnscache.map_url(url)
        return url, post_body, headers

    @staticmethod
    def _make_request(url, post_body, headers):
        req = urllib.request.Request(url, data=post_body, headers=headers)
        res = urllib.request.urlopen(req)

        # FIXME: catch exceptions raised and
        # also check the response code
        #if res.status_code != requests.codes.ok:
        #    raise APICallFailed(res.status_code)

        return res.read()

    @staticmethod
    def _deserialize_response(data, protocol):
        proto = PROTOCOLS[protocol]
        r = proto.deserialize(data)

        success = r['success']
        if not success:
            r = Exception(r['message']) # FIXME: raise proper exc
        else:
            r = r['result']

        return r

    @staticmethod
    def _serialize_params(params, protocol):
        proto = PROTOCOLS[protocol]
        data = proto.serialize(params)
        return data

    def __call__(self, *args, **kwargs):
        assert(not args) # FIXME: raise appropriate exception

        if self._path:
            # FIXME: support streaming in both directions
            _kwargs = get_loggable_params(kwargs or {})
            self._log.debug('kwikapi.client.__call__',
                    path=self._path, kwargs=_kwargs,
                    url=self._url, version=self._version, protocol=self._protocol)

            post_body = self._serialize_params(kwargs, self._protocol)
            url, post_body, headers = self._prepare_request(post_body)
            res = self._make_request(url, post_body, headers)
            res = self._deserialize_response(res, self._protocol)

            if isinstance(res, Exception):
                raise res
            else:
                return res
        else:
            return self._copy(**kwargs)

    def __getattr__(self, attr):
        return self._copy(path=self._path + [attr])
