# -*- coding: utf-8 -*
from future.standard_library import install_aliases
install_aliases()

import ast
import abc
import time
import inspect
import traceback
from urllib.parse import parse_qs, urlparse
import typing
import concurrent.futures

from deeputil import Dummy, AttrDict, generate_random_string

from .protocols import PROTOCOLS, DEFAULT_PROTOCOL
from .apidoc import ApiDoc

from .exception import DuplicateAPIFunction, UnknownAPIFunction
from .exception import ProtocolAlreadyExists, UnknownProtocol
from .exception import UnsupportedType, TypeNotSpecified

from .utils import get_loggable_params

DUMMY_LOG = Dummy()

PROTOCOL_HEADER = 'X-KwikAPI-Protocol'
NETPATH_HEADER = 'X-KwikAPI-Netpath'

class Counter:
    def __init__(self, v=0):
        self.v = v

    def increment(self, v):
        self.v += v

    def decrement(self, v):
        self.v -= v

    @property
    def value(self):
        return self.v

class BaseRequest(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.fn_name = None
        self.fn = None
        self.fn_params = None
        self.response = None
        self.protocol = None
        self.id = generate_random_string(length=5).decode('utf8')

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
    def write(self, data, protocol, stream=False):
        self._data = None
        C = Counter

        if not stream:
            t = time.time()
            self._data = protocol.serialize(data)
            return C(len(self._data)), C(time.time() - t)


        n = C(0)
        t = C(0.0)

        def fn():
            for x in data:
                _t = time.time()
                d = protocol.serialize(x)
                t.increment(time.time() - _t)

                s = protocol.get_record_separator()
                n.increment(len(d) + len(s))

                yield d
                yield s

        self._data = fn()

        return n, t

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

    def write(self, data, protocol, stream=False):
        n, t = super().write(data, protocol, stream=stream)

        self.raw_response = self._data

        return n, t

    def flush(self):
        pass

    def close(self):
        pass

class API(object):
    """
    A collection of APIFragments
    """

    # FIXME: need to find a way to not enumerate like this
    # but do it automatically by introspecting the typing module
    TYPING_ANNOTATIONS = [typing.List, typing.Dict, typing.Tuple, typing.Generator, typing.Union, typing.Any,
            typing.NewType, typing.Callable, typing.Mapping, typing.Sequence, typing.TypeVar, typing.Generic,
            typing.Sized, typing.Type, typing.Reversible, typing.SupportsInt, typing.SupportsFloat,
            typing.SupportsComplex, typing.SupportsBytes, typing.SupportsAbs, typing.SupportsRound,
            typing.Container, typing.Set, typing.Iterable, typing.Iterator,typing.Reversible, typing.Sequence]

    ALLOWED_ANNOTATIONS = [bool, int, float, str, list, tuple, dict, Exception, Request] + TYPING_ANNOTATIONS

    THREADPOOL_SIZE = 32

    def __init__(self, default_version=None, id='',
            threadpool=None, threadpool_size=THREADPOOL_SIZE,
            log=DUMMY_LOG):

        self._api_funcs = {}
        self.log = log.bind(api_id=id)
        self.id = id
        self.default_version = default_version

        self.threadpool = None

        if threadpool:
            self.threadpool = threadpool
        else:
            if threadpool_size:
                pass
                #self.threadpool = concurrent.futures.ThreadPoolExecutor(max_workers=threadpool_size)

        self.register(ApiDoc(self._api_funcs), "v1")

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
            _type = annotations.get(arg, None)

            params[arg] = dict(required=True, default=None, type=_type)

        for arg, val in defaults.items():
            _type = annotations.get(arg, None)

            params[arg] = dict(required=False, default=val, type=_type)

        try:
            _return_type = annotations['return']
        except KeyError:
            _return_type = 'None'

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

        for fn_name, fn in inspect.getmembers(api_fragment, predicate=inspect.ismethod):

            # skipping non-public methods
            if fn_name.startswith('_'):
                continue

            fn_info = self._get_fn_info(fn)
            api_funcs[(version, fn_name, namespace)] = dict(obj=fn, info=fn_info)

        return api_funcs

    def _check_type(self, _type):
        for allowed_type in self.ALLOWED_ANNOTATIONS:
            try:
                if _type == type(None) or _type == None:
                    break
                if issubclass(_type, allowed_type):
                    break
            except TypeError:
                try:
                    if _type.__module__ == 'typing':
                        break
                    else:
                        raise UnsupportedType(_type)
                except AttributeError:
                    raise UnsupportedType(_type)
        else:
            raise UnsupportedType(_type)

    def _check_type_info(self, _type):
        try:
            for arg in _type.__args__:
                self._check_type_info(arg)
                self._check_type(arg)
        except (AttributeError, TypeError):
            pass

    def _ensure_type_annotations(self, funcs):
        for fn in funcs.values():
            params = fn['info']['params']

            for arg in params.keys():
                _type = params[arg]['type']
                if not _type:
                    raise TypeNotSpecified(arg)

                self._check_type(_type)
                self._check_type_info(_type)

            return_type = fn['info']['return_type']
            if return_type == 'None':
                raise TypeNotSpecified('return')
            else:
                self._check_type(return_type)
                self._check_type_info(return_type)

    def _ensure_no_overlap(self, funcs):
        for (version, fn_name, namespace), _ in funcs.items():
            if (version, fn_name) in self._api_funcs:
                raise DuplicateAPIFunction(version, fn_name)

    def register(self, api_fragment, version, namespace=None):
        funcs = self._discover_funcs(api_fragment, version, namespace)
        self._ensure_type_annotations(funcs)
        self._ensure_no_overlap(funcs)
        self._api_funcs.update(funcs)
        if not getattr(api_fragment, 'log', None):
            api_fragment.log = self.log

    def isversion(self, version):
        for key in self._api_funcs:
            if version == key[0]:
                return True

    def has_api_fn(self, fn_name, version, namespace):
        return (version, fn_name, namespace) in self._api_funcs

    def get_default_version(self):
        return self.default_version

    def get_api_fn(self, fn_name, version, namespace):
        return self._api_funcs[(version, fn_name, namespace)]

class BaseRequestHandler(object):
    PROTOCOLS = PROTOCOLS
    DEFAULT_PROTOCOL = DEFAULT_PROTOCOL

    def __init__(self, api,
            default_version=None, default_protocol=DEFAULT_PROTOCOL,
            log=DUMMY_LOG):
        self.api = api
        self.default_version = default_version
        self.default_protocol = default_protocol
        self.log = log

        self._protocols = self.PROTOCOLS

    def set_default_protocol(self, default_proto=DEFAULT_PROTOCOL):
        if protocol not in self.PROTOCOLS:
            raise UnknownProtocol(protocol)

        self.default_protocol = protocol

    def register_protocol(self, protocol, update=True):
        name = protocol.get_name()
        if not update and name in self._protocols:
            raise ProtocolAlreadyExists(protocol)
        self._protocols[name] = protocol

    def _resolve_call_info(self, request):
        r = AttrDict()
        r.time_deserialize = 0.0
        r.namespace = None
        r.function = None
        r.method = 'GET'

        urlp = urlparse(request.url)
        path_parts = urlp.path.lstrip('/').split('/')
        path_parts = path_parts[1:] # ignore "/api/" part

        version = path_parts[0]
        fn_name = path_parts[-1]
        path_parts = path_parts[:-1]
        r.function = fn_name

        if self.api.isversion(version):
            namespace = '/'.join(path_parts[1:])
        else:
            version = self.api.get_default_version()
            namespace = '/'.join(path_parts)

        namespace = namespace if namespace else None
        r.namespace = namespace or ''

        request.netpath = '{netpath}=>{id}_{reqid}({namespace}/{function})'.format(
            netpath=request.headers.get(NETPATH_HEADER, ''),
            id=self.api.id,
            reqid=request.id,
            namespace=r.namespace,
            function=fn_name,
        )

        request.log = self.log.bind(__netpath=request.netpath)

        query_string = urlp.query

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
            except: # FIXME: bald except!
                param_vals[key] = val

        if request.method == 'POST':
            r.method = 'POST'
            protocol = self._find_request_protocol(request)

            for stream_param in params:
                try:
                    if params[stream_param]['type'] == typing.Generator:
                        stream_param = stream_param
                        break
                except AttributeError:
                    continue
            else:
                stream_param = None

            # FIXME: request.body: what type is it supposed to be? byte string or file like?
            if not stream_param:
                t = time.time()
                p = protocol.deserialize(request.body)
                r.deserialize_time = time.time() - t

                param_vals.update(protocol.deserialize(request.body))
            else:
                param_vals[stream_param] = protocol.deserialize_stream(request.body)

        if info.get('req', None):
            param_vals['req'] = request

        request.fn_params = param_vals

        return r

    def _find_request_protocol(self, request):
        protocol = request.headers.get(PROTOCOL_HEADER, self.default_protocol)
        return self.PROTOCOLS[protocol]

    def handle_request(self, request):
        #import pdb; pdb.set_trace()
        protocol = self._find_request_protocol(request)
        request.protocol = protocol.get_name()
        response = request.response
        response.headers['Content-Type'] = protocol.get_mime_type()

        try:
            rinfo = self._resolve_call_info(request)

            # invoke the API function
            tcompute = time.time()
            result = request.fn(**request.fn_params)
            tcompute = time.time() - tcompute

            # Serialize the response
            if request.fn.__func__.func_info['gives_stream']:
                n, t = response.write(result, protocol, stream=True)
            else:
                n, t = response.write(dict(success=True, result=result), protocol)

            request.log.info('kwikapi.handle_request',
                    function=rinfo.function, namespace=rinfo.namespace,
                    method=rinfo.method, compute_time=tcompute, serialize_time=t.value,
                    deserialize_time=rinfo.time_deserialize,
                    __params=get_loggable_params(request.fn_params or {}),
                    protocol=request.protocol, type='metric')

        except Exception as e:
            message = e.message if hasattr(e, 'message') else str(e)
            message = '[(%s) %s: %s]' % (self.api.id, e.__class__.__name__, message)

            self.log.exception('handle_request_error', message=message)
            response.write(dict(success=False, message=message), protocol)

        response.flush()
        response.close()

        return response.raw_response
