from urllib.parse import urljoin

import requests
from deeputil import Dummy

from .protocols import PROTOCOLS
from .exception import APICallFailed
from .api import PROTOCOL_HEADER, NETPATH_HEADER

DUMMY_LOG = Dummy()

class Client:
    DEFAULT_PROTOCOL = 'messagepack'

    def __init__(self, url, version=None,
            session=None, protocol=DEFAULT_PROTOCOL,
            path=None, netpath='', log=DUMMY_LOG):

        self._url = url
        self._version = version
        # FIXME: how to configure session params correctly for high perf?
        self._session = session if session else requests.Session()
        self._protocol = protocol # FIXME: check validity

        self._path = path or []
        self._netpath = netpath
        self._log = log

    def _get_state(self):
        return dict(url=self._url, version=self._version,
            session=self._session, protocol=self._protocol,
            path=self._path, netpath=self._netpath, log=self._log)

    def _copy(self, **kwargs):
        _kwargs = self._get_state()
        _kwargs.update(kwargs)
        return Client(**_kwargs)

    def _make_api_call(self, **kwargs):
        # FIXME: support streaming in both directions
        self._log.debug('kwikapi.client._make_api_call',
                path=self._path, kwargs=kwargs, url=self._url,
                version=self._version, protocol=self._protocol)

        headers = {}
        headers[PROTOCOL_HEADER] = self._protocol
        headers[NETPATH_HEADER] = self._netpath

        proto = PROTOCOLS[self._protocol]
        data = proto.serialize(kwargs)

        upath = [self._version] + self._path
        upath = '/'.join(x for x in upath if x)
        url = urljoin(self._url, upath)

        res = self._session.post(url, data=data, headers=headers)
        if res.status_code != requests.codes.ok:
            raise APICallFailed(res.status_code)

        resp_data = proto.deserialize(res.content)
        return resp_data

    def __call__(self, *args, **kwargs):
        assert(not args) # FIXME: raise appropriate exception

        if self._path:
            r = self._make_api_call(**kwargs)
            success = r['success']
            if not success:
                raise Exception(r['message']) # FIXME: raise proper exc
            else:
                return r['result']
        else:
            return self._copy(**kwargs)

    def __getattr__(self, attr):
        return self._copy(path=self._path + [attr])
