# GPT 输出设置紧凑重排 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GPT 模型页面的 9 个输出设置和输出像素预览重排为按内容长度分配宽度的响应式矩阵，在不改变参数语义、事件和提交数据的前提下显著减少占用高度。

**Architecture:** 保留现有原生 `<select>`、控件 ID、option value 和 TypeScript 事件绑定，只调整顶层 DOM 分组、旧版 GPT 字段显隐目标和 CSS 网格。`settingsGrid` 提供容器查询上下文，新的 `compactOutputSettings` 作为 12/6/2/1 列响应式矩阵；尺寸模式继续保持 `auto/preset/custom` 三态，压缩率弹层和锁定摘要继续复用现有实现。

**Tech Stack:** HTML、CSS Grid、CSS Container Queries、TypeScript、Python `unittest`/`pytest`、Node.js、esbuild、TypeScript 6

---

## 方案确认

采用此前方案 **A：12 列响应式矩阵**，并根据当前源码核对结果做两项必要修正。

| 项目 | 确认结果 |
|---|---|
| 布局方向 | 保留 12 列矩阵；宽屏两行，中等宽度四行，窄屏两列，超窄单列 |
| 查询容器 | `container-type` 放在父级 `.settings-grid`，不能放在需要改变自身列数的 `.compact-output-settings` 上 |
| 字段顺序 | DOM、视觉和键盘顺序保持一致：提示词处理 → 尺寸模式 → 方向 → 分辨率 → 比例 → 质量 → 数量 → 审核 → 输出格式 → 输出像素 |
| GPT 专用显隐 | 提示词处理移出 `modeSpecificSettings` 后独立显隐；主模型/API 直连提示仍由 `modeSettingsSlot` 控制 |
| 旧版参数显隐 | 拆除 `quantity-quality-row` 后，`model-parameters.ts` 必须分别定位质量和数量字段 |
| 尺寸模式三态 | `auto` 为默认项；`auto` 隐藏方向、分辨率、比例和自定义尺寸，`preset` 显示三个预设控件，`custom` 只显示自定义尺寸面板 |
| 自定义尺寸 | 方向、分辨率、预设比例隐藏；自定义尺寸面板占满整行；其他输出项保持紧凑 |
| 压缩率 | PNG 隐藏；JPEG/WebP 显示原有按钮和弹层，不改事件逻辑 |
| 输出像素 | 从带内联样式的整行提示改为矩阵中的紧凑状态块 |
| 依赖 | 不增加依赖，不实现自定义下拉组件 |

### 目标布局

默认进入 `auto`，首屏不显示方向、分辨率、比例和自定义尺寸：

```text
提示词处理 | 尺寸模式：自动 | 质量 | 数量 | 审核 | 输出格式 | 输出像素：auto
```

用户切换到 `preset` 后显示完整预设尺寸矩阵；以下断点示意均以 `preset` 为例。

#### 宽屏：容器宽度 `>= 760px`

