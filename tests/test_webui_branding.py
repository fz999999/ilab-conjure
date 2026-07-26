from __future__ import annotations

import json
from pathlib import Path
import struct

from fastapi import FastAPI
from fastapi.testclient import TestClient

from codex_image.webui.access_gate import hash_password, install_password_access_gate


BRAND_NAME = "大川生图站"
BRAND_ICON_64 = "/static/brand/dachuan-logo-64.png"
BRAND_ICON_180 = "/static/brand/dachuan-logo-180.png"


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def _protected_login_page():
    app = FastAPI()
    install_password_access_gate(
        app,
        password_hash=hash_password("correct-password", iterations=10_000),
        session_secret="test-session-secret-with-enough-entropy",
        cookie_secure=True,
    )
    return TestClient(app, base_url="https://testserver").get("/login")


def test_user_visible_brand_copy_is_dachuan_everywhere() -> None:
    exact_brand_files = [
        Path("codex_image/webui/access_gate.py"),
        Path("codex_image/webui/app.py"),
        Path("codex_image/webui/static/index.html"),
        Path("codex_image/webui/static/history.html"),
        Path("codex_image/webui/static/manifest.webmanifest"),
        Path("codex_image/webui/frontend/src/state-defaults.ts"),
        Path("codex_image/webui/static/app.js"),
        Path("codex_image/webui/static/history.js"),
        *sorted(Path("codex_image/webui/frontend/src/i18n").glob("*.ts")),
    ]

    for path in exact_brand_files:
        source = path.read_text(encoding="utf-8")
        assert "iLab CONJURE" not in source, path

    assert BRAND_NAME in Path("codex_image/webui/static/index.html").read_text(encoding="utf-8")
    assert BRAND_NAME in Path("codex_image/webui/static/history.html").read_text(encoding="utf-8")
    assert BRAND_NAME in Path("codex_image/webui/access_gate.py").read_text(encoding="utf-8")


def test_home_and_history_use_photo_brand_icons() -> None:
    index = Path("codex_image/webui/static/index.html").read_text(encoding="utf-8")
    history = Path("codex_image/webui/static/history.html").read_text(encoding="utf-8")
    styles = Path("codex_image/webui/static/styles.css").read_text(encoding="utf-8")

    for html in (index, history):
        assert f'<link rel="icon" type="image/png" sizes="64x64" href="{BRAND_ICON_64}" />' in html
        assert f'<link rel="apple-touch-icon" sizes="180x180" href="{BRAND_ICON_180}" />' in html

    assert f'<img class="brand-logo-image" src="{BRAND_ICON_180}" alt=""' in index
    assert f'aria-label="{BRAND_NAME}"' in index
    assert f'<div class="brand-name">{BRAND_NAME}</div>' in index
    assert "brand-rabbit-logo" not in index
    assert ".brand-logo-image" in styles
    assert "object-fit: cover" in styles

    worker = Path("codex_image/webui/static/service-worker.js").read_text(encoding="utf-8")
    assert BRAND_ICON_64 in worker
    assert BRAND_ICON_180 in worker
    assert "/static/brand/favicon.svg" not in worker


def test_manifest_uses_dachuan_name_description_and_photo_icons() -> None:
    manifest = json.loads(Path("codex_image/webui/static/manifest.webmanifest").read_text(encoding="utf-8"))

    assert manifest["name"] == BRAND_NAME
    assert manifest["short_name"] == BRAND_NAME
    assert manifest["description"] == "大川生图站，支持图片生成与编辑。"
    assert [(icon["src"], icon["sizes"]) for icon in manifest["icons"]] == [
        ("/static/brand/pwa-icon-192.png", "192x192"),
        ("/static/brand/pwa-icon-512.png", "512x512"),
    ]


def test_brand_photo_assets_exist_with_expected_dimensions() -> None:
    expected = {
        "dachuan-logo-64.png": (64, 64),
        "dachuan-logo-180.png": (180, 180),
        "pwa-icon-192.png": (192, 192),
        "pwa-icon-512.png": (512, 512),
    }
    brand_dir = Path("codex_image/webui/static/brand")

    for filename, size in expected.items():
        path = brand_dir / filename
        assert path.is_file(), path
        assert _png_size(path) == size


def test_login_page_uses_dachuan_brand_and_public_photo() -> None:
    response = _protected_login_page()
    page = response.text

    assert f"<title>登录 · {BRAND_NAME}</title>" in page
    assert f"<h1>{BRAND_NAME}</h1>" in page
    assert f'<link rel="icon" type="image/png" sizes="64x64" href="{BRAND_ICON_64}" />' in page
    assert f'<img class="login-logo" src="{BRAND_ICON_180}" alt="{BRAND_NAME}"' in page
    assert "img-src 'self'" in response.headers["content-security-policy"]
