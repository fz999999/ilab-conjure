# 大川生图站品牌替换设计

## 目标

将 WebUI 中所有用户可见的 `iLab CONJURE` 品牌统一替换为 `大川生图站`，并使用用户提供的正方形照片作为首页 Logo、登录页 Logo、favicon、Apple Touch Icon 和 PWA 图标。

## 已批准方案

采用方案 A：保留原照片完整构图，不裁掉人物、马匹或天空。页面中以圆角方形展示照片；不同平台图标只做高质量等比缩放，不重新绘制、不加文字水印。

源图片：`D:\Desktop\微信图片_2026-07-08_181514_155.jpg`，JPEG，939 × 939。

## 范围

### 修改

- 首页浏览器标题、侧栏品牌文字、品牌无障碍名称和 Logo。
- 历史页浏览器标题、favicon、Apple Touch Icon。
- 登录页标题、站名、Logo 和 favicon。
- PWA `name`、`short_name`、中文描述及 192/512 图标。
- FastAPI 应用标题和静态文件缺失时的后备页面标题。
- 前端默认文档标题及 13 个语言文件中的历史页文档标题。
- 登录门禁只公开本次品牌图片的精确 URL；其他静态资源继续要求登录。

### 不修改

- Python 包名、模块名和内部存储键。
- `ilab-conjure.service`、`/opt/ilab-conjure`、部署入口名称。
- API User-Agent、发行打包脚本、桌面启动器内部品牌。
- 既有登录密码、会话密钥和供应商余额配置。

## 静态资源

生成以下 PNG：

- `codex_image/webui/static/brand/dachuan-logo-64.png`：favicon。
- `codex_image/webui/static/brand/dachuan-logo-180.png`：首页和登录页 Logo、Apple Touch Icon。
- `codex_image/webui/static/brand/pwa-icon-192.png`：PWA 图标。
- `codex_image/webui/static/brand/pwa-icon-512.png`：PWA 图标。

所有图片保持 1:1 比例和完整画面。首页 Logo 使用 42 × 42 CSS 尺寸，登录页使用 58 × 58 CSS 尺寸，均使用 `object-fit: cover` 与圆角边框。

## 安全设计

登录页未建立会话时也需要加载 Logo。门禁中增加精确路径白名单，仅允许以上四张品牌图片匿名访问。不得放开整个 `/static`；样式表、脚本、生成结果和 API 仍由现有会话门禁保护。

登录页 CSP 增加 `img-src 'self'`，其他限制保持不变。

## 验收标准

1. 首页、历史页、登录页和 PWA 元数据均显示 `大川生图站`。
2. 上述用户可见文件不再包含 `iLab CONJURE`。
3. 首页和登录页显示用户照片，照片无拉伸、无额外裁切。
4. favicon、Apple Touch Icon、PWA 192/512 图标尺寸正确。
5. 未登录可访问精确品牌图片，其他静态资源仍返回 401 或重定向登录。
6. 原有单密码登录、供应商余额查询、退出登录和前端构建不受影响。
