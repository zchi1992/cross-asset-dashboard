# 知识星球数据采集

本项目实现一条本地数据流水线：

- 按文件名筛选知识星球附件
- 下载并按日期归档原始 Excel
- 解析首个工作表
- 将指标映射成英文 `metric_name`
- 分别写入 `data/series/core/` 和 `data/series/instruments/`

## 快速开始

0. 创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
```

1. 初始化会话配置：

```bash
.venv/bin/python3 zsxq.py auth init
```

2. 用本地样例验证解析和时序汇总：

```bash
.venv/bin/python3 zsxq.py reparse examples
```

3. 查看生成结果：

```bash
find data -maxdepth 3 -type f | sort
```

4. 启动 Local Asset Terminal：

```bash
cd frontend && npm install && npm run build && cd ..
scripts/run_market_map_dashboard.sh
```

本机浏览器访问：

```text
http://127.0.0.1:8000
```

如需开发模式，可分别启动后端和 Vite 前端：

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

5. 轮询知识星球：

```bash
.venv/bin/python3 zsxq.py poll once
.venv/bin/python3 zsxq.py worker run
```

## 自动运行

已提供 macOS `launchd` 配置，可在北京时间工作日每天 18:00 运行一次单次轮询：

```bash
scripts/install_launchd.sh
```

安装后会加载 `com.chizhi.zsxq.daily-poll`，实际执行 `scripts/run_daily_poll.sh`。日志写入：

- `logs/daily-poll.out.log`
- `logs/daily-poll.err.log`

如需取消自动运行：

```bash
scripts/uninstall_launchd.sh
```

6. 回填历史数据（默认从 2026-05-08 开始）：

```bash
.venv/bin/python3 zsxq.py backfill history
.venv/bin/python3 zsxq.py backfill history --since 2026-05-08 --max-pages 100
```

`backfill history` 会优先使用知识星球网页版的文件搜索接口，按 `filename_filter.include_patterns` 中的关键词检索历史附件，再下载符合条件的 `.xlsx/.xls` 文件。

## 配置

默认配置位于 `config.yaml`。当前环境未安装 YAML 解析库，因此该文件使用 JSON 兼容写法保存；文件扩展名依然是 `.yaml`，后续安装 `PyYAML` 后可无缝切换到普通 YAML 风格。

## 目录结构

- `data/raw/YYYY-MM-DD/`：原始 Excel 归档
- `data/series/core/`：核心数据集资产序列
- `data/series/instruments/`：押注工具资产序列

资产序列文件只保留以下列：

- `date`
- `dataset_type`
- `asset_code`
- `asset_name`
- `metric_name`
- `metric_value`

## 存储格式

- 资产序列默认写为 `csv`，避免运行环境安装额外依赖后改变输出格式
- `SeriesStore` 仍保留显式 `backend="parquet"` 能力，供后续需要时单独接入

## 派生指标计算

信号计算模块放在 `src/zsxq_pipeline/signals/`。输入读取 `data/series/core/` 和
`data/series/instruments/` 中的每资产 long format 序列，输出到：

- `data/processed/series/core/`
- `data/processed/series/instruments/`

processed 文件仍采用现有 schema：

- `date`
- `dataset_type`
- `asset_code`
- `asset_name`
- `metric_name`
- `metric_value`

批量构建入口：

```python
from pathlib import Path

from src.zsxq_pipeline.signals import build_processed_series_with_trend_scores

