# Signal Calculation Reference

本文记录当前 processed signal 的计算逻辑。实现以 `src/zsxq_pipeline/signals/` 为准，输入和输出都使用 long format：

```text
date,dataset_type,asset_code,asset_name,metric_name,metric_value
```

同一个资产同一天的多行 `metric_name` 会先聚合成一组输入，再输出新的派生 `metric_name`。

## 1. 趋势分数

实现位置：`src/zsxq_pipeline/signals/trend_score.py`

最终 dashboard 使用的趋势分数字段是 `capped_final_trend_score`。

### 输入字段

| 输入字段 | 含义 | 合法值或要求 |
|---|---|---|
| `monthly_trend` | 月频趋势方向 | `up` / `neutral` / `down`，也支持中文同义值 |
| `weekly_trend` | 周频趋势方向 | 同上 |
| `daily_trend` | 日频趋势方向 | 同上 |
| `monthly_trend_bars` 或 `monthly_trend_duration` | 当前月频趋势已持续的 bar 数 | 数值，不能小于 `0` |
| `weekly_trend_bars` 或 `weekly_trend_duration` | 当前周频趋势已持续的 bar 数 | 数值，不能小于 `0` |
| `daily_trend_bars` 或 `daily_trend_duration` | 当前日频趋势已持续的 bar 数 | 数值，不能小于 `0` |

趋势方向会被归一化为：

```text
up = 1
neutral = 0
down = -1
```

三频权重：

```text
monthly = 3
weekly = 2
daily = 1
```

成熟阈值：

```text
monthly = 6 bars
weekly = 12 bars
daily = 20 bars
```

### 计算逻辑

1. 归一化三频趋势：

```text
monthly_value = value(monthly_trend)
weekly_value  = value(weekly_trend)
daily_value   = value(daily_trend)
```

2. 计算当前方向原始分：

```text
raw_current_score =
  monthly_value * 3
  + weekly_value * 2
  + daily_value * 1

current_score = raw_current_score / 6 * 100
```

3. 计算持续时间成熟度因子。中性趋势不贡献持续时间分：

```text
duration_multiplier = 0                         if trend == neutral
duration_multiplier = 1 + min(sqrt(bars / maturity_bars), 1)
```

因此非中性趋势的成熟度因子范围是 `1~2`。

4. 计算带持续时间的趋势分：

```text
raw_duration_score =
  monthly_value * 3 * monthly_duration_multiplier
  + weekly_value * 2 * weekly_duration_multiplier
  + daily_value * 1 * daily_duration_multiplier

duration_score = raw_duration_score / 12 * 100
```

分母 `12` 来自三频权重总和 `6` 乘以最大成熟度因子 `2`。

5. 计算趋势变化分。变化分和上一日期比较；如果没有上一日期，则用当前日期自己作为上一日期，变化分为 `0`：

```text
monthly_change = current_monthly_value - previous_monthly_value
weekly_change  = current_weekly_value  - previous_weekly_value
daily_change   = current_daily_value   - previous_daily_value

raw_transition_score =
  monthly_change * 3
  + weekly_change * 2
  + daily_change * 1

transition_score = raw_transition_score / 12 * 100
decayed_transition_score = transition_score
```

6. 计算最终趋势分，并限制在 `[-100, 100]`：

```text
raw_final_trend_score = duration_score + 0.4 * decayed_transition_score
capped_final_trend_score = max(-100, min(100, raw_final_trend_score))
```

### 输出字段

| 输出字段 | 含义 |
|---|---|
| `trend_combo` | 三频组合，例如 `up/neutral/down` |
| `state_name` | 根据三频组合映射出的趋势状态，例如 `主升浪`、`震荡下探` |
| `current_score` | 只看当前三频方向的百分制分 |
| `duration_score` | 加入趋势持续时间成熟度后的趋势分 |
| `transition_score` | 相比上一日期的三频变化分 |
| `raw_final_trend_score` | 未截断最终趋势分 |
| `capped_final_trend_score` | 截断到 `[-100, 100]` 后的最终趋势分 |
| `transition_label` | 对本期趋势变化的中文描述 |

### 例子

假设某资产当天为：

```text
monthly_trend = up, monthly_trend_bars = 6
weekly_trend  = up, weekly_trend_bars  = 3
daily_trend   = neutral, daily_trend_bars = 0

上一日期：
monthly_trend = up
weekly_trend  = neutral
daily_trend   = neutral
```

