# 供应商余额显示实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在主界面顶部当前供应商名称旁显示已验证渠道的剩余 USD 余额，并通过服务端安全查询，跳过没有可靠余额协议的渠道。

**Architecture:** 新增独立的 New API 余额服务，读取供应商配置中的可选 `balance_url`、`balance_token`、`balance_user_id` 字段；服务端提供 `/api/provider-balances/{provider_id}`，只返回状态、余额、更新时间，不返回任何凭据。前端在生成目录加载后按选中供应商查询余额，将文案插入现有 themed select trigger 的供应商名称与箭头之间。

**Tech Stack:** FastAPI、httpx、Python `unittest`/pytest、TypeScript、原生 DOM、esbuild。

## Global Constraints

- 只支持复用文档中已验证的 New API 兼容端点：`GET {balance_url}/api/user/self`。
- 余额换算固定使用 `quota / 500000`；已用额度和总额由服务端计算，但默认界面只显示剩余 USD。
- 余额 Token、用户 ID 和 API Key 只能在服务端配置和服务端请求中使用，不进入公开目录、前端代码、响应体或日志。
- Aihub/Sub2API 在本轮没有可靠、已验证的余额接口，保持不显示余额，不猜测其管理端接口。
- 余额请求超时 15 秒；失败返回稳定的 `unavailable` 状态，不影响生图和供应商切换。
- 不新增第三方依赖；复用项目已有 `httpx`。
- 普通供应商设置保存必须保留已有余额字段，前端不负责编辑余额密钥。

---

### Task 1: 扩展供应商余额配置的校验与持久化

**Files:**
- Modify: `codex_image/webui/provider_validation.py`
- Modify: `codex_image/webui/provider_settings.py`
- Test: `tests/test_provider_settings_v2.py`

**Interfaces:**
- Add normalized provider fields: `balance_url: str`, `balance_token: str`, `balance_user_id: str`.
- Add public field: `balance_configured: bool`; never expose `balance_token`.

- [ ] **Step 1: Write the failing tests**

Add tests that create a schema v2 provider with balance fields and assert `ProviderSettings.read()` preserves them, `public_settings()` returns only `balance_configured`, and a subsequent normal provider write does not erase them.

```python
settings = {
    "schema_version": 2,
    "active_provider_id": "relay",
    "default_provider_by_model": {"gpt-image-2": "relay"},
    "providers": [{
        "id": "relay", "name": "Relay", "base_url": "https://relay.example",
        "api_key": "key", "auth_scheme": "bearer", "concurrency": 2,
        "balance_url": "https://relay.example",
        "balance_token": "server-only-token",
        "balance_user_id": "42",
        "bindings": [{
            "id": "relay-image", "canonical_model_id": "gpt-image-2",
            "remote_model_id": "gpt-image-2", "protocol_profile": "openai_images",
            "parameter_codec": "gpt_openai_images", "operations": ["generate", "edit"],
        }],
    }],
}
provider_settings = ProviderSettings(path)
provider_settings.write(settings)
public = provider_settings.public_settings()
provider = public["providers"][0]
assert provider["balance_configured"] is True
assert "balance_token" not in provider
provider_settings.write({**settings, "providers": [{**settings["providers"][0], "name": "Renamed"}]})
assert provider_settings.read()["providers"][0]["balance_token"] == "server-only-token"
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m pytest tests/test_provider_settings_v2.py -q`

Expected: FAIL because balance fields are currently rejected or not preserved/publicly represented.

- [ ] **Step 3: Implement minimal normalization and key-copy semantics**

Add strict optional HTTPS/HTTP URL normalization for `balance_url`, trim token/user ID, copy existing balance fields when omitted in an update, and include only `balance_configured` in `public_settings()`.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_provider_settings_v2.py -q`

Expected: PASS.

---

### Task 2: Implement New API balance service and route

**Files:**
- Create: `codex_image/webui/provider_balance.py`
- Create: `codex_image/webui/routes/provider_balance.py`
- Modify: `codex_image/webui/routes/__init__.py`
- Test: `tests/test_webui_provider_balance.py`

**Interfaces:**
- `parse_new_api_balance(payload: Mapping[str, Any]) -> ProviderBalanceResult`.
- `fetch_provider_balance(provider: Mapping[str, Any], client: httpx.Client | None = None) -> ProviderBalanceResult`.
- `GET /api/provider-balances/{provider_id}` returns:
  - success: `{"provider_id": ..., "status": "ok", "remaining_usd": number, "used_usd": number, "total_usd": number}`
  - unavailable: `{"provider_id": ..., "status": "unavailable"}`

- [ ] **Step 1: Write the failing parser and route tests**

```python
def test_parse_new_api_balance_converts_quota_units():
    result = parse_new_api_balance({"data": {"quota": 5_000_000, "used_quota": 1_000_000}})
    assert result.status == "ok"
    assert result.remaining_usd == 10.0
    assert result.used_usd == 2.0
    assert result.total_usd == 12.0

def test_parse_new_api_balance_rejects_missing_fields():
    assert parse_new_api_balance({"data": {"quota": 1}}).status == "unavailable"

