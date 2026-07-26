# GPT 输出设置三态紧凑重排 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留 GPT Image 2 `auto/preset/custom` 三种真实尺寸语义的前提下，把 9 个输出设置和输出像素预览重排为随尺寸模式变化的紧凑响应式矩阵，减少默认首屏高度，并确保 `auto` 最终仍以 `size: "auto"` 提交给供应商。

**Architecture:** 以当前提交 `042c2e3` 的 Auto 尺寸功能作为不可回退的行为基线。保留现有原生 `<select>`、控件 ID、option value、TypeScript 事件绑定和隐藏字段 `#size`，只重组输出设置顶层 DOM、字段显隐目标和 CSS Grid；`.settings-grid` 提供容器查询上下文，`.compact-output-settings` 根据 `auto-size-mode`、默认 `preset` 和 `custom-size-mode` 使用不同字段跨度。

**Tech Stack:** HTML、CSS Grid、CSS Container Queries、TypeScript、Python `pytest`、Node.js `node:test`、esbuild、TypeScript 6

---

## 文档状态与实施基线

本计划已在 **2026 年 7 月 26 日** 按当前 Auto 功能重新编写。执行布局改造前，必须先确认工作区包含提交：

```text
042c2e3 让 GPT Image 2 默认由模型自动决定画布尺寸
```

Auto 已经是现有功能，不属于本计划待实现项。本计划只能保护和适配它，不能重新定义它。

| 已有能力 | 当前契约 | 本计划要求 |
|---|---|---|
| 模型默认值 | `gpt-image-2` 的 `canvas.size.default == "auto"` | 保留 |
| HTML 默认值 | `sizeModeSelect=auto`、隐藏字段 `size=auto` | 保留 |
| 尺寸模式 | `auto/preset/custom` 三态 | 保留并用于布局分支 |
| Auto 显隐 | 隐藏方向、分辨率、比例、自定义尺寸 | 保留 |
| Preset 显隐 | 显示方向、分辨率、比例，隐藏自定义尺寸 | 保留 |
| Custom 显隐 | 隐藏方向、分辨率、比例，显示自定义尺寸 | 保留 |
| 参数提交 | `canvas.size="auto"` | 必须继续提交 |
| Images 负载 | 顶层 `size: "auto"` | 必须继续提交 |
| Responses 负载 | `tools[].size: "auto"` | 必须继续提交 |
| 历史恢复 | `auto` 恢复 Auto；像素尺寸恢复 Preset/Custom | 保留 |
| 默认像素提示 | `输出像素: auto（OpenAI 自动选择）` | 改成紧凑状态块，但语义不变 |

### 禁止回退

- 不得把 `auto` 转换为 `1024x1024`。
- 不得仅在前端显示“自动”，却从 `parameters_json` 中删除 `canvas.size`。
- 不得通过 CSS 隐藏字段后把其草稿值清空。
- 不得把 `auto` 重新解释成 `preset`。
- 不得修改 GPT Image 2 的供应商协议或增加第三方依赖。

---

## 方案确认

采用 **12 列响应式矩阵 + 三态布局修饰类**。

| 项目 | 确认结果 |
|---|---|
| 查询容器 | `container-type` 放在父级 `.settings-grid`，不能放在需要改变自身列数的 `.compact-output-settings` 上 |
| DOM/键盘顺序 | 提示词处理 → 尺寸模式 → 方向 → 分辨率 → 比例 → 质量 → 数量 → 审核 → 自定义尺寸 → 输出格式 → 输出像素 |
| Auto 默认布局 | 只显示 7 个块；宽容器一行，中等容器两行 |
| Preset 布局 | 显示 10 个块；宽容器固定两行 |
| Custom 布局 | 显示 8 个块；宽容器两行，自定义尺寸与格式/像素共享第二行 |
| GPT 专用显隐 | 提示词处理移出 `modeSpecificSettings` 后独立显隐；主模型/API 直连提示仍由 `modeSettingsSlot` 控制 |
| 旧版参数显隐 | 拆除 `quantity-quality-row` 后，`model-parameters.ts` 分别定位质量和数量字段 |
| 压缩率 | PNG 隐藏；JPEG/WebP 沿用现有按钮和弹层 |
| 输出像素 | 移除内联样式，改为矩阵中的状态块；Auto 显示自动语义，Preset/Custom 显示像素 |
| 依赖 | 不增加依赖，不实现自定义下拉组件 |

---

## 三种尺寸模式的目标布局

### 1. Auto：默认且最紧凑

容器宽度 `>= 900px`：

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ 提示词处理 │ 尺寸模式：自动 │ 质量 │ 数量 │ 审核 │ 输出格式 │ 输出像素：Auto │
└──────────────────────────────────────────────────────────────────────────────┘
```

12 列跨度：

| 字段 | 列跨度 |
|---|---:|
| 提示词处理 | 2 |
| 尺寸模式 | 2 |
| 质量 | 1 |
| 数量 | 1 |
| 审核 | 2 |
| 输出格式 | 2 |
| 输出像素 | 2 |

约束：

- `.orientation-field`、`.resolution-field`、`.ratio-field`、`.custom-size` 必须为 `display: none`。
- 输出像素短块只显示 Auto 状态，不伪造具体像素。
- JPEG/WebP 出现压缩率按钮时，输出格式块仍有足够宽度。

### 2. Preset：完整预设矩阵

容器宽度 `>= 900px`：

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ 提示词处理      │ 尺寸模式      │ 方向   │ 分辨率 │ 比例                    │
│ 质量            │ 数量          │ 审核   │ 输出格式          │ 输出像素 │
└──────────────────────────────────────────────────────────────────────────────┘
```

