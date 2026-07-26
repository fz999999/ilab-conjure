# GPT 输出设置精简 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GPT Image 2 输出设置精简为“比例、分辨率、数量、输出像素反馈”，同时保留所有隐藏参数、历史恢复和 API 兼容能力。

**Architecture:** 撤销已取消的紧凑矩阵提交，但保留真实 `size=auto` 基线。复用现有 `ratio`、`sizeModeSelect`、`orientation` 与 `sizeForPreset()`：比例选择器成为唯一可见尺寸入口，其余低频控件通过永久隐藏类保留在 DOM；服务端只调整缺省质量和审核值，显式请求仍优先。

**Tech Stack:** FastAPI / Python、TypeScript、原生 HTML/CSS、Node `node:test`、Python `unittest`/pytest、esbuild。

---

### Task 1: 保存方案并撤销旧紧凑矩阵

**Files:**
- Create: `docs/superpowers/plans/2026-07-26-gpt-output-settings-simplified.md`
- Restore through revert: `codex_image/webui/static/index.html`
- Restore through revert: `codex_image/webui/frontend/src/api-mode-settings.ts`
- Restore through revert: `codex_image/webui/frontend/src/model-parameters.ts`
- Restore through revert: `tests/test_webui_static_layout.py`
- Restore through revert: `tests/test_webui_static_prompt.py`
- Restore through revert: `tests/test_webui_static_model_parameters.py`

- [ ] **Step 1: 提交本实施计划**

```powershell
git add docs/superpowers/plans/2026-07-26-gpt-output-settings-simplified.md
git commit -m "文档：新增 GPT 输出设置精简实施计划"
```

- [ ] **Step 2: 撤销旧矩阵代码提交**

```powershell
git revert --no-edit a287e24
```

期望：生成新的 revert 提交，不改写历史，且 `042c2e3` 的 `size=auto` 功能仍存在。

- [ ] **Step 3: 验证撤销后的 Auto 基线**

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py -q
```

期望：相关基线测试通过；若测试仍在约束旧矩阵，只修改被旧提交引入的矩阵契约，不删除 Auto 契约。

### Task 2: 服务端隐藏参数默认值

**Files:**
- Modify: `codex_image/webui/routes/generation.py:527-680`
- Test: `tests/test_webui_generation.py`

- [ ] **Step 1: 添加缺省参数与显式覆盖测试**

在现有生成测试夹具中拦截提交给任务服务的参数，分别覆盖 `/api/generate` 和 `/api/edit`：

```python
self.assertEqual(params["size"], "auto")
self.assertEqual(params["quality"], "auto")
self.assertEqual(params["output_format"], "png")
self.assertEqual(params["moderation"], "auto")
self.assertEqual(params["prompt_fidelity"], "strict")
self.assertFalse(params["web_search"])
```

另发起显式 `quality=high`、`moderation=low` 等请求，断言传入值未被覆盖。

- [ ] **Step 2: 运行新测试并确认 RED**

```powershell
python -m pytest tests/test_webui_generation.py -k "default_generation_parameters or explicit_generation_parameters or default_edit_parameters or explicit_edit_parameters" -q
```

期望：缺省质量或审核仍为旧值，测试失败。

- [ ] **Step 3: 最小化修改路由默认值**

```python
quality: str = Form("auto")
moderation: str = Form("auto")
```

只修改 `/api/generate` 与 `/api/edit` 的函数签名；保留 `output_format`、`prompt_fidelity`、`web_search` 和所有显式参数处理。

- [ ] **Step 4: 运行测试并确认 GREEN**

```powershell
python -m pytest tests/test_webui_generation.py -q
```

- [ ] **Step 5: 提交**

```powershell
git add codex_image/webui/routes/generation.py tests/test_webui_generation.py
git commit -m "功能：统一 GPT 隐藏参数的服务端默认值"
```

### Task 3: 统一比例下拉框与尺寸联动

**Files:**
- Modify: `codex_image/webui/static/index.html:610-760`
- Modify: `codex_image/webui/frontend/src/custom-size-controls.ts:260-330`
- Modify: `codex_image/webui/frontend/src/form-controls.ts:105-155`
- Modify: `codex_image/webui/frontend/src/shell-ui.ts:320-370`
- Test: `tests/test_webui_static_layout.py`

- [ ] **Step 1: 添加静态与行为测试**

测试要求：`#ratio` 第一个选项为 `<option value="auto" selected>智能自动匹配</option>`，其后完整保留 11 个固定比例且没有 `custom`；`#sizeModeSelect`、方向与自定义宽高元素仍存在。用现有 JavaScript 提取执行辅助方法断言：