def test_balance_route_never_returns_token():
    response = client.get("/api/provider-balances/relay")
    assert response.status_code == 200
    assert "balance_token" not in response.text
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/test_webui_provider_balance.py -q`

Expected: FAIL because the service, route, and route registration do not exist.

- [ ] **Step 3: Implement the parser, server-side request, and route**

Use `httpx.Client(timeout=15.0)` or the project’s existing HTTP abstraction. Request `GET {balance_url}/api/user/self` with `Authorization: Bearer <balance_token>`, `Content-Type: application/json`, `User-Agent: cc-switch/1.0`, and optional `New-Api-User`. Do not include URLs, headers, or response bodies in error logs. Return `unavailable` for missing config, non-2xx, invalid JSON, or invalid quota values.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_webui_provider_balance.py -q`

Expected: PASS.

---

### Task 3: Add provider balance state and top navigation display

**Files:**
- Modify: `codex_image/webui/static/index.html`
- Modify: `codex_image/webui/static/styles.css`
- Modify: `codex_image/webui/frontend/src/types.ts`
- Modify: `codex_image/webui/frontend/src/state.ts`
- Modify: `codex_image/webui/frontend/src/state-defaults.ts`
- Modify: `codex_image/webui/frontend/src/themed-select.ts`
- Modify: `codex_image/webui/frontend/src/provider-selection.ts`
- Create: `codex_image/webui/frontend/src/provider-balance.ts`
- Test: `tests/frontend/provider_balance_behavior.test.ts`

**Interfaces:**
- `formatProviderBalance(status: ProviderBalanceStatus): string` returns empty for unavailable, `查询中…` for loading, `余额未知` for errors, and `$12.34` for success.
- `refreshProviderBalance(providerId: string | null): Promise<void>` fetches the server route and updates `state.providerBalances`.
- `themed-select.ts` adds `generation-provider-balance` span only to `generationProviderSelect` trigger.

- [ ] **Step 1: Write the failing formatter test**

```ts
import test from "node:test";
import assert from "node:assert/strict";
import { formatProviderBalance } from "../../codex_image/webui/frontend/src/provider-balance";

test("formats successful balance", () => {
  assert.equal(formatProviderBalance({ status: "ok", remaining_usd: 12.34 }), "$12.34");
});
test("hides unavailable balance", () => {
  assert.equal(formatProviderBalance({ status: "unavailable" }), "");
});
```

- [ ] **Step 2: Run frontend test and verify failure**

Run: `npx esbuild tests/frontend/provider_balance_behavior.test.ts --bundle --platform=node --format=esm --target=node20 --outfile=$env:TEMP/provider-balance.test.mjs; node $env:TEMP/provider-balance.test.mjs`

Expected: FAIL because the balance module does not exist.

- [ ] **Step 3: Implement state, DOM hook, and fetch behavior**

Add a `Map`-like provider balance state keyed by provider ID. After catalog refresh and after `selectGenerationProvider`, trigger a non-blocking refresh. The refresh must use a request sequence so stale responses cannot overwrite a later provider selection. Update a dedicated span in the themed select trigger; leave the native select hidden and preserve existing option rendering.

- [ ] **Step 4: Add CSS and static markup hooks**

Add an empty `<span id="generationProviderBalance" class="generation-provider-balance" aria-live="polite"></span>` inside the provider shell or create it in the themed select trigger. Keep it compact, muted, and hidden when empty; do not increase top-nav height. On narrow screens truncate provider name before hiding balance.

- [ ] **Step 5: Run frontend tests and typecheck**

Run: `npx esbuild tests/frontend/provider_balance_behavior.test.ts --bundle --platform=node --format=esm --target=node20 --outfile=$env:TEMP/provider-balance.test.mjs; node $env:TEMP/provider-balance.test.mjs` and `npm run typecheck:webui`.

Expected: PASS and zero TypeScript errors.

---

### Task 4: Configure verified channels only and verify full build

**Files:**
- Modify: deployment/server provider settings file discovered from `api_settings_path`.
- Do not modify: Aihub/Sub2API balance fields until a verified endpoint and response contract are available.

- [ ] **Step 1: Add only the four documented channels**

Set balance fields for the four channels from the local confidential document. Keep the token values out of source control, frontend responses, logs, and chat output. Do not add any balance fields for Aihub.

- [ ] **Step 2: Run backend and frontend verification**

Run:

```powershell
python -m pytest -q
npm run check:webui
```

Expected: all applicable tests pass, TypeScript passes, CSS and JS bundles build.

- [ ] **Step 3: Inspect the diff for secrets**

Run:

```powershell
git diff --check
git diff -- codex_image tests | Select-String -Pattern 'sk-|token|Authorization|balance_token' -CaseSensitive:$false
```

Expected: no real credentials or bearer values in tracked source; only field names and test placeholders may appear.

- [ ] **Step 4: Deploy and smoke-test**

Use the existing server deployment mechanism only after local verification. Check `/api/provider-balances/<verified-provider-id>` through the deployed site, confirm the UI shows the amount for a verified channel, and confirm Aihub has no balance text. If server settings cannot be safely updated without exposing credentials, stop deployment and report the exact blocker.