12 列跨度：

| 字段 | 列跨度 |
|---|---:|
| 提示词处理 | 3 |
| 尺寸模式 | 3 |
| 方向 | 2 |
| 分辨率 | 2 |
| 比例 | 2 |
| 质量 | 2 |
| 数量 | 2 |
| 审核 | 2 |
| 输出格式 | 4 |
| 输出像素 | 2 |

约束：

- 方向、分辨率和比例联动保持原样。
- `#size` 必须继续保存计算后的 `宽x高`。
- 自定义尺寸面板隐藏且不占网格位置。

### 3. Custom：自定义卡片参与矩阵

容器宽度 `>= 900px`：

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ 提示词处理 │ 尺寸模式：自定义 │ 质量 │ 数量 │ 审核                        │
│ 自定义尺寸面板（8/12）                 │ 输出格式（2/12） │ 像素（2/12） │
└──────────────────────────────────────────────────────────────────────────────┘
```

约束：

- 方向、分辨率和预设比例隐藏。
- 自定义尺寸面板在宽容器占 `8/12`，不再强制独占一整行。
- 输出格式和输出像素与自定义尺寸同处第二行，顶部对齐。
- 宽高、交换宽高、比例锁定、首图比例、验证提示和像素预览保持原逻辑。
- 容器小于 `900px` 时，自定义尺寸面板恢复整行，避免内部控件拥挤。

---

## 响应式规则

| `.settings-grid` 容器宽度 | 网格 | Auto | Preset | Custom |
|---|---|---|---|---|
| `>= 900px` | 12 列 | 1 行 | 2 行 | 2 行 |
| `680–899px` | 6 列 | 2 行 | 4 行 | 4 行，自定义面板整行 |
| `360–679px` | 2 列 | 4 行 | 5 行 | 自定义面板整行 |
| `< 360px` | 1 列 | 7 行 | 10 行 | 自定义面板整行 |

通用标准：

| 属性 | 目标值 |
|---|---|
| 下拉框最小高度 | `36px` |
| 标签到控件间距 | `6px` |
| 字段横向间距 | `10px` |
| 字段纵向间距 | `12px` |
| 字段最小宽度 | `0` |
| 焦点环 | 不被容器裁切 |
| 横向滚动 | 不允许 |
| 标签裁切 | 不允许；超窄视口改为单列 |
| Auto 宽屏高度 | 比当前旧布局减少至少 `45%` |
| Preset 宽屏高度 | 比当前旧布局减少 `35%–45%` |

---

## 范围与文件职责

| 文件 | 职责 |
|---|---|
| `codex_image/webui/static/index.html` | 建立紧凑矩阵，移动提示词和自定义尺寸节点，拆除质量/数量组合容器，移除像素预览内联样式 |
| `codex_image/webui/static/styles/70-output-settings.css` | 三态矩阵、字段跨度、像素状态块、容器查询和自定义尺寸布局 |
| `codex_image/webui/static/styles/80-utilities-responsive.css` | 删除与新矩阵冲突的旧短屏选择器 |
| `codex_image/webui/static/styles.css` | 由 `npm run build:webui:css` 生成，不手工编辑 |
| `codex_image/webui/frontend/src/api-mode-settings.ts` | 提示词处理从模式槽显隐中解耦 |
| `codex_image/webui/frontend/src/model-parameters.ts` | 拆除组合容器后分别控制质量/数量；保持三态修饰类 |
| `codex_image/webui/frontend/src/custom-size-controls.ts` | 只做回归保护；不改变 `auto/preset/custom` 状态机和 `#size` 赋值 |
| `codex_image/providers/codecs/gpt_image.py` | 只做回归保护；继续原样传递 `canvas.size` |
| `tests/test_webui_static_layout.py` | DOM 顺序、三态跨度、断点、自定义尺寸和像素块契约 |
| `tests/test_webui_static_prompt.py` | 提示词处理移位后的 GPT/API 模式显隐 |
| `tests/test_webui_static_model_parameters.py` | GPT 旧版字段独立显隐与三态 class |
| `tests/test_webui_static_output_settings_overlay.py` | 锁定摘要覆盖编辑区 |
| `tests/test_webui_static_output_settings_lock.py` | 锁定、任务参数采用和草稿恢复 |
| `tests/test_webui_static_short_height.py` | 短屏高度规则不依赖旧 DOM |
| `tests/test_generation_catalog.py` | GPT Image 2 的 `canvas.size` 默认值保持 Auto |
| `tests/test_legacy_provider_adapters.py` | 四条 GPT 协议路径继续提交 `size="auto"` |
| `tests/frontend/model_parameters_history.test.ts` | 三态草稿、历史恢复和隐藏参数提交行为 |