```javascript
ratio.value = "auto";
updateSizeFromPreset();
assert.equal(sizeModeSelect.value, "auto");
assert.equal(size.value, "auto");

ratio.value = "16:9";
updateSizeFromPreset();
assert.equal(sizeModeSelect.value, "preset");
assert.equal(orientation.value, "landscape");
assert.equal(size.value, "1536x864");

ratio.value = "auto";
resolution.value = "4k";
updateSizeFromPreset();
assert.equal(size.value, "auto");
```

- [ ] **Step 2: 运行新测试并确认 RED**

```powershell
python -m pytest tests/test_webui_static_layout.py -k "unified_ratio or automatic_ratio" -q
```

期望：比例选项尚无 `auto`，联动行为测试失败。

- [ ] **Step 3: 实现唯一可见比例入口**

在 `#ratio` 中加入默认项并补全用途文本：

```html
<option value="auto" selected>智能自动匹配</option>
<option value="1:1">1:1 方形/头像/商品</option>
<!-- 其余比例按设计文档顺序保留 -->
```

在 `updateSizeFromPreset()` 开头按比例同步隐藏状态：

```typescript
const selectedRatio = String(els.ratio?.value || "auto");
if (selectedRatio === "auto") {
  if (els.sizeModeSelect) els.sizeModeSelect.value = "auto";
} else {
  if (els.sizeModeSelect) els.sizeModeSelect.value = "preset";
  syncOrientationFromRatio(selectedRatio);
}
```

使用项目现有方向同步方法或同等最小映射，不创建第二套像素计算；固定比例仍调用 `sizeForPreset()`。

- [ ] **Step 4: 更新重置默认状态**

重置/初始化时让 `ratio.value = "auto"`、`sizeModeSelect.value = "auto"`、`size.value = "auto"`；历史恢复后若旧任务为固定比例，继续触发 `updateSizeFromPreset()`。

- [ ] **Step 5: 运行布局及尺寸测试并确认 GREEN**

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_model_parameters.py tests/test_webui_static_history.py -q
npm run typecheck:webui
```

- [ ] **Step 6: 提交**

```powershell
git add codex_image/webui/static/index.html codex_image/webui/frontend/src/custom-size-controls.ts codex_image/webui/frontend/src/form-controls.ts codex_image/webui/frontend/src/shell-ui.ts tests/test_webui_static_layout.py
git commit -m "功能：用统一比例下拉框控制 GPT 画布尺寸"
```

### Task 4: 永久隐藏低频控件但保留参数

**Files:**
- Modify: `codex_image/webui/static/index.html:550-760`
- Modify: `codex_image/webui/static/css/components/forms.css`
- Modify if required: `codex_image/webui/frontend/src/model-parameters.ts`
- Modify if required: `codex_image/webui/frontend/src/api-mode-settings.ts`
- Test: `tests/test_webui_static_layout.py`
- Test: `tests/test_webui_static_prompt.py`
- Test: `tests/test_webui_static_model_parameters.py`

- [ ] **Step 1: 添加永久隐藏契约测试**

断言以下字段容器使用专用 `gpt-output-permanently-hidden` 类，但其输入元素 ID 和默认值仍存在：

```text
apiDirectSettingsNotice
webSearchField
promptFidelityField
sizeModeSelect 的字段容器
orientation 的字段容器
quality 的字段容器
moderation 的字段容器
outputFormatField
customSize
```

同时断言 `ratio`、`resolution`、`nInput` 和输出像素反馈的容器没有该类。

- [ ] **Step 2: 运行新测试并确认 RED**

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py -k "permanently_hidden or simplified_output" -q
```

