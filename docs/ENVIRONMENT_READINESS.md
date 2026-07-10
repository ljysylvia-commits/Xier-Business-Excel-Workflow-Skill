# ENVIRONMENT_READINESS —— 安装 / 首次运行轻量 Gate

> 目标：只判断当前工作台画像与本次表格处理需求，给出 Excel / xlsx 后端建议。不要把 SQL / API / browser download / external workbench / secret management 变成安装 gate。

## 1. 原则

- 本 Skill 是数据工作流护栏，不是 Excel 引擎、浏览器引擎、SQL 客户端、API SDK 或插件管理器。
- 安装 / 首次运行 readiness gate 只检测 / 确认两个输入字段：
  - `workbench_profile`
  - `table_processing_need`
- `detected_table_backend`、Excel 后端 recommendation、视觉验收风险都属于 derived outputs / risk notes，不是新的 gate 检测项。
- SQL / API / browser download / external workbench / secret management 只在 `DATA_ACQUISITION_SOP.md` 的 source_preflight 中表达缺口、风险和降级建议，不触发安装推荐。
- Dashboard workbook、公式重算、Office 渲染和截图验收不进入 readiness gate；它们只进入 `risk_notes.visual_acceptance_need`、`OUTPUT_ACCEPTANCE.md` 和 validation contract 的未验证范围。

## 2. Gate Inputs

| 字段 | 允许值 | 说明 |
|---|---|---|
| `workbench_profile` | `workbuddy` / `codex` / `claude_code` / `enterprise_agent` / `unknown` | 当前显示在哪个工作台或 Agent 环境 |
| `table_processing_need` | `csv_only` / `xlsx_read` / `xlsx_read_write` / `workbook_inspect` | 本次数据获取、数据清洗或数据分析需要哪类表格文件处理能力 |

判断方式：

- `workbench_profile` 优先来自当前会话明确上下文、用户说明或 Agent 可见运行环境。
- `table_processing_need` 来自用户请求、已命中的 data_acquisition source、data_cleansing 套件、data_analysis 套件，或本次 raw data 的格式。
- 不扫描整台机器，不探测 SQL / API / browser / secret / external workbench。

## 3. 建议输出格式

```yaml
readiness_gate:
  gate_inputs:
    workbench_profile: workbuddy | codex | claude_code | enterprise_agent | unknown
    table_processing_need: csv_only | xlsx_read | xlsx_read_write | workbook_inspect
  derived_outputs:
    detected_table_backend: xlsx.skill | spreadsheets | openpyxl_only | user_provided | none | unknown
    recommendation: none | install_xlsx_skill | use_spreadsheets_skill | ask_user_to_confirm_backend
  risk_notes:
    visual_acceptance_need: none | formula_recalc | office_render | dashboard_screenshot | dashboard_workbook
    visual_acceptance_is_not_gate_item: true
  notes_only:
    - sql_api_browser_workbench_secret_capabilities_are_not_gate_items
```

要求：

- `gate_inputs` 是唯一 gate 判断依据。
- `derived_outputs` 只能从 gate inputs、当前可见表格后端和用户确认推导。
- `risk_notes` 只说明输出验收风险，不得升级为安装 gate。

## 4. Excel 后端推荐规则

| 当前环境 | 缺失能力 | 推荐 | 原因 |
|---|---|---|---|
| Workbuddy / 外部 Agent / 企业 Agent | `xlsx_read`、`xlsx_write`、`workbook_inspect`、基础 workbook 修改 | 优先建议安装 `xlsx.skill` | 更像通用 Agent Skill，适合作为外部环境的 Excel 文件处理后端 |
| Codex / OpenAI primary runtime | `.xlsx` / `.csv` / `.tsv` 创建、编辑、分析、可视化、渲染、导出 | 使用 `spreadsheets` skill | 该能力依赖 OpenAI primary runtime 与 artifact-tool，适合 Codex 内部 |
| Workbuddy 明确支持 OpenAI `spreadsheets` runtime | 同上 | 可建议 `spreadsheets` skill | 仅当 runtime 兼容性已明确时使用 |
| 仅缺公式重算 / Office 渲染 / Dashboard 截图 | 不进入 readiness gate | 只写风险说明，建议用户用本地 Office / 外部工作台验收 | Excel 后端不等于真实 Office 视觉验收 |

标准提示：

```text
当前环境缺少 Excel/xlsx 文件处理能力，会影响 {xlsx 读取 / workbook 结构识别 / xlsx 写出}。

如果你在 Workbuddy 或类似外部 Agent 环境中使用本 Skill，建议优先安装 `xlsx.skill`，作为本 Skill 的 Excel 文件处理后端。

如果你在 Codex / OpenAI primary runtime 中使用本 Skill，或 Workbuddy 已明确支持 OpenAI `spreadsheets` runtime，则使用 `spreadsheets` skill。

本 Skill 不会自行实现完整 xlsx 引擎；它只会调用已安装的 Excel 后端，并记录输入、输出、校验和未验证范围。
```

## 5. 不进入 Gate 的能力

| 能力 | 文档处理方式 |
|---|---|
| SQL / 数仓 | 如果用户已有只读 SQL / DB MCP / 企业数据平台，data_acquisition 可以记录 query handle、参数、输出和校验；未检测到时不推荐安装项 |
| API | 如果用户已有官方 API connector，data_acquisition 可以记录 connector handle、请求参数、raw response 和 schema 校验；未检测到时不推荐安装项 |
| browser download | 如果用户已有浏览器自动化 / 工作台下载能力，data_acquisition 可以记录页面、筛选条件、导出动作和证据；未检测到时不推荐安装项 |
| external workbench | 用户可用 Workbuddy / Qoderwork / 企业 Agent 做外部操作，data_acquisition 只记录输入、输出和人工确认范围；不推荐具体工作台 |
| secret management | 只写安全边界：不保存账号、密码、cookie、token 或真实 `.env` 到 Skill / source / suite / repo；secret 管理由用户本地或企业环境负责，Skill 只记录外部引用名 |
| Office / visual acceptance | 只进入 output acceptance 与 validation contract 的风险说明；不能声明完整视觉验收 |

## 6. 记录要求

当任务涉及 Excel / xlsx raw data、workbook inspect、Dashboard workbook 或外部工作台时，在 plan 第 6 章或 run info 中记录：

- `workbench_profile`
- `table_processing_need`
- `detected_table_backend`
- `recommendation`
- `risk_notes.visual_acceptance_need`
- 不进入 gate 的能力缺口及影响

缺能力时，不要承诺完整交付。应按 `VALIDATION_CONTRACT.md` 写明 `partial_verified` 或 `validation_failed` 的边界。
