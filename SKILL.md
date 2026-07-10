---
name: xier-business-data-workflow-skill
description: |
  Xier Business Data Workflow Skill：让 Agent 稳定复用同类业务数据的获取、处理和分析流程，
  用可校验的数据资产支持业务问题回答和决策输出。
  面向业务、运营、电商、市场、销售分析和企业内部 Agent 场景；帮助 Agent 在用户已有权限下取得或接收
  Excel、CSV、JSON、JSONL、网页表格、BI 导出文件、业务系统下载文件、压缩包等业务数据，
  清洗成可理解、可追溯、可校验的数据资产，再生成业务分析、看板、报告或协同产物。
  首次遇到新数据源、新表结构或新分析问题时走共创；跑通后注册为可复用 data_acquisition source、
  data_cleansing suite 或 data_analysis suite；之后同类任务稳定复用，并用 source contract / validation contract 说明结果边界。
  触发场景：① 用户没有上传 raw data，但提出业务分析、报表、看板、复盘或决策支持需求，需要从数仓、BI、网站、API、外部工作台或手动导出取得数据；
  ② 用户提供 Excel/CSV/JSON/JSONL/html_table/zip 等 raw data，需要清洗、规整、宽转长、字段标准化、结构校验或按已注册 suite 处理；
  ③ 用户基于 raw data 或 clean data 提业务问题，需要趋势、同比、占比、渠道/商品/人群/区域对比、异常识别、活动复盘、Dashboard、HTML/Markdown 报告或协同产物；
  ④ 用户要新增或修改数据获取 source、数据清洗 suite、数据分析 suite。
  关键词：业务数据工作流、数据获取、取数、data_acquisition、data_cleansing、data_analysis、清洗、规整、宽转长、业务分析、运营分析、电商分析、决策支持、报表、看板、复盘、HTML 报告、source contract、validation contract、复用、共创、source、suite、manifest。
---

# Xier Business Data Workflow Skill

> 这是一个面向业务数据工作流的**数据获取、数据清洗、数据分析与交付护栏**。它自带执行/共创/注册流程、原则文档与校验工具，但**不预置任何业务 source、数据清洗套件或数据分析套件**——
> `data_acquisition/`、`data_cleansing/` 与 `data_analysis/` 初始为空。任何业务的第一次取数/清洗/分析都会走"共创"，跑通后固化为可复用套件。

## 1. 四种模式

| 模式 | 触发 | 做什么 | 详细步骤 |
|---|---|---|---|
| 数据获取 `data_acquisition` | 用户没有上传数据，或数据在数仓 / BI / 网站 / API / 外部工作台 | 匹配已注册 source → source_preflight → 调用或交接给批准后端 / 手动导出 → raw data 校验 → handoff 到清洗/分析 | `docs/DATA_ACQUISITION_SOP.md` |
| 数据清洗 `data_cleansing` | 已有 raw data，或上传 Excel/CSV/JSON/JSONL/网页表格/业务系统下载文件 | 匹配已注册数据清洗套件 → 确认 → 清洗成可理解、可追溯、可校验的数据资产 → validation contract 判定状态 → 证据交付 | `docs/EXECUTION_SOP.md` 第 2 节 |
| 数据分析 `data_analysis` | 业务提问 / 指定分析需求 | 匹配已注册数据分析套件 → 定位数据 → 计算 → validation contract 判定状态 → 多形态证据交付 | `docs/EXECUTION_SOP.md` 第 3 节 |
| 共创 / 注册 | 不匹配任何已注册 data_acquisition source / data_cleansing suite / data_analysis suite，或用户明确提新需求（**首次使用必经此模式**） | 对齐方案(plan.md) → 生成套件 → 校验跑通 → 注册 | `docs/COCREATION_SOP.md`；注册见 `docs/REGISTRATION_SOP.md` |

## 2. 入口路由决策表（收到用户输入后，按第一条命中的行走）

