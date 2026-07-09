# EXECUTION_SOP —— 执行标准流程（清洗 / 分析 / 跨动线）

> 使用方式：按 checklist 逐步执行，每步一个动作；判断点只走表内分支，不自行发挥。
> 校验脚本必须输出 validation contract。交付状态由 contract 决定，不由 Agent 自述或固定话术决定。

## 1. 通用约定（所有执行必须遵守）

1. **数据可达性先检**：没有本地 raw data / clean CSV 时，不得直接进入清洗或分析。先按 `docs/DATA_ACQUISITION_SOP.md` 匹配或共创 data_acquisition source，完成 source_preflight、raw data 校验和 evidence log 后再 handoff。
2. **就地执行**：以绝对路径调用套件内 `scripts/`；输入/输出路径一律参数传入；禁止复制脚本到工作目录。
3. **输出目录**：用 `tools/output_manager.py` 创建，命名 `{套件id}_{数据截止日期YYYYMMDD}_{3位序号}`；数据截止日期在产物生成后从 CSV max(date) 回填（先用占位目录，后重命名）。`finalize` 只代表生成完成，状态为 `generated`。
4. **断点续跑**：每步完成立即通过 `tools/output_manager.py step` 把 `{step名, status}` 写入本次运行的 `info.json` `steps` 区块，并同步生成人读 `pipeline_info.yaml` / `analysis_info.yaml`。开始执行前先检查输出区是否有同输入的未完成 run（`info.json.steps` 未全 done）→ 有则报告"上次执行到第 N 步（XX）"并问用户"续跑还是重跑？"。
5. **轻量 readiness**：按 `docs/ENVIRONMENT_READINESS.md` 只确认 `workbench_profile` 与 `table_processing_need`，记录 `detected_table_backend`、recommendation 和 `risk_notes.visual_acceptance_need`。SQL / API / browser download / external workbench / secret management 不进入 readiness gate，只能在 data_acquisition source_preflight 中表达缺口和降级。
6. **校验隔离**：独立校验脚本不得 import 主生成脚本；必须从源数据或 clean CSV 重新取数复算关键结果。校验脚本必须输出 `validation_contract.json`，再用 `output_manager validate --contract ...` 回写状态。
7. **统计**：执行成功后 usage.json 对应条目 run_count +1、last_run 更新（output_manager 完成）；同一 run 重复 validate 不得重复计数。
8. **旧 run 清理**：同 pipeline 新 run 通过后，旧 run 只能由 `tools/cleanup_manager.py` 按 `run_lifecycle.cleanup_policy` 生成 plan / 执行清理；默认只列候选并请用户确认，不手工删除。
9. **异常总则**：任何校验不过 → 输出校验报告路径 + 摘要，**不交付产物**；脚本报错 → 报错原文，不猜测原因空转。

## 2. 清洗线 checklist

