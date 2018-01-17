# kwikapi
### What is kwikapi
An api, which processes any (Ex: Django, Tornado) kind of requests

### Usage

#### Example for making request and getting response from `kwikapi`
```python
>>> import json

>>> from kwikapi import API, MockRequest, BaseRequestHandler
>>> from logging import Logger

>>> class Calc(object):
...    def add(self, request, a: int, b: int):
...        return a + b

>>> api = API(Logger, default_version='v1')
>>> api.register(Calc(), "v1")
>>> api.register(Calc(), "v2")

>>> req = MockRequest(url="/api/v2/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
30
>>> res['success']
True

```
#### If you don't specify version in the request URL then default version will be used
```python
>>> req = MockRequest(url="/api/add?a=10&b=20")
>>> res = json.loads(BaseRequestHandler(api).handle_request(req))

>>> res['result']
30
>>> res['success']
True

```
#### Run test cases
```bash
$ python -m doctest -v README.md
```
