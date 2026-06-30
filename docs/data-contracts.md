# Data and API Contracts

## Processed series

Dashboard 输入位于：

- `data/processed/series/core/*.csv`
- `data/processed/series/instruments/*.csv`

CSV 使用 long format：

```text
date,dataset_type,asset_code,asset_name,metric_name,metric_value
```

每个资产日期必须包含趋势分与状态、月周日趋势、相对强度分与状态、资金分与方向。
字段缺失或数值无法解析时，该资产日期不会进入 dashboard。

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

现有字段由 `backend/app/schemas.py` 定义，前端镜像位于
`frontend/src/services/contracts.ts`。改变字段时必须同步两端并增加契约测试。

## Cache invalidation

后端缓存键包含：

- 配置文件路径、修改时间和大小。
- 所有 processed CSV 的路径、修改时间和大小。

相同签名复用解析结果；配置或数据签名变化后重新构建 rows 和 playback frames。