```text
┌──────────────────────────────────────────────────────────────┐
│ 提示词处理     尺寸模式      方向      分辨率      比例        │
│ [保真     ▼]  [预设尺寸 ▼]  [方形 ▼]  [1K  ▼]    [1:1 ▼]    │
│                                                              │
│ 质量       数量       审核       输出格式          输出像素    │
│ [自动 ▼]  [1  ▼]    [auto ▼]  [png ▼] [压缩率]  1024×1024  │
└──────────────────────────────────────────────────────────────┘
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

#### 中等宽度：容器宽度 `520–759px`

```text
提示词处理 3/6  | 尺寸模式 3/6
方向 2/6 | 分辨率 2/6 | 比例 2/6
质量 2/6 | 数量 2/6 | 审核 2/6
输出格式 4/6 | 输出像素 2/6
```

#### 窄屏：容器宽度 `360–519px`

```text
提示词处理 | 尺寸模式
方向       | 分辨率
比例       | 质量
数量       | 审核
输出格式   | 输出像素
```

#### 超窄：容器宽度 `< 360px`

全部字段单列，禁止横向滚动和文字裁切。

### 尺寸与间距

| 属性 | 目标值 |
|---|---|
| 下拉框最小高度 | `36px` |
| 标签到控件间距 | `6px` |
| 字段横向间距 | `10px` |
| 字段纵向间距 | `12px` |
| 字段最小宽度 | `0`，允许网格正确收缩 |
| 普通短选项视觉宽度 | 约 `88–180px` |
| 提示词处理、尺寸模式 | 约 `160–220px` |
| 输出格式 | 预留压缩率按钮空间 |
| 高度目标 | `auto` 默认模式最短；`preset` 模式比现状减少约 `35%–45%` |

## 范围与文件职责

| 文件 | 职责 |
|---|---|
| `codex_image/webui/static/index.html` | 建立紧凑矩阵，移动提示词字段，拆除质量/数量组合容器，移除输出像素内联样式 |
| `codex_image/webui/static/styles/70-output-settings.css` | 矩阵、字段跨度、像素状态块、`auto/custom` 尺寸模式和容器查询 |
| `codex_image/webui/static/styles/80-utilities-responsive.css` | 清理与新矩阵冲突的短屏旧规则，保留短屏高度压缩能力 |
| `codex_image/webui/static/styles.css` | 由 `npm run build:webui:css` 生成，不手工编辑 |
| `codex_image/webui/frontend/src/api-mode-settings.ts` | 将提示词处理显隐从模式槽显隐中解耦 |
| `codex_image/webui/frontend/src/model-parameters.ts` | 在拆除 `quantity-quality-row` 后分别控制质量和数量字段 |
| `tests/test_webui_static_layout.py` | DOM、网格跨度、响应式断点、自定义尺寸和像素状态回归契约 |
| `tests/test_webui_static_prompt.py` | 提示词处理移位后的 GPT/API 模式显隐契约 |
| `tests/test_webui_static_model_parameters.py` | 旧版 GPT 字段独立显隐契约 |
| `tests/test_webui_static_output_settings_overlay.py` | 锁定摘要仍覆盖原编辑区的契约 |
| `tests/test_webui_static_output_settings_lock.py` | 锁定、任务参数采用和摘要布局回归 |
| `tests/test_webui_static_short_height.py` | 短屏压缩规则不再依赖旧布局选择器 |

## 不改变的行为

- 9 个 `<select>` 的 ID、既有 option value 和 i18n key；`sizeModeSelect` 已新增的 `auto` 选项必须保留。
- `sizeModeSelect` 维持 `auto/preset/custom` 三态，并与隐藏的 `customSizeToggle` 兼容同步。
- `auto` 继续作为 HTML、模型清单和新建任务默认值，隐藏字段 `size` 必须保持字符串 `"auto"`。
- `preset` 下方向、分辨率、比例联动和 `size` 隐藏字段计算保持不变。
- 自定义宽高、交换宽高、比例锁定和取首图比例。
- 质量、数量、审核、输出格式的提交参数。
- PNG/JPEG/WebP 与压缩率弹层的显示逻辑。
- 模型参数草稿保存、恢复和任务历史参数采用。
- 输出设置锁定摘要和遮罩。
- 深色/浅色主题变量、原生键盘选择和焦点行为。

---

### Task 1: 锁定新 DOM 结构和 GPT 字段显隐

**Files:**
- Modify: `tests/test_webui_static_layout.py:2298-2405`
- Modify: `tests/test_webui_static_prompt.py:1318-1370`
- Modify: `tests/test_webui_static_model_parameters.py:19-88`
- Modify: `codex_image/webui/static/index.html:530-786`
- Modify: `codex_image/webui/frontend/src/api-mode-settings.ts:29-41`
- Modify: `codex_image/webui/frontend/src/model-parameters.ts:794-812`

- [ ] **Step 1: 写入紧凑矩阵 DOM 失败测试**

在 `WebUIStaticLayoutTests` 中增加：

```python
def test_gpt_output_settings_share_one_compact_matrix(self) -> None:
    html = Path("codex_image/webui/static/index.html").read_text(encoding="utf-8")
    matrix = re.search(
        r'<div id="compactOutputSettings" class="compact-output-settings full-width">([\s\S]*?)\n\s*</div>\n\s*</div>\n\s*</div>\n\s*</section>',
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
        "outputFormatField",
        "pixelPreview",
    )
    positions = [markup.index(f'id="{element_id}"') for element_id in expected_ids]
    self.assertEqual(positions, sorted(positions))
    self.assertNotIn('class="field-pair full-width quantity-quality-row"', markup)
    self.assertNotRegex(markup, r'id="pixelPreview"[^>]*style=')
