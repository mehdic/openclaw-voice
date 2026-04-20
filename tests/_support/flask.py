from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse


class _Proxy:
    def __init__(self, getter):
        object.__setattr__(self, "_getter", getter)

    def _target(self):
        return object.__getattribute__(self, "_getter")()

    def __getattr__(self, name):
        return getattr(self._target(), name)

    def __setattr__(self, name, value):
        setattr(self._target(), name, value)

    def __getitem__(self, key):
        return self._target()[key]

    def __setitem__(self, key, value):
        self._target()[key] = value

    def get(self, *args, **kwargs):
        return self._target().get(*args, **kwargs)

    def pop(self, *args, **kwargs):
        return self._target().pop(*args, **kwargs)

    def clear(self):
        return self._target().clear()

    def update(self, *args, **kwargs):
        return self._target().update(*args, **kwargs)

    def setdefault(self, *args, **kwargs):
        return self._target().setdefault(*args, **kwargs)


class Response:
    def __init__(self, json_data=None, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code
        self.headers = {}

    def get_json(self):
        return self._json_data


class _Session(dict):
    permanent = False


class _Request:
    def __init__(self, method: str, path: str, args: dict[str, str], json_data):
        self.method = method
        self.path = path
        self.args = args
        self._json_data = json_data

    def get_json(self, silent: bool = False):
        return self._json_data


_context_stack: list[SimpleNamespace] = []


def _current_context():
    if not _context_stack:
        raise RuntimeError("No active request context")
    return _context_stack[-1]


request = _Proxy(lambda: _current_context().request)
session = _Proxy(lambda: _current_context().session)
g = _Proxy(lambda: _current_context().g)


def jsonify(data):
    return Response(json_data=data)


class Flask:
    def __init__(self, import_name: str, static_folder: str | None = None, static_url_path: str | None = None):
        self.import_name = import_name
        self.static_folder = static_folder
        self.static_url_path = static_url_path
        self.secret_key = ""
        self.config = {}
        self._routes: dict[tuple[str, str], object] = {}
        self._before_request = []
        self._after_request = []

    def route(self, path: str, methods: list[str] | None = None):
        methods = methods or ["GET"]

        def decorator(func):
            for method in methods:
                self._routes[(method.upper(), path)] = func
            return func

        return decorator

    def get(self, path: str):
        return self.route(path, methods=["GET"])

    def post(self, path: str):
        return self.route(path, methods=["POST"])

    def before_request(self, func):
        self._before_request.append(func)
        return func

    def after_request(self, func):
        self._after_request.append(func)
        return func

    def send_static_file(self, _filename: str):
        return Response(status_code=200)

    def run(self, **_kwargs):
        return None

    @contextmanager
    def test_request_context(self, path: str, method: str = "GET", json=None):
        parsed = urlparse(path)
        args = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        ctx = SimpleNamespace(
            app=self,
            request=_Request(method.upper(), parsed.path or "/", args, json),
            session=_Session(),
            g=SimpleNamespace(),
        )
        _context_stack.append(ctx)
        try:
            yield ctx
        finally:
            _context_stack.pop()

    def test_client(self):
        return _TestClient(self)


class _TestClient:
    def __init__(self, app: Flask):
        self._app = app
        self._session = _Session()

    def _open(self, method: str, path: str, json_data=None):
        parsed = urlparse(path)
        args = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        ctx = SimpleNamespace(
            app=self._app,
            request=_Request(method, parsed.path or "/", args, json_data),
            session=self._session,
            g=SimpleNamespace(),
        )
        _context_stack.append(ctx)
        try:
            for func in self._app._before_request:
                func()

            handler = self._app._routes.get((method, parsed.path or "/"))
            if handler is None:
                response = Response(status_code=404)
            else:
                response = handler()
                if isinstance(response, tuple):
                    response, status_code = response
                    response.status_code = status_code
                elif not isinstance(response, Response):
                    response = Response(json_data=response)

            for func in self._app._after_request:
                response = func(response)

            return response
        finally:
            _context_stack.pop()

    def get(self, path: str):
        return self._open("GET", path)

    def post(self, path: str, json=None):
        return self._open("POST", path, json_data=json)
