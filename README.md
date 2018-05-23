# KwikAPI

Quickly build API services to expose functionality in Python.

`KwikAPI` lets a python developer focus on writing their logic and not worrying about the service like funtionality (There are numerous things to address like serialization protocols, bulk requests, versioning, grouping API calls into logical sets etc).

## Installation
```bash
$ sudo pip3 install kwikapi
```

## Usage

### Quick example
Here is an example of how to use `KwikAPI` to expose `Calc` as a service. We will use `KwikAPI` with the `tornado` webserver in this example.
> To use KwikAPI with tornado install `sudo pip3 install kwikapi[tornado]`

```python
import tornado.ioloop
import tornado.web

from kwikapi.tornado import RequestHandler
from kwikapi import API

# Core logic that you want to expose as a service
class Calc(object):
    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b

# Standard boilerplate code to define the service. This
# code will remain more or less the same size regardless
# of how big the code/complexity of `BaseCalc` above is.

# Register BaseCalc with KwikAPI
api = API()
api.register(Calc(), 'v1')

# Passing RequestHandler to the KwikAPI
def make_app():
    return tornado.web.Application([
        (r'^/api/.*', RequestHandler, dict(api=api)),
    ])

# Starting the application
if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
```

Making an API request
```bash
$ wget http://localhost:8888/api/v1/add?a=10&b=20
$ wget http://localhost:8888/api/v1/subtract?a=10&b=20
```