---

## 不改变的行为

- 9 个 `<select>` 的 ID、既有 option value 和 i18n key。
- `sizeModeSelect` 的 `auto/preset/custom` 三个值及默认 `auto`。
- 隐藏的 `customSizeToggle` 与新三态选择框的兼容同步。
- `auto` 时隐藏字段 `size` 为字符串 `"auto"`。
- `preset` 时方向、分辨率、比例联动和像素计算。
- `custom` 时宽高、交换、比例锁定和首图比例。
- 质量、数量、审核、输出格式和压缩率提交参数。
- 参数草稿保存、恢复、任务历史检查和“使用此任务参数”。
- 输出设置锁定摘要、遮罩和解锁行为。
- 深色/浅色主题变量、原生键盘选择、Tab 顺序和焦点行为。

---

### Task 0: 锁定 Auto 三态基线

**Files:**
- Verify: `codex_image/generation/catalog.py`
- Verify: `codex_image/webui/static/index.html`
- Verify: `codex_image/webui/frontend/src/custom-size-controls.ts`
- Verify: `codex_image/webui/frontend/src/model-parameters.ts`
- Verify: `codex_image/providers/codecs/gpt_image.py`
- Test: `tests/test_generation_catalog.py`
- Test: `tests/test_legacy_provider_adapters.py`
- Test: `tests/frontend/model_parameters_history.test.ts`

- [ ] **Step 1: 确认工作区包含 Auto 基线提交**

```powershell
git merge-base --is-ancestor 042c2e3 HEAD
```

Expected: exit code `0`。

- [ ] **Step 2: 运行模型目录和供应商负载测试**

```powershell
python -m pytest tests/test_generation_catalog.py tests/test_legacy_provider_adapters.py -q
```

Expected: 全部通过，并覆盖：

```text
openai_images    -> size="auto"
openai_responses -> tools[].size="auto"
codex_images     -> size="auto"
codex_responses  -> tools[].size="auto"
```

- [ ] **Step 3: 运行三态前端行为测试**

Windows 使用可执行的 `.cmd` 入口：

```powershell
$out = Join-Path $env:TEMP 'model-parameters-history.test.mjs'
.\node_modules\.bin\esbuild.cmd tests\frontend\model_parameters_history.test.ts --bundle --platform=node --format=esm --target=node20 "--outfile=$out" --log-level=warning
node --test $out
```

Expected: `19 passed`、`0 failed`。如果测试数量增加，以 `0 failed` 为硬性标准。

- [ ] **Step 4: 记录基线，不修改业务代码**

如果以上测试失败，先修复 Auto 功能并单独提交；不得带着失败基线开始排版。

---

### Task 1: 重组紧凑矩阵 DOM

**Files:**
- Modify: `tests/test_webui_static_layout.py`
- Modify: `tests/test_webui_static_prompt.py`
- Modify: `tests/test_webui_static_model_parameters.py`
- Modify: `codex_image/webui/static/index.html`
- Modify: `codex_image/webui/frontend/src/api-mode-settings.ts`
- Modify: `codex_image/webui/frontend/src/model-parameters.ts`

- [ ] **Step 1: 先写 DOM 顺序失败测试**

在 `WebUIStaticLayoutTests` 中增加：

```python
def test_gpt_output_settings_use_three_state_compact_matrix(self) -> None:
    html = Path("codex_image/webui/static/index.html").read_text(encoding="utf-8")
    matrix = re.search(
        r'<div id="compactOutputSettings" class="compact-output-settings full-width">([\s\S]*?)\n\s*</div>\n\s*</div>\n\s*</section>',
        html,
    )
    self.assertIsNotNone(matrix)
    markup = matrix.group(1)
    expected_ids = (
        "promptFidelityField",
        "sizeModeSelect",
        "orientation",
        "resolution",
        "ratio",
        "quality",
        "nInput",
        "moderation",
        "customSize",
        "outputFormatField",
        "pixelPreview",
    )
    positions = [markup.index(f'id="{element_id}"') for element_id in expected_ids]
    self.assertEqual(positions, sorted(positions))
    self.assertNotIn("quantity-quality-row", markup)
    self.assertNotRegex(markup, r'id="pixelPreview"[^>]*style=')
    self.assertRegex(markup, r'id="sizeModeSelect"[\s\S]*value="auto" selected')
    self.assertRegex(markup, r'id="size"[^>]*value="auto"')
```

- [ ] **Step 2: 写提示词独立显隐失败测试**

```python
def test_prompt_fidelity_moves_outside_mode_slot_but_keeps_own_visibility(self) -> None:
    html = Path("codex_image/webui/static/index.html").read_text(encoding="utf-8")
    script = Path("codex_image/webui/frontend/src/api-mode-settings.ts").read_text(encoding="utf-8")
    mode_slot = re.search(r'<div id="modeSettingsSlot"[\s\S]*?</div>\n\s*</div>', html)
    self.assertIsNotNone(mode_slot)
    self.assertNotIn('id="promptFidelityField"', mode_slot.group(0))
    self.assertIn(
        "setModeSpecificElementVisibility(els.promptFidelityField, visibility.showPromptFidelity);",
        script,
    )
```