```
□ 0. 优先使用标准 runner
     若是已注册清洗动线复用，优先运行 `tools/pipeline_runner.py run` 串联匹配、preflight、
     drift_check、transform、finalize、validation contract 和 usage 更新。runner 报多命中、
     首次执行需确认、partial drift 或 validation_failed 时，按本 checklist 对应分支处理。

□ 1. 匹配动线
     读 pipelines/manifest.json（只看 status=enabled）。先用 filename_hint/pattern_hint 初筛，
     再读命中套件的 pipeline.yaml 做核验。多命中 → 列出差异请用户选。全不中 → 转共创。

□ 2. 理解 + 确认闸门（按 understand.mode 分支）
     [fixed]
       核验指纹："全中" = required_sheets 全命中 + dynamic_sheets 关键词可匹配到
                 + 各 Sheet 的 section 顺序/metric 序列一致 + 无未知新增 Sheet。
       ├─ 该动线首次执行（usage.json 无记录）→ 向用户确认："已匹配 {动线名}，指纹全中，开始清洗？"
       ├─ 非首次 + 全中 → 免确认直接执行，告知一句："已匹配 {动线名}（指纹全中），直接执行。"
       ├─ 部分中（Sheet 齐但顺序/序列有差异）→ 列出差异清单，请用户判断
       └─ 不中 → 转共创
     [parametric]
       遍历套件 profiles/ 做结构核验：
       ├─ 命中已确认 profile → 跳过确认直接用，告知所用 profile 名
       └─ 不命中 → 跑 understand.profile_detect.script → 用 confirm_prompt 向用户展示 profile 草稿
                    → 确认后存入 profiles/（命名），或用户调整后再存

□ 3. preflight：先确认 raw data 已在本地且通过 data_acquisition source contract 或用户上传文件基本检查；
     再按 docs/ENVIRONMENT_READINESS.md 确认 workbench_profile + table_processing_need；requires 依赖逐项核验（缺 → 报缺失项与安装提示，停）；
     输入文件可读；输出可写；运行 `tools/drift_check.py --suite-dir {pipeline_dir} --input {file}`，
     pass 才可免确认继续，partial 必须点名差异请用户判断，fail 转局部重共创；
     记录本次表格后端、derived recommendation、视觉验收风险和可能的降级策略

□ 4. 建输出目录（output_manager，先占位命名）

□ 5. 变换：按 yaml transform.steps 顺序执行；有 produces 声明的中间产物按占位符传给后续 step

□ 6. 回填数据日期：从产出 CSV 取 max(date) → 目录重命名 {id}_{YYYYMMDD}_{seq}

□ 7. 校验：按 validation.layers 顺序执行，最终必须生成 validation contract
     - rigor=staged 层：通过才继续
     - rigor=exhaustive 终检层【硬门】：全量逐格 100% 通过才算清洗成功
     - 增量终检（可选提效）：仅当 输出区存在同动线上一次已 verified 的运行
       且 本次指纹/结构一致 且 数据仅为日期顺延追加 时，
       允许"新增日期行全量逐格 + 历史行抽样"；否则全量逐格

□ 8. 写 pipeline_info.yaml（含 steps 全清单、data_date_range、validation、outputs、
     parametric 另记 profile_used）；只有 contract 状态为 verified / partial_verified 才允许 usage.json +1

□ 9. 旧 run 生命周期处理（只在 verified / partial_verified 后执行）
     - 默认完整重跑当前 Excel 生成新 CSV，不对旧 CSV 做增量 append
     - 若 pipeline.yaml 未声明 run_lifecycle，则按 cleanup_policy=ask：生成 cleanup_plan.json，列出同 pipeline 旧 run 候选，请用户确认
     - 若 cleanup_policy=auto_delete_csv，则调用 cleanup_manager apply，只删除旧 run 的 CSV 产物，并保留 info / validation / tombstone
     - pinned 或被 analysis 引用的旧 run 默认保护，不删除

□ 10. 证据交付（按 validation contract，不得越界承诺）：
     - 验证状态：{verified / partial_verified / validation_failed}
     - 验证范围：{coverage_scope}
     - 未验证范围：{unverified_scope；无则写无}
     - oracle 来源：{oracle_provenance_summary}
     - 假设项：{assumptions；无则写无}
     - 关键数复算：{从 validation report 摘 3 个高风险/关键值}
     - 校验报告：{路径}
     - cleanup 状态：{无旧 run / 已生成 cleanup_plan / 已按 policy 清理 / 因 pinned 或 analysis 引用而保护}
     只有 coverage_scope=full_cell 时，才允许说“全量逐格”；否则必须按实际范围描述。
```

## 3. 分析线 checklist

