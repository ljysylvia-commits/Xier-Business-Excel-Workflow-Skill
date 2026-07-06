# IMPROVEMENTS —— Skill 自迭代建议登记

> 用途：注册（REGISTRATION_SOP 第 10 步）时，Agent 自查"本次共创是否遇到现有架构/Schema/SOP 不支持之处？
> 有什么好经验值得升为 Skill 规则？"，把建议登记在此，**经用户拍板后**再修订 Skill 本体并升版本。
> 这让 Skill 越用越稳——但改动本体必须用户同意，不得擅自变更。

## 登记格式

| 日期 | 来源类型 | 来源套件/场景 | 问题/机会 | 建议改动（影响面） | 用户裁决 | 状态 |
|---|---|---|---|---|---|---|
| | registration_retrospective / audit / user_request / eval | | | | 待议/采纳/否决 | 待改/已改/关闭 |

只登记通用规则缺口、工具化机会、验证模式更新或环境依赖更新。案例专属经验写入套件 `LEARNINGS.md`，不进入本文件。

## 记录

| 2026-07-03 | audit | doc_coherence_tests/agent_e | 共创阶段发现 plan 闸门失效时，IMPROVEMENTS 触发点偏注册尾声 | 已在 `SKILL.md`、`COCREATION_SOP.md`、`plan_template.md` 加强 plan 前置闸门；影响共创入口 | 采纳 | 已改 |
| 2026-07-03 | audit | doc_coherence_tests/agent_f | partial_verified 的人读材料可能被误读为“校验通过可放心交付” | 已在输出状态、验收文档和验证契约中强化 run_status / contract_status 区分；影响证据交付 | 采纳 | 已改 |
| 2026-07-03 | audit | doc_coherence_tests/agent_c | 复用执行缺标准 runner / drift checker，Agent 需自行串联 manifest/yaml/preflight/output_manager | 已新增 `tools/pipeline_runner.py` 与 `tools/drift_check.py`，并在执行/注册 SOP 与模板中接入；影响已注册清洗动线复用 | 采纳 | 已改 |
