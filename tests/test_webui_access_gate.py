from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
import pytest

from codex_image.webui.app import create_app

from codex_image.webui.access_gate import (
    hash_password,
    install_password_access_gate,
    verify_password,
)


def _protected_app(*, max_attempts: int = 5) -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def home() -> dict[str, bool]:
        return {"ok": True}

    @app.api_route("/api/private", methods=["GET", "POST"])
    def private_api() -> dict[str, bool]:
        return {"ok": True}

    install_password_access_gate(
        app,
        password_hash=hash_password("correct-password"),
        session_secret="test-session-secret-with-enough-entropy",
        cookie_secure=True,
        max_attempts=max_attempts,
    )
    return app


def test_password_hash_accepts_correct_password_and_rejects_wrong_password() -> None:
    encoded = hash_password("correct-password", iterations=10_000)

    assert encoded.startswith("pbkdf2_sha256$10000$")
    assert verify_password("correct-password", encoded) is True
    assert verify_password("wrong-password", encoded) is False
    assert verify_password("correct-password", "invalid") is False


def test_unauthenticated_html_request_redirects_to_password_only_login() -> None:
    client = TestClient(_protected_app(), base_url="https://testserver")

    response = client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login?next=%2F"

    login = client.get(response.headers["location"])
    assert login.status_code == 200
    assert 'type="password"' in login.text
    assert 'name="password"' in login.text
    assert 'name="username"' not in login.text
    assert "Cache-Control" in login.headers
    assert login.headers["Cache-Control"] == "no-store"


def test_unauthenticated_api_request_returns_json_401_without_basic_challenge() -> None:
    client = TestClient(_protected_app(), base_url="https://testserver")

    response = client.get("/api/private", headers={"Accept": "application/json"})

    assert response.status_code == 401
    assert response.json() == {"detail": "authentication_required"}
    assert "www-authenticate" not in response.headers