```

- [ ] **Step 2: 更新提示词处理位置和显隐失败测试**

将 `test_api_direct_mode_hides_non_applicable_main_model_but_keeps_prompt_fidelity` 中原来要求 `promptFidelityField` 位于 `modeSpecificSettings` 内部的断言改为：

```python
mode_settings = re.search(
    r'<div id="modeSpecificSettings"[\s\S]*?</div>\n\s*</div>',
    html,
)
self.assertIsNotNone(mode_settings)
self.assertNotIn('id="promptFidelityField"', mode_settings.group(0))
self.assertRegex(
    html,
    r'id="compactOutputSettings"[\s\S]*id="promptFidelityField"[\s\S]*id="sizeModeSelect"',
)
self.assertIn(
    "const showModeSettings = visibility.showMainModel || visibility.showApiDirectNotice;",
    script,
)
self.assertIn(
    "setModeSpecificElementVisibility(els.promptFidelityField, visibility.showPromptFidelity);",
    script,
)
```

- [ ] **Step 3: 写入旧版 GPT 字段独立显隐失败测试**

在 `ModelParameterFrontendContractTests` 中增加：

```python
def test_legacy_gpt_visibility_targets_quality_and_quantity_independently(self) -> None:
    source = Path("codex_image/webui/frontend/src/model-parameters.ts").read_text(encoding="utf-8")
    self.assertIn('els.quality?.closest(".quality-field")', source)
    self.assertIn('els.nInput?.closest(".quantity-field")', source)
    self.assertNotIn('els.quality?.closest(".quantity-quality-row")', source)
    self.assertIn('els.settingsGrid?.classList.toggle("custom-size-mode", visibility.customSize);', source)
    self.assertIn('els.settingsGrid?.classList.toggle("auto-size-mode", visibility.autoSize);', source)
```

- [ ] **Step 4: 运行测试并确认按预期失败**

Run:

```powershell
python -m pytest tests/test_webui_static_layout.py::WebUIStaticLayoutTests::test_gpt_output_settings_share_one_compact_matrix tests/test_webui_static_prompt.py::WebUIStaticPromptTests::test_api_direct_mode_hides_non_applicable_main_model_but_keeps_prompt_fidelity tests/test_webui_static_model_parameters.py::ModelParameterFrontendContractTests::test_legacy_gpt_visibility_targets_quality_and_quantity_independently -q
```

Expected: 三项测试失败，原因分别是矩阵不存在、提示词仍位于模式槽、质量仍通过 `quantity-quality-row` 定位。

- [ ] **Step 5: 重组 HTML，保留原控件内部内容**

最终顶层顺序和 class 必须精确为：

```html
<div id="compactOutputSettings" class="compact-output-settings full-width">
  <div id="promptFidelityField" class="field compact-output-field compact-output-field--prompt"></div>
  <div class="field-group custom-size-control compact-output-field compact-output-field--size-mode"></div>
  <div class="field orientation-field compact-output-field compact-output-field--orientation"></div>
  <div class="field resolution-field compact-output-field compact-output-field--resolution"></div>
  <div class="field ratio-field compact-output-field compact-output-field--ratio"></div>
  <div id="customSize" class="custom-size hidden compact-output-field compact-output-field--custom-size" aria-hidden="true"></div>
  <div class="field quality-field compact-output-field compact-output-field--quality"></div>
  <div class="field quantity-field compact-output-field compact-output-field--quantity"></div>
  <div class="field moderation-field compact-output-field compact-output-field--moderation"></div>
  <div id="outputFormatField" class="field output-format-field compact-output-field compact-output-field--format"></div>
  <div id="pixelPreview" class="compact-output-pixel-preview compact-output-field compact-output-field--pixels"></div>