- [ ] **Step 3: 写质量/数量独立定位失败测试**

```python
def test_legacy_gpt_fields_do_not_depend_on_quantity_quality_wrapper(self) -> None:
    source = Path("codex_image/webui/frontend/src/model-parameters.ts").read_text(encoding="utf-8")
    self.assertIn('els.quality?.closest(".quality-field")', source)
    self.assertIn('els.nInput?.closest(".quantity-field")', source)
    self.assertNotIn('els.quality?.closest(".quantity-quality-row")', source)
    self.assertIn('classList.toggle("auto-size-mode", visibility.autoSize)', source)
    self.assertIn('classList.toggle("custom-size-mode", visibility.customSize)', source)
```

- [ ] **Step 4: 运行测试并确认失败原因正确**

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py -q
```

Expected: 只有新契约测试失败，失败原因是新矩阵尚未建立。

- [ ] **Step 5: 重组 HTML，但不重建控件内部内容**

最终顶层结构：

```html
<div id="compactOutputSettings" class="compact-output-settings full-width">
  <div id="promptFidelityField" class="field compact-output-field compact-output-field--prompt"></div>
  <div class="field-group custom-size-control compact-output-field compact-output-field--size-mode"></div>
  <div class="field orientation-field compact-output-field compact-output-field--orientation"></div>
  <div class="field resolution-field compact-output-field compact-output-field--resolution"></div>
  <div class="field ratio-field compact-output-field compact-output-field--ratio"></div>
  <div class="field quality-field compact-output-field compact-output-field--quality"></div>
  <div class="field quantity-field compact-output-field compact-output-field--quantity"></div>
  <div class="field moderation-field compact-output-field compact-output-field--moderation"></div>
  <div id="customSize" class="custom-size hidden compact-output-field compact-output-field--custom-size" aria-hidden="true"></div>
  <div id="outputFormatField" class="field output-format-field compact-output-field compact-output-field--format"></div>
  <div id="pixelPreview" class="compact-output-pixel-preview compact-output-field compact-output-field--pixels"></div>
  <input type="text" id="size" class="hidden" value="auto" />
</div>
```

移动现有完整节点，不重建 `<option>`、帮助按钮、自定义尺寸内部控件或压缩率弹层。

- [ ] **Step 6: 解耦提示词显隐并修正字段定位**

`api-mode-settings.ts`：

```typescript
function applyModeSettingsVisibility(visibility: ModeSettingsVisibility): void {
  const showModeSettings = visibility.showMainModel || visibility.showApiDirectNotice;
  setModeSpecificElementVisibility(els.modeSettingsSlot, showModeSettings);
  setModeSpecificElementVisibility(els.modeSpecificSettings, showModeSettings);
  setModeSpecificElementVisibility(els.mainModelField, visibility.showMainModel);
  setModeSpecificElementVisibility(els.apiDirectSettingsNotice, visibility.showApiDirectNotice);
  setModeSpecificElementVisibility(els.promptFidelityField, visibility.showPromptFidelity);
}
```

`model-parameters.ts` 中分别使用：

```typescript
els.quality?.closest(".quality-field")
els.nInput?.closest(".quantity-field")
```

- [ ] **Step 7: 运行结构测试**

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py -q
```

Expected: 全部通过。

- [ ] **Step 8: 提交本任务**

```powershell
git add codex_image/webui/static/index.html codex_image/webui/frontend/src/api-mode-settings.ts codex_image/webui/frontend/src/model-parameters.ts tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py
git commit -m "让三态输出设置进入统一紧凑矩阵" -m "移动现有节点而不改变控件值和事件，并让提示词、质量和数量拥有独立显隐目标。`n`nConstraint: Auto 默认值和隐藏 size 字段必须保留`nConfidence: high`nScope-risk: moderate`nTested: DOM、提示词显隐和模型字段契约测试"
```

---

### Task 2: 实现宽容器三态网格

**Files:**
- Modify: `tests/test_webui_static_layout.py`
- Modify: `codex_image/webui/static/styles/70-output-settings.css`
- Generate: `codex_image/webui/static/styles.css`

- [ ] **Step 1: 写 12 列和三态跨度失败测试**

测试必须检查：

```python
self.assertRegex(styles, r"\.settings-grid\s*\{[^}]*container-type:\s*inline-size")
self.assertRegex(styles, r"\.compact-output-settings\s*\{[^}]*grid-template-columns:\s*repeat\(12,")
self.assertIn(".settings-grid.auto-size-mode .compact-output-field--prompt", styles)
self.assertIn(".settings-grid.custom-size-mode .compact-output-field--custom-size", styles)
self.assertIn("grid-column: span 8", styles)
```

同时检查 Auto 和 Custom 隐藏的三项预设尺寸字段都使用 `display: none`。

- [ ] **Step 2: 运行新测试确认失败**

```powershell
python -m pytest tests/test_webui_static_layout.py -q
```

Expected: 新三态网格测试失败。

- [ ] **Step 3: 写入基础矩阵与 Preset 跨度**

```css
.settings-grid {
  container-type: inline-size;
  container-name: output-settings;
}

