# VALIDATION_CONTRACT —— 验证状态契约

> 目标：让“是否可交付”由机器可读证据决定，而不是由 Agent 话术决定。任何数据类交付都必须先生成 validation contract，再根据 contract 状态交付。

## 1. 运行状态

运行状态只能取以下值：

| 状态 | 含义 | 是否可作最终结论 |
|---|---|---|
| `generated` | 产物已生成，尚未完成验证 | 否 |
| `validation_failed` | 验证失败或 contract 不满足通过条件 | 否 |
| `partial_verified` | 关键范围通过，但存在未验证范围、弱 oracle 或未确认假设 | 只能作为带边界/假设的交付 |
| `verified` | contract 证明验证覆盖范围满足交付标准 | 是 |

`output_manager finalize` 只能写 `generated`。只有 `output_manager validate --contract ...` 可以把状态改为 `verified`、`partial_verified` 或 `validation_failed`。

注意：contract 自身的 `status=pass` 只表示 validator 没有发现失败项，不等于最终 `verified`。最终交付状态必须看 output_manager 写回的 run status；若存在 `assumptions`、`unverified_scope`、`agent_inferred` 或弱 oracle，只能降级为 `partial_verified`。

旧 run cleanup 不改变 validation 状态。cleanup 只能在新 run 已进入 `verified` / `partial_verified` 后执行，并且必须由 `cleanup_manager` 记录 plan / tombstone；被清理旧 run 的历史 validation contract 仍应保留。

## 2. Contract Schema

校验脚本必须输出 JSON 文件，建议命名 `validation_contract.json`：

```json
{
  "status": "pass",
  "validator_exit_code": 0,
  "total_checks": 66,
  "failed_checks": 0,
  "coverage_scope": "full_cell",
  "oracle_provenance_summary": {
    "source_recomputed": 60,
    "external_authoritative": 0,
    "user_provided_target": 6,
    "agent_inferred": 0
  },
  "unverified_scope": [],
  "assumptions": [],
  "reports": {
    "human_report": "validation_report.md",
    "machine_report": "validation_results.json"
  }
}
```

必填字段：

- `status`: `pass` / `fail`。
- `validator_exit_code`: 校验脚本退出码。
- `total_checks`: 校验项总数。
- `failed_checks`: 失败项数量。
- `coverage_scope`: 验证覆盖范围。
- `oracle_provenance_summary`: 验证基准来源统计。
- `unverified_scope`: 未覆盖范围。
- `assumptions`: 仍依赖的未确认假设。
- `reports`: 人读/机读报告路径。

## 3. coverage_scope

| 值 | 含义 |
|---|---|
| `full_cell` | 原始单元格到输出值全量逐格验证 |
| `full_metric` | 所有声明指标逐项独立复算 |
| `key_metrics` | 关键数锚点独立复算 |
| `structural_plus_key_metrics` | 结构检查 + 关键数锚点复算 |
| `sample_only` | 只做抽样 |
| `structural_only` | 只检查结构、文件、Sheet/DOM |
| `partial` | 其它局部验证 |

只有 `full_cell`、`full_metric`、`key_metrics`、`structural_plus_key_metrics` 可能进入可交付状态。`sample_only`、`structural_only`、`partial` 只能进入 `partial_verified` 或 `validation_failed`。

## 4. Oracle Provenance

每个 expected value 必须标注来源，汇总到 `oracle_provenance_summary`：

| 来源 | 可否证明正确性 |
|---|---|
| `source_recomputed` | 强 oracle：从源数据独立复算 |
| `external_authoritative` | 强 oracle：外部权威来源 |
| `user_provided_target` | 弱 oracle：可作目标验收，但不证明源数据事实 |
| `agent_inferred` | 不能作 correctness oracle，只能作假设 |

若关键指标包含 `agent_inferred`，不得进入 `verified`。若只有 `user_provided_target`，最多进入 `partial_verified`。

## 5. Evidence Delivery

交付时必须按 contract 表达：

- 验证状态：`verified` / `partial_verified` / `validation_failed`。
- 验证范围：来自 `coverage_scope`。
- 未验证范围：来自 `unverified_scope`。
- 假设项：来自 `assumptions`。
- 关键数复算：来自 validation report。
- 是否可作为最终结论：由状态决定。

禁止在 `coverage_scope` 不是 `full_cell` 时使用“全量逐格”“100% 单元格还原”等表达。

当 output_manager 写回 `partial_verified` 时，必须显式说明“不能作为最终可信结论”，即使 validator contract 的 `status` 是 `pass`。