| # | 输入情形 | 路由 |
|---|---|---|
| 1 | 未上传文件 + 业务分析 / 报表 / 看板 / 复盘需求 | 先进入 **数据获取模式**：读 `data_acquisition/manifest.json`（只看 status=enabled）→ 命中 source 后按 `DATA_ACQUISITION_SOP` 取得 raw data；不命中 → 共创（新 data_acquisition source） |
| 2 | 用户说明数据在数仓 / BI / 网站 / API / 外部工作台 | 先进入 **数据获取模式**，不直接清洗或分析 |
| 3 | 上传文件 + 消息含"做/生成/样例/模板/看板"类意图词 | **先问**："这个文件是要清洗的数据，还是你想要的结果样例？" → 数据→走 5；样例→共创(分析场景) |
| 4 | 一次上传多个文件 | 逐个进入行 5 的匹配，按队列依次执行 |
| 5 | 上传文件（要清洗的数据） | 读 `data_cleansing/manifest.json`（只看 status=enabled）→ 匹配数据清洗套件 → 命中走清洗线；**空表或不匹配 → 共创（新数据清洗套件）** |
| 6 | 文件命中多条数据清洗套件指纹 | 列出命中项与差异，请用户选，再走清洗线 |
| 7 | 已有 raw data / clean data 后的业务提问 | 读 `data_analysis/manifest.json`（只看 status=enabled）→ 数据分析套件定位 → 命中走分析线；**空表或不匹配 → 共创（新数据分析套件）** |
| 8 | 明确提出新需求（"帮我加一条取数路径/数据清洗套件/数据分析套件"） | 共创模式 |

> 冷启动说明：初次部署时三个 manifest 均为空，因此**前几次交互几乎都会落到共创**——这是预期行为，不是错误。每成功共创一次就多一条可复用 source / data_cleansing suite / data_analysis suite，Skill 逐步"长厚"。

## 3. 硬规则（任何模式都必须遵守）

1. **验证契约是硬门**：产物生成后只算 `generated`；必须由 validation contract 判定 `verified` / `partial_verified` / `validation_failed`。不过 → 不交付为结果，自行修复后重跑。
2. **plan.md 活文档**：共创没有 plan.md 不开工；共创实现前必须通读 `docs/plan_template.md` 并创建完整 9 章骨架，只读 `COCREATION_SOP.md` 不满足开工条件；交互/执行/校验中的任何问题与修改立即回写 plan.md。
3. **单一事实源**：逻辑=脚本；口径与理由=plan.md + CALIBERS.md；yaml=执行契约（由 plan 生成）；manifest=工具汇编的派生物（不手编）；运行统计=usage.json（工具写回）。同一信息不在两个可编辑处重复。
4. **脚本就地执行**：以绝对路径调用套件内 scripts/，输入/输出路径一律参数传入；禁止把脚本复制到工作目录；禁止引用 skill 外的绝对路径（用 `tools/`）。
5. **证据交付**：交付必须依据 validation contract；只说明已验证范围、未验证范围、oracle 来源、假设项和关键数复算，不用安抚性话术替代证据。
6. **断点续跑**：执行每步完成即通过 `tools/output_manager.py step` 写回本次运行 `info.json` 的 `steps` 区块，并同步生成人读 `data_cleansing_info.yaml` / `data_analysis_info.yaml`；中断重入先读 `info.json`，报告进度并询问续跑/重跑。
7. **业务口径中立**：本 Skill 本体可以用典型系统导出报表作为触发例子，但不写死任何业务指标定义、渠道分类、平台专属算法或分析结论；一切业务语义都存在具体套件的 CALIBERS.md 与 references 里，由共创产生。
8. **工具协作边界**：本 Skill 不替代表格/文档/可视化工具；若环境已有 spreadsheet/xlsx/html 能力，优先调用成熟工具完成读写与渲染，本 Skill 只负责流程、契约、溯源、校验与沉淀。若后续接入专门的 HTML 分析 Skill，本 Skill 作为上游提供 clean CSV、CALIBERS、数据范围、关键数锚点和 validation summary。
9. **数据获取先检**：没有 raw data 时不得直接进入清洗/分析。先按 `docs/DATA_ACQUISITION_SOP.md` 匹配或共创 data_acquisition source，完成 source_preflight、access / runtime requirements 确认、raw data 校验和 `data_acquisition_log.json` 后，才能 handoff。
10. **环境 readiness 收窄**：安装 / 首次运行 gate 只检测 / 确认 `workbench_profile` 与 `table_processing_need`；SQL / API / browser download / external workbench / secret management 只进入 data_acquisition 的 source_preflight 和风险提示，不作为 gate 检测或安装推荐。缺 Excel / xlsx 文件处理能力时，Workbuddy / 外部 Agent / 企业 Agent 默认建议 `xlsx.skill`；Codex / OpenAI runtime 默认使用 `spreadsheets` skill。
11. **校验隔离**：独立校验脚本不得 import 主生成脚本的计算函数；必须从源数据或 clean CSV 重新取数复算关键结果，并把 validation 状态回写到本次运行 info。
12. **旧产物清理走工具**：同数据清洗套件每日新增数据默认完整重跑生成新 run；旧 run 的 CSV 不做原地 append，清理只能走 `tools/cleanup_manager.py` 的 plan / apply / tombstone 流程。