</div>
```

实施时移动现有完整节点，不重建 `<option>`、自定义尺寸输入、压缩率弹层和帮助按钮；`<input id="size">` 保留在矩阵中并继续使用 `hidden` class。

- [ ] **Step 6: 解耦提示词处理显隐**

将 `applyModeSettingsVisibility` 改为：

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

- [ ] **Step 7: 更新旧版 GPT 字段列表**

将 `legacyElements` 中质量/数量部分改为：

```typescript
const legacyElements = [
  els.sizeModeSelect?.closest(".custom-size-control"),
  els.orientation?.closest(".orientation-field"),
  els.resolution?.closest(".resolution-field"),
  els.ratio?.closest(".ratio-field"),
  els.quality?.closest(".quality-field"),
  els.nInput?.closest(".quantity-field"),
  els.pixelPreview,
  els.outputFormatField,
  els.moderation?.closest(".moderation-field"),
].filter(Boolean) as HTMLElement[];
```

- [ ] **Step 8: 运行结构和显隐测试**

Run:

```powershell
python -m pytest tests/test_webui_static_layout.py::WebUIStaticLayoutTests::test_gpt_output_settings_share_one_compact_matrix tests/test_webui_static_prompt.py::WebUIStaticPromptTests::test_api_direct_mode_hides_non_applicable_main_model_but_keeps_prompt_fidelity tests/test_webui_static_model_parameters.py::ModelParameterFrontendContractTests::test_legacy_gpt_visibility_targets_quality_and_quantity_independently -q
```

Expected: `3 passed`。

- [ ] **Step 9: 提交本任务**

```powershell
git add codex_image/webui/static/index.html codex_image/webui/frontend/src/api-mode-settings.ts codex_image/webui/frontend/src/model-parameters.ts tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py
git commit -m "让输出设置结构支持紧凑矩阵" -m "保留全部控件值和事件，只调整字段归属并修正 GPT 专用显隐。`n`nConstraint: 提示词处理必须独立于主模型/API 直连模式槽显示`nRejected: 继续使用质量数量组合容器 | 无法为两个短字段独立分配网格跨度`nConfidence: high`nScope-risk: moderate`nTested: DOM、模式显隐和旧版 GPT 字段契约测试"
```

---

### Task 2: 实现宽屏 12 列紧凑矩阵

**Files:**
- Modify: `tests/test_webui_static_layout.py:2298-2410`
- Modify: `codex_image/webui/static/styles/70-output-settings.css:696-870`
- Modify: `codex_image/webui/static/styles/70-output-settings.css:1317-1582`
- Generated: `codex_image/webui/static/styles.css`

- [ ] **Step 1: 写入基础矩阵和字段跨度失败测试**

```python
def test_compact_output_matrix_uses_twelve_columns_and_content_sized_spans(self) -> None:
    styles = Path("codex_image/webui/static/styles/70-output-settings.css").read_text(encoding="utf-8")
    self.assertRegex(styles, r"\.settings-grid\s*\{[^}]*container-type:\s*inline-size")
    self.assertRegex(styles, r"\.settings-grid\s*\{[^}]*container-name:\s*output-settings")
    self.assertRegex(
        styles,
        r"\.compact-output-settings\s*\{[^}]*display:\s*grid[^}]*grid-template-columns:\s*repeat\(12,\s*minmax\(0,\s*1fr\)\)",
    )
    spans = {
        "prompt": 3,
        "size-mode": 3,
        "orientation": 2,
        "resolution": 2,
        "ratio": 2,
        "quality": 2,
        "quantity": 2,
        "moderation": 2,
        "format": 4,
        "pixels": 2,
    }
    for name, span in spans.items():
        with self.subTest(name=name):
            self.assertRegex(
                styles,
                rf"\.compact-output-field--{name}\s*\{{[^}}]*grid-column:\s*span\s+{span}",
            )
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
python -m pytest tests/test_webui_static_layout.py::WebUIStaticLayoutTests::test_compact_output_matrix_uses_twelve_columns_and_content_sized_spans -q
```

Expected: FAIL，原因是 `.compact-output-settings` 和字段跨度规则尚不存在。

- [ ] **Step 3: 写入基础矩阵 CSS**

在 `.settings-grid` 中保留现有两列外层布局，并增加查询上下文；新增矩阵规则：

```css
.settings-grid {
  --custom-size-mode-card-height: 175px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  container-type: inline-size;
  container-name: output-settings;
  transition: height var(--motion-height);
}

.compact-output-settings {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 12px 10px;
  align-items: end;
  min-width: 0;
}

.compact-output-field {
  min-width: 0;
}

.compact-output-field--prompt { grid-column: span 3; }
.compact-output-field--size-mode { grid-column: span 3; }
.compact-output-field--orientation { grid-column: span 2; }
.compact-output-field--resolution { grid-column: span 2; }
.compact-output-field--ratio { grid-column: span 2; }
.compact-output-field--custom-size { grid-column: 1 / -1; }
.compact-output-field--quality { grid-column: span 2; }
.compact-output-field--quantity { grid-column: span 2; }
.compact-output-field--moderation { grid-column: span 2; }
.compact-output-field--format { grid-column: span 4; }
.compact-output-field--pixels { grid-column: span 2; }
```

删除 `#promptFidelityField { grid-column: 1 / -1; }` 和只服务于已移除组合容器的 `.quantity-quality-row` 规则。