当前方向：

```text
raw_current_score = 1*3 + 1*2 + 0*1 = 5
current_score = 5 / 6 * 100 = 83.33
```

持续时间成熟度：

```text
monthly_multiplier = 1 + min(sqrt(6/6), 1) = 2.00
weekly_multiplier  = 1 + sqrt(3/12) = 1.50
daily_multiplier   = 0 because daily is neutral
```

带持续时间：

```text
raw_duration_score = 1*3*2.00 + 1*2*1.50 + 0 = 9
duration_score = 9 / 12 * 100 = 75.00
```

趋势变化：

```text
monthly_change = 1 - 1 = 0
weekly_change  = 1 - 0 = 1
daily_change   = 0 - 0 = 0

raw_transition_score = 0*3 + 1*2 + 0*1 = 2
transition_score = 2 / 12 * 100 = 16.67
```

最终：

```text
raw_final_trend_score = 75.00 + 0.4 * 16.67 = 81.67
capped_final_trend_score = 81.67
state_name = 主升整理
```

## 2. 比价强度分数

实现位置：`src/zsxq_pipeline/signals/relative_strength.py`

最终 dashboard 使用的比价强度字段是 `rs_score`。

### 输入字段

| 输入字段 | 含义 | 合法值或要求 |
|---|---|---|
| `early_reversal` | 早期转折分，偏快变量 | 数值 |
| `strength_momentum` | 强度动量分，偏快变量 | 数值 |
| `relative_strength` | 相对强度分，偏慢变量 | 数值 |
| `current_relative_state` | 当前比价状态 | `Lead` / `Weakening` / `Improving` / `Lag` |
| `previous_relative_state` | 此前比价状态 | 同上，且必须不同于当前状态 |
| `current_relative_state_duration` 或 `current_state_duration` | 当前比价状态持续时间 | 数值，不能小于 `1` |
| `previous_relative_state_duration` 或 `previous_state_duration` | 此前比价状态持续时间 | 数值，不能小于 `1` |

### 状态跃迁基础分

| 跃迁 | 基础分 | 类型 |
|---|---:|---|
| `Lag -> Lead` | `120` | `strong_reversal_to_lead` |
| `Weakening -> Lead` | `110` | `renewed_leadership` |
| `Lag -> Improving` | `100` | `low_level_improvement` |
| `Improving -> Lead` | `100` | `improvement_confirmed` |
| `Weakening -> Improving` | `60` | `weakness_repairing` |
| `Lead -> Improving` | `30` | `leadership_cooling_but_positive` |
| `Lag -> Weakening` | `-40` | `weak_to_unstable` |
| `Improving -> Weakening` | `-60` | `improvement_failed` |
| `Lead -> Weakening` | `-90` | `leadership_losing_momentum` |
| `Improving -> Lag` | `-90` | `reversal_failed_to_lag` |
| `Weakening -> Lag` | `-100` | `weakness_confirmed` |
| `Lead -> Lag` | `-120` | `leadership_collapse` |

### 计算逻辑

1. 根据 `previous_relative_state -> current_relative_state` 找到 `base_transition_score`。

2. 计算当前状态新鲜度。当前状态持续越久，新鲜度越低：

```text
freshness_factor = exp(-(current_duration - 1) / 5)
```

3. 计算此前状态成熟度。此前状态持续到 `15` 天后成熟度封顶：

```text
previous_maturity_factor = min(previous_duration / 15, 1)
```

4. 计算状态跃迁分：

```text
transition_score =
  base_transition_score
  * freshness_factor
  * previous_maturity_factor
```

5. 计算综合比价强度分：

```text
rs_score =
  0.20 * early_reversal
  + 0.30 * strength_momentum
  + 0.35 * relative_strength
  + 0.15 * transition_score
```

### 输出字段

| 输出字段 | 含义 |
|---|---|
| `rs_score` | 综合比价强度分 |
| `state_transition` | 状态跃迁，例如 `Lag->Improving` |
| `base_transition_score` | 跃迁基础分 |
| `relative_signal_type` | 跃迁类型标签 |
| `freshness_factor` | 当前状态新鲜度因子 |
| `previous_maturity_factor` | 此前状态成熟度因子 |
| `transition_score` | 最终状态跃迁分 |

### 例子

假设某资产：