.compact-output-settings {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 12px 10px;
  align-items: end;
  min-width: 0;
}

.compact-output-field { min-width: 0; }
.compact-output-field--prompt { grid-column: span 3; }
.compact-output-field--size-mode { grid-column: span 3; }
.compact-output-field--orientation { grid-column: span 2; }
.compact-output-field--resolution { grid-column: span 2; }
.compact-output-field--ratio { grid-column: span 2; }
.compact-output-field--quality { grid-column: span 2; }
.compact-output-field--quantity { grid-column: span 2; }
.compact-output-field--moderation { grid-column: span 2; }
.compact-output-field--format { grid-column: span 4; }
.compact-output-field--pixels { grid-column: span 2; }
```

- [ ] **Step 4: 写入 Auto 一行跨度**

```css
.settings-grid.auto-size-mode .compact-output-field--prompt { grid-column: span 2; }
.settings-grid.auto-size-mode .compact-output-field--size-mode { grid-column: span 2; }
.settings-grid.auto-size-mode .compact-output-field--quality { grid-column: span 1; }
.settings-grid.auto-size-mode .compact-output-field--quantity { grid-column: span 1; }
.settings-grid.auto-size-mode .compact-output-field--moderation { grid-column: span 2; }
.settings-grid.auto-size-mode .compact-output-field--format { grid-column: span 2; }
.settings-grid.auto-size-mode .compact-output-field--pixels { grid-column: span 2; }
```

- [ ] **Step 5: 写入 Custom 两行跨度**

```css
.settings-grid.custom-size-mode .compact-output-field--prompt { grid-column: span 3; }
.settings-grid.custom-size-mode .compact-output-field--size-mode { grid-column: span 3; }
.settings-grid.custom-size-mode .compact-output-field--quality { grid-column: span 2; }
.settings-grid.custom-size-mode .compact-output-field--quantity { grid-column: span 2; }
.settings-grid.custom-size-mode .compact-output-field--moderation { grid-column: span 2; }
.settings-grid.custom-size-mode .compact-output-field--custom-size { grid-column: span 8; }
.settings-grid.custom-size-mode .compact-output-field--format { grid-column: span 2; align-self: start; }
.settings-grid.custom-size-mode .compact-output-field--pixels { grid-column: span 2; align-self: start; }
```

- [ ] **Step 6: 将像素预览改为状态块**

```css
.compact-output-pixel-preview {
  display: grid;
  place-items: center;
  min-height: 36px;
  padding: 6px 8px;
  border: 1px solid color-mix(in srgb, var(--primary) 22%, var(--line));
  border-radius: 8px;
  background: color-mix(in srgb, var(--primary-light) 74%, var(--surface));
  color: var(--primary);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  text-align: center;
  white-space: normal;
}
```

- [ ] **Step 7: 构建 CSS 并运行测试**

```powershell
npm run build:webui:css
python -m pytest tests/test_webui_static_layout.py -q
```

Expected: 测试通过，`styles.css` 包含源文件的新规则。

- [ ] **Step 8: 提交本任务**

```powershell
git add codex_image/webui/static/styles/70-output-settings.css codex_image/webui/static/styles.css tests/test_webui_static_layout.py
git commit -m "按尺寸模式压缩输出设置占用" -m "Auto、Preset 和 Custom 使用独立字段跨度，在宽容器分别形成一行、两行和两行布局。`n`nConstraint: Auto 必须是默认且最短布局`nRejected: 所有模式共用固定跨度 | Auto 会留下大量空位`nConfidence: high`nScope-risk: moderate`nTested: CSS 构建和三态网格契约测试"
```

---

### Task 3: 实现容器响应式和 Custom 安全降级

**Files:**
- Modify: `tests/test_webui_static_layout.py`
- Modify: `tests/test_webui_static_short_height.py`
- Modify: `codex_image/webui/static/styles/70-output-settings.css`
- Modify: `codex_image/webui/static/styles/80-utilities-responsive.css`
- Generate: `codex_image/webui/static/styles.css`

- [ ] **Step 1: 写断点失败测试**

测试必须锁定以下断点：

```text
900px：12 列三态布局
680px：6 列布局，Custom 面板整行
360px：2 列布局
359px：1 列布局
```

并确认规则使用：

```css
@container output-settings (max-width: 899px)
@container output-settings (max-width: 679px)
@container output-settings (max-width: 359px)
```

- [ ] **Step 2: 运行断点测试确认失败**

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_short_height.py -q
```

- [ ] **Step 3: 实现 6 列中等布局**

```css
@container output-settings (max-width: 899px) {
  .compact-output-settings { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .compact-output-field--prompt,
  .compact-output-field--size-mode { grid-column: span 3; }
  .compact-output-field--orientation,
  .compact-output-field--resolution,
  .compact-output-field--ratio,
  .compact-output-field--quality,
  .compact-output-field--quantity,
  .compact-output-field--moderation { grid-column: span 2; }
  .compact-output-field--format { grid-column: span 4; }
  .compact-output-field--pixels { grid-column: span 2; }
  .settings-grid.custom-size-mode .compact-output-field--custom-size { grid-column: 1 / -1; }
}
```