- [ ] **Step 4: 将输出像素改为紧凑状态块**

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
  white-space: nowrap;
}
```

- [ ] **Step 5: 构建合并 CSS 并运行测试**

Run:

```powershell
npm run build:webui:css
python -m pytest tests/test_webui_static_layout.py::WebUIStaticLayoutTests::test_gpt_output_settings_use_compact_select_controls tests/test_webui_static_layout.py::WebUIStaticLayoutTests::test_compact_output_matrix_uses_twelve_columns_and_content_sized_spans -q
```

Expected: `2 passed`，`codex_image/webui/static/styles.css` 包含新矩阵规则。

- [ ] **Step 6: 提交本任务**

```powershell
git add codex_image/webui/static/styles/70-output-settings.css codex_image/webui/static/styles.css tests/test_webui_static_layout.py
git commit -m "减少输出设置的无效横向占用" -m "按字段内容长度分配 12 列跨度，并把输出像素并入紧凑矩阵。`n`nConstraint: 原生下拉框保持 36px 最小点击高度`nRejected: auto-fit 自动换行 | 无法稳定控制字段行序和压缩率空间`nConfidence: high`nScope-risk: narrow`nTested: CSS 构建和宽屏矩阵契约测试"
```

---

### Task 3: 实现容器响应式和自定义尺寸模式

**Files:**
- Modify: `tests/test_webui_static_layout.py:2460-2620`
- Modify: `tests/test_webui_static_short_height.py:49-92`
- Modify: `codex_image/webui/static/styles/70-output-settings.css:1317-1615`
- Modify: `codex_image/webui/static/styles/80-utilities-responsive.css:408-674`
- Generated: `codex_image/webui/static/styles.css`

- [ ] **Step 1: 写入容器断点失败测试**

```python
def test_compact_output_matrix_reflows_at_container_breakpoints(self) -> None:
    styles = Path("codex_image/webui/static/styles/70-output-settings.css").read_text(encoding="utf-8")
    self.assertRegex(
        styles,
        r"@container output-settings \(max-width:\s*759px\)\s*\{[\s\S]*"
        r"\.compact-output-settings\s*\{[^}]*grid-template-columns:\s*repeat\(6,\s*minmax\(0,\s*1fr\)\)",
    )
    self.assertRegex(
        styles,
        r"@container output-settings \(max-width:\s*519px\)\s*\{[\s\S]*"
        r"\.compact-output-settings\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)",
    )
    self.assertRegex(
        styles,
        r"@container output-settings \(max-width:\s*359px\)\s*\{[\s\S]*"
        r"\.compact-output-settings\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)",
    )