build_processed_series_with_trend_scores(Path("data"))
```

构建时会跳过字段不完整或为空的日期，避免单个脏日期阻断整批输出；纯计算函数会对缺失字段和无法识别的状态值抛出
`ValueError`，便于测试和调试。

### 原始字段映射

Excel 中的中文指标会先映射为英文 `metric_name`。这些字段是派生计算的主要输入：

| 原始中文指标 | 英文字段 | 用途 |
|---|---|---|
| 日级别趋势 | `daily_trend` | 趋势评分输入 |
| 日级别趋势持续时间 | `daily_trend_duration`，计算时归一为 `daily_trend_bars` | 趋势评分输入 |
| 周级别趋势 | `weekly_trend` | 趋势评分输入 |
| 周级别趋势持续时间 | `weekly_trend_duration`，计算时归一为 `weekly_trend_bars` | 趋势评分输入 |
| 月级别趋势 | `monthly_trend` | 趋势评分输入 |
| 月级别趋势持续时间 | `monthly_trend_duration`，计算时归一为 `monthly_trend_bars` | 趋势评分输入 |
| 相对强度 | `relative_strength` | 比价评分输入 |
| 强度动量 | `strength_momentum` | 比价评分输入 |
| 早期转折 | `early_reversal` | 比价评分输入 |
| 当前比价状态 | `current_relative_state` | 比价评分输入；资金评分也会使用同名字段 |
| 当前比价状态持续时间 | `current_relative_state_duration` | 比价评分输入；资金评分也会使用同名字段 |
| 当前比价状态涨幅 | `current_relative_state_return` | 资金评分输入 |
| 此前比价状态 | `previous_relative_state` | 比价评分输入；资金评分也会使用同名字段 |
| 此前比价状态持续时间 | `previous_relative_state_duration` | 比价评分输入；资金评分也会使用同名字段 |
| 此前比价状态涨幅 | `previous_relative_state_return` | 资金评分输入 |
| 当前杠杆资金状态 | `current_leverage_state` | 资金评分输入 |
| 当前杠杆资金状态持续时间 | `current_leverage_state_duration` | 资金评分输入 |
| 当前杠杆资金状态涨幅 | `current_leverage_state_return` | 资金评分输入 |
| 此前杠杆资金状态 | `previous_leverage_state` | 资金评分输入 |
| 此前杠杆资金状态涨幅 | `previous_leverage_state_return` | 资金评分输入 |
| 杠杆资金数值 | `leverage_value` | 资金评分输入，表示杠杆资金水平 |
| 杠杆资金相比前日变动 | `leverage_value_change_d1` | 资金评分输入，表示杠杆资金日变化 |

趋势状态会归一为 `up`、`neutral`、`down`。比价状态会归一为 `Lead`、`Weakening`、`Improving`、`Lag`。

### 趋势派生指标

实现位置：`src/zsxq_pipeline/signals/trend_score.py`

趋势评分使用月、周、日三个频率。权重为：

- 月线：`3`
- 周线：`2`
- 日线：`1`

趋势值映射为：

- `up = 1`
- `neutral = 0`
- `down = -1`

成熟周期阈值为：

- 月线：`6`
- 周线：`12`
- 日线：`20`

输出字段：

| 派生指标 | 含义 |
|---|---|
| `monthly_trend` | 归一后的月线趋势，取值 `up/neutral/down` |
| `weekly_trend` | 归一后的周线趋势，取值 `up/neutral/down` |
| `daily_trend` | 归一后的日线趋势，取值 `up/neutral/down` |
| `trend_combo` | 三频趋势组合，格式为 `monthly/weekly/daily`，例如 `up/neutral/down` |
| `state_name` | 根据 `trend_combo` 映射出的中文趋势状态，例如 `主升浪`、`震荡下探` |
| `monthly_trend_bars` | 当前月线趋势持续时间 |
| `weekly_trend_bars` | 当前周线趋势持续时间 |
| `daily_trend_bars` | 当前日线趋势持续时间 |
| `monthly_duration_multiplier` | 月线持续时间成熟度因子 |
| `weekly_duration_multiplier` | 周线持续时间成熟度因子 |
| `daily_duration_multiplier` | 日线持续时间成熟度因子 |
| `raw_current_score` | 当前三频方向原始分：`月线值*3 + 周线值*2 + 日线值*1` |
| `current_score` | 当前三频方向百分制分：`raw_current_score / 6 * 100` |
| `raw_duration_score` | 带持续时间成熟度的原始分 |
| `duration_score` | 带持续时间成熟度的百分制分：`raw_duration_score / 12 * 100` |
| `raw_transition_score` | 相比上一日期的三频变化原始分 |
| `transition_score` | 相比上一日期的三频变化百分制分：`raw_transition_score / 12 * 100` |
| `decayed_transition_score` | 当前等于 `transition_score`，预留给后续衰减逻辑 |
| `raw_final_trend_score` | 趋势总分：`duration_score + 0.4 * decayed_transition_score` |
| `capped_final_trend_score` | 截断后的趋势总分，限制在 `[-100, 100]` |
| `transition_label` | 对本期趋势变化的中文描述，例如 `日线趋势转弱`；无变化时为空 |

`state_name` 的核心映射示例：

| `trend_combo` | `state_name` |
|---|---|
| `up/up/up` | `主升浪` |
| `up/up/down` | `主升回调` |
| `up/neutral/neutral` | `上行中继震荡` |
| `neutral/neutral/neutral` | `静默` |
| `neutral/neutral/down` | `震荡下探` |
| `down/down/down` | `主跌浪` |

完整映射见 `STATE_NAMES`。

### 相对比价派生指标

实现位置：`src/zsxq_pipeline/signals/relative_strength.py`

比价评分使用四类输入：

- `early_reversal`
- `strength_momentum`
- `relative_strength`
- 当前/此前比价状态及持续时间

综合分权重：

- `early_reversal`: `20%`
- `strength_momentum`: `30%`
- `relative_strength`: `35%`
- `transition_score`: `15%`

输出字段：

| 派生指标 | 含义 |
|---|---|
| `rs_score` | 综合比价强度分 |
| `early_reversal` | 原始早期转折分 |
| `strength_momentum` | 原始强度动量分 |
| `relative_strength` | 原始相对强度分 |
| `current_relative_state` | 当前比价状态，取值 `Lead/Weakening/Improving/Lag` |
| `previous_relative_state` | 此前比价状态 |
| `current_state_duration` | 当前比价状态持续时间 |
| `previous_state_duration` | 此前比价状态持续时间 |
| `base_transition_score` | 由“此前状态 -> 当前状态”映射得到的基础跃迁分 |
| `state_transition` | 状态跃迁，格式如 `Lag->Improving` |
| `relative_signal_type` | 状态跃迁类型标签 |
| `freshness_factor` | 当前状态新鲜度因子，公式为 `exp(-(current_duration - 1) / 5)` |
| `previous_maturity_factor` | 此前状态成熟度因子，公式为 `min(previous_duration / 15, 1)` |
| `transition_score` | 状态跃迁分：`base_transition_score * freshness_factor * previous_maturity_factor` |

常用状态跃迁解释：

| 跃迁 | `base_transition_score` | `relative_signal_type` | 解释 |
|---|---:|---|---|
| `Lag->Lead` | `120` | `strong_reversal_to_lead` | 从落后直接转领先，强反转 |
| `Lag->Improving` | `100` | `low_level_improvement` | 低位改善 |
| `Improving->Lead` | `100` | `improvement_confirmed` | 改善确认进入领先 |
| `Lead->Improving` | `30` | `leadership_cooling_but_positive` | 领先降温但仍偏正 |
| `Improving->Lag` | `-90` | `reversal_failed_to_lag` | 改善失败回落 |
| `Lead->Lag` | `-120` | `leadership_collapse` | 领先坍塌 |

`rs_score` 公式：

```text
rs_score =
  0.20 * early_reversal
  + 0.30 * strength_momentum
  + 0.35 * relative_strength
  + 0.15 * transition_score
