# VALIDATION_PATTERNS —— 独立校验模式

> 本文提供通用校验模式，不包含任何业务口径。具体指标、字段和阈值由场景自己的 plan / CALIBERS / expected values 决定。校验脚本必须同时输出 `docs/VALIDATION_CONTRACT.md` 定义的 contract。

## 1. 硬规则

- 校验脚本不得 import 主生成脚本的计算函数。
- 校验输入应为源文件、clean CSV、expected values、产物文件和参数。
- 校验输出至少包含机器可读结果（json/csv）和人读报告（md/log）。
- 校验输出必须包含 `validation_contract.json`。
- 校验失败时 exit code 非 0；通过时 exit code 为 0。
- 校验完成后回写本次运行 info 的 validation 状态、总检查数、失败数和报告路径。

## 2. 清洗校验

最小检查：

- 行数、月份/周期、维度取值、字段类型。
- 排除行是否正确：标题、说明、空白、汇总、备注。
- 数值转换是否正确：千分位、货币、百分比、pp、空值。
- 输出值是否可追溯到 source_sheet / source_row / source_col / source_range。
- 关键汇总数从源数据和 clean CSV 分别复算并一致。

## 3. Dashboard 校验

最小检查：

- workbook 可打开。
- 必要 Sheet 存在。
- clean data 行数与 CSV 一致。
- 关键数锚点的单元格值与独立复算结果一致。
- 公式错误字符串扫描：`#REF!`、`#DIV/0!`、`#VALUE!`、`#NAME?`、`#N/A`。
- 有图表时检查图表对象数量；无法做视觉截图时记录降级原因。

## 4. HTML 报告校验

最小检查：

- 文件可打开且不是空文件。
- 必要章节存在。
- 关键数锚点文本存在，且与独立复算结果一致。
- 报告声明数据范围和关键口径。
- 图表/表格容器存在；无法浏览器渲染时记录降级原因。
- 不出现“真实平台导出”“真实客户数据”等与合成/脱敏声明冲突的表述。

## 5. expected values 文件建议

推荐字段：

```csv
metric_id,metric_name,scope,period,expected_value,unit,calculation,acceptance_tolerance,provenance,anchor
```

- `metric_id`：稳定机器名。
- `metric_name`：人读名称。
- `scope` / `period`：过滤条件。
- `expected_value` / `unit`：期望值与单位。
- `calculation`：验收公式或来源。
- `acceptance_tolerance`：容差。
- `provenance`：`source_recomputed` / `external_authoritative` / `user_provided_target` / `agent_inferred`。
- `anchor`：Dashboard 单元格、HTML 文本、图表标签或其它验收锚点。