```

- [ ] **Step 2: 更新自定义尺寸契约测试**

将旧的 `.settings-grid.custom-size-mode` 断言调整为矩阵后代规则，并增加：

```python
self.assertRegex(
    styles,
    r"\.settings-grid\.custom-size-mode\s+\.compact-output-field--orientation,\s*"
    r"\.settings-grid\.custom-size-mode\s+\.compact-output-field--resolution,\s*"
    r"\.settings-grid\.custom-size-mode\s+\.compact-output-field--ratio\s*\{[^}]*display:\s*none",
)
self.assertRegex(
    styles,
    r"\.settings-grid\.custom-size-mode\s+\.compact-output-field--custom-size\s*\{[^}]*grid-column:\s*1\s*/\s*-1",
)
self.assertNotRegex(styles, r"\.settings-grid\.custom-size-mode\s+\.compact-output-field--quantity\s*\{[^}]*grid-column:\s*1\s*/\s*-1")
```

- [ ] **Step 3: 运行响应式和自定义尺寸测试并确认失败**

Run:

```powershell
python -m pytest tests/test_webui_static_layout.py::WebUIStaticLayoutTests::test_compact_output_matrix_reflows_at_container_breakpoints tests/test_webui_static_layout.py -k "custom_size" -q
```

Expected: 新断点测试失败；旧自定义尺寸选择器断言需要更新。

- [ ] **Step 4: 实现三级容器断点**

```css
@container output-settings (max-width: 759px) {
  .compact-output-settings {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .compact-output-field--prompt,
  .compact-output-field--size-mode { grid-column: span 3; }

  .compact-output-field--orientation,
  .compact-output-field--resolution,
  .compact-output-field--ratio,
  .compact-output-field--quality,
  .compact-output-field--quantity,
  .compact-output-field--moderation,
  .compact-output-field--pixels { grid-column: span 2; }

  .compact-output-field--format { grid-column: span 4; }
  .compact-output-field--custom-size { grid-column: 1 / -1; }
}

@container output-settings (max-width: 519px) {
  .compact-output-settings {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .compact-output-field:not(.compact-output-field--custom-size) {
    grid-column: span 1;
  }

  .compact-output-field--custom-size { grid-column: 1 / -1; }

  .settings-grid.custom-size-mode .compact-output-field--pixels {
    grid-column: 1 / -1;
  }
}

@container output-settings (max-width: 359px) {
  .compact-output-settings {
    grid-template-columns: minmax(0, 1fr);
  }

  .compact-output-field,
  .compact-output-field--custom-size {
    grid-column: 1 / -1;
  }
}
```

- [ ] **Step 5: 将 `auto/custom` 尺寸模式选择器指向新矩阵字段**

```css
.settings-grid.custom-size-mode .compact-output-field--orientation,
.settings-grid.custom-size-mode .compact-output-field--resolution,
.settings-grid.custom-size-mode .compact-output-field--ratio,
.settings-grid.auto-size-mode .compact-output-field--orientation,
.settings-grid.auto-size-mode .compact-output-field--resolution,
.settings-grid.auto-size-mode .compact-output-field--ratio {
  display: none;
}

.settings-grid.custom-size-mode .compact-output-field--custom-size {
  display: grid;
  grid-column: 1 / -1;
}
```

`auto-size-mode` 不显示 `.compact-output-field--custom-size`；保留 `.custom-size` 内部宽高输入、比例锁定、动画和 `prefers-reduced-motion` 规则。

- [ ] **Step 6: 清理短屏旧布局覆盖**

在 `80-utilities-responsive.css` 中：

1. 删除 `.quantity-quality-row` 专用 gap 规则。
2. 删除把 `#promptFidelityField` 放回 `mode-specific-settings` 第二列的规则。
3. 将 `#pixelPreview` 的短屏规则改为 `.compact-output-pixel-preview`，去掉依赖 HTML 内联样式的 `!important`。
4. 保留 `.settings-grid` 的短屏控制高度变量和自定义尺寸卡片高度变量。
5. 不修改 workspace、侧栏、预览区和上传区断点。

- [ ] **Step 7: 构建 CSS 并运行布局测试**

Run:

```powershell
npm run build:webui:css
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_short_height.py -q
```

Expected: 两个测试文件全部通过，无旧 `quantity-quality-row` 和模式槽内提示词定位断言。

- [ ] **Step 8: 提交本任务**

```powershell
git add codex_image/webui/static/styles/70-output-settings.css codex_image/webui/static/styles/80-utilities-responsive.css codex_image/webui/static/styles.css tests/test_webui_static_layout.py tests/test_webui_static_short_height.py
git commit -m "让紧凑输出设置适配不同面板宽度" -m "使用父容器查询在 12、6、2、1 列之间切换，并保持自定义尺寸面板全宽。`n`nConstraint: 响应式判断必须基于输出面板而不是浏览器窗口`nRejected: 媒体查询 | 侧栏与预览区会导致同一窗口宽度下可用空间不同`nConfidence: high`nScope-risk: moderate`nTested: 布局、短屏和自定义尺寸静态契约测试"
```

---

### Task 4: 回归锁定、压缩率和参数恢复

**Files:**
- Modify: `tests/test_webui_static_output_settings_overlay.py`
- Modify: `tests/test_webui_static_output_settings_lock.py`
- Modify: `tests/test_webui_static_model_parameters.py`
- Test: `tests/test_webui_static_model_providers.py`

- [ ] **Step 1: 增加矩阵与锁定层共存契约**

在 `OutputSettingsOverlayLayoutContractTests` 增加：

```python
def test_locked_overlay_keeps_compact_matrix_in_the_editor_stage(self) -> None:
    html = Path("codex_image/webui/static/index.html").read_text(encoding="utf-8")
    stage = re.search(r'id="outputSettingsStage"[\s\S]*?</section>', html)
    self.assertIsNotNone(stage)
    markup = stage.group(0)
    self.assertLess(markup.index('id="outputSettingsLockedSummary"'), markup.index('id="settingsGrid"'))
    self.assertIn('id="compactOutputSettings"', markup)
```

- [ ] **Step 2: 增加压缩率和参数恢复检查**

在现有测试中确认以下源码契约仍存在：

```python
self.assertIn('els.compressionTrigger?.classList.toggle("hidden", !compressionEnabled);', script)
self.assertIn('if (!compressionEnabled) {\n    closeCompressionPopover();', script)
self.assertIn('els.sizeModeSelect?.addEventListener("change", handleSizeModeChange);', script)
self.assertIn('els.compressionTrigger?.addEventListener("click", openCompressionPopover);', script)
```

- [ ] **Step 3: 运行回归测试**

Run:

```powershell
python -m pytest tests/test_webui_static_output_settings_overlay.py tests/test_webui_static_output_settings_lock.py tests/test_webui_static_model_parameters.py tests/test_webui_static_model_providers.py -q
```

Expected: 全部通过；如果失败，只修复新矩阵引起的选择器或结构断言，不改变锁定、恢复和提交语义。

- [ ] **Step 4: 提交本任务测试变更**

```powershell
git add tests/test_webui_static_output_settings_overlay.py tests/test_webui_static_output_settings_lock.py tests/test_webui_static_model_parameters.py
git commit -m "保护紧凑排版下的输出设置行为" -m "补充锁定层、压缩率和参数恢复契约，防止布局调整改变提交行为。`n`nConstraint: 本次只允许布局变化`nConfidence: high`nScope-risk: narrow`nTested: 输出设置锁定、覆盖层、模型参数和供应商模型回归测试"
```

---

### Task 5: 构建、类型检查和完整静态回归

**Files:**
- Generated: `codex_image/webui/static/styles.css`
- Generated: `codex_image/webui/static/app.js`
- Generated: `codex_image/webui/static/app.js.map`
- Generated: `codex_image/webui/static/history.js`
- Generated: `codex_image/webui/static/history.js.map`

- [ ] **Step 1: 运行 WebUI 完整检查**

Run:

```powershell
npm run check:webui
```

Expected: CSS 构建、TypeScript `--noEmit` 和两个 esbuild 入口全部成功，退出码为 `0`。

- [ ] **Step 2: 运行相关 Python 测试**

Run:

```powershell
python -m pytest tests/test_webui_static_layout.py tests/test_webui_static_prompt.py tests/test_webui_static_model_parameters.py tests/test_webui_static_model_providers.py tests/test_webui_static_output_settings_lock.py tests/test_webui_static_output_settings_overlay.py tests/test_webui_static_short_height.py -q
```

Expected: 全部通过，无失败和错误。

- [ ] **Step 3: 运行静态检查**

Run:

```powershell
python -m compileall -q codex_image
npm run typecheck:webui
git diff --check
```

Expected: 三条命令退出码均为 `0`，`git diff --check` 无输出。

- [ ] **Step 4: 提交构建产物**

```powershell
git add codex_image/webui/static/styles.css codex_image/webui/static/app.js codex_image/webui/static/app.js.map codex_image/webui/static/history.js codex_image/webui/static/history.js.map
git commit -m "更新紧凑输出设置的前端构建产物" -m "重新生成 CSS 和 JavaScript，确保源码与静态服务产物一致。`n`nConstraint: 线上服务直接读取 static 目录构建结果`nConfidence: high`nScope-risk: narrow`nTested: npm run check:webui、TypeScript 类型检查和相关 Python 回归测试"
```

---

### Task 6: 本地交互和视觉验收

**Files:**
- Create: `artifacts/gpt-output-compact-layout/desktop-light.png`
- Create: `artifacts/gpt-output-compact-layout/desktop-dark.png`
- Create: `artifacts/gpt-output-compact-layout/narrow.png`
- Create: `artifacts/gpt-output-compact-layout/mobile.png`
- Create: `.omx/state/gpt-output-compact-layout/ralph-progress.json`

- [ ] **Step 1: 启动本地 WebUI**

Run:

```powershell
python -m uvicorn codex_image.webui.app:app --host 127.0.0.1 --port 8787 --no-access-log
```

Expected: `http://127.0.0.1:8787/` 可访问，无启动异常。

- [ ] **Step 2: 验证自动和预设尺寸交互**

逐项验证：

| 操作 | 预期结果 |
|---|---|
| 新建任务/首次进入 GPT | 尺寸模式为 `auto`，输出像素显示自动，提交参数包含 `"canvas.size": "auto"` |
| `auto` → `preset` | 方向、分辨率、比例出现，并按当前预设计算像素 |
| `preset/custom` → `auto` | 隐藏方向、分辨率、比例和自定义尺寸，参数草稿恢复后仍为 `auto` |
| 提示词处理切换三项 | 选择值正常保留并进入请求预览 |
| 方向切换 | 比例与像素值同步 |
| 分辨率切换 | 输出像素立即更新 |
| 比例切换 | 方向与像素值同步 |
| 数量切换 1–4 | 请求数量正确 |
| PNG → JPEG/WebP | 压缩率按钮出现，弹层可打开 |
| JPEG/WebP → PNG | 压缩率按钮隐藏，已打开弹层关闭 |
| GPT → 非 GPT 模型 | 旧版 GPT 输出字段按现有规则隐藏 |
| 返回 GPT 模型 | 原字段值和草稿恢复 |
| 锁定/解锁输出设置 | 摘要、遮罩和编辑区状态正常 |

- [ ] **Step 3: 验证自定义尺寸交互**

确认 `custom` 下方向、分辨率和预设比例隐藏，自定义尺寸卡片占满矩阵宽度；宽高输入、交换宽高、比例锁定、首图比例和输出像素更新均正常。切回 `auto` 后自定义尺寸卡片关闭且 `size` 恢复为 `auto`。

- [ ] **Step 4: 截取四种视口截图**

| 截图 | 视口与主题 |
|---|---|
| `desktop-light.png` | `1440 × 1000`，浅色 |
| `desktop-dark.png` | `1440 × 1000`，深色 |
| `narrow.png` | `900 × 1000`，输出面板进入 6 列布局 |
| `mobile.png` | `430 × 932`，输出面板进入 2 列布局 |

截图必须包含完整输出设置区域，且不包含密码、Token、API Key、供应商密钥或浏览器开发者工具中的请求头。

- [ ] **Step 5: 执行 `$visual-verdict`**

使用改造前截图 `artifacts/gpt-output-selects/desktop.png` 和 `artifacts/gpt-output-selects/mobile.png` 作为密度对照，将 JSON 保存到：

```text
.omx/state/gpt-output-compact-layout/ralph-progress.json
```

验收阈值：

| 项目 | 标准 |
|---|---|
| 视觉评分 | `>= 90` |
| 宽屏高度 | 比改造前减少 `35%–45%` |
| 宽屏行数 | 预设模式最多两行 |
| 横向滚动 | 不允许出现 |
| 文字裁切 | 中文、英文及其他现有语言不得裁切 |
| 对齐 | 同一行标签基线和控件底部一致 |
| 主题 | 浅色、深色边框、背景、焦点状态正常 |
| 可访问性 | Tab 顺序与视觉顺序一致，原生方向键选择正常 |

评分低于 `90` 时，按 verdict 的 `differences` 和 `suggestions` 修正，每次改动前后都重新截图并再次执行 `$visual-verdict`。

- [ ] **Step 6: 最终工作区检查**

Run:

```powershell
git status --short
git diff --check
```

Expected: 只包含本计划列出的源码、测试、构建产物、截图和视觉状态文件；`git diff --check` 无输出。

- [ ] **Step 7: 提交视觉验收记录**

```powershell
git add artifacts/gpt-output-compact-layout .omx/state/gpt-output-compact-layout/ralph-progress.json
git commit -m "记录紧凑输出设置的视觉验收" -m "保存桌面、窄屏和移动端证据，确认高度、对齐、主题和交互达到验收阈值。`n`nConstraint: 视觉评分必须达到 90 分`nConfidence: high`nScope-risk: narrow`nTested: 四种视口截图、预设尺寸、自定义尺寸、压缩率和锁定交互"
```

---

## 最终验收清单

- [ ] 9 个下拉框仍为原生 `<select>`，ID 和 option value 未改变。
- [ ] 宽屏为两行矩阵，中等宽度为四行，窄屏两列，超窄单列。
- [ ] 普通短下拉框不再横跨整个输出面板。
- [ ] 提示词处理移出模式槽后仍只在适用模型显示。
- [ ] `auto/preset/custom` 三态显隐、参数草稿恢复和 `canvas.size` 提交值正常。
- [ ] 自定义尺寸、方向/分辨率/比例联动和像素预览正常。
- [ ] PNG/JPEG/WebP 压缩率入口和弹层正常。
- [ ] 输出设置锁定、任务参数采用和草稿恢复正常。
- [ ] `npm run check:webui` 通过。
- [ ] 相关 Python 测试全部通过。
- [ ] `git diff --check` 无输出。
- [ ] 四种截图完成，`$visual-verdict` 评分不低于 `90`。

## 已知风险

| 风险 | 控制措施 |
|---|---|
| CSS 容器查询错误地作用于自身 | 查询容器放在 `.settings-grid`，规则只修改其后代 `.compact-output-settings` |
| 提示词处理移位后模式槽被错误保留空白 | `showModeSettings` 不再包含 `showPromptFidelity` |
| 拆除质量/数量组合容器后非 GPT 模型出现遗留字段 | `model-parameters.ts` 分别定位 `.quality-field` 和 `.quantity-field` |
| 短屏旧规则覆盖新矩阵 | 清理 `80-utilities-responsive.css` 中的旧选择器并运行短屏测试 |
| 自动尺寸默认值在重排中被覆盖 | 保留 HTML、模型清单和新建任务的 `auto` 默认值，并测试任务提交与草稿恢复 |
| 自定义尺寸展开造成字段重叠 | 自定义卡片始终 `grid-column: 1 / -1`，三个预设尺寸字段在 custom mode 隐藏 |
| 多语言标签变长 | 359px 以下单列，并用四种视口和现有语言资源做裁切检查 |
| CSS/TS 源码与线上静态产物不一致 | 必须执行 `npm run check:webui` 并提交生成文件 |

## 计划边界

本计划负责本地源码、测试、构建产物和视觉验收。服务器备份、上传、服务重启和公网验证在本计划全部通过后，按项目现有部署流程单独执行，避免把未通过视觉验收的布局直接发布到生产环境。


