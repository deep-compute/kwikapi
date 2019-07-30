import abc
from abc import abstractmethod
import base64

from deeputil import xcode, AttrDict

from .api import Request
from .exception import AuthenticationError


class BaseServerAuthenticator:
    """Helps in authenticating a request on the server"""

    __metaclass__ = abc.ABCMeta

    TYPE = "base"

    def _read_auth(self, req):
        auth = req.headers.get("Authorization")
        _type, info = auth.split(" ", 1)
        if _type.lower() != self.TYPE:
            raise AuthenticationError(_type)

        auth = AuthInfo(type=self.TYPE)
        auth.header_info = info
        return auth

    def authenticate(self, req):
        return self._read_auth(req)


class AuthInfo(AttrDict):
    """Represents authentication information (post auth)"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, type=None):
        self.type = type
        self.is_authenticated = False


class BasicServerAuthenticator(BaseServerAuthenticator):
    TYPE = "basic"

    def __init__(self, user_store=None):
        self.user_store = user_store or {}

    def authenticate(self, req):
        auth = super().authenticate(req)
        auth.username, auth.password = (
            base64.b64decode(xcode(auth.header_info)).decode("utf-8").split(":")
        )

        auth_info = self.user_store.get(auth.username, None)
        if not auth_info:
            return auth

        if auth_info.get("password", None) != auth.password:
            return auth

        auth.is_authenticated = True
        auth.update(auth_info)

        return auth


class BearerServerAuthenticator(BaseServerAuthenticator):
    TYPE = "bearer"

    def __init__(self, token_store=None):
        self.token_store = token_store or {}

    def authenticate(self, req):
        auth = super().authenticate(req)
        auth.token = auth.header_info

        auth_info = self.token_store.get(auth.token, None)
        if auth_info:
            auth.is_authenticated = True
            auth.update(auth_info)

        return auth


class HMACServerAuthenticator(BaseServerAuthenticator):
    pass


class BaseClientAuthenticator:
    """Helps in signing a request with auth info"""

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.type = None

    @abstractmethod
    def sign(self, url, headers, body):
        pass


class BasicClientAuthenticator(BaseClientAuthenticator):
    def __init__(self, username, password):
        self.username = xcode(username)
        self.password = xcode(password)
        self.encoded_key = b"%s:%s" % (self.username, self.password)
        self.encoded_key = base64.b64encode(self.encoded_key)

    def sign(self, url, headers, body):
        headers["Authorization"] = b"Basic %s" % self.encoded_key


class BearerClientAuthenticator(BaseClientAuthenticator):
    def __init__(self, bearer_token):
        self.bearer_token = xcode(bearer_token)

    def sign(self, url, headers, body):
        headers["Authorization"] = b"Bearer %s" % self.bearer_token


class HMACClientAuthenticator(BaseClientAuthenticator):
    pass


class BaseAuthAPI:
    __metaclass__ = abc.ABCMeta

    @abstractmethod
    def login(self, req: Request, username: str, password: str) -> str:
        pass

    @abstractmethod
    def logout(self, req: Request) -> None:
        pass

    @abstractmethod
    def signup(self, req: Request, username: str, password: str, email: str) -> str:
        pass
