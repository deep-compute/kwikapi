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
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
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
...    def add(self, a, b):
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
- Namespace
- Customizing request and response
- Streaming
- Protocol handling
- API Doc
- Bulk request handling

### Versioning support
Versioning support will be used if user wants different versions of functionality with slightly changed behaviour.
 
Specifying the version is mandatory for every class.
 
We can register the same class with different versions (for testing here)

 ```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    def add(self, a, b):
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
...    def add(self, a, b):
...        return a + b

>>> class ConcStr(object):
...    def add(self, a, b):
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

>>> req = MockRequest(url="/api/v2/add?a=hello&b=hi")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
>>> res['result']
'hellohi'
>>> res['success']
True
 
 ```

We can specify the default version so that when you don't mention version in the request URL then default version will be used.

```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    def add(self, a, b):
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

### Namespace
Register methods with different namespaces

```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    def add(self, a, b):
...        return a + b

>>> class ConcStr(object):
...    def add(self, a, b):
...        return a + b

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
...    def add(self, a, b):
...        return a + b

>>> class CalcScintific(object):
...    def add(self, a, b):
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
...    def add(self, req: Request, a, b):
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
    def streaming_response_test(self, num):
        for i in range(num):
            yield {i: i}

    # Streaming request
    def streaming_request_test(self, numbers):
        _sum = 0
        for i in numbers:
            _sum += i
        return _sum
```

```bash
$ wget "http://localhost:8888/api/v1/streaming_response_test" --post-data '{"a": 10}'

$ wget "http://localhost:8888/api/v1/streaming_request_test" --header="X-KwikAPI-Streamparam: numbers" --post-file /tmp/numbers

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
KwikAPI supports JSON protocol and Messagepack protocol

#### KwikAPI also supports custom protocols instead of using existing protocols
```python 
# Users can define their own protocols and can register with KwikAPI

>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler, Request, BaseProtocol

>>> class Calc(object):
...    # Type information must be specified
...    def add(self, req: Request, a, b):
...        return a + b

>>> class CustomProtocol(BaseProtocol):
...    @staticmethod
...    def get_name():
...        return 'json'

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
...    def add(self, a, b):
...        return a + b

>>> api = API()
>>> api.register(Calc(), "v1") # `v1` is the version of this example
>>> base = BaseRequestHandler(api)
>>> base.set_default_protocol('messagepack')

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
```

### API Doc
Using API Doc we can look at what are the all API methods available

To see available API methods the URL will be http://localhost:8888/api/apidoc for default version

To check API methods under specific version we can provide URL as http://localhost:8888/api/version/apidoc

```python
>>> import json
>>> from pprint import pprint

>>> from kwikapi import API, MockRequest, BaseRequestHandler

>>> class Calc(object):
...    def add(self, a, b):
...        return a + b

>>> api = API()
>>> api.register(Calc(), "v1")

>>> req = MockRequest(url="/api/v1/apidoc")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> pprint(res['result'])
{'add': {'doc': None,
         'gives_stream': False,
         'params': {'a': {'default': None, 'required': True},
                    'b': {'default': None, 'required': True}}}}

>>> res['success']
True

```

### Bulk request handling
It will be very convenient if the user has facility to make bulk requests.
When making a large number of requests, the overhead of network latency and HTTP request/response processing
can slow down the operation. It is convenient and necessary to have a mechanism to sent a set of requests in
bulk.

We are going to support bulk requests in `KwikAPI` in future.

## Run test cases
```bash
$ python3 -m doctest -v README.md
```
