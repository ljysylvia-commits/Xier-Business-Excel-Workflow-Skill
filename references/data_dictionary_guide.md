# 数据字典读写指南（data_dictionary_guide）

## 定位
每条清洗动线的 `references/data_dictionary.md` 是分析共创 Phase 2 的**首选读源**。原则：**按需、轻量、不求穷尽**——一开始能用就好，随共创/使用增量补充；不给用户增加额外维护负担。

## 内容（三段式，够用即可）
1. **表 schema**：每个产出 CSV 的列名 + 一句话含义；
2. **已知口径**：已确认的指标口径/单位/特殊含义（含来源：来自口径说明 Sheet / 用户确认 / Agent 推断-待复核）；
3. **JOIN 路径**：表间可用什么键关联（如：均以 date 为主键，可加 platform）。

## 读规则（Agent）
- 分析共创先读字典；字典缺失或不覆盖所需字段 → **直接读 CSV 表头 + 抽样若干行推断**，不阻塞。
- `[Agent推断]` 只能用于生成待复核方案和假设分析，不能作为 expected values 或 correctness oracle。
- 关键指标若依赖 `[Agent推断]`，validation contract 必须进入 `partial_verified`，不得进入 `verified`。

## 写规则（Agent）
- 推断出的结论**回填字典**并标注 `[Agent推断 YYYY-MM-DD]`；用户确认后去掉标注。
- 清洗脚本自动生成的 `cleaned_metric_dictionary.md` 是字典的自动部分；人工/共创补充写在同目录 `data_dictionary.md`，两者并存互补（自动件不手改）。
- 字典只写"数据含义"，不写清洗/分析逻辑（逻辑在脚本，口径决策在 CALIBERS）。