For more examples of KwikAPI with Tornado go through this [link](https://github.com/deep-compute/kwikapi.tornado/blob/master/README.md) and with Django go through this [link](https://github.com/deep-compute/kwikapi.django/blob/master/README.md)

## Mock request
To demonstrate the various features of `KwikAPI` and also to use the same examples
as living documentation and test cases, we use `MockRequest` so we don't need
`tornado` or `django`

```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    # Type information must be specified
...    def add(self, a: int, b: int) -> int:
...        return a + b

>>> api = API()
>>> api.register(Calc(), "v1") # `v1` is the version of this example

>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
30
>>> res['success']
True
 
 ```

## Features

- Versioning support
- Type checking
- Namespace
- Customizing request and response
- Streaming
- Protocol handling
- API Doc
- Bulk request handling
- KwikAPI Client

### Versioning support
Versioning support will be used if user wants different versions of functionality with slightly changed behaviour.
 
Specifying the version is mandatory for every class.
 
We can register the same class with different versions (for testing here)

 ```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    def add(self, a: int, b: int) -> int:
...        return a + b

>>> api = API()
>>> api.register(Calc(), "v1")
>>> api.register(Calc(), "v2")
 
>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
>>> res['result']
30
>>> res['success']
True

>>> req = MockRequest(url="/api/v2/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
>>> res['result']
30
>>> res['success']
True

```

We can register different classes with different versions

```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    def add(self, a: int, b: int) -> int:
...        return a + b

>>> class ConcStr(object):
...    def add(self, a: str, b: str) -> str:
...        return a+b

>>> api = API()
>>> api.register(Calc(), "v1")
>>> api.register(ConcStr(), "v2")
 
>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
>>> res['result']
30
>>> res['success']
True

>>> req = MockRequest(url="/api/v2/add?a=in&b=dia")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
>>> res['result']
'india'
>>> res['success']
True
 
 ```

We can specify the default version so that when you don't mention version in the request URL then default version will be used.

```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    # Type information must be specified
...    def add(self, a: int, b: int) -> int:
...        return a + b

>>> api = API(default_version='v1')
>>> api.register(Calc(), "v1")

>>> req = MockRequest(url="/api/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
30
>>> res['success']
True
 
```
 
### Type checking
Specifying type for parameters and for return value will exactly meet the functionality. This is mandatory in KwikAPI (If the method don't return anything then `None` should be specified as return type)

```python
>>> class Calc(object):
...    # Type information must be specified
...    def add(self, a: int, b: int) -> int:
...        return a + b
...    def sub(self, a: int, b: int) -> None:
...        c = a - b

```

KwikAPI supports builtin types and types from typing such as Union, List, Tuple, Dict, Generator, Any and so on.

Here are some examples of how to use type hints.

- If a single argument expects two or more types then Union can be used
```python
>>> from typing import Union
>>> class Calc(object):
...    def add(self, a: Union[int, float], b: int) -> Union[int, float]:
...        return a + b

```

- If we want to pass same type of values in list then List type can be used. If the list values are different types then builtin list can be used as type annotation
```python
>>> from typing import List
>>> class Calc(object):
...    def add(self, a: List[str], b: list) -> list:
...        return a + b

```

- If we want to pass same type of keys and same type of values in dictionary then Dict type can be used. If the dictionary keys and values are different types then builtin dict can be used as type annotation
```python
>>> from typing import Dict
>>> class Calc(object):
...    def add(self, a: Dict[str, int], b: dict) -> dict:
...        return a.update(b)

```

- For cheking values inside tuple then we can use Tuple from typing other wise we can use builtin tuple
```python
>>> from typing import Tuple
>>> class Calc(object):
...    def add(self, a: Tuple[str, int, float], b: tuple) -> tuple:
...        return a + b

```

- If the method contains more than one return value then we can mention types in square brackets
```python
>>> from typing import List
>>> class Calc(object):
...    def add(self, a: int, b: int) -> [int, int]:
...        return a, b

```

- If request or response contains stream data then we can use Generator
```python
>>> from typing import Generator
>>> class Calc(object):
...    def add(self, a: Generator) -> int:
...        _sum = 0
...        for i in a:
...            _sum += i

...        return _sum

```

- If we don't need to bother about type checking then we can simply use Any from typing
```python
>>> from typing import Any
>>> class Calc(object):
...    def add(self, a: Any, b: Any) -> Any:
...        return a, b

```

### Namespace
Register methods with different namespaces

```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    def add(self, a: int, b: int) -> int:
...        return a + b

>>> class ConcStr(object):
...    def add(self, a: str, b: str) -> str:
...        return a+b

>>> api = API(default_version="v1")
>>> api.register(Calc(), "v1", "Calc")
>>> api.register(ConcStr(), "v1", "Calc/ConcStr")
 
>>> req = MockRequest(url="/api/v1/Calc/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
>>> res['result']
30
>>> res['success']
True

>>> req = MockRequest(url="/api/v1/Calc/ConcStr/add?a=in&b=dia")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
>>> res['result']
'india'
>>> res['success']
True
 
```
Register same methods with same version with different namespaces

```python
>>> import json
 
>>> from kwikapi import API, MockRequest, BaseRequestHandler, Request
 
>>> class Calc(object):
...    def add(self, req: Request, a: int, b: int) -> int:
...        return a + b

>>> class CalcScintific(object):
...    def add(self, req: Request, a: int, b: int) -> int:
...        return a + b + 10

>>> api = API()
>>> api.register(Calc(), "v1")
>>> api.register(CalcScintific(), "v1", "scintific")

>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
30
>>> res['success']
True

>>> req = MockRequest(url="/api/v1/scintific/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
40
>>> res['success']
True

```

> We can also register same methods with same namespace with different versions

### Customizing request and response
User can change the response if he wants it

```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler, Request

>>> class Calc(object):
...    # Type information must be specified
...    def add(self, req: Request, a: int, b: int) -> int:
...        req.response.headers['something'] = 'something'
...        return a + b

>>> api = API()
>>> api.register(Calc(), "v1")

>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
30
>>> res['success']
True
 
```

### Streaming
KwikAPI supports request and response Streaming

```python
class MyAPI(object):
    # Streaming response
    def streaming_response_test(self, num: int) -> Generator:
        for i in range(num):
            yield {i: i}

    # Streaming request
    def streaming_request_test(self, numbers: Generator) -> int:
        _sum = 0
        for i in numbers:
            _sum += i
        return _sum
```

```bash
$ wget "http://localhost:8888/api/v1/streaming_response_test" --post-data '{"a": 10}'

$ wget "http://localhost:8888/api/v1/streaming_request_test" --post-file /tmp/numbers

/tmp/numbers
0
1
2
3
...
...
1000000

```

### Protocol handling
KwikAPI supports JSON, Messagepack, Pickle and Numpy protocols

#### KwikAPI also supports custom protocols instead of using existing protocols
```python 
# Users can define their own protocols and can register with KwikAPI

>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler, Request, BaseProtocol

>>> class Calc(object):
...    # Type information must be specified
...    def add(self, req: Request, a: int, b: int) -> int:
...        return a + b

>>> class CustomProtocol(BaseProtocol):
...    @staticmethod
...    def get_name():
...        return 'custom'

...    @staticmethod
...    def serialize(data):
...        return json.dumps(data)

...    @staticmethod
...    def deserialize(data):
...        return json.loads(data)

...    @classmethod
...    def deserialize_stream(cls, data):
...        for line in data:
...            yield cls.deserialize(line.decode('utf8'))

...    @staticmethod
...    def get_record_separator():
...        return '\n'

...    @staticmethod
...    def get_mime_type():
...        return 'application/json'

>>> api = API()
>>> api.register(Calc(), "v1")
 
>>> base = BaseRequestHandler(api)
>>> base.register_protocol(CustomProtocol())

>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = json.loads(base.handle_request(req))

>>> res['result']
30
>>> res['success']
True

```

#### By default KwikAPI uses JSON protocol. User can  change the default protocol.
```python
>>> import msgpack
>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    # Type information must be specified
...    def add(self, a: int, b: int) -> int:
...        return a + b

>>> api = API()
>>> api.register(Calc(), "v1") # `v1` is the version of this example
>>> base = BaseRequestHandler(api, default_protocol='messagepack')

>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = msgpack.unpackb(base.handle_request(req))

>>> res[b'result']
30
>>> res[b'success']
True
 
```

#### KwikAPI also supports defining specific protocol for specific request
If user wants to use specific protocol with specific request then he should specify the protocol in headers
ex:

```bash
$ wget "http://localhost:8888/api/v1/add" --header="X-KwikAPI-Protocol: messagepack" --post-file /tmp/data.msgpack
$ wget "http://localhost:8888/api/v1/subtract" --header="X-KwikAPI-Protocol: json" --post-data '{"a": 10, "b": 20}'
$ wget "http://localhost:8888/api/v1/add" --header="X-KwikAPI-Protocol: pickle" --post-file /tmp/data.pickle
$ wget "http://localhost:8888/api/v1/add" --header="X-KwikAPI-Protocol: numpy" --post-file /tmp/data.numpy
```

### Bulk request handling
It will be very convenient if the user has facility to make bulk requests.
When making a large number of requests, the overhead of network latency and HTTP request/response processing
can slow down the operation. It is convenient and necessary to have a mechanism to sent a set of requests in
bulk.

### KwikAPI Client
`KwikAPI` provides client tool which will help in making calls to server. The `KwikAPI Client` will take
care of serialization and deserialization of the data.

Usage:
```python
from kwikapi import Client

c = Client('http://localhost:8818/api/', version='v1')

# `add` is the api method
print(c.add(a=10, b=10))

# Namespace will be used with Client object

print(c.namespace.add(a=10, b=10))

# Parameters can be changed that are passed to the Client object

print(c(version='v2', prtocol='pickle').namespace.add(a=10, b=10))
```

## Run test cases
```bash
$ python3 -m doctest -v README.md
```
