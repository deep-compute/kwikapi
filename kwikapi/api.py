# -*- coding: utf-8 -*
import sys
import ast
import abc
import inspect
import json
import msgpack
import traceback
import importlib
from itertools import chain
from urllib.parse import parse_qs

from deeputil import Dummy

DUMMY_LOG = Dummy()

class BaseProtocol(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_name(self):
        pass

    @abc.abstractmethod
    def serialize(self, data):
        pass

    @abc.abstractmethod
    def deserialize(self, data):
        pass

    @abc.abstractmethod
    def deserialize_stream(self, data):
        pass

    @abc.abstractmethod
    def get_record_separator(self):
        pass

    @abc.abstractmethod
    def get_mime_type(self):
        pass

class JsonProtocol(BaseProtocol):

    @staticmethod
    def get_name():
        return 'json'

    @staticmethod
    def serialize(data):
        return json.dumps(data)

    @staticmethod
    def deserialize(data):
        return json.loads(data.decode('utf-8'))

    @classmethod
    def deserialize_stream(cls, data):
        for line in data:
            yield cls.deserialize(line)

    @staticmethod
    def get_record_separator():
        return '\n'

    @staticmethod
    def get_mime_type():
        return 'application/json'

class MessagePackProtocol(BaseProtocol):

    @staticmethod
    def get_name():
        return 'messagepack'

    @staticmethod
    def serialize(data):
        return msgpack.packb(data)

    @staticmethod
    def deserialize(data):
        return {k.decode('utf8'): v for k, v in msgpack.unpackb(data).items()}

    @classmethod
    def deserialize_stream(cls, data):
        unpacker = msgpack.Unpacker(data)
        for item in unpacker:
            yield item

    @staticmethod
    def get_record_separator():
        return ''

    @staticmethod
    def get_mime_type():
        return 'application/x-msgpack'

class BaseRequest(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.fn_name = None
        self.fn = None
        self.fn_params = None
        self.response = None

    @abc.abstractproperty
    def url(self):
        pass

    @abc.abstractproperty
    def method(self):
        pass

    @abc.abstractproperty
    def body(self):
        pass

    @abc.abstractproperty
    def headers(self):
        pass

Request = BaseRequest

class BaseResponse(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.raw_response = None

    @abc.abstractmethod
    def write(self, data, proto, stream=False):
        self._data = None

        if not stream:
            self._data = proto.serialize(data)
            return

        def fn():
            for x in data:
                yield proto.serialize(x)
                yield proto.get_record_separator()

        self._data = fn()

    @abc.abstractmethod
    def flush(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass

class MockRequest(BaseRequest):

    def __init__(self, **kwargs):
        super().__init__()
        self._request = dict(method='GET', body='', headers={})
        self._request.update(kwargs)
        self.response = MockResponse()

    @property
    def url(self):
        return self._request['url']

    @property
    def method(self):
        return self._request['method']

    @property
    def body(self):
        return self._request['body']

    @property
    def headers(self):
        return self._request['headers']

class MockResponse(BaseResponse):
    def __init__(self):
        super().__init__()
        self.headers = {}
        self.raw_response = None

    def write(self, data, proto, stream=False):
        super().write(data, proto, stream=stream)

        self.raw_response = self._data

    def flush(self):
        pass

    def close(self):
        pass

class BaseException(Exception):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def message(self):
        pass

class DuplicateAPIFunction(BaseException):
    def __init__(self, version, api_fn):
        self.version = version
        self.api_fn = api_fn

    @property
    def message(self):
        return '"%s" API function already exists in the version "%s"' % (self.api_fn, self.version)

class UnknownAPIFunction(BaseException):
    def __init__(self, api_fn_name):
        self.fn_name = api_fn_name

    @property
    def message(self):
        return 'Unknown API Function: "%s"' % self.fn_name

class ProtocolAlreadyExists(BaseException):
    def __init__(self, proto):
        self.proto = proto

    @property
    def message(self):
        return '"%s" is already exists' % self.proto

class UnknownProtocol(BaseException):
    def __init__(self, proto):
        self.proto = proto

    @property
    def message(self):
        return '"%s" protocol is not exist to make it default' % self.proto

class UnknownVersion(BaseException):
    def __init__(self, version):
        self.version = version

    @property
    def message(self):
        return '"%s" There are no methods associated with this version' % self.version

class API(object):
    """
    A collection of APIFragments
    """

    def __init__(self, log=DUMMY_LOG, default_version=None):
        self._api_funcs = {}
        self.log = log
        self.default_version = default_version

    def _get_fn_info(self, fn):
        argspec = inspect.getfullargspec(fn)
        args, defaults, annotations = argspec.args, argspec.defaults, \
                argspec.annotations

        for value in annotations.values():
            if value == Request:
                N_PREFIX_ARGS = 2
                _req = value
                break
        else:
            N_PREFIX_ARGS = 1

        defaults = defaults if defaults else ()
        n_req_args = len(args) - len(defaults)
        defaults = dict(zip(args[n_req_args:], defaults))
        args = args[N_PREFIX_ARGS:n_req_args]

        params = {}
        for arg in args:
            params[arg] = dict(required=True, default=None)

        for arg, val in defaults.items():
            params[arg] = dict(required=False, default=val)

        info = dict(
            doc=fn.__doc__,
            params=params,
            gives_stream=inspect.isgeneratorfunction(fn)
        )

        if N_PREFIX_ARGS == 2:
            info['req'] = _req

        fn.__func__.func_info = info
        return info

    def _discover_funcs(self, api_fragment, version, namespace):
        api_funcs = {}

        for fn_name, fn in inspect.getmembers(api_fragment,
                                predicate=inspect.ismethod):

            # skipping non-public methods
            if fn_name.startswith('_'):
                continue

            fn_info = self._get_fn_info(fn)
            api_funcs[(version, fn_name, namespace)] = dict(obj=fn, info=fn_info)

        return api_funcs

    def _ensure_no_overlap(self, api_fragment_funcs):
        for (version, fn_name, namespace), info in api_fragment_funcs.items():
            if (version, fn_name) in self._api_funcs:
                raise DuplicateAPIFunction(version, fn_name)

    def register(self, api_fragment, version, namespace=None):
        funcs = self._discover_funcs(api_fragment, version, namespace)
        self._ensure_no_overlap(funcs)
        self._api_funcs.update(funcs)
        api_fragment.log = self.log

    def isversion(self, version):
        for key in self._api_funcs.keys():
            if version in key:
                return True

    def doc(self, version=None, namespace=None):
        versions = {}
        for (ver, fn_name, namespace), fninfo in self._api_funcs.items():
            vfns = versions.get(ver, {})
            vfns[fn_name] = fninfo['info']
            versions[ver] = vfns

        if version:
            return versions[version]

        return versions

    def has_api_fn(self, fn_name, version, namespace):
        return (version, fn_name, namespace) in self._api_funcs

    def get_default_version(self):
        return self.default_version

    def get_api_fn(self, fn_name, version, namespace):
        return self._api_funcs[(version, fn_name, namespace)]

class BaseRequestHandler(object):

    PROTOCOLS = dict((p.get_name(), p) for p in [
        JsonProtocol,
        MessagePackProtocol,
    ])

    DEFAULT_PROTOCOL = JsonProtocol.get_name()

    def __init__(self, api, default_version=None):
        self.api = api
        self.default_version = default_version
        self._protocols = dict(self.PROTOCOLS)

    def set_default_protocol(self, default_proto=JsonProtocol.get_name()):
        self.DEFAULT_PROTOCOL = default_proto

        if self.DEFAULT_PROTOCOL not in self.PROTOCOLS:
            raise UnknownProtocol(self.DEFAULT_PROTOCOL)

    def register_protocol(self, proto, update=True):
        name = proto.get_name()
        if not update and name in self._protocols:
            raise ProtocolAlreadyExists(proto)
        self._protocols[name] = proto

    STREAMPARAM_HEADER = 'X-KwikAPI-Streamparam'
    def _resolve_call_info(self, request):

        url_components = request.url.split('/')
        version = url_components[2]

        if 'apidoc' in url_components:
            if self.api.isversion(version):
                return self.api.doc(version)
            elif 'apidoc' == url_components[2]:
                return self.api.doc(self.api.get_default_version())
            else:
                raise UnknownVersion(version)

        namespace = ''
        if self.api.isversion(version):
            for namespaceparts in url_components[3:len(url_components)-1]:
                namespace = namespace + namespaceparts + '/'
        else:
            version = self.api.get_default_version()

            for namespaceparts in url_components[2:len(url_components)-1]:
                namespace = namespace + namespaceparts + '/'

        if namespace == '':
            namespace = None
        else:
            namespace = namespace.rstrip('/')

        fn_name = url_components[len(url_components)-1]

        if '?' in fn_name:

            fn_name = fn_name.split('?')

            query_string = fn_name[1]
            fn_name = fn_name[0]

        else:
            query_string = ''

        request.fn_name = fn_name
        if not self.api.has_api_fn(fn_name, version, namespace):
            raise UnknownAPIFunction(fn_name)

        fninfo = self.api.get_api_fn(fn_name, version, namespace)
        request.fn = fninfo['obj']
        info = fninfo['info']
        params = info['params']

        # parse function arguments from the request
        param_vals = dict((k, v[0]) \
            for k, v in parse_qs(query_string).items())

        for key, val in param_vals.items():
            try:
                param_vals[key] = ast.literal_eval(val)
            except:
                param_vals[key] = val

        if request.method == 'POST':
            proto = self._find_request_protocol(request)
            stream_param = request.headers.get(self.STREAMPARAM_HEADER, None)

            if not stream_param:
                try:
                    param_vals.update(proto.deserialize(request.body.read()))
                except AttributeError:
                    param_vals.update(proto.deserialize(request.body))
            else:
                param_vals[stream_param] = proto.deserialize_stream(request.body)

        if info.get('req', None):
            param_vals['req'] = request

        request.fn_params = param_vals

        return request

    PROTOCOL_HEADER = 'X-KwikAPI-Protocol'
    def _find_request_protocol(self, request):
        proto = request.headers.get(self.PROTOCOL_HEADER, self.DEFAULT_PROTOCOL)
        return self.PROTOCOLS[proto]

    def handle_request(self, request):

        proto = self._find_request_protocol(request)
        response = request.response
        response.headers['Content-Type'] = proto.get_mime_type()

        response_data = ''

        try:
            result = self._resolve_call_info(request)

            if request.fn_params:

                # invoke the API function
                result = request.fn(**request.fn_params)

                # Serialize the response
                if request.fn.__func__.func_info['gives_stream']:
                    response.write(result, proto, stream=True)

                else:
                    response.write(dict(
                        success = True,
                        result = result,
                    ), proto)

            else:
                response.write(dict(
                    success = True,
                    result = result,
                ), proto)

        except Exception as e:
            message = e.message if hasattr(e, 'message') else str(e)
            message = '%s: %s' % (e.__class__.__name__, message)

            # TODO: remove after we can log this to logger
            print(traceback.print_tb(e.__traceback__))

            response.write(dict(
                success = False,
                message = message
            ), proto)

        response.flush()
        response.close()

        return response.raw_response
