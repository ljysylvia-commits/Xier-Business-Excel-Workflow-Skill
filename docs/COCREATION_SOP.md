# COCREATION_SOP —— 共创标准流程（阶段一：workspace 自由共创）

> 触发：上传/提问不匹配任何已注册 data_acquisition source、data_cleansing 套件或 data_analysis 套件，或用户明确提出新需求。
> **两阶段模型**：本文件覆盖 Phase 1~5（在 workspace 自由共创，只求跑通，不要求符合 Skill 目录/命名规范）；
> 跑通后进入阶段二，按 `REGISTRATION_SOP.md` 一次性规范化迁入 Skill。
> **两条铁则**：① 没有 plan.md 不开工（用 `docs/plan_template.md` 建骨架）；
> ② 交互/执行/**校验**中的任何问题与用户修改，立即回写 plan.md 对应章节。

## Phase 0 · plan 前置闸门（任何共创先做）

```
□ 完整读取 docs/plan_template.md。
□ 在本次 workspace run 目录复制 9 章骨架，创建 plan.md。
□ 先填入已知信息；未知项显式标成 [Agent推断-待复核] / [假设-按默认先跑] / [结构依赖]，不得留空跳过。
□ 没有完成 plan.md 骨架前，不得写实现脚本、清洗 CSV、Dashboard、HTML、validation contract 或注册文件。
```

## Phase 1 · 意图理解 → plan 第 1 章

```
□ 三问（缺哪问哪，已明确的不重复问）：
   1) 想达成什么？ 2) 给谁看？ 3) 多久用一次？（一次性则最后不必注册）
□ 先判断数据是否已经可达：
   - 没有上传文件，且数据在数仓 / BI / 网站 / API / 外部工作台 → 本次共创对象先定为 data_acquisition source
   - 已有 raw Excel/CSV → 可共创 data_cleansing 套件
   - 已有 clean CSV 或规整表 → 可共创 data_analysis 套件
□ 产出形态由你从意图推理（不预设 Excel）：
   快速回答→结论/文本表格；定期汇报→Excel/HTML；邮件送达→email；数据供后续加工→CSV/Excel
□ 若做 Excel Dashboard/工作簿：请用户提供目标样例/模板（含格式）；若环境已有 spreadsheet/xlsx 能力，优先调用该能力完成读写与渲染
□ 写入 plan 第 1 章，向用户复述一句话意图请其确认
```

## Phase 2 · 桥接 + 残余歧义 → plan 第 2~6 章

```
□ 若数据还不在本地，先读：
   - docs/DATA_ACQUISITION_SOP.md（数据获取模式、source_preflight、引用文件读取、raw data 校验）
   - data_acquisition/sources/_template/（新增 source 脚手架）
□ 若涉及 Excel/CSV 清洗、Excel Dashboard 或 HTML 报告，先读：
   - docs/EXCEL_AGENT_PRINCIPLES.md（表格处理原则与避坑）
   - docs/OUTPUT_ACCEPTANCE.md（交付验收标准）
   - docs/VALIDATION_CONTRACT.md（机器可读验证状态契约）
   - docs/VALIDATION_PATTERNS.md（独立校验与关键数锚点）
□ 定位源：
   - data_acquisition 共创：确认 source_type、source_handle、access、runtime_requirements、execution.mode、execution_backend、raw_outputs[]、validation checks 和 handoff
   - 不写 SQL / API connector / 浏览器自动化；只记录 query_handle / connector handle / dashboard handle / runbook / prompt / subagent task、外部 `.env` 引用名或 secret manager 引用名
□ 读源：
   - 清洗共创：读原始 Excel 各 Sheet 表头与抽样行，识别结构（固定结构？还是可参数化的模式？）
   - 分析共创：优先读依赖动线的 references/data_dictionary.md；缺失或不全 → 直接读 CSV 表头+抽样推断，
     并把推断结论回填数据字典（轻量，不求穷尽）
□ 建映射：产出的每个字段 → 数据源的具体查询/变换，写入 plan 第 3 章
□ 定关键数锚点：列出 Dashboard/HTML 必须出现并可自动验收的关键指标、位置或文本锚点，写入 plan 第 4/5 章
□ 生成残余歧义清单（只问"目标与源都推不出"的，提议式=给默认值+理由，用户点头/改）：
   ├─ 必问：聚合方式(总量/日均) / 对比口径(读现成/重算) / 比例分母 / 周期天数规则 / 边界处理(缺失/无基准)
   ├─ 能猜就猜：字段/维度语义（如用户口中的某业务词 ≈ 数据中某列的某个取值）→ 在 plan 显式标注"Agent 推断，请重点复核"
   └─ 不问：样例已写明的单位/小数位/负值样式/布局/列
□ 清洗类深域知识的获取法：清洗后若合计对不上/交叉校验异常 → 怀疑原表标签误标 →
   向用户追问业务口径（"这个'同比'列，实际是比率还是百分点差？"）→ 确认后作为修正规则落进脚本，
   并记入 plan 第 3 章与第 7 章
```

## Phase 3 · 用户确认（对齐闸门——此前不写实现代码）

```
□ 把方案草稿（plan 第 1~6 章）+ 第 7 章确认清单 + 残余歧义清单一并给用户
□ 用户逐条回答/修改 → 每处改动立即回写 plan
□ 用户也答不上来的口径 → 采用你建议的默认值先跑 + 在 plan 第 7 章登记为 [假设]，交付时提醒
□ 用户给的样例本身口径存疑 → 先质疑并摆证据（数据比对/口径矛盾点）；用户坚持 → 照办并在 plan 第 8 章存证
□ 闸门条件：plan 第 1~6 章已有内容，且第 7 章确认清单全部打勾（含 [Agent推断] 项获复核、[假设] 项已登记）
□ 闸门未满足前，不得生成实现代码、清洗脚本、校验脚本、clean CSV、Dashboard/HTML 或 validation contract
```

## Phase 4 · 生成实现

```
□ 生成执行脚本（逻辑的唯一真相源）：
   - argparse 传参（--input/--output/--report-date 等），不硬编码路径，不引用 skill 外绝对路径
   - 数值：全精度推导，仅最终结果 round(…, 6)（防链式舍入误差）
   - 日志：结构化写 {output}.log
   - 可调用环境中的 spreadsheet/xlsx/html 等成熟工具，但必须把输入、输出、参数、关键计算与校验记录落盘
□ 若是 data_acquisition source：
   - 生成 `acquisition.yaml`、`LEARNINGS.md`
   - 按 `execution.mode` 生成 `RUNBOOK.md`、`PROMPT.md` 或 `SUBAGENT_TASK.md`
   - `acquisition.yaml` 必须声明 `execution_backend`、`execution.*_usage`、`required_refs`、`ref_read_order`、`instruction_policy`、`access`、`runtime_requirements`、`source_preflight`、`output.raw_outputs[]`、`validation`、`data_acquisition_log`、`handoff.raw_outputs[]`
   - 不生成通用自动取数工具；如需脚本，必须是用户批准、无密钥、可审计的 source 专属脚本
   - 不保存真实 `.env`、密码、token、cookie、API key 或登录态
□ 生成独立校验脚本（与主脚本同源异构）：
   - 不 import 主脚本任何函数；从数据源零知识重算全部结果；逐格对比（容差 0.001 / 相对 0.01%）
   - exit 0=通过 / 1=失败；差异明细写 {output}.validate.log；同时输出 validation_contract.json
   - 校验 Dashboard/HTML 时至少检查关键数锚点；无法渲染截图时，改查 Sheet/DOM 结构、关键单元格/文本、图表对象数量、错误字符串
□ （清洗类）校验按两级：中间校验（位置映射/完整性，可轻量）+ 终检全量逐格（原始格↔CSV 逐格，100%）
```

## Phase 5 · 校验闭环

```
□ 跑通全链路：生成 → 校验
□ data_acquisition source 的跑通标准：source_preflight 通过或明确降级 → raw outputs 可取得或手动导出 → 格式、结构类型、expected columns / fields、row/record count、date_range 校验通过 → `data_acquisition_log.json` 字段完整 → handoff 决策明确
□ 校验不过 → 你自行迭代修复（读 validate 日志定位→改脚本→重跑），不把实现问题抛给用户
□ 每次修复与结果回写 plan 第 8 章执行日志
□ 通过后按 validation contract 做证据交付（验证状态 + 范围 + 未验证范围 + oracle 来源 + 假设项 + 关键数），并问：
   "这个{数据获取 source / 数据清洗套件 / 数据分析套件}以后还会再用吗？要注册成可复用的{source / data_cleansing 套件 / data_analysis 套件}吗？"
   ├─ 是 → 进入阶段二：按 docs/REGISTRATION_SOP.md 执行
   └─ 否 → 不注册为 source / 套件，只把本次过程证据留在 workspace
```
