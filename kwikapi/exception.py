# -*- coding: utf-8 -*
import abc


class ResponseError(Exception):
    def __init__(self, response):
        super(ResponseError, self).__init__(response)
        self.message = response['message']
        self.code = response['code']
        self.callee_error = response['error']


class BaseException(Exception):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def message(self):
        pass

    @abc.abstractmethod
    def code(self):
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

    @property
    def code(self):
        return 50001


class UnknownAPIFunction(BaseException):
    def __init__(self, api_fn_name):
        self.fn_name = api_fn_name

    @property
    def message(self):
        return 'Unknown API Function: "%s"' % self.fn_name

    @property
    def code(self):
        return 50002


class ProtocolAlreadyExists(BaseServerException):
    def __init__(self, proto):
        self.proto = proto

    @property
    def message(self):
        return '"%s" is already exists' % self.proto

    @property
    def code(self):
        return 50003


class UnknownProtocol(BaseException):
    def __init__(self, proto):
        self.proto = proto

    @property
    def message(self):
        return '"%s" protocol is not exist to make it default' % self.proto

    @property
    def code(self):
        return 50004


class UnknownVersion(BaseException):
    def __init__(self, version):
        self.version = version

    @property
    def message(self):
        return '"%s" There are no methods associated with this version' % self.version

    @property
    def code(self):
        return 50005


class UnsupportedType(BaseServerException):
    def __init__(self, _type):
        self._type = _type

    @property
    def message(self):
        return '"%s" type is not supported' % self._type

    @property
    def code(self):
        return 50006


class TypeNotSpecified(BaseServerException):
    def __init__(self, arg):
        self.arg = arg

    @property
    def message(self):
        return 'Please specify type for the argument "%s"' % (self.arg)

    @property
    def code(self):
        return 50007



class UnknownVersionOrNamespace(BaseException):
    def __init__(self, arg):
        self.arg = arg

    @property
    def message(self):
        return 'No methods associated with this version "%s" or namespace "%s".' % (self.arg[0], self.arg[1])

    @property
    def code(self):
        return 50008


class StreamingNotSupported(BaseException):
    def __init__(self, proto):
        self.proto = proto

    @property
    def message(self):
        return 'Streaming not supported for "%s" protocol' % self.proto

    @property
    def code(self):
        return 50009


class KeywordArgumentError(BaseException):
    def __init__(self, error_message):
        self.error_message = error_message

    @property
    def message(self):
        return self.error_message

    @property
    def code(self):
        return 50010

class AuthenticationError(BaseException):
    def __init__(self, error_type):
        self._type = error_type

    @property
    def message(self):
        return 'Invalid auth type: %s' % self._type

    @property
    def code(self):
        return 50011


class NonKeywordArgumentsError(BaseException):
    def __init__(self, non_keyword_args):
        self.non_keyword_args = ','.join(map(str, non_keyword_args))
        self.error_value = '[() %s]' % (self.__class__.__name__)
        response_message = dict(message=self.message,code=self.code,
                                error=self.error_value)
        super(NonKeywordArgumentsError, self).__init__(response_message)


    @property
    def message(self):
        return 'Found non keyword arguments: %s' % self.non_keyword_args

    @property
    def code(self):
        return 50012
