import ast
import abc
import json
import pickle
import msgpack
import numpy as np

from .exception import StreamingNotSupported
from .utils import walk_data_structure, liteval

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

    @staticmethod
    def should_wrap():
        '''
        While returning the response the,
        kwikapi will wrap the response as -
        {success: value, result: value}

        This method, can used in above situation,
        if no wrapping is required,
        override this method in the protocol class.
        '''
        return True

class JsonProtocol(BaseProtocol):

    @staticmethod
    def get_name():
        return 'json'

    @staticmethod
    def serialize(data):
        data = json.dumps(data)

        return data.encode('utf-8')

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
        return msgpack.unpackb(data, encoding="utf-8")

    @classmethod
    def deserialize_stream(cls, data):
        unpacker = msgpack.Unpacker(data, encoding="utf-8")
        for item in unpacker:
            yield item

    @staticmethod
    def get_record_separator():
        return ''

    @staticmethod
    def get_mime_type():
        return 'application/x-msgpack'

class PickleProtocol(BaseProtocol):

    @staticmethod
    def get_name():
        return 'pickle'

    @staticmethod
    def serialize(data):
        return pickle.dumps(data)

    @staticmethod
    def deserialize(data):
        return pickle.loads(data)

    @classmethod
    def deserialize_stream(cls, data):
        raise StreamingNotSupported(cls.get_name())

    @classmethod
    def get_record_separator(cls):
        raise StreamingNotSupported(cls.get_name())

    @staticmethod
    def get_mime_type():
        return 'application/pickle'

class RawProtocol(BaseProtocol):
    @staticmethod
    def get_name():
        return 'raw'

    @staticmethod
    def serialize(data):
        return data

    @staticmethod
    def deserialize(data):
        return data

    @classmethod
    def deserialize_stream(cls, data):
        return data

    @classmethod
    def get_record_separator(cls):
        return b''

    @staticmethod
    def get_mime_type():
        return 'application/octet-stream'

    @classmethod
    def should_wrap(cls):
        return False

class NumpyProtocol(BaseProtocol):

    @staticmethod
    def get_name():
        return 'numpy'

    @staticmethod
    def serialize(data):
        arrays = []

        def _serialize_cb(v, path):
            if isinstance(v, np.ndarray):
                buf = v.tobytes()
                v = dict(__type__='ndarray', shape=v.shape,
                        dtype=liteval(str(v.dtype)), size=len(buf), index=sum(len(x) for x in arrays))
                arrays.append(buf)

            return v

        data = walk_data_structure(data, _serialize_cb)
        data = json.dumps(data).encode('utf8')
        data = b''.join([data, b'\n'] + arrays)
        return data

    @staticmethod
    def deserialize(data):
        data, arrays = data.split(b'\n', 1)
        data = json.loads(data.decode('utf8'))

        def _deserialize_cb(v, path):
            if isinstance(v, dict) and v.get('__type__') == 'ndarray':
                sidx = v['index']
                eidx = sidx + v['size']
                _arr = arrays[sidx:eidx]
                dtype = v['dtype']
                if isinstance(dtype, list):
                    dtype = [tuple(x) for x in dtype]
                _arr = np.frombuffer(_arr, dtype=dtype).reshape(v['shape'])
                return _arr

            return v

        data = walk_data_structure(data, _deserialize_cb)
        return data

    @classmethod
    def deserialize_stream(cls, data):
        raise StreamingNotSupported(cls.get_name())

    @staticmethod
    def get_record_separator():
        raise StreamingNotSupported(cls.get_name())

    @staticmethod
    def get_mime_type():
        return 'application/numpy'

PROTOCOLS = dict((p.get_name(), p) for p in [
    JsonProtocol,
    MessagePackProtocol,
    PickleProtocol,
    NumpyProtocol,
    RawProtocol,
])

DEFAULT_PROTOCOL = JsonProtocol.get_name()