Auto 在该断点用额外规则形成两行，不强制一行压缩。

- [ ] **Step 4: 实现两列和单列布局**

```css
@container output-settings (max-width: 679px) {
  .compact-output-settings { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .compact-output-field { grid-column: span 1; }
  .compact-output-field--custom-size { grid-column: 1 / -1; }
}

@container output-settings (max-width: 359px) {
  .compact-output-settings { grid-template-columns: minmax(0, 1fr); }
  .compact-output-field,
  .compact-output-field--custom-size { grid-column: 1 / -1; }
}
```

- [ ] **Step 5: 删除冲突旧规则**

从 `80-utilities-responsive.css` 删除只针对以下旧结构的跨度或顺序覆盖：

```text
.quantity-quality-row
#promptFidelityField 旧整行规则
#pixelPreview 旧整行规则
旧 settings-grid 子节点 nth-child 定位
```

保留短屏高度、滚动和触控尺寸规则。

- [ ] **Step 6: 验证 Custom 降级**

```powershell
npm run build:webui:css
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_short_height.py -q
```

Expected: 全部通过；Custom 在 `<900px` 时占整行，Auto/Preset 不出现空白占位。

- [ ] **Step 7: 提交本任务**

```powershell
git add codex_image/webui/static/styles/70-output-settings.css codex_image/webui/static/styles/80-utilities-responsive.css codex_image/webui/static/styles.css tests/test_webui_static_layout.py tests/test_webui_static_short_height.py
git commit -m "让三态输出矩阵适配窄屏" -m "使用父容器查询控制 12、6、2、1 列，并让自定义尺寸在空间不足时恢复整行。`n`nConstraint: 359px 以下禁止横向滚动和标签裁切`nConfidence: high`nScope-risk: narrow`nTested: 响应式布局和短屏静态测试"
```

---

### Task 4: 锁定三态交互、草稿和真实请求参数

**Files:**
- Modify: `tests/frontend/model_parameters_history.test.ts`
- Modify: `tests/test_webui_static_layout.py`
- Modify: `tests/test_webui_static_output_settings_overlay.py`
- Modify: `tests/test_webui_static_output_settings_lock.py`
- Verify: `codex_image/webui/frontend/src/custom-size-controls.ts`
- Verify: `codex_image/providers/codecs/gpt_image.py`

- [ ] **Step 1: 增加三态切换行为测试**

覆盖：

| 操作 | 期望状态 |
|---|---|
| 新任务进入 GPT Image 2 | `sizeModeSelect=auto`、`size=auto` |
| `auto → preset` | 显示方向/分辨率/比例，计算具体像素 |
| `preset → custom` | 隐藏三个预设字段，显示自定义尺寸 |
| `custom → auto` | 自定义卡片关闭，`size=auto` |
| 历史 `canvas.size=auto` | 恢复 Auto |
| 历史 `canvas.size=1024x1024` | 恢复 Preset |
| 历史非预设像素 | 恢复 Custom |
| 锁定后切换任务 | 编辑区和摘要不互相污染 |

- [ ] **Step 2: 断言隐藏字段不进入错误提交**

在前端测试中确认：

```typescript
assert.equal(autoValues["canvas.size"], "auto");
assert.equal("canvas.orientation" in autoValues, false);
assert.equal("canvas.resolution" in autoValues, false);
assert.equal("canvas.aspect_ratio" in autoValues, false);
```

Preset 和 Custom 仍提交各自需要的尺寸值。

- [ ] **Step 3: 再次运行四条供应商负载测试**

```powershell
python -m pytest tests/test_legacy_provider_adapters.py::LegacyProviderAdapterTests::test_gpt_codecs_preserve_auto_size_in_provider_payloads -q
```

Expected: `1 passed`。

- [ ] **Step 4: 运行锁定和摘要测试**

```powershell
python -m pytest tests/test_webui_static_output_settings_overlay.py tests/test_webui_static_output_settings_lock.py -q
```

- [ ] **Step 5: 运行前端行为测试**

```powershell
$out = Join-Path $env:TEMP 'model-parameters-history.test.mjs'
.\node_modules\.bin\esbuild.cmd tests\frontend\model_parameters_history.test.ts --bundle --platform=node --format=esm --target=node20 "--outfile=$out" --log-level=warning
node --test $out
```

Expected: `0 failed`。

- [ ] **Step 6: 只在测试暴露回归时修改业务代码**

允许修改范围：

```text
codex_image/webui/frontend/src/custom-size-controls.ts
codex_image/webui/frontend/src/model-parameters.ts
codex_image/providers/codecs/gpt_image.py
```

不得为了适配布局更改 Auto 的参数语义。

- [ ] **Step 7: 提交本任务**

```powershell
git add tests/frontend/model_parameters_history.test.ts tests/test_webui_static_layout.py tests/test_webui_static_output_settings_overlay.py tests/test_webui_static_output_settings_lock.py codex_image/webui/frontend/src/custom-size-controls.ts codex_image/webui/frontend/src/model-parameters.ts codex_image/providers/codecs/gpt_image.py
git commit -m "防止紧凑布局破坏 Auto 参数提交" -m "覆盖三态切换、历史恢复、锁定摘要和四条 GPT 供应商负载，确保布局显隐不改变请求语义。`n`nConstraint: Auto 必须原样提交给 GPT Image 2`nConfidence: high`nScope-risk: narrow`nTested: 前端三态、锁定摘要和供应商负载回归"
```

---

### Task 5: 构建和完整回归

**Files:**
- Generate: `codex_image/webui/static/app.js`
- Generate: `codex_image/webui/static/app.js.map`
- Generate: `codex_image/webui/static/history.js`
- Generate: `codex_image/webui/static/history.js.map`
- Generate: `codex_image/webui/static/styles.css`

- [ ] **Step 1: 构建、类型检查和静态产物生成**

```powershell
npm run check:webui
```

Expected:

```text
build:webui:css passed
typecheck:webui passed
build:webui passed
```

- [ ] **Step 2: 运行相关 Python 回归**

```powershell
python -m pytest tests/test_generation_catalog.py tests/test_legacy_provider_adapters.py tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py tests/test_webui_static_output_settings_overlay.py tests/test_webui_static_output_settings_lock.py tests/test_webui_static_short_height.py -q
```

Expected: `0 failed`。

- [ ] **Step 3: 检查生成文件和源码一致性**

```powershell
git diff --check
git status --short
```

Expected: 无空白错误；只有计划列出的源码、测试和构建产物发生变化。

- [ ] **Step 4: 提交构建产物**

```powershell
git add codex_image/webui/static/app.js codex_image/webui/static/app.js.map codex_image/webui/static/history.js codex_image/webui/static/history.js.map codex_image/webui/static/styles.css
git commit -m "同步三态紧凑布局的静态产物" -m "提交经类型检查和构建生成的 WebUI 文件，避免服务器运行旧版静态资源。`n`nConstraint: 不手工修改生成文件`nConfidence: high`nScope-risk: narrow`nTested: npm run check:webui 和相关 Python 回归"
```

---

### Task 6: 本地交互和视觉验收

**Files:**
- Create: `docs/superpowers/evidence/gpt-output-compact-layout/auto-desktop-light.png`
- Create: `docs/superpowers/evidence/gpt-output-compact-layout/auto-desktop-dark.png`
- Create: `docs/superpowers/evidence/gpt-output-compact-layout/preset-desktop.png`
- Create: `docs/superpowers/evidence/gpt-output-compact-layout/custom-desktop.png`
- Create: `docs/superpowers/evidence/gpt-output-compact-layout/mobile-three-modes.png`
- Runtime state: `.omx/state/gpt-output-compact-layout/ralph-progress.json`（本地忽略，不提交）
- Create: `docs/superpowers/evidence/gpt-output-compact-layout/visual-verdict.json`

- [ ] **Step 1: 启动本地服务**

```powershell
python -m uvicorn codex_image.webui.app:app --host 127.0.0.1 --port 8787
```

如果项目入口由 `deploy/ilab_conjure_server.py` 提供，则使用现有本地启动命令，不创建第二套入口。

- [ ] **Step 2: 验证 Auto 默认状态**

| 检查 | 期望 |
|---|---|
| 首次进入 GPT Image 2 | Auto 已选中 |
| 可见字段 | 提示词、尺寸模式、质量、数量、审核、格式、输出像素 |
| 隐藏字段 | 方向、分辨率、比例、自定义尺寸 |
| 输出像素 | 显示 `auto（OpenAI 自动选择）` |
| 请求预览 | `canvas.size: "auto"` |
| 刷新/切换模型后返回 | Auto 草稿正确恢复 |

- [ ] **Step 3: 验证 Preset 和 Custom**

Preset：方向、分辨率、比例可见并联动，像素值立即更新。

Custom：自定义面板出现；宽高、交换、比例锁定、首图比例、验证提示正常；切回 Auto 后卡片关闭且 `size` 恢复为 `auto`。

- [ ] **Step 4: 验证压缩率、锁定和历史采用**

- PNG 不显示压缩率按钮。
- JPEG/WebP 显示按钮和弹层。
- 锁定后矩阵由摘要替代，解锁后草稿保持。
- 从 Auto、Preset、Custom 三种历史任务采用参数后，界面恢复到正确模式。

- [ ] **Step 5: 截图**

| 截图 | 视口与主题 |
|---|---|
| `auto-desktop-light.png` | `1920 × 1080`，浅色，Auto，确认输出设置容器 `>=900px` |
| `auto-desktop-dark.png` | `1920 × 1080`，深色，Auto，确认输出设置容器 `>=900px` |
| `preset-desktop.png` | `1920 × 1080`，Preset，确认输出设置容器 `>=900px` |
| `custom-desktop.png` | `1920 × 1080`，Custom，确认输出设置容器 `>=900px` |
| `mobile-three-modes.png` | `430 × 932`，三态分别检查并保存组合证据 |

截图不得包含密码、Token、API Key、供应商密钥或请求头。

- [ ] **Step 6: 每轮视觉修改执行 `$visual-verdict`**

结果保存到：

```text
.omx/state/gpt-output-compact-layout/ralph-progress.json
```
达到最终阈值后，将最终 verdict 复制到：

```text
docs/superpowers/evidence/gpt-output-compact-layout/visual-verdict.json
```

验收阈值：

| 项目 | 标准 |
|---|---|
| 视觉评分 | `>= 90` |
| Auto 宽屏行数 | 1 行 |
| Preset 宽屏行数 | 2 行 |
| Custom 宽屏行数 | 2 行 |
| Auto 高度减少 | `>= 45%` |
| Preset 高度减少 | `35%–45%` |
| 横向滚动 | 无 |
| 标签裁切 | 无 |
| 对齐 | 同行标签基线和控件底部一致 |
| 主题 | 浅色、深色的背景、边框、焦点状态正常 |
| 可访问性 | Tab 顺序与视觉顺序一致，原生方向键选择正常 |

- [ ] **Step 7: 最终 Git 检查并提交视觉证据**

```powershell
git status --short
git diff --check
git add docs/superpowers/evidence/gpt-output-compact-layout
git commit -m "记录三态输出设置视觉验收" -m "保存 Auto、Preset、Custom 的桌面和移动端证据，确认高度、对齐、主题和交互达到阈值。`n`nConstraint: Auto 宽屏必须保持一行且真实参数不变`nConfidence: high`nScope-risk: narrow`nTested: 三种模式、两种主题、移动端、锁定和历史恢复"
```

---

## 最终验收清单

- [ ] 当前分支包含 Auto 基线提交 `042c2e3`。
- [ ] 9 个下拉框仍是原生 `<select>`，ID 和 option value 未改变。
- [ ] `sizeModeSelect` 默认 `auto`，隐藏字段 `size` 默认 `auto`。
- [ ] Auto 宽屏一行，Preset 宽屏两行，Custom 宽屏两行。
- [ ] 6/2/1 列容器断点正确，无横向滚动和标签裁切。
- [ ] Auto 隐藏方向、分辨率、比例、自定义尺寸。
- [ ] Preset 显示方向、分辨率、比例并生成具体像素。
- [ ] Custom 显示自定义尺寸，宽度不足时安全降为整行。
- [ ] `canvas.size="auto"` 仍进入标准参数。
- [ ] 四条 GPT 协议路径最终负载仍提交 `size="auto"`。
- [ ] 历史 Auto/Preset/Custom 参数恢复正确。
- [ ] PNG/JPEG/WebP 压缩率入口和弹层正常。
- [ ] 输出设置锁定、摘要、任务参数采用和草稿恢复正常。
- [ ] `npm run check:webui` 通过。
- [ ] 相关 Python 和 Node 测试 `0 failed`。
- [ ] `git diff --check` 无错误。
- [ ] 五张视觉证据完成，`$visual-verdict` 评分不低于 `90`。
- [ ] 每个实施任务完成后都有独立 Git 提交。

---

## 已知风险

| 风险 | 控制措施 |
|---|---|
| 排版时把 Auto 当成纯前端选项 | Task 0 和 Task 4 验证标准参数及四条供应商负载 |
| Auto 一行跨度导致英文标签拥挤 | 只在 `>=900px` 使用一行；低于该宽度切换 6/2/1 列 |
| JPEG/WebP 压缩率按钮挤压格式下拉框 | Auto 宽屏给格式 `3/12`；截图覆盖 JPEG/WebP |
| Custom 面板与格式/像素同行高度错位 | Custom 宽屏使用 `8+2+2`，格式和像素 `align-self:start` |
| DOM 顺序和视觉顺序不同 | 不使用 `order`；按 Tab 顺序安排节点 |
| 隐藏预设字段后草稿被清空 | 只改变显示，不修改 `activeParameterValuesFor` 的草稿保留策略 |
| 旧任务 `1024x1024` 被错误恢复成 Auto | Node 历史测试分别覆盖 Auto、Preset 和非预设 Custom |
| 提示词移位后模式槽留下空白 | `showModeSettings` 不包含 `showPromptFidelity` |
| 拆除质量/数量组合容器影响非 GPT 模型 | 分别定位 `.quality-field` 和 `.quantity-field` |
| 短屏旧 CSS 覆盖容器查询 | 删除旧结构选择器并运行短屏测试 |
| 多语言标签变长 | `<360px` 单列，并检查中文、英文及其他现有语言 |
| 源码与静态产物不一致 | 强制执行 `npm run check:webui` 并提交生成文件 |

---

## 计划边界

本计划只实施本地源码、测试、构建产物和视觉验收，不发起会产生费用的真实图片生成请求。供应商参数通过编码器负载测试验证。

本计划全部通过后，按项目固定顺序发布：

```text
验证 → Git 提交 → 推送 GitHub → 服务器创建回退分支 → fast-forward 到 origin/main → 重启服务 → 公网验证
```

公网验证至少检查：

- `https://image.84868988.xyz/` 登录页、首页和生成目录接口返回 `200`。
- GPT Image 2 目录中的 `canvas.size.default` 为 `auto`。
- 页面默认选择 Auto，输出像素显示自动语义。
- 本地、GitHub 和服务器提交 SHA 一致。