## 4. 使用约定（向用户说明）

- **清洗与其后的分析请在同一个 Session 内完成**：Skill 目录内文件跨 Session 持久，但 workspace 运行产物不保证跨 Session 存在。分析时找不到依赖的清洗产物 → 按 SOP 提示用户先补清洗。
- 分析不必都依赖数据清洗套件：也支持用户直接提供一张规整的表来做分析（见 analysis.yaml 的 `user_files`）。
- 运行产物统一落 workspace：`output/data_cleansing/{id}_{数据截止日期}_{序号}/` 与 `output/data_analysis/{id}_{数据截止日期}_{序号}/`。

## 5. 目录导航（按需读取，不要一次性全读）

| 路径 | 内容 | 何时读 |
|---|---|---|
| `docs/DATA_ACQUISITION_SOP.md` | 数据获取模式：source 匹配、source_preflight、引用文件读取、raw data 校验和 handoff | 用户未上传数据、数据在外部系统、或分析依赖数据尚未取得时 |
| `docs/EXECUTION_SOP.md` | 数据清洗 / 数据分析 / 跨套件执行 checklist | 执行时 |
| `docs/COCREATION_SOP.md` | 共创流程（阶段一） | 共创时（**首次使用必读**） |
| `docs/REGISTRATION_SOP.md` | 注册改造 checklist（阶段二） | 注册时 |
| `docs/ENVIRONMENT_READINESS.md` | 收窄的安装/首次运行 readiness gate：workbench_profile + table_processing_need + derived outputs | 安装后、首次处理表格数据时 |
| `docs/plan_template.md` | 对齐文档 9 章骨架 | 共创开工前必读，并用于先创建本次 plan.md |
| `docs/EXCEL_AGENT_PRINCIPLES.md` | Agent 处理 Excel/CSV 的通用原则与避坑清单 | 表格清洗、Dashboard、Excel 交付时 |
| `docs/OUTPUT_ACCEPTANCE.md` | CSV / Excel Dashboard / HTML 报告的验收标准 | 交付前 |
| `docs/VALIDATION_CONTRACT.md` | 机器可读验证状态契约；决定 verified / partial / failed | 生成校验脚本前 |
| `docs/VALIDATION_PATTERNS.md` | 独立校验脚本的通用模式与关键数锚点约定 | 生成校验脚本前 |
| `docs/IMPROVEMENTS.md` | Skill 自迭代建议登记 | 注册第 10 步写入 |
| `data_cleansing/_template/` | 新增数据清洗套件的脚手架（fixed / parametric 两种完整示例） | 共创数据清洗套件时照抄 |
| `data_acquisition/sources/_template/` | 新增数据获取 source 的脚手架（acquisition.yaml + RUNBOOK/PROMPT/SUBAGENT_TASK/LEARNINGS/plan） | 共创数据获取 source 时照抄 |
| `data_analysis/_template/` | 新增数据分析套件的脚手架（完整示例） | 共创数据分析套件时照抄 |
| `data_acquisition/manifest.json` / `data_cleansing/manifest.json` / `data_analysis/manifest.json` | 注册索引（初始为空，工具汇编维护） | 路由时 |
| `references/data_dictionary_guide.md` | 数据字典读写指南 | 共创取数时 |
| `tools/` | data_cleansing_runner / drift_check / cleanup_manager / output_manager / consistency_check / recalc | 由 SOP 指定步骤调用；复用已注册数据清洗套件时优先用 data_cleansing_runner；旧 run 清理走 cleanup_manager |
