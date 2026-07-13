# “宏观地图”v1：G5 利率曲线与公开信用指标

## 目标

在现有终端增加“宏观地图”页签，导航顺序固定为：

`宏观地图 → Market Map → Opportunities`

“宏观地图”为默认落地页，提供 G5 利率曲线、公开信用指标和金融压力指标的最新值、变化、新鲜度、历史下钻、来源及口径说明。宏观来源失败不得影响 Market Map。

## 数据接入与计算

### G5 利率曲线

| 市场 | 官方来源 | 固定期限 |
| --- | --- | --- |
| 美国 | US Treasury daily par curve | 2Y / 5Y / 10Y / 30Y |
| 欧元区 | ECB AAA zero-coupon spot curve | 2Y / 5Y / 10Y / 30Y |
| 中国 | 财政部 / 中债国债收益率曲线 | 2Y / 5Y / 10Y / 30Y |
| 日本 | 日本财务省 JGB constant-maturity CSV | 2Y / 5Y / 10Y / 30Y |
| 英国 | BoE nominal government spot curve | 2Y / 5Y / 10Y / 30Y |

新建独立 `macro_pipeline` 与 `macro.py`，支持：

- `macro.py backfill --years 5`
- `macro.py poll once`
- 不耦合现有 ZSXQ pipeline。

保存不可变 raw 响应、标准化曲线 / 信用序列、processed indicators 和 source manifest。同日修订按业务键覆盖，文件采用原子替换，并在来源级别隔离失败、保留 last-good 数据。

固定计算：

- `Level = 10Y`
- `Slope = (10Y - 2Y) × 100bp`
- `Curvature = (2 × 5Y - 2Y - 10Y) × 100bp`
- 仅使用同一观察日的完整期限点；计算前 1 / 5 / 20 个可用观测变化。
- 不跨日补齐；处理负利率、缺期限、异步日期、重复抓取、修订和坏值。

### 信用与压力指标

通过 FRED API 获取：

- `BAMLH0A0HYM2`：HY OAS
- `BAMLC0A0CM`：IG OAS
- `NFCI`
- `DRTSCILM`：SLOOS

通过 OFR 官方日度数据获取 OFR FSI。

- `HY-IG = (HY OAS - IG OAS) × 100bp`
- SLOOS 使用环比一轮、同比四轮调查变化。
- `FRED_API_KEY` 只允许放在本机环境变量；缺失时标记为 `unconfigured`。
- 阈值配置化：曲线 / OAS 20-observation 变化默认 10bp，NFCI / OFR 默认 0.25，SLOOS 默认 5pp。
- 只生成机械诊断标签，不生成交易建议。

FedWatch 暂不接入，等待 CME 授权 API；不做网页抓取、CDX / iTraxx、外部通知或综合交易 regime。

## API 契约

新增独立接口：

- `GET /api/macro/ready`：整体 `ready / degraded / not_ready`，以及各来源的 `fresh / lagging / error / unconfigured`。
- `GET /api/macro/overview?as_of=`：曲线点、三因子、变化、信用卡片、真实 `observed_at` 和来源状态。
- `GET /api/macro/history?series_id=&start=&end=`：稳定 series ID 的历史序列；未知 ID 返回 `404`。

保持现有 `/api/ready`、snapshot、playback 契约不变。宏观缓存独立失效，宏观来源失败不影响资产数据。

## 页面与运行

- `activeView = "macroMap"` 为默认状态。
- 页签依次渲染“宏观地图”“Market Map”“Opportunities”。
- 切换页签后保留既有筛选、选择和 playback 状态；宏观区间与选中指标也需保留。
- 宏观页面展示来源健康摘要、G5 曲线卡片与曲线图、Level / Slope / Curvature 历史、信用与压力卡片。
- 支持 1M / 3M / 1Y / 3Y / 5Y 区间。
- 每张卡展示单位、as-of、来源、曲线类型和滞后状态。
- 仅在宏观页签激活时加载宏观接口，每 5 分钟刷新；宏观页不显示资产 playback。
- 新增独立 launchd job，每天北京时间 09:00、20:30 运行 `macro.py poll once`。

## 测试与验收

为五个曲线来源和信用来源提供最小合成 fixture，覆盖公式、单位转换、负利率、缺期限、异步日期、重复抓取、修订和坏值。

验证以下场景：

- 部分来源失败、FRED key 缺失、数据滞后、last-good 保留。
- macro 缓存独立失效；原有 API 完全兼容。
- 页签顺序、默认进入“宏观地图”、切换后状态保留。
- 曲线 / 信用历史下钻和局部错误状态。
- `make check`、`make smoke`、`make e2e`。
- 真实 backfill / poll；使用 `curl --noproxy '*'` 验证 macro API 和 launchd 日志。

## 文档与安全

同步更新产品、架构、数据契约、可靠性、测试和安全文档；保留 FRED 非背书声明、ICE OAS 内部使用限制及所有来源署名。不同拟合或计息口径的国家曲线只比较各自市场的变化，不做绝对水平排名。

