# -*- coding: utf-8 -*
import abc

class BaseException(Exception):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def message(self):
        pass

class BaseServerException(BaseException):
    pass

class BaseClientException(BaseException):
    pass

class DuplicateAPIFunction(BaseServerException):
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

class ProtocolAlreadyExists(BaseServerException):
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

class UnsupportedType(BaseServerException):
    def __init__(self, _type):
        self._type = _type

    @property
    def message(self):
        return '"%s" type is not supported' % self._type

class TypeNotSpecified(BaseServerException):
    def __init__(self, arg):
        self.arg = arg

    @property
    def message(self):
        return 'Please specify type for the argument "%s"' % (self.arg)

class UnknownVersionOrNamespace(BaseException):
    def __init__(self, arg):
        self.arg = arg

    @property
    def message(self):
        return 'No methods associated with this version "%s" or namespace "%s".' % (self.arg[0], self.arg[1])

class StreamingNotSupported(BaseException):
    def __init__(self, proto):
        self.proto = proto

    @property
    def message(self):
        return 'Streaming not supported for "%s" protocol' % self.proto

class APICallFailed(BaseClientException):
    def __init__(self, code):
        self.code = code

    @property
    def message(self):
        return 'HTTP Error code: %d' % self.code
