from __future__ import annotations

import base64
from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
import hmac
import html
import secrets
import threading
import time
from typing import Callable, Deque
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response


PASSWORD_SCHEME = "pbkdf2_sha256"
DEFAULT_PASSWORD_ITERATIONS = 310_000
DEFAULT_SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
DEFAULT_COOKIE_NAME = "ilab_access_session"
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 5 * 60
DEFAULT_MAX_ATTEMPTS = 5
MIN_SESSION_SECRET_LENGTH = 32
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_BRAND_ASSET_PATHS = frozenset(
    {
        "/static/brand/dachuan-logo-64.png",
        "/static/brand/dachuan-logo-180.png",
        "/static/brand/pwa-icon-192.png",
        "/static/brand/pwa-icon-512.png",
    }
)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def hash_password(password: str, *, iterations: int = DEFAULT_PASSWORD_ITERATIONS) -> str:
    if not password:
        raise ValueError("password must not be empty")
    if iterations < 10_000:
        raise ValueError("password hash iterations are too low")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{PASSWORD_SCHEME}${iterations}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, iterations_raw, salt_raw, digest_raw = encoded_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        iterations = int(iterations_raw)
        if iterations < 10_000:
            return False
        salt = _b64decode(salt_raw)
        expected = _b64decode(digest_raw)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    except (TypeError, ValueError, UnicodeError):
        return False
    return secrets.compare_digest(actual, expected)


def _validate_session_secret(session_secret: str) -> None:
    if len(session_secret) < MIN_SESSION_SECRET_LENGTH:
        raise ValueError(f"session secret must be at least {MIN_SESSION_SECRET_LENGTH} characters")


