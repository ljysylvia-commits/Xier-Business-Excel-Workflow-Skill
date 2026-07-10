# OUTPUT_ACCEPTANCE —— 交付验收标准

> 适用于清洗 CSV、Excel Dashboard、HTML 分析报告。交付前逐项检查；未通过则修复重跑，不把半成品交给用户。

## 1. 通用验收

- 产物目录符合 `output/data_cleansing/{id}_{YYYYMMDD}_{seq}/` 或 `output/data_analysis/{id}_{YYYYMMDD}_{seq}/`。
- 目录内包含产物文件、`info.json`、对应人读 `data_cleansing_info.yaml` / `data_analysis_info.yaml` 视图、执行日志、校验日志。
- `info.json` 是机读事实源，记录输入文件、参数、数据日期范围、steps、可用工具链/降级原因、产物清单和 validation contract 摘要；`data_cleansing_info.yaml` / `data_analysis_info.yaml` 只作为同内容的人读视图。
- plan 第 8 章记录本次执行、失败、修复和最终通过状态。
- 向用户交付时必须包含证据摘要：验证状态、验证范围、未验证范围、oracle 来源、假设项、关键数复算和校验报告路径。
- 若同 data_cleansing 套件存在旧 run，交付时必须说明 cleanup 状态：无旧 run、已生成 cleanup_plan 待确认、已清理旧 CSV、或因 pinned / data_analysis 引用而保护。

## 2. 清洗 CSV

- schema 与 plan / cleansing.yaml 一致。
- 日期、数值、比例、货币、空值类型已统一。
- 每个输出值可追溯到源 Sheet / 行 / 列 / 单元格或源范围。
- 全量逐格校验通过时，`coverage_scope=full_cell`。若因源表结构无法逐格，只能进入 `partial_verified`，必须列出未验证范围；用户确认不能替代验证。
- 数据字典至少覆盖本次分析所需字段，不要求穷尽。
- 每日新增数据默认完整重跑生成新 run；旧 run 的 CSV 只能通过 cleanup_manager 清理，不在旧 CSV 上直接 append。

## 2.1 旧 run cleanup 验收

- cleanup 只能在新 run 状态为 `verified` / `partial_verified` 后发生。
- `cleanup_policy=ask` 时只允许生成 `cleanup_plan.json`，不得删除文件。
- `cleanup_policy=auto_delete_csv` 时只能删除 cleanup plan 中列出的旧 CSV 文件。
- 被 data_analysis run 引用或标记 `pinned: true` 的旧 run 默认不得删除。
- cleanup 后旧 run 目录必须保留 `info.json`、`data_cleansing_info.yaml`、validation contract / report，并写入 `cleanup_tombstone.json`。
- tombstone 必须列出 superseded_by、deleted_files、kept_files、cleanup_time 和 reason。

## 3. Excel Dashboard

- 面向指定受众回答指定问题，不只是源数据透视表。
- 核心 KPI、同比/环比/占比/差值的口径在 CALIBERS 中可查。
- 关键数据格通过独立重算校验。
- 打开文件无明显公式错误、空白错位、样式破坏、图表空白或文本溢出。
- 使用公式、条件格式或图表时，需记录生成工具与重算/检查结果。
- 若无法做截图或真实渲染检查，必须执行替代验收：Sheet 列表、关键单元格锚点、图表对象数量、行列尺寸、错误字符串扫描，并记录降级原因。

## 4. HTML 分析报告

- 报告包含标题、数据范围、核心发现、关键指标、对比分析、结论建议和口径说明。
- 关键数字全部可追溯；至少抽取核心 KPI、最大变化项、一个同比/占比项进行独立复算。
- 图表或表格能在浏览器中正常渲染，无遮挡、空图、错位或明显文本溢出。
- 若无法使用浏览器渲染，至少检查 HTML 章节、关键数文本锚点、表格/图表容器、错误占位符和本地可打开性。
- 结论中区分事实、推断和建议，不把模型判断伪装成数据事实。

## 5. template / example 候选

- 案例数据为合成或已脱敏。
- 输入要求清晰，换一组同结构数据可以复用。
- 输出形态清楚，校验脚本可复跑。
- 不含用户私有业务名、内部路径、真实客户数据或平台敏感字段。
- 平台风格示例必须声明：合成数据、非真实平台导出、字段不等于平台私有字段。
- 只有用户确认后，才从 evals / examples_draft 晋升到正式 templates / examples。

## 6. 关键数锚点

Dashboard / HTML 类产物必须在 plan 或任务包中列出关键数锚点：

- 指标名与口径。
- 期望来源：源数据、clean CSV、expected_values 或用户确认；每个 expected value 必须有 provenance。
- Dashboard 中的单元格、Sheet、图表标签或文本锚点。
- HTML 中的章节、表格行、文本锚点或 DOM 标识。
- 容差规则。

没有关键数锚点的 Dashboard/HTML，只能视为展示草稿，不能视为可验收交付。

## 7. 状态门槛

- `generated`：只能说明产物已生成，不能说校验通过。
- `validation_failed`：不得交付为结果，只能交付失败报告和修复建议。
- `partial_verified`：只能交付“带边界/假设的分析”，必须列出未验证范围或弱 oracle。
- `verified`：可以交付为最终结果，但仍必须说明验证范围。

## 8. partial_verified 标准表达

当状态为 `partial_verified` 时，交付必须使用边界表达：

```text
验证状态：partial_verified
可交付性质：带边界/假设的分析，不是最终可信结论
验证范围：{coverage_scope}
未验证范围：{unverified_scope}
弱 oracle / agent 推断：{oracle_provenance_summary}
假设项：{assumptions}
下一步：补齐未验证范围或请用户确认假设后重跑 validation
```

禁止使用下列表达：

- “已验证可交付”
- “校验通过无问题”
- “最终可信结论”
- “数据完全正确”
- “可以放心使用”

若 validator 自身 `status=pass`，但 output_manager 最终状态为 `partial_verified`，必须以 output_manager 的最终状态为准。
