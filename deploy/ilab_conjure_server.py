from __future__ import annotations

import os
from pathlib import Path

from codex_image.webui.app import create_app


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} must be configured for production WebUI access control")
    return value


ACCESS_PASSWORD_HASH = required_env("ILAB_WEBUI_ACCESS_PASSWORD_HASH")
ACCESS_SESSION_SECRET = required_env("ILAB_WEBUI_ACCESS_SESSION_SECRET")
DATA_DIR = Path(os.environ.get("ILAB_CONJURE_DATA_DIR", "/var/lib/ilab-conjure")).resolve()
INPUT_ROOT = DATA_DIR / "webui-inputs"
OUTPUT_ROOT = DATA_DIR / "webui-outputs"

DATA_DIR.mkdir(parents=True, exist_ok=True)

app = create_app(
    input_root=INPUT_ROOT,
    output_root=OUTPUT_ROOT,
    gallery_root=INPUT_ROOT / "gallery",
    reference_asset_root=INPUT_ROOT / "reference-assets",
    source_data_root=OUTPUT_ROOT / "source-data",
    webui_settings_path=DATA_DIR / "webui-settings.json",
    auth_settings_path=DATA_DIR / "webui-auth-settings.json",
    api_settings_path=DATA_DIR / "webui-api-settings.json",
    color_settings_path=DATA_DIR / "webui-color-settings.json",
    prompt_snippets_path=DATA_DIR / "webui-prompt-snippets.json",
    prompt_templates_path=DATA_DIR / "webui-prompt-templates.json",
    access_password_hash=ACCESS_PASSWORD_HASH,
    access_session_secret=ACCESS_SESSION_SECRET,
)
