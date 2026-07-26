# 大川生图站品牌替换实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 WebUI 用户可见品牌统一改为“大川生图站”，并用指定照片替换页面 Logo、favicon 和 PWA 图标。

**Architecture:** 使用现有静态资源目录保存四个等比缩放 PNG；首页、历史页、登录页和 manifest 统一引用这些资源。登录门禁增加精确公开路径集合，保证未登录页面可以加载品牌图片，同时保持其他静态文件受保护。

**Tech Stack:** Python 3、FastAPI/Starlette、HTML/CSS、TypeScript、Pillow（仅用于一次性生成静态图片，项目不新增依赖）

## Global Constraints

- 站名必须精确为 `大川生图站`。
- 保留照片完整构图，不裁掉人物、马匹或天空。
- 不增加项目依赖。
- 不修改服务名、服务器目录、Python 包名、内部模块名和登录凭据。
- 不清理或回退工作区中其他未提交修改。
- 先运行失败测试，再修改生产代码。

---

### Task 1: 品牌契约测试

**Files:**
- Create: `tests/test_webui_branding.py`
- Modify: `tests/test_webui_access_gate.py`

**Interfaces:**
- Consumes: 现有静态 HTML、manifest、登录门禁中间件。
- Produces: 品牌文字、图片尺寸、资源引用和匿名访问边界的回归测试。

- [ ] 写入品牌文字、图片路径、PNG 尺寸和登录页引用测试。
- [ ] 写入“品牌图片匿名可访问、其他静态文件仍受保护”测试。
- [ ] 运行两个测试文件，确认因新品牌尚未实现而失败。

### Task 2: 生成品牌图片并替换页面品牌

**Files:**
- Create: `codex_image/webui/static/brand/dachuan-logo-64.png`
- Create: `codex_image/webui/static/brand/dachuan-logo-180.png`
- Modify: `codex_image/webui/static/brand/pwa-icon-192.png`
- Modify: `codex_image/webui/static/brand/pwa-icon-512.png`
- Modify: `codex_image/webui/static/index.html`
- Modify: `codex_image/webui/static/history.html`
- Modify: `codex_image/webui/static/manifest.webmanifest`
- Modify: `codex_image/webui/static/styles.css`（由 CSS 构建脚本生成）
- Modify: `codex_image/webui/static/styles/30-layout-top-nav-panels.css`

**Interfaces:**
- Consumes: 939 × 939 用户照片。
- Produces: 64、180、192、512 像素 PNG 及页面图片引用。

- [ ] 使用 Pillow LANCZOS 等比缩放生成四个 PNG，不裁切。
- [ ] 将首页内联兔子 SVG 替换为图片标签，并更新站名、标题、favicon、Apple Touch Icon。
- [ ] 更新历史页标题及图标链接。
- [ ] 更新 manifest 名称、描述和图标元数据。
- [ ] 调整 Logo 圆角、边框和对象适配 CSS。

### Task 3: 登录页、后备页面和前端标题

**Files:**
- Modify: `codex_image/webui/access_gate.py`
- Modify: `codex_image/webui/app.py`
- Modify: `codex_image/webui/frontend/src/state-defaults.ts`
- Modify: `codex_image/webui/frontend/src/i18n/*.ts`
- Modify: `tests/test_webui_static_layout.py`
- Modify: `tests/test_webui_static_i18n.py`
- Modify: `tests/test_webui_static_model_providers.py`

**Interfaces:**
- Produces: 登录页品牌 HTML、精确公开资源集合、统一文档标题。

- [ ] 登录页改用图片 Logo，增加 favicon 和允许同源图片的 CSP。
- [ ] 中间件仅对白名单品牌图片跳过认证。
- [ ] 替换 FastAPI 标题、后备页面标题、默认标题和 13 个历史页标题。
- [ ] 更新既有测试中已经过时的旧品牌断言。
- [ ] 运行品牌与门禁测试，确认通过。

### Task 4: 构建、回归和视觉检查

**Files:**
- Modify: `codex_image/webui/static/app.js`
- Modify: `codex_image/webui/static/app.js.map`
- Modify: `codex_image/webui/static/history.js`
- Modify: `codex_image/webui/static/history.js.map`
- Create: `.omx/state/dachuan-branding/ralph-progress.json`

- [ ] 运行 `npm run check:webui` 重新生成 CSS/JS 并完成类型检查。
- [ ] 运行品牌、门禁、供应商余额、供应商路由和重构契约测试。
- [ ] 运行 Python 编译检查和 `git diff --check`。
- [ ] 启动本地服务，截取登录页、主界面浅色/深色截图。
- [ ] 执行 visual-verdict，将 JSON 保存到 `.omx/state/dachuan-branding/ralph-progress.json`；低于 90 分则按建议修正并重跑。

### Task 5: 服务器部署与公网验证

**Files:**
- Server backup: `/opt/ilab-conjure/deploy/backups/<UTC>-dachuan-branding/`
- Server project: `/opt/ilab-conjure/`

- [ ] 通过 SSH 创建 UTC 时间备份目录并备份本次修改文件。
- [ ] 上传 Python、HTML、CSS、JS、manifest 和图片资产。
- [ ] 重启 `ilab-conjure.service`。
- [ ] 验证 `systemctl is-active ilab-conjure.service` 与 `nginx -t`。
- [ ] 在公网验证登录页 Logo/站名、登录后首页 Logo/站名、favicon、历史页和 manifest；确认余额查询与退出登录仍工作。
