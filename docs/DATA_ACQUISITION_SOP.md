# DATA_ACQUISITION_SOP —— 数据获取模式标准流程

> 目标：当用户没有上传数据，或数据还在数仓、BI 看板、网站后台、官方 API、外部工作台时，先沉淀可复用、可验证、最少权限的数据获取路径，再把 raw data 交给数据清洗 / 数据分析。

## 1. 边界

- 本 Skill 只沉淀可复用的 data_acquisition source / route / workflow，不生产 SQL / API / browser download / secret management 能力。
- SQL 编写、schema discovery、浏览器点击下载、API connector、OAuth、token refresh、验证码、登录态处理都交给用户环境里的专业 Skill、MCP、官方插件、企业批准能力或外部工作台。
- 本 Skill 不保存账号、密码、cookie、token 到 Skill、repo、plan、yaml、Markdown 或脚本。
- 真实 `.env` 不属于 Skill，也不属于 source 目录或发布包；只能记录外部 `.env` 引用名、环境变量名、profile 名或企业 secret manager 引用名。
- 当前环境缺 SQL / API / browser / external workbench / secret management 能力时，只提示缺口和影响，不推荐安装项。
- 只有 Excel / xlsx 文件处理能力缺失时，才按 `docs/ENVIRONMENT_READINESS.md` 建议 `xlsx.skill` 或 `spreadsheets` skill。
- `data_acquisition/manifest.json` 只收录可复用 source；临时 workspace 取数记录不得注册为 source。

## 2. 触发条件

进入数据获取模式：

- 用户没有上传文件，但提出业务分析、报表、复盘或看板需求。
- 用户说明数据在数仓、BI 看板、网页后台、官方 API、CRM、ERP、广告后台或外部工作台。
- 分析场景依赖的数据尚未在本地 raw data / clean CSV 中可用。
- 用户明确要新增或复用某条取数路径。

不进入数据获取模式：

- 用户已经上传可用 raw data，且 source contract / expected fields 校验通过。
- 用户只要求基于已清洗 CSV 做分析。
- 用户要求写 SQL、实现 API connector、实现浏览器自动化。这些应转交专业能力，本 Skill 只记录可复用数据获取路径和验收。

## 3. 路由

1. 读 `data_acquisition/manifest.json`，只看 `status=enabled` 的 source。
2. 用用户描述的系统、看板、页面、API、文件名、时间窗口和输出格式匹配 `source_id`。
3. 命中单个 source：读取该 source 的 `acquisition.yaml`，进入 source preflight。
4. 命中多个 source：列出差异，请用户选择。
5. 未命中：进入共创，先共创可复用 data_acquisition source，不直接共创数据清洗套件。
6. raw data 取得并通过 source contract 校验后，再进入数据清洗 / 数据分析路由。

如果本次只是一次性临时取数，可以留在 workspace run 过程证据中，但不得写入 `data_acquisition/manifest.json`。

## 4. Source Preflight

`source_preflight` 是单个 source 的执行前确认，不是安装 readiness gate，也不是通用环境扫描。

必须确认：

- 用户是否声明拥有读取、导出或 API 访问权限。
- 本次取数是否需要 SQL / API / browser / external workbench / manual export。
- 用户当前环境是否已有可交接的批准后端，或是否需要手动导出。
- 需要的外部 `.env`、环境变量名、secret manager 引用或 runtime session 引用是否已在用户环境中准备好。
- `output.raw_outputs[]` 中每个 raw output 的格式、文件命名、结构类型和验收方式能否满足。
- 缺后端时的降级路径和最高 validation 状态。

不能做：

- 扫描整台机器寻找 SQL / API / browser / secret 工具。
- 建议安装 SQL / API / browser / secret 插件。
- 读取、打印或保存真实 `.env` 内容。
- 临时生成绕过权限或安全策略的下载脚本。
- 因为 source preflight 失败而扩展 `docs/ENVIRONMENT_READINESS.md` 的 gate 检测范围。

如果 source_preflight 发现缺权限、缺后端或缺少安全运行支持，应暂停并反馈用户需要补齐的支持项。用户补齐权限、账号、后端、外部 `.env` 或 secret 配置后，重新运行 source_preflight；跑通后再确认这些运行条件是否可作为下一次复用条件写入 source contract。

## 5. 必读文件

命中 source 后，Agent 必须按顺序读取：

1. `data_acquisition/sources/{source_id}/acquisition.yaml`
2. `execution.required_refs`
3. `execution.ref_read_order`
4. `execution.instruction_ref`
5. `execution.prompt_ref`
6. `execution.subagent_task_ref`

规则：