def test_correct_password_sets_secure_cookie_and_allows_access() -> None:
    client = TestClient(_protected_app(), base_url="https://testserver")

    response = client.post(
        "/login",
        data={"password": "correct-password", "next": "/"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookie = response.headers["set-cookie"]
    assert "ilab_access_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=2592000" in cookie
    assert client.get("/").json() == {"ok": True}
    assert client.get("/api/private").json() == {"ok": True}


def test_wrong_password_returns_401_without_session_cookie() -> None:
    client = TestClient(_protected_app(), base_url="https://testserver")

    response = client.post(
        "/login",
        data={"password": "wrong-password", "next": "/"},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert "密码不正确" in response.text
    assert "ilab_access_session" not in response.headers.get("set-cookie", "")


def test_login_rejects_external_redirect_target() -> None:
    client = TestClient(_protected_app(), base_url="https://testserver")

    response = client.post(
        "/login",
        data={"password": "correct-password", "next": "//attacker.example/path"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_logout_clears_session_and_protects_page_again() -> None:
    client = TestClient(_protected_app(), base_url="https://testserver")
    login = client.post("/login", data={"password": "correct-password", "next": "/"}, follow_redirects=False)
    assert login.status_code == 303
    assert client.get("/").status_code == 200

    logout = client.post("/logout", follow_redirects=False)

    assert logout.status_code == 303
    assert logout.headers["location"] == "/login"
    assert "Max-Age=0" in logout.headers["set-cookie"]
    assert client.get("/", headers={"Accept": "text/html"}, follow_redirects=False).status_code == 302


def test_repeated_wrong_password_attempts_are_rate_limited() -> None:
    client = TestClient(_protected_app(max_attempts=2), base_url="https://testserver")

    first = client.post("/login", data={"password": "wrong", "next": "/"})
    second = client.post("/login", data={"password": "wrong", "next": "/"})
    blocked = client.post("/login", data={"password": "correct-password", "next": "/"})

    assert first.status_code == 401
    assert second.status_code == 401
    assert blocked.status_code == 429
    assert "尝试次数过多" in blocked.text


def _real_app(tmp_path, **access_options):
    return create_app(
        input_root=tmp_path / "inputs",
        output_root=tmp_path / "outputs",
        gallery_root=tmp_path / "gallery",
        reference_asset_root=tmp_path / "reference-assets",
        reference_file_root=tmp_path / "reference-files",
        source_data_root=tmp_path / "source-data",
        auth_settings_path=tmp_path / "auth.json",
        api_settings_path=tmp_path / "api.json",
        color_settings_path=tmp_path / "colors.json",
        prompt_snippets_path=tmp_path / "snippets.json",
        prompt_templates_path=tmp_path / "templates.json",
        webui_settings_path=tmp_path / "settings.json",
        queue_path=tmp_path / "queue.json",
        auto_start_queue=False,
        **access_options,
    )


def test_create_app_enables_access_gate_only_when_both_secrets_are_configured(tmp_path) -> None:
    app = _real_app(
        tmp_path,
        access_password_hash=hash_password("correct-password", iterations=10_000),
        access_session_secret="test-session-secret-with-enough-entropy",
    )
    client = TestClient(app, base_url="https://testserver")

    response = client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?next=%2F"


def test_create_app_rejects_partial_access_gate_configuration(tmp_path) -> None:
    with pytest.raises(ValueError, match="configured together"):
        _real_app(tmp_path, access_password_hash=hash_password("correct-password", iterations=10_000))


def test_main_navigation_has_post_logout_control() -> None:
    index_html = Path("codex_image/webui/static/index.html").read_text(encoding="utf-8")
    layout_css = Path("codex_image/webui/static/styles/30-layout-top-nav-panels.css").read_text(encoding="utf-8")

    assert 'class="access-logout-form" method="post" action="/logout"' in index_html
    assert 'class="access-logout-button"' in index_html
    assert ".access-logout-form" in layout_css
    assert ".access-logout-button" in layout_css
    assert ".access-logout-button:focus-visible" in layout_css


def test_session_secret_must_have_at_least_32_characters() -> None:
    from codex_image.webui.access_gate import create_session_cookie

    with pytest.raises(ValueError, match="at least 32 characters"):
        create_session_cookie("too-short")


def test_authenticated_cross_origin_write_is_rejected() -> None:
    client = TestClient(_protected_app(), base_url="https://testserver")
    login = client.post("/login", data={"password": "correct-password", "next": "/"}, follow_redirects=False)
    assert login.status_code == 303

    rejected = client.post("/api/private", headers={"Origin": "https://attacker.example"})
    allowed = client.post("/api/private", headers={"Origin": "https://testserver"})

    assert rejected.status_code == 403
    assert rejected.json() == {"detail": "cross_site_request_rejected"}
    assert allowed.status_code == 200


def test_public_brand_assets_bypass_gate_but_other_static_files_remain_protected() -> None:
    app = FastAPI()
    app.mount(
        "/static",
        StaticFiles(directory=Path("codex_image/webui/static")),
        name="static",
    )
    install_password_access_gate(
        app,
        password_hash=hash_password("correct-password", iterations=10_000),
        session_secret="test-session-secret-with-enough-entropy",
        cookie_secure=True,
    )
    client = TestClient(app, base_url="https://testserver")

    for path in (
        "/static/brand/dachuan-logo-64.png",
        "/static/brand/dachuan-logo-180.png",
        "/static/brand/pwa-icon-192.png",
        "/static/brand/pwa-icon-512.png",
    ):
        response = client.get(path, headers={"Accept": "image/*"})
        assert response.status_code == 200, path
        assert response.headers["content-type"] == "image/png"

    protected = client.get("/static/styles.css", headers={"Accept": "text/css"})
    assert protected.status_code == 401
    assert protected.json() == {"detail": "authentication_required"}

def test_production_entry_requires_access_gate_environment(tmp_path) -> None:
    env = os.environ.copy()
    env.pop("ILAB_WEBUI_ACCESS_PASSWORD_HASH", None)
    env.pop("ILAB_WEBUI_ACCESS_SESSION_SECRET", None)
    env["ILAB_CONJURE_DATA_DIR"] = str(tmp_path / "data")
    env["PYTHONPATH"] = str(Path.cwd())
    result = subprocess.run(
        [sys.executable, "deploy/ilab_conjure_server.py"],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode != 0
    assert "ILAB_WEBUI_ACCESS_PASSWORD_HASH must be configured" in result.stderr
