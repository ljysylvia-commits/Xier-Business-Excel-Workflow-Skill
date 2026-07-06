# REGISTRATION_SOP —— 注册改造 checklist（阶段二：注册即改造）

> 用途：把 workspace 里**已跑通**的共创产物，一次性规范化改造并迁入 Skill 目录。
> 同时可作为**存量迁移** checklist（迁移=一次注册）。
> 前置条件：□ 端到端跑通 □ 校验闭环通过 □ plan.md 存在且第 7 章确认清单全打勾

## 十步 checklist

```
□ 1. 整理 plan：把 workspace 的 plan.md 按 docs/plan_template.md 的 9 章骨架整理齐
     （缺章补齐；第 8 章执行日志保留原始记录不删）

□ 2. 生成 yaml（最小执行契约）：
     - 字段：pipeline_id/scene_id、version、generated_from、requires、
       understand(fixed→fingerprint+filename_hint / parametric→pattern_hint+profiles_dir+profile_detect)、
       transform.steps(含 produces 中间产物) 或 execution.steps、validation.layers(rigor 标注，
       终检必须 exhaustive)、trigger(场景)、inputs(pipelines+user_files)、params、output、
       calibers 指针、validation_contract、run_lifecycle(清洗动线可选)、entrypoint(可选)
     - 【铁则】指纹/hint 一律从脚本实际读取的 Sheet 名/结构生成，不从旧文档抄
     - 【铁则】yaml 不写映射细节/计算逻辑/口径说明（映射与逻辑在脚本，口径在 CALIBERS/plan）

□ 3. 抽 CALIBERS.md：从 plan 第 7 章生成（参考 `pipelines/_template/CALIBERS.md.example`
     或 `analysis/scenes/_template/CALIBERS.md.example` 的四区块），
     补第四区"结构依赖基线"（列出依赖的 Sheet/section/sub_channel/metric）；
     清洗类须注明每条修正规则的**实现位置**（脚本内哪个常量/标志）

□ 4. 脚本归位与参数化：
     - 移入套件 scripts/；全部 argparse 传参；删除对脚本目录/工作目录的路径依赖
     - 引用共享工具一律指向 skill 内 tools/（禁止 skill 外绝对路径）
     - entrypoint 类脚本（如一键再生）输出命名对齐 {id}_{data_date}_{seq} 规范

□ 5. 跑 tools/consistency_check.py：
     检查项 = yaml↔脚本↔CALIBERS 引用存在且一致 + 套件必备文件齐全 +
              脚本 py_compile 可编译 + requires 依赖可 import + 外部绝对路径扫描 +
              validation_contract 声明 + 校验脚本不得 import 主生成脚本
     发现不一致 → 工具只报差异清单；你结合上下文给对齐建议；**决策由用户做**；确认后修正并回写 plan

□ 6. 在 Skill 目录内复跑一次端到端（含 validation contract）→ 必须通过；
     最小状态机命令序列：
     - 已注册清洗动线优先用 `tools/pipeline_runner.py run --skill-root {skill} --input {file} --output-root {output_root}`；
     - 若不适用 runner，则运行生成脚本，产出 CSV / Dashboard / HTML 等文件；
     - 运行独立 validator，产出 validation_contract.json；
     - 运行 `tools/output_manager.py validate --dir {run_dir} --contract validation_contract.json`；
     - 若 contract 有 assumptions / unverified_scope / agent_inferred，即使 validator status=pass，也只能是 partial_verified；
     - validation_failed 不得进入 manifest enabled。
     - 若设置 `run_lifecycle.cleanup_policy`，必须额外验证 cleanup_manager：
       policy=ask 只生成 cleanup_plan，不删除；policy=auto_delete_csv 只删除旧 run CSV 并写 tombstone。
     同时做负向测试：故意改坏一个 expected value 或关键输入，校验必须失败并进入 validation_failed

□ 7. 汇编 manifest：由 consistency_check 从套件 yaml 生成/更新 manifest 条目
     （新套件默认 status=draft；用户确认可用后改 enabled）

□ 8. 版本演进：若与已注册套件同名/同类 → 问用户
     "这是原{动线/场景}的升级（覆盖，版本号+1，旧版记入历史）还是全新（并存）？"

□ 9. template / example 晋升判断：
     - 若本套件对开源用户有可复用价值，先写入候选清单，不直接进入正式模板
     - 候选信息包括：适用场景、输入数据要求、输出形态、可复用程度、业务特定假设、脱敏状态
     - 只有用户确认后，才迁入 templates/ 或 examples/；否则留在 evals/ 或 examples_draft/

□ 10. 注册复盘 gate（Skill 自迭代只在此发生）：
      前置：端到端跑通 + 正向 validation 通过或明确 partial 边界 + 负向测试能失败 + 套件文件已迁入。
      由共创/注册 Agent 总结本次 pipeline / scene 的注册复盘，至少包含：
      - case_specific_learnings：只属于本套件的坑、口径、数据结构经验 → 写入套件 `LEARNINGS.md`
      - generalizable_skill_gaps：通用 SOP / schema / validation / output acceptance 缺口 → 写入 `docs/IMPROVEMENTS.md`
      - validation_pattern_updates：是否出现可复用的校验模式 → 候选写入 `docs/IMPROVEMENTS.md`
      - environment_dependency_updates：是否发现环境能力 / 插件 / 工作台依赖缺口 → 候选写入 `docs/IMPROVEMENTS.md`
      - template_or_example_candidates：是否值得成为 template/example → 写入候选清单，用户确认后才晋升
      - tooling_opportunities：是否需要扩展 runner / drift checker / readiness 工具 → 写入 `docs/IMPROVEMENTS.md`
      - user_decisions_needed：哪些必须用户裁决，Agent 不得自行改本体
      分流规则：
      - 案例经验留在套件 `LEARNINGS.md`
      - 通用规则缺口才进 `docs/IMPROVEMENTS.md`
      - template/example 候选不得直接进入正式模板
      - 用户拍板前不得修改 Skill 本体规则
```

## 注册完成的定义

manifest 有条目（status 由用户定）、套件内 yaml + plan + CALIBERS + scripts + LEARNINGS 齐全、
validation_contract 已声明、cleanup policy（如有）已验证、consistency_check 通过、正向端到端复跑通过、负向测试能失败。此后执行走 EXECUTION_SOP，不再读本文件。
