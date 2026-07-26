# 单密码登录实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将公网 iLab CONJURE 入口改为仅输入一个密码的应用内登录，并保持所有 WebUI API 受保护。

**Architecture:** 在 FastAPI 内增加独立的访问门禁模块。登录页和认证路由由应用提供，登录成功后使用 HMAC 签名 Cookie；生产密码哈希和会话密钥通过 systemd 环境文件注入。Nginx 只负责 HTTPS 反向代理，不再弹出 Basic Auth。

**Tech Stack:** Python 3.13、FastAPI/Starlette、PBKDF2-HMAC-SHA256、HMAC-SHA256、Nginx、systemd。

---

### Task 1: 建立访问门禁的失败测试

**Files:**
- Create: `tests/test_webui_access_gate.py`
- Test: `codex_image/webui/access_gate.py`

- [ ] **Step 1: 写测试覆盖哈希、Cookie、登录和保护行为**

测试以下行为：
- `hash_password`/`verify_password` 能验证正确密码并拒绝错误密码。
- 未认证 HTML 请求重定向到 `/login`。
- 未认证 API 请求返回 JSON 401。
- 正确密码登录返回 303 并设置安全 Cookie。
- 错误密码返回 401。
- 有效 Cookie 可以访问受保护资源。
- `/logout` 清除 Cookie。

- [ ] **Step 2: 运行测试确认失败**

```powershell
python -m pytest tests/test_webui_access_gate.py -q
```

Expected: FAIL，因为访问门禁模块尚不存在。

---

### Task 2: 实现独立的访问门禁模块

**Files:**
- Create: `codex_image/webui/access_gate.py`
- Modify: `codex_image/webui/app.py`

- [ ] **Step 1: 添加 PBKDF2 密码哈希和 HMAC Cookie 工具**

接口固定为：

```python
def hash_password(password: str, *, iterations: int = 310_000) -> str: ...
def verify_password(password: str, encoded_hash: str) -> bool: ...
def create_session_cookie(session_secret: str, *, now: int | None = None, ttl_seconds: int = 2_592_000) -> str: ...
def verify_session_cookie(session_secret: str, cookie: str | None, *, now: int | None = None) -> bool: ...
```

哈希格式：`pbkdf2_sha256$iterations$base64_salt$base64_digest`。Cookie 使用带过期时间的签名载荷，使用 `secrets.compare_digest`。

- [ ] **Step 2: 添加限速器和登录页**

实现按客户端 IP 的内存失败记录：5 分钟窗口内最多 5 次失败；成功登录后清除记录。登录页使用内联 HTML/CSS，只包含一个 `password` 输入框、提交按钮和错误提示。

- [ ] **Step 3: 添加 Starlette HTTP 中间件**

中间件行为：
- `/login` 的 GET/POST 和 `/logout` 允许未认证访问。
- 有效 Cookie 放行全部请求。
- 未认证的 HTML 请求 302 到 `/login?next=...`。
- 未认证 API/资源请求返回 `401` JSON。
- `next` 只接受以单个 `/` 开头的站内路径。
- 登录成功设置 `ilab_access_session` Cookie：`HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=2592000`。
- 登出清除同名 Cookie。

- [ ] **Step 4: 将门禁接入 `create_app`**

增加可选参数 `access_password_hash`、`access_session_secret`。仅当二者都存在时启用门禁；无配置时保持现有测试和本地开发行为。

- [ ] **Step 5: 运行测试确认通过**

```powershell
python -m pytest tests/test_webui_access_gate.py -q
```

Expected: 全部通过。

---

### Task 3: 增加退出入口

**Files:**
- Modify: `codex_image/webui/static/index.html`
- Modify: `codex_image/webui/static/styles.css`

- [ ] **Step 1: 在顶部导航增加退出按钮**

按钮提交 `POST /logout`，不把密码或会话值写入 JavaScript。

- [ ] **Step 2: 使用现有主题变量补充按钮样式**

保持浅色、深色主题可见性和键盘焦点样式。

- [ ] **Step 3: 运行前端构建和静态契约测试**

```powershell
npm run check:webui
python -m pytest tests/test_webui_refactor_contract.py -q
```

---

### Task 4: 生成生产配置并更新部署入口

**Files:**
- Modify: `.omx/deploy/ilab_conjure_server.py`
- Create: `docs/superpowers/specs/2026-07-25-single-password-login-design.md`
- Create: `docs/superpowers/plans/2026-07-25-single-password-login.md`

- [ ] **Step 1: 从环境变量读取访问门禁配置**

部署入口读取：
- `ILAB_WEBUI_ACCESS_PASSWORD_HASH`
- `ILAB_WEBUI_ACCESS_SESSION_SECRET`

不得在源码中写入明文密码。

- [ ] **Step 2: 用一次性脚本生成 PBKDF2 哈希**

在本机生成哈希后，通过受控 SSH 命令写入服务器 root 仅可读环境文件；明文密码不写入文件、不进入 Git、不打印到日志。

- [ ] **Step 3: 生成随机会话密钥**

使用 Python `secrets.token_urlsafe(32)`，写入同一环境文件。

---

### Task 5: 备份、修改 Nginx 并部署

**Files:**
- Remote: `/etc/nginx/sites-enabled/*` 中 `image.84868988.xyz:8443` 对应配置
- Remote: `/etc/systemd/system/ilab-conjure.service.d/10-access-gate.conf`

- [ ] **Step 1: 备份 Nginx 和 systemd 配置**

备份到带 UTC 时间戳的 `/opt/ilab-conjure/deploy/backups/` 目录。

- [ ] **Step 2: 写入环境覆盖文件并 daemon-reload**

环境文件权限设置为 `0600`，内容只包含哈希和随机会话密钥。

- [ ] **Step 3: 移除 `auth_basic` 配置**

只修改 `image.84868988.xyz` 的 8443 HTTPS server 块，保留 TLS、代理目标和其他站点配置。

- [ ] **Step 4: 检查并重载 Nginx，重启 WebUI**

```bash
nginx -t
systemctl daemon-reload
systemctl restart ilab-conjure.service
systemctl reload nginx
```

---

### Task 6: 端到端验证

- [ ] **Step 1: 未登录访问**

确认公网 `/` 返回登录页，状态不是 401 Basic Auth challenge，页面只有密码输入框。

- [ ] **Step 2: 错误密码**

确认返回 401 且不会设置有效会话 Cookie。

- [ ] **Step 3: 正确密码**

确认进入主页面、API 返回 200、余额查询接口仍可用。

- [ ] **Step 4: 登出**

确认 POST `/logout` 后 Cookie 失效，访问 `/` 再次回到登录页。

- [ ] **Step 5: 服务检查**

确认 Nginx 配置和 systemd 服务均为正常状态。
