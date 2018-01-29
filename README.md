# KwikApi

An api, which processes any (Ex: Django, Tornado) kind of requests

## Usage

### Basic example for making request and getting response from `kwikapi`
```python
>>> import json
>>> from logging import Logger

>>> from kwikapi import API, MockRequest, BaseRequestHandler, Request

>>> class Calc(object):
...    # Type information must be specified
...    def add(self, req: Request, a: int, b: int) -> int:
...        return a + b

>>> api = API(Logger)
>>> api.register(Calc(), "v1") # `v1` is the version of this example

>>> req = MockRequest(url="/api/v1/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
30
>>> res['success']
True
 
```
### If you don't specify version in the request URL then default version will be used
```python
>>> api = API(Logger, default_version="v1")
>>> api.register(Calc(), "v1")
 
>>> req = MockRequest(url="/api/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
 
```
### Register methods with namespaces
```python
>>> api = API(Logger, default_version="v1")
>>> api.register(Calc(), "v1", "scientific")
 
>>> req = MockRequest(url="/api/v1/scientific/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))
 
```
### Register same methods with same version with different namespaces
```python
>>> import json
 
>>> from kwikapi import API, MockRequest, BaseRequestHandler, Request
 
>>> class Calc(object):
...    def add(self, req: Request, a: int, b: int) -> int:
...        return a + b

>>> class CalcScintific(object):
...    def add(self, req: Request, a: int, b: int) -> int:
...        return a + b + 10

>>> api = API(Logger)
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
> You can also register same methods with same namespace with different versions

## Run test cases
```bash
$ python -m doctest -v README.md
```