```

### 资金信号派生指标

实现位置：`src/zsxq_pipeline/signals/funding_lead_score.py`

资金模块输出的是“资金方向 + 资金信号强度”，不是单纯的“杠杆资金水平”。这一点很重要：

- `funding_leverage_value` 表示杠杆资金数值或水平。
- `funding_signal_strength` 表示当前方向上的资金信号强度。
- `funding_signal_direction` 表示这份强度属于加杠杆方向还是去杠杆方向。

因此，一个资产即使处于 `去杠杆`，`funding_signal_strength` 也可以很高；这表示“去杠杆/偏空资金信号很强”，不是“杠杆水平很高”。

输出字段：

| 派生指标 | 含义 |
|---|---|
| `funding_current_leverage_state` | 当前杠杆资金状态，原始取值通常为 `加杠杆` 或 `去杠杆` |
| `funding_current_leverage_state_duration` | 当前杠杆资金状态持续时间 |
| `funding_current_leverage_state_return` | 当前杠杆资金状态期间的涨幅/回报 |
| `funding_previous_leverage_state` | 此前杠杆资金状态 |
| `funding_previous_leverage_state_return` | 此前杠杆资金状态期间的涨幅/回报 |
| `funding_current_relative_state` | 当前资金模块使用的比价状态 |
| `funding_current_relative_state_duration` | 当前资金模块比价状态持续时间 |
| `funding_current_relative_state_return` | 当前资金模块比价状态期间涨幅/回报 |
| `funding_previous_relative_state` | 此前资金模块比价状态 |
| `funding_previous_relative_state_duration` | 此前资金模块比价状态持续时间 |
| `funding_previous_relative_state_return` | 此前资金模块比价状态期间涨幅/回报 |
| `funding_leverage_value` | 杠杆资金数值，即资金水平本身 |
| `funding_leverage_value_change` | 杠杆资金日变化，来自 `leverage_value_change_d1` |
| `funding_relative_return_change` | 当前比价状态回报相对上一日期的变化 |
| `funding_leverage_change_z` | 同一日期、同一数据集内，杠杆资金日变化的 z-score |
| `funding_return_change_z` | 同一日期、同一数据集内，比价回报变化的 z-score |
| `long_funding_lead_score` | 偏多资金领先分，公式为 `funding_leverage_change_z - funding_return_change_z` |
| `short_funding_lead_score` | 偏空资金领先分，公式为 `-funding_leverage_change_z + funding_return_change_z` |
| `funding_signal_direction` | 资金信号方向；`加杠杆 -> long_candidate`，`去杠杆 -> short_candidate` |
| `funding_signal_strength` | 当前方向上的资金信号强度；若方向为 `long_candidate` 取 `long_funding_lead_score`，否则取 `short_funding_lead_score` |
| `funding_duration_priority` | 持续时间优先级；当前杠杆状态持续 `5` 到 `15` 天时为 `1`，否则为 `0` |
| `funding_signal_rank` | 同一日期、同一数据集、同一方向内的排名 |
| `funding_signal_rank_pct` | 排名百分位，`rank / 同方向资产数` |
| `funding_signal_bucket` | 分层标签，取值 `strong/watch/neutral/weak` |

资金信号方向：

| 原始杠杆状态 | `funding_signal_direction` | 解读 |
|---|---|---|
| `加杠杆` | `long_candidate` | 偏多资金信号 |
| `去杠杆` | `short_candidate` | 偏空资金信号 |

资金强度公式：

```text
long_funding_lead_score = funding_leverage_change_z - funding_return_change_z
short_funding_lead_score = -funding_leverage_change_z + funding_return_change_z

