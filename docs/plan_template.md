# {套件名} 方案文档（plan.md）

> 活文档铁则：① 没有本文件不开工；② 交互、执行、**校验**中的任何问题与用户修改，立即回写本文件对应章节，不留在对话里。
> 本模板为 data_acquisition source、data_cleansing 套件与 data_analysis 套件**共用**的 9 章骨架。类型化完整示例见 `data_acquisition/sources/_template/plan.md.example`（数据获取）、`data_cleansing/_template/plan.md.example`（数据清洗）与 `data_analysis/_template/plan.md.example`（数据分析）。
> 涉及 Excel/CSV 或 HTML 交付时，同时遵守 `docs/EXCEL_AGENT_PRINCIPLES.md`、`docs/OUTPUT_ACCEPTANCE.md` 与 `docs/VALIDATION_CONTRACT.md`。
> 本模板是共创实现前的对齐闸门，不是注册后补全文档。Agent 必须先复制 9 章骨架再共创；第 2~6 章可以先写推断或待确认项，但不得空白进入实现。

## 第 1 章 问题定义（以意图理解开头）

- 用户想达成什么（一句话）：
- 给谁看 / 多久用一次：
- 输入是什么（文件类型 / 数据源 / 外部系统）：
- 产出形态（由 Agent 从意图推理，用户确认；多态：CSV / Excel / HTML / Markdown / 结论 / 邮件）：
- 用户提供的样例/模板（如有，记录文件名与要点）：

## 第 2 章 输入理解

- 数据源结构（Sheet 结构 / 字段含义 / 维度层级）：
- （数据获取 source）source_type / source_handle / access / runtime_requirements / raw outputs：
- 覆盖范围（时间、渠道、指标）：
- 脏数据 / 缺失 / 特殊值情况（如字符串 "(NULL)"、多种日期格式）：
- （数据分析套件）依赖哪些清洗产物 或 用户直接提供的表：

## 第 3 章 映射规则

- 原始数据 → 目标结果的字段级映射（逐项列表，含查询条件）：
- （数据获取 source）source handle / filters / params / execution.mode / handoff 规则：
- 特殊处理（误标修正 / 前缀拆分 / 表合并 / 指标统一化 / 单位换算）：
- 标注：哪些映射是 **Agent 推断**（用户须重点复核）。

## 第 4 章 输出定义

- 产物清单（文件名 + 用途）：
- 字段 Schema（名称 / 类型 / 格式 / 单位）：
- （数据获取 source）raw_outputs[] / expected columns 或 fields / data_acquisition_log.json 字段：
- 关键数锚点（Dashboard/HTML 必须出现且可校验的指标、位置或文本锚点）：
- expected values 来源分级（source_recomputed / external_authoritative / user_provided_target / agent_inferred）：
- 命名规范：`{套件id}_{数据截止日期YYYYMMDD}_{3位序号}`；数据截止日期 = CSV max(date)。

## 第 5 章 校验方案

- 清洗：中间校验（可轻量）+ **终检全量逐格**（原始单元格↔CSV 逐格比对，100% 通过为硬门）。
- 数据获取：raw output 格式可读、required columns 或 fields、row/record count、date_range、sample_total_recalc、source evidence 字段完整。
- 分析：**独立重算逐格**（校验脚本不得 import 主生成脚本、从 CSV 或源数据零知识重算、逐格对比，容差 0.001 / 相对 0.01%，exit 0/1）。
- Dashboard/HTML：按关键数锚点检查；无法截图/渲染时，记录降级原因并做结构、关键单元格/文本、错误字符串替代验收。
- validation contract：校验脚本输出 `validation_contract.json`，由 output_manager 决定 generated / verified / partial_verified / validation_failed。
- 通过标准与失败处理（不过 → 不交付，修复重跑）。

## 第 6 章 执行计划

- 步骤列表（脚本 + 参数；当前 runner 只支持已声明的标准 placeholder，不支持 `{mid}`）：
- 运行依赖 requires（如 openpyxl / lxml / libreoffice / 环境内 spreadsheet 或 xlsx 能力）：
- （数据获取 source）execution.required_refs / ref_read_order / instruction_policy / source_preflight / runtime_requirements / fallback：
- 轻量 readiness 与降级策略（workbench_profile、table_processing_need、derived table backend、visual risk notes）：
- 参数（如 report_date，缺省 = 自动取数据最大日期）：

## 第 7 章 确认清单（注册时抽出生成 CALIBERS.md）

> 每条 = 一个口径决策，用户逐条打勾。分四类标注：[已确认] / [Agent推断-待复核] / [假设-按默认先跑] / [结构依赖]。

- [ ] 聚合方式（总量 / 日均 / 累计）：
- [ ] 对比口径（读现成同比字段 / 按同口径重算）：
- [ ] 比例分母（占比 ÷ 谁）：
- [ ] 周期天数规则（完整月 / 当月 / YTD）：
- [ ] 边界处理（单日缺失 / 去年无基准）：
- [ ] 单位与差值表达（pp / 原单位）：
- [ ] （数据获取 source）用户确认有访问 / 导出权限，且凭据不落盘：
- [ ] （数据获取 source）外部 `.env` / 环境变量名 / secret manager 引用名只记录引用，不记录值：
- [ ] （数据获取 source）用户补齐权限 / 后端 / secret / 外部 `.env` 支持后，确认这些运行条件可作为下一次复用条件：
- [ ] （数据获取 source）execution.mode 与 handoff 方式：
- [ ] （按需增删其它口径…）

## 第 8 章 执行日志（全程回写）

> 格式：`日期 | 事件(修改/校验/问题/决策) | 内容 | 结果/去向`

| 日期 | 事件 | 内容 | 结果 |
|---|---|---|---|
|  |  |  |  |

## 第 9 章 知识沉淀

> 本章在注册阶段整理。自迭代不在普通共创/测试时直接改 Skill 本体，而是在 data_cleansing / data_analysis 注册 gate 做结构化复盘。

- case_specific_learnings（只属于本套件的坑、口径、数据结构经验 → 写入套件 `LEARNINGS.md`）：
- generalizable_skill_gaps（通用 SOP / schema / validation / output acceptance 缺口 → 候选写入 `docs/IMPROVEMENTS.md`）：
- data_acquisition_dependency_updates（source_preflight / backend handoff / raw data 校验缺口）：
- validation_pattern_updates（是否出现可复用校验模式）：
- environment_dependency_updates（是否发现环境能力 / 插件 / 工作台依赖缺口）：
- template_or_example_candidates（适用场景、输入要求、输出形态、业务假设、脱敏状态；用户确认后才晋升）：
- tooling_opportunities（runner / drift checker / readiness 工具等）：
- user_decisions_needed（必须用户裁决，Agent 不得自行改本体）：