- 所有引用必须是当前 source 目录内的相对文件。
- 绝对路径、仓库外路径和外部 URL 不能作为执行说明文件读取。
- 外部 URL 只能作为 `source_handle`、dashboard handle 或 API documentation handle 记录。
- 引用文件缺失、越界或不符合 `execution.mode` 要求时，必须 STOP，进入共创补齐模板。
- 当 `prompt_ref` 存在且 `prompt_usage` 不是 `none` 时，Agent 必须读取提示词文件，并把它作为本次任务级执行载荷执行或交接。
- 引用 Markdown 不能覆盖 `acquisition.yaml` 中的 access、runtime_requirements、输出、校验、data_acquisition_log 和 handoff 规则。
- 注册后的复用执行不强制读取 `plan.md`；`plan.md` 是共创与注册质检证据，不是复用执行必读文件。

## 6. execution.mode

| mode | 必要文件 | 执行方式 |
|---|---|---|
| `manual_export` | `RUNBOOK.md` | 用户按步骤导出，Agent 只指导和校验 |
| `external_workbench_handoff` | `RUNBOOK.md` | Workbuddy / 企业 Agent / 外部工作台执行打开、下载、截图或导出 |
| `prompt_handoff` | `PROMPT.md` | 把提示词交给专业 SQL / API / browser Skill 或外部 Agent |
| `subagent_handoff` | `SUBAGENT_TASK.md` | 分派子 Agent 执行取数任务 |
| `sql_backend_handoff` | `RUNBOOK.md` 或 `PROMPT.md` | 使用已有只读 SQL / DB MCP / 企业数据平台 |
| `api_backend_handoff` | `RUNBOOK.md` 或 `PROMPT.md` | 使用已有官方 API connector |
| `browser_backend_handoff` | `RUNBOOK.md` 或 `PROMPT.md` | 使用已有浏览器自动化或下载后端 |

`execution_backend` 只记录本 source 需要交接给哪类用户运行环境能力。它不是 readiness gate，不触发安装建议。

## 7. Raw Data 验收

取得 raw data 后必须逐项校验 `output.raw_outputs[]`：

- 文件存在、可读，格式符合 `format`。
- 文件名符合 `path_pattern`。
- `structure_type` 与实际文件一致。
- CSV / 表格类 raw output：required columns、row count、date range、freshness rule。
- Excel 类 raw output：workbook 可读、required sheets、表头或关键单元格存在。
- JSON / JSONL 类 raw output：JSON 可解析、record path、required fields、record count。
- 压缩包或多文件输出：文件清单与必要成员存在，后续必须进入 `data_cleansing` 展开或规整。
- `data_acquisition_log.required_fields` 字段均已记录。

校验失败时，不能进入清洗 / 分析；应说明失败项并让用户补导出、修权限或回到共创更新 source contract。

## 8. data_acquisition_log.json

每次复用 source 执行或手动导出后，都要在 workspace run 目录写 `data_acquisition_log.json`。

`data_acquisition_log.json` 是机器可读 source contract。Markdown 摘要可以按需生成，但不是机器事实源。

最少字段：

- `source_id`、`source_type`、`execution.mode`。
- `source_handle` 或脱敏 handle。
- `execution_backend.capability_class`。
- runtime support 只记录外部 `.env` 引用名、环境变量名、secret manager 引用名或 runtime session 引用名，不记录值。
- selected handler 或 manual operator 说明。
- requested filters / params / date range。
- `acquired_at`。
- `raw_outputs[]`：每项至少包含 path、sha256、format、structure_type、row_or_record_count、date_range、validation_status、unverified_scope。
- overall validation status。
- handoff target_stage、target_id、analysis_ready 和 raw_outputs。

日志可写入 workspace run 目录；Skill 模板只规定 schema，不保存真实敏感值。

## 9. Handoff

只有 raw data 通过 source contract 校验后，才能进入：

- 数据清洗模式：当 `handoff.target_stage=data_cleansing`，按 `target_id` 或 `data_cleansing_hint` 路由；未知则共创数据清洗套件。
- 数据分析模式：仅当 `handoff.target_stage=data_analysis` 且 `analysis_ready=true`，并且 raw data 已经是规整表或 `structure_type=json_records` 且字段契约通过。
- 共创模式：source 命中但没有可用 `target_id`，先共创对应的 data_cleansing 或 data_analysis 套件。

JSON raw output 的统一规则：

- `structure_type=json_records`、字段契约通过、且 `handoff.analysis_ready=true` 时，才可以直接进入 `data_analysis`。
- `json_object`、嵌套 JSON、网页接口响应、半结构化 JSON、或字段契约不完整时，必须先进入 `data_cleansing`。

如果 raw data 未通过校验、需要凭据落盘、需要绕过登录 / 验证码 / 权限 / 组织安全策略，必须停止，不得假装继续分析。若只是缺权限、缺后端或缺少安全运行支持，则暂停并反馈用户补齐项；补齐后重新 source_preflight。