- [ ] **Step 3: 添加专用永久隐藏样式**

```css
.gpt-output-permanently-hidden {
  display: none !important;
}
```

给字段容器添加该类，不删除任何 `<select>`、`<input>`、选项或元素 ID。`!important` 防止模型显隐逻辑移除普通 `.hidden` 后重新展示这些字段。

- [ ] **Step 4: 保持隐藏字段参数链完整**

确认 `renderModelParameters()`、API 模式切换和提示词处理代码可以继续更新隐藏元素，但不得移除永久隐藏类。确认提交代码仍读取：

```text
quality=auto
output_format=png
moderation=auto
prompt_fidelity=strict
web_search=false
```

- [ ] **Step 5: 运行相关测试并确认 GREEN**

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py tests/test_webui_static_output_settings_lock.py -q
npm run typecheck:webui
```

- [ ] **Step 6: 提交**

```powershell
git add codex_image/webui/static/index.html codex_image/webui/static/css/components/forms.css codex_image/webui/frontend/src/model-parameters.ts codex_image/webui/frontend/src/api-mode-settings.ts tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py
git commit -m "界面：隐藏 GPT 低频输出设置并保留参数能力"
```

### Task 5: 请求、历史与自定义 API 兼容回归

**Files:**
- Test: `tests/test_webui_static_tasks.py`
- Test: `tests/test_webui_static_history.py`
- Test: `tests/test_webui_generation.py`
- Test: `tests/test_generation_parameter_normalizer.py`（若现有自定义尺寸测试位于其他文件，则使用实际文件）

- [ ] **Step 1: 增补缺失的兼容测试**

验证默认表单继续追加隐藏参数；历史任务恢复时隐藏字段存在且不会抛错；API 显式提交 `size=1536x1024` 或合法自定义尺寸时仍进入原参数归一化流程；数量 `n=4` 仍原样传递。

- [ ] **Step 2: 运行兼容测试并确认结果**

```powershell
python -m pytest tests/test_webui_static_tasks.py tests/test_webui_static_history.py tests/test_webui_generation.py -q
```

若新增测试为 RED，只做恢复兼容所需的最小改动，不恢复任何前端入口。

- [ ] **Step 3: 提交测试或最小兼容修复**

```powershell
git add tests codex_image/webui/frontend/src codex_image/webui/routes/generation.py
git commit -m "测试：保护 GPT 隐藏参数与历史任务兼容"
```

### Task 6: 构建、视觉验收与交付

**Files:**
- Generated: `codex_image/webui/static/app.js`
- Generated: `codex_image/webui/static/app.js.map`
- Generated as applicable: `codex_image/webui/static/css/app.css`

- [ ] **Step 1: 运行完整前端构建**

```powershell
npm run check:webui
```

期望：CSS 构建、TypeScript 类型检查和 esbuild 全部退出码 0。

- [ ] **Step 2: 运行全套相关测试与差异检查**

```powershell
python -m pytest tests/test_webui_generation.py tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py tests/test_webui_static_history.py tests/test_webui_static_tasks.py tests/test_webui_static_output_settings_lock.py -q
git diff --check
git status --short
```

- [ ] **Step 3: 本地无费用视觉验收**

启动本地服务，仅打开页面验证，不点击真实生成：桌面与移动宽度、浅色与深色主题下只显示比例/分辨率/数量/输出像素；默认显示“智能自动匹配”和 `auto`；固定比例后像素反馈正确；无横向溢出。

- [ ] **Step 4: 提交构建产物和最终调整**

```powershell
git add codex_image/webui/static docs tests
git commit -m "构建：更新 GPT 输出设置前端产物"
```

- [ ] **Step 5: 推送、合并并部署**

将功能分支合并到本地 `main`，推送 GitHub `main`，服务器 `/opt/ilab-conjure` 拉取同一提交并重启 `ilab-conjure.service`。核对：

```text
local main SHA == GitHub main SHA == server SHA
```

在线仅做页面与健康检查，不发起付费生成。