```
□ 0. 数据依赖检查
     若用户没有提供 raw data / clean data，且本分析依赖的数据尚未在本 Session 输出区可达，
     先转 `docs/DATA_ACQUISITION_SOP.md` 匹配或共创 data_acquisition source。

□ 1. 场景定位（读 analysis/manifest.json，只看 status=enabled）
     ├─ 精确命中 keywords → 直接执行
     ├─ 模糊但可意会 → 执行 + 告知"我用了 {场景名}"
     ├─ 完全不明确 → 列出可用场景 + 一句话说明，请用户选
     └─ 不匹配 → 转共创

□ 2. 读 scene.yaml + CALIBERS.md

□ 3. 定位数据（按 inputs 分两类）
     a. pipelines 依赖：扫描本 Session 输出区各来源动线最新 pipeline_info.yaml
        （按 data_date 最新；并列取 run_time 最新；params 可用 --as-of 钉住日期）
        → 某依赖动线无任何产物 → 若有可用 data_acquisition source，先取 raw data 并完成清洗；
          否则告知"本分析依赖 {X} 动线的清洗数据，请先上传对应报表或共创数据获取 source"
          → 取数/清洗完成后自动接回本分析请求
     b. user_files 依赖：请用户提供文件 → 按 expected_columns 做列完整性核验后使用

□ 4. preflight：先按 docs/ENVIRONMENT_READINESS.md 确认 workbench_profile + table_processing_need；requires 依赖逐项核验（缺→报缺失项，停）；CSV 存在/列完整（缺列→停）；
     params 合法；输出可写；数据覆盖 report_date（不足→警告继续）；
     输出为 Excel/HTML 时记录 risk_notes.visual_acceptance_need；若无法截图/渲染，改用结构检查+关键数锚点+错误字符串扫描，并记录降级原因；
     若由外部/未来 HTML 分析 Skill 生成报告，本 Skill 仍需向其提供 clean CSV、CALIBERS、数据范围、关键数锚点和 validation summary，
     并在本次 run 记录 handoff 输入与返回产物；
     结构漂移检测：当前数据结构 vs CALIBERS 第四区块基线
     → 无漂移→继续；有漂移→点名可能失效口径→转局部重共创（见第 4 节）

□ 5. 建输出目录（output_manager，先占位命名）

□ 6. 执行：按 execution.steps 跑生成脚本（或用 entrypoint 一键执行生成+校验，
     按其分级退出码判断：0=全过 / 1=输入或依赖失败 / 2=生成失败 / 3=校验未通过）

□ 7. 校验：跑 validate 脚本（独立重算；禁止 import 主生成脚本；必须输出 validation contract；exit 0/1）。exit≠0 → 读 .validate.log 摘要差异，
     自行修复重跑，不把实现问题抛给用户

□ 8. 日志落盘：确认 {output}.log、{output}.validate.log、validation_contract.json 在输出目录

□ 9. 回填 data_date、写 analysis_info.yaml（source_pipelines/run/params/validation）；只有 contract 状态为 verified / partial_verified 才允许 usage.json +1

□ 10. 证据交付（按 validation contract，不得越界承诺）：
      - 验证状态：{verified / partial_verified / validation_failed}
      - 验证范围：{coverage_scope}
      - 未验证范围：{unverified_scope；无则写无}
      - oracle 来源：{oracle_provenance_summary}
      - 假设项：{assumptions；无则写无}
      - 关键数复算：{从 validation report 摘 3 个高风险/关键值}
      - 产物与校验报告：{路径}
      若状态为 partial_verified，只能交付“带边界/假设的分析”，不能说“最终可信结论”。
```

## 4. 复用策略（不是独立流程；漂移检测已内嵌在上面 checklist 中）

| 情况 | 走法 |
|---|---|
| 每日增量（结构不变） | 默认完整重跑当前 Excel 生成新 run；fixed 全中免确认；parametric profile 命中免确认；清洗终检可用旧 verified run 做历史对照，但不直接 append 旧 CSV |
| 换报告日期 / 新数据 | 正常跑；preflight 顺带复核 CALIBERS 第一区口径仍成立 |
| 数据结构变了（新增/改名 section、渠道） | preflight 漂移检测拦截 → 向用户点名"以下口径可能失效：{清单}" → 局部重共创（只修受影响的映射/口径/脚本段，走 COCREATION_SOP Phase 2~5 的窄化版） → 完成后按 REGISTRATION_SOP 第 8 步问"升级还是全新" |

## 5. 跨动线分析（inputs.pipelines 长度 > 1）

1. 逐个来源按第 3 节步骤 3a 定位最新产物。
2. **可比窗口与输出命名日期 = 各来源数据截止日期的最小值（min）**——联合分析受限于最短的源。
3. 口径对齐：优先读该场景 CALIBERS 第四区"已确认的跨表口径映射"→ 有则直接用，不重判；
   无则 Agent 读双方 references 提出映射建议（含相关性/覆盖率证据）→ 用户确认 → **写入 CALIBERS 第四区固化**。
4. 其余步骤与单动线一致（执行→独立校验→证据交付）。
