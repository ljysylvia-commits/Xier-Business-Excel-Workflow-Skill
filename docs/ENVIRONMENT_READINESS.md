# ENVIRONMENT_READINESS —— 安装 / 首次运行能力检查

> 目标：让 Agent 在处理 Excel/CSV/Dashboard/HTML 前先判断环境能力。缺关键能力时，先建议用户安装适配的官方插件 / Skill / 工作台能力；不要用低可信降级路径伪装完整交付。

## 1. 原则

- 本 Skill 是数据交付流程护栏，不是 Excel 引擎、浏览器引擎或插件管理器。
- 执行前按能力矩阵判断，不按环境名硬编码。
- 有官方或环境原生成熟能力时，优先使用成熟能力；没有时只能做可验证子集，或停止并建议安装。
- 外部能力提供方（如 CoderWork / WorkBuddy）可以作为 workbook 读写、Office 渲染或人工可视检查的承载，但必须记录输入、输出、操作摘要和验收证据。
- 缺少视觉/重算能力时，Excel Dashboard / HTML 报告最高只能进入 `partial_verified`；无法验证关键数时应停止。

## 2. 能力矩阵

首次安装后、首次处理新交付形态前，记录以下能力：

| 能力 | 必要性 | 可接受来源 | 缺失时处理 |
|---|---|---|---|
| `csv_read_write` | CSV 清洗必需 | shell / Python / 内置数据工具 | 缺失则停止 |
| `xlsx_read` | Excel 清洗必需 | 官方 spreadsheet/xlsx Skill、Python openpyxl、Office/工作台导出 | 缺失则不能处理 xlsx |
| `xlsx_write` | Excel Dashboard 必需 | 官方 spreadsheet/xlsx Skill、Office/工作台、可靠 workbook 库 | 缺失则不交付 xlsx Dashboard |
| `formula_recalc` | 含公式 workbook 必需 | 官方 spreadsheet 能力、LibreOffice/Office、工作台 | 缺失则不能声明公式结果已验证 |
| `dashboard_render_or_screenshot` | 可视 Dashboard 验收必需 | 浏览器/Office 渲染、截图工具、WorkBuddy/CoderWork 人工可视检查 | 缺失则只做结构+关键数替代验收，状态最多 partial |
| `html_render_or_dom_check` | HTML 报告必需 | 浏览器渲染或 DOM/静态检查 | 无浏览器时至少 DOM 检查；关键视觉无法验证则 partial |
| `browser_available` | HTML/截图强验收需要 | 官方 browser 插件、Playwright、工作台浏览器 | 缺失则记录降级 |
| `libreoffice_or_office_available` | workbook 重算/打开检查需要 | LibreOffice、Excel、工作台 Office 能力 | 缺失则不能承诺打开/重算正常 |
| `yaml_support` | 注册/manifest 汇编需要 | PyYAML 或等价 YAML parser | 缺失则不能注册/汇编 manifest |
| `python_packages` | 套件脚本依赖 | `requirements.txt` + suite yaml `requires` | 缺失则停止并列安装项 |

## 3. 交付形态的最低能力

| 交付形态 | 最低能力 | 没有时 |
|---|---|---|
| 清洗 CSV | `csv_read_write` + 源文件读取能力 + 独立校验 | 停止 |
| 清洗 Excel | `xlsx_read` + 溯源校验 | 停止或请用户转 CSV |
| Excel Dashboard | `xlsx_read` + `xlsx_write` + 关键数独立复算；若含公式还需 `formula_recalc` | 停止或改为 CSV/HTML/Markdown；不能伪装 Dashboard 完成 |
| HTML 报告 | HTML 生成 + DOM/文本锚点检查；最好有浏览器渲染 | 无渲染则最多 partial，并记录未验证范围 |
| 可视验收 | `dashboard_render_or_screenshot` 或等价人工可视检查证据 | 最多 partial |
| 注册套件 | YAML 支持 + consistency_check + 正向/负向 validation | 缺失则不得注册 |

## 4. Codex 适配

在 Codex 环境中：

- 先检查当前会话是否已有官方 spreadsheet / xlsx、documents、browser 等能力。
- 有 spreadsheet/xlsx 能力：Excel 读写、样式、公式、图表、渲染优先交给该能力。
- 有 browser 能力：HTML 报告和 Dashboard 截图优先做真实渲染检查。
- 没有这些能力：建议用户安装或启用对应官方插件 / Skill；安装前只做 CSV、静态 HTML、或其它可验证子集。
- 不要把 openpyxl 文件写出等同于“Excel Dashboard 视觉验收通过”；必须有重算/打开/渲染证据或明确 partial。

## 5. Claude Code 适配

在 Claude Code 环境中：

- 先检查可用 Claude Skills、MCP 工具、shell、Python 包、LibreOffice/Office。
- 如果没有本地 xlsx/spreadsheet Skill，但用户有 CoderWork / WorkBuddy，可建议把它作为 workbook 打开、渲染、截图、人工检查的能力提供方。
- 使用 CoderWork / WorkBuddy 时，必须记录：
  - 发送/打开的文件。
  - 执行的操作摘要。
  - 返回或保存的产物。
  - 可视检查证据或用户确认范围。
- 若只能用 shell + Python，Excel Dashboard 不应声明 fully verified；可交付 CSV 或静态 HTML 子集，并写清未验证范围。

## 6. Antigravity 适配

在 Antigravity 环境中：

- 不假设插件名称；先根据工具列表判断是否有表格、浏览器、Office/渲染、文件系统和 shell 能力。
- 若只有代码执行能力，可做 CSV 清洗、静态 HTML、结构检查和关键数独立复算。
- 需要 Excel Dashboard、公式重算或截图验收时，建议用户安装官方/可信表格处理与浏览器/Office 渲染能力，或接入 CoderWork / WorkBuddy 作为外部工作台。
- 无法补齐能力时，按 `VALIDATION_CONTRACT.md` 降级或停止，不得说最终可信。

## 7. 缺能力时的标准提示

```text
当前环境缺少 {能力名}，会影响 {交付形态/验证范围}。

我可以继续做的部分：{CSV / 静态 HTML / 结构检查 / 关键数复算}
不能承诺的部分：{Excel 打开正常 / 公式已重算 / Dashboard 视觉已验收 / 浏览器渲染正常}
建议安装或启用：{官方 spreadsheet/xlsx Skill 或插件 / browser 能力 / LibreOffice 或 Office 渲染能力 / CoderWork 或 WorkBuddy 工作台}
若继续降级执行，最终状态最多为 partial_verified，并会在 validation contract 中列出未验证范围。
```

## 8. 记录要求

每次涉及 Excel Dashboard、HTML 报告、注册或跨工具协作时，`info.json`、对应人读 `pipeline_info.yaml` / `analysis_info.yaml` 视图、以及 plan 第 8 章必须记录：

- 本次可用能力矩阵。
- 缺失能力与影响。
- 选择的工具路径。
- 降级原因。
- 未验证范围。