def create_session_cookie(
    session_secret: str,
    *,
    now: int | None = None,
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
) -> str:
    _validate_session_secret(session_secret)
    issued_at = int(time.time()) if now is None else int(now)
    payload = f"v1:{issued_at + ttl_seconds}".encode("ascii")
    signature = hmac.new(session_secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def verify_session_cookie(
    session_secret: str,
    cookie: str | None,
    *,
    now: int | None = None,
) -> bool:
    if len(session_secret) < MIN_SESSION_SECRET_LENGTH or not cookie:
        return False
    try:
        payload_raw, signature_raw = cookie.split(".", 1)
        payload = _b64decode(payload_raw)
        supplied_signature = _b64decode(signature_raw)
        expected_signature = hmac.new(session_secret.encode("utf-8"), payload, hashlib.sha256).digest()
        version, expires_raw = payload.decode("ascii").split(":", 1)
        expires_at = int(expires_raw)
    except (TypeError, ValueError, UnicodeError):
        return False
    current_time = int(time.time()) if now is None else int(now)
    return (
        version == "v1"
        and expires_at > current_time
        and secrets.compare_digest(supplied_signature, expected_signature)
    )


@dataclass
class LoginAttemptLimiter:
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    clock: Callable[[], float] = time.monotonic
    _attempts: dict[str, Deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _prune(self, client_id: str, now: float) -> Deque[float]:
        attempts = self._attempts[client_id]
        threshold = now - self.window_seconds
        while attempts and attempts[0] <= threshold:
            attempts.popleft()
        if not attempts:
            self._attempts.pop(client_id, None)
            return deque()
        return attempts

    def blocked(self, client_id: str) -> bool:
        now = self.clock()
        with self._lock:
            return len(self._prune(client_id, now)) >= self.max_attempts

    def record_failure(self, client_id: str) -> None:
        now = self.clock()
        with self._lock:
            self._prune(client_id, now)
            self._attempts[client_id].append(now)

    def clear(self, client_id: str) -> None:
        with self._lock:
            self._attempts.pop(client_id, None)


def _safe_next(value: str | None) -> str:
    candidate = (value or "/").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    return candidate


def _login_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    }


def _login_page(*, next_path: str, error: str | None = None, status_code: int = 200) -> HTMLResponse:
    error_html = f'<div class="error" role="alert">{html.escape(error)}</div>' if error else ""
    safe_next = html.escape(_safe_next(next_path), quote=True)
    body = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
  <title>登录 · 大川生图站</title>
  <link rel="icon" type="image/png" sizes="64x64" href="/static/brand/dachuan-logo-64.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="/static/brand/dachuan-logo-180.png" />
  <style>
    :root {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #183129; background: #edf3ef; }}
    * {{ box-sizing: border-box; }}
    body {{ min-height: 100vh; margin: 0; display: grid; place-items: center; padding: 24px; background: radial-gradient(circle at 20% 10%, rgba(69,123,102,.18), transparent 34%), #edf3ef; }}
    main {{ width: min(100%, 390px); padding: 34px; border: 1px solid rgba(24,49,41,.12); border-radius: 24px; background: rgba(255,255,255,.9); box-shadow: 0 24px 80px rgba(26,55,45,.13); backdrop-filter: blur(18px); }}
    .login-logo {{ width: 58px; height: 58px; display: block; object-fit: cover; margin-bottom: 22px; border: 1px solid rgba(24,49,41,.14); border-radius: 18px; box-shadow: 0 12px 28px rgba(31,67,54,.18); }}
    h1 {{ margin: 0; font-size: 25px; letter-spacing: -.035em; }}
    p {{ margin: 9px 0 25px; color: #60736c; font-size: 14px; line-height: 1.6; }}
    label {{ display: block; margin-bottom: 8px; font-size: 13px; font-weight: 650; }}
    input {{ width: 100%; height: 48px; padding: 0 14px; border: 1px solid #bdcbc5; border-radius: 13px; background: #fff; color: #183129; font: inherit; outline: none; transition: border-color .18s, box-shadow .18s; }}
    input:focus {{ border-color: #457b66; box-shadow: 0 0 0 4px rgba(69,123,102,.14); }}
    button {{ width: 100%; height: 48px; margin-top: 14px; border: 0; border-radius: 13px; background: #315f50; color: #fff; font: 650 15px/1 inherit; cursor: pointer; }}
    button:hover {{ background: #284f43; }}
    button:focus-visible {{ outline: 3px solid rgba(69,123,102,.32); outline-offset: 3px; }}
    .error {{ margin: 0 0 14px; padding: 10px 12px; border-radius: 11px; background: #fff0ed; color: #a23a2b; font-size: 13px; }}
    @media (prefers-color-scheme: dark) {{
      :root {{ color: #e8f0ec; background: #111916; }}
      body {{ background: radial-gradient(circle at 20% 10%, rgba(83,148,121,.2), transparent 34%), #111916; }}
      main {{ border-color: rgba(226,240,233,.12); background: rgba(27,39,34,.92); box-shadow: 0 24px 80px rgba(0,0,0,.34); }}
      p {{ color: #9bada5; }}
      input {{ border-color: #43564e; background: #14211c; color: #eef5f1; }}
      .error {{ background: #3b211e; color: #ffb7aa; }}
    }}
  </style>
</head>
<body>
  <main>
    <img class="login-logo" src="/static/brand/dachuan-logo-180.png" alt="大川生图站" width="58" height="58" />
    <h1>大川生图站</h1>
    <p>输入访问密码后继续。</p>
    {error_html}
    <form method="post" action="/login">
      <input type="hidden" name="next" value="{safe_next}" />
      <label for="password">访问密码</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required autofocus />
      <button type="submit">进入工作台</button>
    </form>
  </main>
</body>
</html>"""
    return HTMLResponse(body, status_code=status_code, headers=_login_headers())


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _wants_html(request: Request) -> bool:
    return request.method in {"GET", "HEAD"} and "text/html" in request.headers.get("accept", "")


def _effective_port(scheme: str, port: int | None) -> int | None:
    if port is not None:
        return port
    return 443 if scheme == "https" else 80 if scheme == "http" else None


def _origin_matches_request(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    try:
        parsed = urlsplit(origin)
        origin_port = parsed.port
    except ValueError:
        return False
    request_scheme = request.url.scheme.lower()
    origin_scheme = parsed.scheme.lower()
    return (
        origin_scheme in {"http", "https"}
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
        and (parsed.hostname or "").casefold() == (request.url.hostname or "").casefold()
        and _effective_port(origin_scheme, origin_port) == _effective_port(request_scheme, request.url.port)
        and origin_scheme == request_scheme
    )


def install_password_access_gate(
    app: FastAPI,
    *,
    password_hash: str,
    session_secret: str,
    cookie_name: str = DEFAULT_COOKIE_NAME,
    cookie_secure: bool = True,
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
) -> None:
    if not password_hash or not session_secret:
        raise ValueError("password hash and session secret are required")
    _validate_session_secret(session_secret)
    limiter = LoginAttemptLimiter(max_attempts=max_attempts, window_seconds=rate_limit_window_seconds)

    @app.get("/login", response_model=None)
    async def login_page(request: Request, next: str = "/") -> Response:
        if verify_session_cookie(session_secret, request.cookies.get(cookie_name)):
            return RedirectResponse(_safe_next(next), status_code=302)
        return _login_page(next_path=next)

    @app.post("/login", response_model=None)
    async def login(request: Request) -> Response:
        form = await request.form()
        next_path = _safe_next(str(form.get("next") or "/"))
        client_id = _client_id(request)
        if limiter.blocked(client_id):
            return _login_page(next_path=next_path, error="尝试次数过多，请五分钟后再试。", status_code=429)
        password = str(form.get("password") or "")
        if not verify_password(password, password_hash):
            limiter.record_failure(client_id)
            return _login_page(next_path=next_path, error="密码不正确，请重新输入。", status_code=401)
        limiter.clear(client_id)
        response = RedirectResponse(next_path, status_code=303)
        response.set_cookie(
            cookie_name,
            create_session_cookie(session_secret, ttl_seconds=session_ttl_seconds),
            max_age=session_ttl_seconds,
            httponly=True,
            secure=cookie_secure,
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/logout", response_model=None)
    async def logout() -> Response:
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(cookie_name, path="/", secure=cookie_secure, httponly=True, samesite="lax")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def password_access_gate(request: Request, call_next: Callable[[Request], Response]) -> Response:
        if request.url.path in {"/login", "/logout"} or request.url.path in PUBLIC_BRAND_ASSET_PATHS:
            return await call_next(request)
        if verify_session_cookie(session_secret, request.cookies.get(cookie_name)):
            if request.method in UNSAFE_METHODS and not _origin_matches_request(request):
                return JSONResponse(
                    {"detail": "cross_site_request_rejected"},
                    status_code=403,
                    headers={"Cache-Control": "no-store"},
                )
            return await call_next(request)
        if _wants_html(request):
            target = request.url.path
            if request.url.query:
                target = f"{target}?{request.url.query}"
            return RedirectResponse(f"/login?next={quote(target, safe='')}", status_code=302)
        return JSONResponse(
            {"detail": "authentication_required"},
            status_code=401,
            headers={"Cache-Control": "no-store"},
        )