if funding_signal_direction == "long_candidate":
    funding_signal_strength = long_funding_lead_score
else:
    funding_signal_strength = short_funding_lead_score
```

资金排名逻辑：

1. 同一 `dataset_type`、同一日期内计算 z-score。
2. 按 `funding_signal_direction` 分组，分别排名。
3. 排名优先级依次为：
   - `funding_duration_priority` 高者优先
   - `funding_signal_strength` 高者优先
   - `funding_current_leverage_state_duration` 高者优先
   - `asset_code` 字典序
4. `funding_signal_bucket`：
   - `signal_strength <= 0` 或 `rank_pct > 0.70`：`weak`
   - `rank_pct <= 0.10`：`strong`
   - `rank_pct <= 0.30`：`watch`
   - 其他：`neutral`

### Dashboard 字段对应关系

Local Asset Terminal 的 market map 从 processed 字段中取以下字段：

| 页面字段 | processed 字段 | 说明 |
|---|---|---|
| 趋势分 | `capped_final_trend_score` | 图中颜色和 panel 趋势分 |
| 趋势状态 | `state_name` | panel 趋势状态 |
| 短/中/长频 | `daily_trend` / `weekly_trend` / `monthly_trend` | panel 三频趋势 |
| 比价强度 | `rs_score` | 横轴 |
| 比价状态 | `current_relative_state` | 过滤和 panel 状态 |
| 资金信号强度 | `funding_signal_strength` | 纵轴；不是杠杆水平 |
| 资金方向 | `funding_signal_direction` | `long_candidate` 映射为 `Leveraging`，`short_candidate` 映射为 `Deleveraging` |

后续阅读 panel 时建议同时看“资金方向”和“资金信号强度”：

```text
Leveraging + 高资金信号强度   = 加杠杆方向强信号
Deleveraging + 高资金信号强度 = 去杠杆方向强信号
```

## 当前实现范围

- 已实现：配置、筛选、样例 Excel 解析、英文指标映射、分目录时序汇总、下载元数据记录、会话存储、远端客户端骨架
- 未验证：真实知识星球接口字段形状和下载 URL 细节，需要你填入有效 `cookie` 后联调
