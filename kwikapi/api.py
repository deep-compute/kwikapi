# -*- coding: utf-8 -*
import ast
import re
import abc
import inspect
import json
import msgpack
import traceback
import importlib
from itertools import chain
from urllib.parse import parse_qs

#from deeputil import Dummy

#DUMMY_LOG = Dummy()

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
        return json.loads(data)

    @classmethod
    def deserialize_stream(cls, data):
        for line in data:
            yield cls.deserialize(line.decode('utf8'))

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
        return msgpack.unpackb(data)

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

class MockRequest(object):
    def __init__(self, **kwargs):
        defaults = dict(method='GET', body='', headers={})
        defaults.update(kwargs)
        self._data = defaults
        self.response = MockResponse()

    def __getattr__(self, attr):
        return self._data[attr]

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

class TypeNotSpecified(BaseException):
    def __init__(self, arg):
        self.arg = arg

    @property
    def message(self):
        return 'Please specify type for the argument "%s"' % (self.arg)

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

class NotExpectedType(BaseException):
    def __init__(self, _type):
        self._type = _type

    @property
    def message(self):
        return '"%s" is not expected type' % self._type

class ProtocolAlreadyExists(BaseException):
    def __init__(self, proto):
        self.proto = proto

    @property
    def message(self):
        return '"%s" is already exists' % self.proto

class API(object):
    """
    A collection of APIFragments
    """

    # FIXME: log should not be compulsory. Please use deeputil.Dummy as default value for log
    def __init__(self, log, default_version=None):
        self._api_funcs = {}
        self.log = log
        self.default_version = default_version

    # Number of positional arguments in an API function
    # that need to be ignored when building the API func doc
    # i.e. For "self" and "request" (that are present in every
    # API function signature.

    def _get_fn_info(self, fn):
        argspec = inspect.getfullargspec(fn)
        args, defaults, annotations = argspec.args, argspec.defaults, \
                argspec.annotations

        if 'req' in args:
            N_PREFIX_ARGS = 2
            _req = args[1]
        else:
            N_PREFIX_ARGS = 1

        defaults = defaults if defaults else ()
        n_req_args = len(args) - len(defaults)
        defaults = dict(zip(args[n_req_args:], defaults))
        args = args[N_PREFIX_ARGS:n_req_args]

        params = {}

        for arg in args:
            _type = annotations.get(arg, None)
            if _type:
                if not _type.__name__ == 'Union':
                    _type = _type.__name__
            else:
                raise TypeNotSpecified(arg)

            params[arg] = dict(required=True, default=None, type=_type)

        _return_type = annotations.get('return', None)

        if isinstance(_return_type, list):
            for index, _type in enumerate(_return_type):
                _return_type[index] = _type.__name__
        elif _return_type:
            if not (_return_type.__name__ == 'Union'):
                _return_type = _return_type.__name__

        for arg, val in defaults.items():
            params[arg] = dict(required=False, default=val, type=_type)

        info = dict(
            doc=fn.__doc__,
            params=params,
            return_type=_return_type,
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

    def has_api_fn(self, fn_name, version, namespace):
        return (version, fn_name, namespace) in self._api_funcs

    def get_default_version(self):
        return self.default_version

    def get_api_fn(self, fn_name, version, namespace):
        return self._api_funcs[(version, fn_name, namespace)]

class TempVersionHolder(object):

    def __init__(self, version, api):
        self.version = version
        self.api = api

    def __getattr__(self, func):
        return self.api.get_api_fn(func, self.version)['obj']

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

    def register_protocol(self, proto, update=True):
        name = proto.get_name()
        if not update and name in self._protocols:
            raise ProtocolAlreadyExists(proto)
        self._protocols[name] = proto

    def _convert_type(self, value, type_):
        try:
            if type_.__name__ == 'Union':
                try:
                    for _type in type_.__union_params__:
                        if _type == str:
                            continue
                        value = _type(value)

                except (ValueError, TypeError) as e:
                    pass

                if type(value) in type_.__union_params__:
                    return value
                else:
                    raise NotExpectedType(type(value))

        except AttributeError:
            module = importlib.import_module('builtins')
            cls = getattr(module, type_)

            return cls(value)

    STREAMPARAM_HEADER = 'HTTP_X_KWIKAPI_STREAMPARAM'
    def _resolve_call_info(self, request):

        url_components = request.url.split('/')

        version = url_components[2]
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
        self.return_type = info['return_type']

        # parse function arguments from the request
        param_vals = dict((k, v[0]) \
            for k, v in parse_qs(query_string).items())

        for key, val in param_vals.items():
            if ('[' in val and ']' in val) or ('{' in val and '}' in val) or ('(' in val and ')' in val):
                param_vals[key] = ast.literal_eval(val)

        for key, val in params.items():
            if key not in param_vals:
                continue

            param_vals[key] = self._convert_type(param_vals[key], val['type'])

        if request.method == 'POST':
            proto = self._find_request_protocol(request)
            stream_param = request.headers.get(self.STREAMPARAM_HEADER, None)

            if not stream_param:
                param_vals.update(proto.deserialize(request.body.read()))
            else:
                param_vals[stream_param] = proto.deserialize_stream(request.body)

        if info.get('req', None):
            param_vals['req'] = info.get('req')

        request.fn_params = param_vals

        # check validity of params and do type conversion (TODO)
        # 3. Perform type conversion

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
            self._resolve_call_info(request)

            # invoke the API function
            result = request.fn(**request.fn_params)

            if isinstance(result, list) and isinstance(self.return_type, list):
                for index, (_value, _type) in enumerate(zip(result, self.return_type)):
                    result[index] = self._convert_type(_value, _type)
            else:
                result = self._convert_type(result, self.return_type)

            # Serialize the response
            if request.fn.__func__.func_info['gives_stream']:
                response.write(result, proto, stream=True)

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

    # FIXME: Why these methods
    def _get_tmp_version_holder(self, version):
        return TempVersionHolder(version, self.api)

    def __getitem__(self, version):
        return self._get_tmp_version_holder(version)

    def __getattr__(self, fn_name):
        return getattr(self._get_tmp_version_holder(self.default_version), fn_name)
