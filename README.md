# kwikapi
An api, which processes both Tornado and Django requests

- Supporting only python 3+ versions
### Installation process
- Create a virtualenv and activate
```bash
- python3 -m virtualenv environment_name(change this environment name)
- source environment_name/bin/activate
```
- Clone `kwikapi` repo
- Setup.py installation
```bash
cd kwikapi
pip install .
```

- Create `django project` and `application`
```bash
django-admin startproject yadatest(change yadatest and use your own project name)
cd yadatest
python manage.py startapp polls(change polls and use your own application name)
```

- Open `yadatest/urls.py` and add these statements
```bash
from django.conf.urls import
```
- Add below statement in `urlpatterns`
```bash
url(r'^', include('polls.urls'))
```
- Open `yadatest/settings.py` and add `polls`(your application name) in `INSTALLED_APPS`

- Open `polls/urls.py` and add below lines
```bash
from django.conf.urls import url, include
from django.http import HttpResponse

from . import views

import json

urlpatterns = [
    url(r'myview/', views.myview),
    url(r'api/', views.api.handle_request, {"request_type": "django"}),
    url(r'apidoc/(\w+)?', lambda r, v=None: HttpResponse(json.dumps(views.api.doc(v)))),
]
```

- Open `polls/views.py` and write sample piece of code(similar to below statements)
```bash
from django.http import HttpResponse
from kwikapi import API, APIFragment
from logging import Logger

class BaseCalc(APIFragment):
    def add(self, request, a: int, b: int):
        return a + b

    def subtract(self, request, a: int, b: int):
        return a - b

class StandardCalc(APIFragment):
    def multiply(self, request, a: int, b: int):
        return a * b

    def divide(self, request, a: int, b: int):
        return a / b

api = API(Logger, default_version='v1')
api.register(BaseCalc(), 'v1')
api.register(StandardCalc(), "v2")

def myview(request):
    result = api['v1'].power(request, 2, 4)
    #result = api.add(request, 1, 2)
    return HttpResponse("result %s" % result)
```
- All the functions, which we wrote in the `BaseCalc` and `StandardCalc` will become `API's`
- `api.register(BaseCalc(), 'v1')` is registering class with version number

- Start django server with below run commands
```bash
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py runserver 9876(random four digit number)
```

- To test `add` api, run below command in the web-browser
```bash
http://localhost:9876/api/v1/add?a=10&b=20
```
- To test `subtract` api, run below command
```bash
http://localhost:9876/api/v1/subtract?a=10&b=20
```
- To test `multiply` api, run below command
```bash
http://localhost:9876/api/v2/multiply?a=10&b=20
```

- To check all the versions and api's info, run below command
```bash
http://localhost:9876/apidoc
```
- To check particular version, run below command
```bash
http://localhost:9876/apidoc/v1
http://localhost:9876/apidoc/v2
```