```text
early_reversal = 105
strength_momentum = 110
relative_strength = 90
previous_relative_state = Lag
current_relative_state = Improving
current_relative_state_duration = 2
previous_relative_state_duration = 10
```

状态跃迁：

```text
Lag -> Improving
base_transition_score = 100
freshness_factor = exp(-(2 - 1) / 5) = 0.8187
previous_maturity_factor = min(10 / 15, 1) = 0.6667
transition_score = 100 * 0.8187 * 0.6667 = 54.58
```

综合分：

```text
rs_score =
  0.20 * 105
  + 0.30 * 110
  + 0.35 * 90
  + 0.15 * 54.58
= 93.69
```

含义：该资产处于低位改善路径，快变量较强，慢变量也处于较高水平，因此 `rs_score` 偏高。

## 3. 杠杆水平与资金信号分数

实现位置：`src/zsxq_pipeline/signals/funding_lead_score.py`

dashboard 里和资金相关的核心字段有三类：

- `funding_leverage_value`：原始杠杆资金数值，即“杠杆水平”。
- `leverage_velocity_score`：杠杆资金变化速度的横截面方向分。
- `funding_signal_strength` / `funding_score`：当前资金方向上的综合机会强度。

注意：当前实现的 `funding_score` 不是单纯的杠杆水平分数，而是由横截面位置、变化速度和状态成熟度组合而成的方向性资金信号。

### 输入字段

| 输入字段 | 含义 | 合法值或要求 |
|---|---|---|
| `current_leverage_state` | 当前杠杆资金状态 | `加杠杆` 或 `去杠杆` |
| `current_leverage_state_duration` | 当前杠杆资金状态持续时间 | 数值，不能小于 `1` |
| `leverage_value` | 当前杠杆资金数值，即原始杠杆水平 | 数值 |
| `leverage_value_change_d1` | 可选，源数据给出的 1D 变化 | 如果校验开启，必须等于当前 `leverage_value` 减上一历史观测日的 `leverage_value` |

状态方向映射：

```text
加杠杆 -> funding_direction = long
去杠杆 -> funding_direction = short

long  -> funding_signal_direction = long_candidate
short -> funding_signal_direction = short_candidate
```

### 基础计算

每个资产按日期排序后，使用历史观测日计算 1D、5D、10D velocity：

```text
velocity_1d  = leverage_value_today - leverage_value_1_observation_ago
velocity_5d  = leverage_value_today - leverage_value_5_observations_ago
velocity_10d = leverage_value_today - leverage_value_10_observations_ago
```

如果历史不足，对应窗口为空。没有任何 velocity 窗口的日期不会输出资金分。

原始综合 velocity 使用权重 `1D/5D/10D = 0.2/0.5/0.3`，缺失窗口会按可用窗口重新归一：

```text
leverage_velocity =
  weighted_average(velocity_1d, velocity_5d, velocity_10d)
```

### 横截面分数

以下横截面都在同一 `dataset_type + date` 内计算。

1. 杠杆水平位置分：

```text
position_score = percentile_rank(funding_leverage_value)
```

数值越大，说明当前杠杆水平在同日资产池中越靠前。多个资产同值时使用平均排名；同一横截面只有一个有效值时为 `50`。

2. 单窗口 velocity 分：

```text
long_velocity_1d_score  = percentile_rank(velocity_1d)
long_velocity_5d_score  = percentile_rank(velocity_5d)
long_velocity_10d_score = percentile_rank(velocity_10d)

short_velocity_1d_score  = percentile_rank(-velocity_1d)
short_velocity_5d_score  = percentile_rank(-velocity_5d)
short_velocity_10d_score = percentile_rank(-velocity_10d)
```

`long` 侧喜欢 velocity 越高越好；`short` 侧喜欢 velocity 越低越好。

3. 综合 velocity 分：

```text
long_velocity_score =
  weighted_average(long_velocity_1d_score, long_velocity_5d_score, long_velocity_10d_score)

short_velocity_score =
  weighted_average(short_velocity_1d_score, short_velocity_5d_score, short_velocity_10d_score)
```

权重同样是 `0.2/0.5/0.3`，缺失窗口会重归一。

4. 有符号杠杆速度分：

```text
leverage_velocity_score > 0  表示综合速度为正，正在加速加杠杆
leverage_velocity_score < 0  表示综合速度为负，正在加速去杠杆
```

