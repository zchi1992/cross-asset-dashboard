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
原始 series 中的 `close_position_vs_60d` 会原值透传到 processed series；旧 processed 数据
缺少该指标时仍可加载，对应 API 字段返回 `null`。
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

## Asset taxonomy

版本化分类主数据位于 `metadata/asset_taxonomy.csv`，通过配置项
`dashboard.market_map.taxonomy_path` 指定；同目录 `taxonomy_registry.json` 定义可用代码、
中英文标签、父子关系和分类标准版本。主表键为规范化后的
`dataset_type + symbol + asset_name`，因此同一 ticker 对应不同资产时不会互相覆盖。

主表列固定为：

```text
dataset_type,symbol,asset_name,primary_category,secondary_category,tertiary_categories,regions,classification_basis,source_url
```

`tertiary_categories` 和 `regions` 使用 `|` 分隔；三级分类最多三个。分类表缺失或某个新资产
没有精确匹配时，行情仍正常加载，并返回 `primary_category=unclassified`、空二级/三级/地区。
`scripts/audit_asset_taxonomy.py` 用于校验主表结构，并可与指定配置的有效行情资产做覆盖率比较。

## HTTP API

- `GET /api/health`：进程 liveness，不检查数据。
- `GET /api/ready`：返回 `status`、`reason`、`date_count`、`asset_count`、
  `latest_date`；无有效数据时状态码为 `503`，原因为 `no_processed_data`。
- `GET /api/config`：分数范围、默认过滤器、播放速度和状态枚举。
- `GET /api/config` 的 `taxonomy` 额外返回一级、二级、三级和地区选项；每个选项包含
  `code`、`label_en`、`label_zh`、`parent_codes`。
- `GET /api/dates`：升序可用日期。
- `GET /api/assets`：按完整资产身份返回 symbol、名称、数据集类别和分类字段，不再仅按 symbol 去重。
- `GET /api/snapshot?date=YYYY-MM-DD`：单日宽表；未知日期返回 `404`。
- `GET /api/playback?start=&end=`：日期和按日期分组的完整帧。

单日宽表和 playback item 保留原有字段，并额外返回：

- `is_gs_exempt`：布尔值，表示该行情记录的 symbol 是否在公司批准名单中；前端据此筛选已有数据，不把名单中无行情的 symbol 补进响应。
- `primary_category`：一级分类稳定代码。
- `secondary_category`：可空的单个二级分类代码。
- `tertiary_categories`：最多三个三级分类代码。
- `regions`：底层敞口地区代码列表；允许值为 `US`、`US_CA`（仅加拿大）、`LATAM`、`EUROPE`、`JP`、`KR`、
  `CN`、`APAC`、`EM`，货币对可包含两个地区。全球或无法归入单一区域的资产返回空列表。
  注册表按 `US`、`CN` 优先，其余区域随后排列。

- `close_position_vs_60d`：原始“收盘价对比60日位置”，用于资产详情面板展示；历史 processed 数据缺失时为 `null`。

- `leverage_duration`：来自 `funding_current_leverage_state_duration`，用于机会排序和表格展示。
- `funding_signal_strength`：来自同名 processed metric，用于机会排序；不替代现有
  `funding_score` 字段。

字段由 `backend/app/schemas.py` 定义，前端镜像位于
`frontend/src/services/contracts.ts`。改变字段时必须同步两端并增加契约测试。

## Macro processed data and API

宏观地图输入与资产 processed series 隔离：

- `data/processed/macro/curve_points.csv`：`date,region,region_name,tenor_years,value,unit,curve_type,source_id,source_name,source_url`。
- `data/processed/macro/credit.csv`：`date,series_id,label,value,unit,frequency,source_id,source_name,source_url`。
- `state/macro_sources.json`：每个来源的抓取状态、最后成功时间、最新观察日期和错误信息。

曲线 factor 只在同一 `region + date` 同时存在 2Y/5Y/10Y 时生成；不跨日补期限。
Level 为 10Y，Slope 为 `(10Y-2Y)×100bp`，Curvature 为 `(2×5Y-2Y-10Y)×100bp`。
HY-IG 只对齐相同日期的 HY/IG OAS。

- `GET /api/macro/ready`：宏观独立 readiness 和 source status。
- `GET /api/macro/overview?as_of=`：G5 曲线、factor、变化、信用卡片及来源。
- `GET /api/macro/history?series_id=&start=&end=`：稳定 series ID 的历史点。

现有资产 API 不增加宏观字段，宏观数据缺失或失败不改变 `/api/ready`。

## Cache invalidation

后端缓存键包含：

- 配置文件路径、修改时间和大小。
- 所有 processed CSV 的路径、修改时间和大小。
- GS exempt 名单文件的路径、修改时间和大小；名单变化会重建 rows 和 playback frames。
- 资产分类主表和分类注册表的路径、修改时间和大小；任一文件变化都会重建 rows 和 playback frames。

相同签名复用解析结果；配置或数据签名变化后重新构建 rows 和 playback frames。

## IBKR portfolio snapshots

持仓快照位于 `data/portfolio/portfolio_YYYYMMDD.csv`。每个持仓一行并重复账户摘要字段；
空仓账户仍写一行，持仓字段为空。快照必须先完整写入临时文件，再以原子替换方式更新同日文件。

元数据字段为 `snapshot_date`、`captured_at`、`sync_source`、`account_id_masked` 和
`base_currency`。账户字段包括 `net_liquidation`、`maint_margin_req`、`sma`、
`excess_liquidity`、`available_funds`、`buying_power`、`gross_position_value` 和
`cushion`。持仓字段保留 IBKR conId、合约描述、数量、市价、市值、成本和盈亏，以及
`option_delta`、`option_gamma`、`option_theta`、`option_vega` 四项 IBKR 模型 Greek。
旧快照缺少 Greeks 字段时仍可读取，对应值为不可计算。
`sync_source` 只允许 `manual`、`scheduled_2000` 或 `scheduled_2330`。

- `GET /api/portfolio`：读取最新有效快照并合并本地 Stop Loss，状态为 `ready`、`stale`、
  `no_snapshot` 或 `error`。
- `POST /api/portfolio/sync`：连接 TWS、获取一次账户和完整持仓、原子覆盖当日快照。
- `PUT /api/portfolio/positions/{conid}/stop-loss`：以正数设置止损，或以 `null` 清除。

Stop Loss 位于忽略版本控制的 `state/ibkr_stop_losses.json`；期权、期货期权和组合合约
不参与止损风险计算。接口只返回掩码账户号，不返回 `IBKR_ACCOUNT_ID`。
