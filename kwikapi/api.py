# -*- coding: utf-8 -*

import re
import abc
import inspect
import json
import msgpack
import traceback
import rapidjson
import importlib
import builtins
from itertools import chain
from structlog import get_logger

from django.http import HttpResponse
from django.http import StreamingHttpResponse
from urllib.parse import parse_qs
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class BaseRequest(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.fn_name = None
        self.fn = None
        self.fn_params = None

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

class BaseResponse(object):
    __metaclass__ = abc.ABCMeta

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

class DjangoRequest(BaseRequest):
    def __init__(self, request):
        super().__init__()
        self.raw_request = self._request = request
        self.response = DjangoResponse(self._request)

    @property
    def url(self):
        return self._request.get_full_path()

    @property
    def method(self):
        return self._request.method

    @property
    def body(self):
        return self._request

    @property
    def headers(self):
        return self._request.META

class DjangoResponse(BaseResponse):
    def __init__(self, request):
        self._request = request
        self.raw_response = self._response = None
        self.headers = {}

    def write(self, data, proto, stream=False):
        super().write(data, proto, stream=stream)

        data = self._data
        r = StreamingHttpResponse(data) if stream else HttpResponse(data)

        for k, v in self.headers.items():
            r[k] = v
        self.headers = r

        self.raw_response = self._response = r

    def flush(self):
        self._response.flush()

    def close(self):
        # Django response doesn't support a close method
        # so we do nothing here.
        pass

class BaseException(Exception):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def message(self):
        pass

class UnknownRequestType(BaseException):
    def __init__(self, request_type):
        self.request_type = request_type

    @property
    def message(self):
        return 'Unknown request type "%s"' % self.request_type

class DuplicateAPIFunction(BaseException):
    def __init__(self, version, api_fn):
        self.versiion = version
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

class APIFragment(object):
    """
    #TODO: Improve this docstring

    A collection of functions grouped under a version string.
    Any method in the class that does not start with an `_` is
    considered an APIFragment method.
    All APIFragment methods must accept "request" as their first parameter.
    e.g.
    def add(self, request, a, b):
        return a + b
    """
    pass

class TempVersionHolder(object):

    def __init__(self, version, api_funcs):
        self.version = version
        self.api_funcs = api_funcs

    def __getattr__(self, func):
        return self.api_funcs[(self.version, func)]['obj']

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

        #TODO Analyse rapidjson to work for interger keys
        # d = rapidjson.dumps({1: 10})
        #return rapidjson.dumps(data)

    @staticmethod
    def deserialize(data):
        return json.loads(data)
        #TODO Analyse rapid json
        #return rapidjson.loads(data)

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

import coloredlogs

class API(object):
    """
    A collection of APIFragments
    """

    PROTOCOLS = dict((p.get_name(), p) for p in [
        JsonProtocol,
        MessagePackProtocol,
    ])

    DEFAULT_PROTOCOL = JsonProtocol.get_name()
    #DEFAULT_PROTOCOL = MessagePackProtocol.get_name()

    def __init__(self, log, default_version=None):
        coloredlogs.install()
        self._api_funcs = {}
        self.log = log
        self.default_version = default_version

    # Number of positional arguments in an API function
    # that need to be ignored when building the API func doc
    # i.e. For "self" and "request" (that are present in every
    # API function signature.
    N_PREFIX_ARGS = 2

    def _get_fn_info(self, fn):
        #args, varargs, varkw, defaults = inspect.getargspec(fn)
        argspec = inspect.getfullargspec(fn)
        args, defaults, annotations = argspec.args, argspec.defaults, \
                argspec.annotations

        defaults = defaults if defaults else ()
        n_req_args = len(args) - len(defaults)
        defaults = dict(zip(args[n_req_args:], defaults))
        args = args[self.N_PREFIX_ARGS:n_req_args]

        params = {}

        for arg in args:
            _type = annotations.get(arg, None)
            _type = _type.__name__ if _type else None

            params[arg] = dict(required=True, default=None, type=_type)

        for arg, val in defaults.items():
            params[arg] = dict(required=False, default=val, type=_type)

        info = dict(
            doc=fn.__doc__,
            params=params,
            gives_stream=inspect.isgeneratorfunction(fn)
        )

        fn.__func__.func_info = info
        return info

    def _discover_funcs(self, api_fragment, version):
        api_funcs = {}

        for fn_name, fn in inspect.getmembers(api_fragment,
                                predicate=inspect.ismethod):

            # skipping non-public methods
            if fn_name.startswith('_'):
                continue

            fn_info = self._get_fn_info(fn)
            api_funcs[(version, fn_name)] = dict(obj=fn, info=fn_info)

        return api_funcs

    def _ensure_no_overlap(self, api_fragment_funcs):
        for (version, fn_name), info in api_fragment_funcs.items():
            if (version, fn_name) in self._api_funcs:
                raise DuplicateAPIFunction(version, fn_name)

    def register(self, api_fragment, version):
        funcs = self._discover_funcs(api_fragment, version)
        self._ensure_no_overlap(funcs)
        self._api_funcs.update(funcs)
        api_fragment.log = self.log

    def doc(self, version=None):
        versions = {}
        for (ver, fn_name), fninfo in self._api_funcs.items():
            vfns = versions.get(ver, {})
            vfns[fn_name] = fninfo['info']
            versions[ver] = vfns

        if version:
            return versions[version]

        return versions

    def _encapsulate_raw_request(self, request, request_type):

        if request_type == 'django':
            return DjangoRequest(request)

        else:
            raise UnknownRequestType(request_type)

    STREAMPARAM_HEADER = 'HTTP_X_KWIKAPI_STREAMPARAM'

    def convert_type(self, value, type_):

        try:
            # Check if it's a builtin type
            module = importlib.import_module('builtins')
            cls = getattr(module, type_)
        except AttributeError:
            # if not, separate module and class
            module, type_ = type_.rsplit(".", 1)
            module = importlib.import_module(module)
            cls = getattr(module, type_)
        return cls(value)

    def _resolve_call_info(self, request):

        if '?' in request.url:
            version, fn_name, query_string = re.findall(r'^/api/(.*)/(.*)\?(.*)', request.url)[0]
        else:
            version, fn_name = re.findall(r'^/api/(.*)/(.*)', request.url)[0]
            query_string = ''

        #version, fn_name, query_string = re.findall(r'^/api/([^/]*?)/([^/]*?)\?(.*)', request.url)[0]
        request.fn_name = fn_name
        if (version, fn_name) not in self._api_funcs:
            raise UnknownAPIFunction(fn_name)

        fninfo = self._api_funcs[(version, fn_name)]
        request.fn = fninfo['obj']
        info = fninfo['info']
        params = info['params']

        # parse function arguments from the request
        param_vals = dict((k, v[0]) \
            for k, v in parse_qs(query_string).items())

        for key, val in params.items():
            if key not in param_vals:
                continue

            param_vals[key] = self.convert_type(param_vals[key], val['type'])

        if request.method == 'POST':
            proto = self._find_request_protocol(request)
            stream_param = request.headers.get(self.STREAMPARAM_HEADER, None)

            if not stream_param:
                param_vals.update(proto.deserialize(request.body.read()))
            else:
                param_vals[stream_param] = proto.deserialize_stream(request.body)

        param_vals['request'] = request
        request.fn_params = param_vals

        # check validity of params and do type conversion (TODO)
        # 3. Perform type conversion

        return request

    PROTOCOL_HEADER = 'X-KwikAPI-Protocol'
    def _find_request_protocol(self, request):
        proto = request.headers.get(self.PROTOCOL_HEADER, self.DEFAULT_PROTOCOL)
        return self.PROTOCOLS[proto]

    @method_decorator(csrf_exempt)
    def handle_request(self, request, request_type):

        request = self._encapsulate_raw_request(request, request_type.lower().strip())
        proto = self._find_request_protocol(request)
        response = request.response
        response.headers['Content-Type'] = proto.get_mime_type()

        response_data = ''

        try:
            self._resolve_call_info(request)

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

    def _get_tmp_version_holder(self, version):
        return TempVersionHolder(version, self._api_funcs)

    def __getitem__(self, version):
        return self._get_tmp_version_holder(version)

    def __getattr__(self, fn_name):
        return getattr(self._get_tmp_version_holder(self.default_version), fn_name)