它会把正 velocity 和负 velocity 分开做 percentile rank；正数得到正分，负数得到负分。

速度标签：

| 条件 | `leverage_velocity_bucket` |
|---|---|
| `leverage_velocity_score >= 70` | `fast_leveraging` |
| `0 < leverage_velocity_score < 70` | `leveraging` |
| `leverage_velocity_score <= -70` | `fast_deleveraging` |
| `-70 < leverage_velocity_score < 0` | `deleveraging` |
| `leverage_velocity_score == 0` | `neutral` |

### 状态成熟度

`maturity_score` 只看当前 `加杠杆` / `去杠杆` 状态持续时间：

```text
duration <= 1       -> 20
1 < duration <= 4   -> 20 + (duration - 1) / 3 * 80
4 < duration <= 10  -> 100
10 < duration <= 20 -> 100 - (duration - 10) / 10 * 50
20 < duration <= 30 -> 50 - (duration - 20) / 10 * 40
duration > 30       -> 10
```

含义：刚启动的状态分数较低，`4~10` 天最成熟，过长后逐步降权。

### 综合资金分

做多资金分：

```text
long_funding_score =
  0.4 * long_velocity_score
  + 0.4 * maturity_score
  + 0.2 * (100 - position_score)
```

做空资金分：

```text
short_funding_score =
  0.4 * short_velocity_score
  + 0.4 * maturity_score
  + 0.2 * position_score
```

最终只取当前资金方向对应的一侧：

```text
funding_score =
  long_funding_score  if current_leverage_state == 加杠杆
  short_funding_score if current_leverage_state == 去杠杆

funding_signal_strength = funding_score
```

直觉：

- `加杠杆` 方向：更喜欢资金速度强、状态成熟、但杠杆位置还没太拥挤。
- `去杠杆` 方向：更喜欢去杠杆速度强、状态成熟、且原本杠杆位置较高。

### 排名和分层

同一 `dataset_type + date + funding_direction` 内，按以下优先级排名：

```text
funding_score desc
velocity_window_count desc
asset_code asc
```

```text
funding_signal_rank_pct = rank / same_direction_asset_count
```

分层：

```text
funding_score <= 0 or rank_pct > 0.70 -> weak
rank_pct <= 0.10                      -> strong
rank_pct <= 0.30                      -> watch
otherwise                             -> neutral
```

### 例子

假设同一日期、同一数据集中，资产 A 的输入和横截面分数如下：

```text
current_leverage_state = 去杠杆
current_leverage_state_duration = 2
leverage_value = 94

velocity_1d = -4
velocity_5d = -6
velocity_10d = -5

position_score = 90
short_velocity_1d_score = 95
short_velocity_5d_score = 60
short_velocity_10d_score = 50
```

方向：

```text
current_leverage_state = 去杠杆
funding_direction = short
funding_signal_direction = short_candidate
```

综合 short velocity：

```text
short_velocity_score =
  0.2 * 95
  + 0.5 * 60
  + 0.3 * 50
= 64
```

状态成熟度：

```text
maturity_score = 20 + (2 - 1) / 3 * 80 = 46.67
```

做空资金分：

```text
short_funding_score =
  0.4 * 64
  + 0.4 * 46.67
  + 0.2 * 90
= 62.27

funding_score = 62.27
funding_signal_strength = 62.27
```

含义：资产 A 处于去杠杆方向，原始杠杆水平仍处于较高横截面位置，且去杠杆速度较强，因此得到中高强度的偏空资金信号。

## Dashboard 使用关系

| Dashboard 页面字段 | processed 字段 | 说明 |
|---|---|---|
| 趋势分 | `capped_final_trend_score` | 图中颜色和详情面板趋势分 |
| 趋势状态 | `state_name` | 详情面板趋势状态 |
| 比价强度 | `rs_score` | 横轴 |
| 比价状态 | `current_relative_state` | 过滤和详情面板状态 |
| 杠杆水平 | `funding_leverage_value` | 原始杠杆资金数值 |
| 杠杆速度 | `leverage_velocity` | 1D/5D/10D 加权后的原始变化速度 |
| 杠杆速度分 | `leverage_velocity_score` | 有符号横截面速度分 |
| 资金信号强度 | `funding_signal_strength` | 纵轴，等于当前方向的 `funding_score` |
| 资金方向 | `funding_signal_direction` | `long_candidate` / `short_candidate` |

