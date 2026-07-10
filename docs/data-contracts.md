# Data and API Contracts

## Processed series

Dashboard 输入位于：

- `data/processed/series/core/*.csv`
- `data/processed/series/instruments/*.csv`

公司批准名单默认读取 `data/gs_exempt_list/gs_exempt_list.xlsx` 的 `Ticker` 列；
固定测试样例可使用同目录同名 CSV。代码按去除首尾空白并转大写后的 ticker 精确匹配，
名单缺失时所有行情记录均视为非公司名单标的。

CSV 使用 long format：

```text
date,dataset_type,asset_code,asset_name,metric_name,metric_value
```

每个资产日期必须包含趋势分与状态、月周日趋势、相对强度分与状态、相对强度分项、
资金分与方向。交易机会 tab 还读取 `funding_current_leverage_state_duration` 和
`funding_signal_strength`；这两个字段在 API 中为可空字段，缺失时不影响 Market Map 行加载。
dashboard 使用的 `trend_score` 来自 `capped_final_trend_score`，该字段表示月/周/日趋势
结构的 duration-only 成熟度分。`transition_score`、`raw_transition_score` 和
`transition_label` 仍保留在 processed series 中，用于后续交易机会筛选，不属于当前
dashboard/API 展示字段。
字段缺失或数值无法解析时，该资产日期不会进入 dashboard。

相对强度总分 `rs_score` 由 `early_reversal`、`strength_momentum`、
`relative_strength` 按 `4/17`、`6/17`、`7/17` 加权得到。状态跃迁只输出
`state_transition` 和 `relative_signal_type` 诊断字段，不再输出状态跃迁基础分，也不再参与
`rs_score`。

测试契约数据位于 `tests/fixtures/dashboard/`，不得依赖仓库外或被忽略的本机数据。

## HTTP API

- `GET /api/health`：进程 liveness，不检查数据。
- `GET /api/ready`：返回 `status`、`reason`、`date_count`、`asset_count`、
  `latest_date`；无有效数据时状态码为 `503`，原因为 `no_processed_data`。
- `GET /api/config`：分数范围、默认过滤器、播放速度和状态枚举。
- `GET /api/dates`：升序可用日期。
- `GET /api/assets`：资产 symbol、名称和类别。
- `GET /api/snapshot?date=YYYY-MM-DD`：单日宽表；未知日期返回 `404`。
- `GET /api/playback?start=&end=`：日期和按日期分组的完整帧。

单日宽表和 playback item 保留原有字段，并额外返回：

- `is_gs_exempt`：布尔值，表示该行情记录的 symbol 是否在公司批准名单中；前端据此筛选已有数据，不把名单中无行情的 symbol 补进响应。

- `leverage_duration`：来自 `funding_current_leverage_state_duration`，用于机会排序和表格展示。
- `funding_signal_strength`：来自同名 processed metric，用于机会排序；不替代现有
  `funding_score` 字段。

字段由 `backend/app/schemas.py` 定义，前端镜像位于
`frontend/src/services/contracts.ts`。改变字段时必须同步两端并增加契约测试。

## Cache invalidation

后端缓存键包含：

- 配置文件路径、修改时间和大小。
- 所有 processed CSV 的路径、修改时间和大小。
- GS exempt 名单文件的路径、修改时间和大小；名单变化会重建 rows 和 playback frames。

相同签名复用解析结果；配置或数据签名变化后重新构建 rows 和 playback frames。
