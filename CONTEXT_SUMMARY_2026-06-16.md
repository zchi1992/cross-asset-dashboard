# Context Summary - 2026-06-16

## Repository Context

- Workspace: `/Users/chizhi/Workspace/地平线数据收集`
- Current branch: `codex/20260615-poll-once`
- Current date in session: `2026-06-16`
- Timezone: `Asia/Shanghai`
- User Git policy:
  - Do not modify directly on `main` or `master`.
  - Before modifying version-controlled files, run:
    - `git branch --show-current`
    - `git status --short`
  - If current branch count is greater than 5, remind the user to clean up branches.
  - Do not commit or push unless explicitly requested.

## Current Git State Before This Document

The branch was checked and confirmed not to be `main` or `master`.

Existing uncommitted changes before creating this file:

```text
 M README.md
 M frontend/src/components/CrossAssetScatter.tsx
 M frontend/src/styles/terminal.css
```

Notes:

- `README.md` was modified earlier to reflect the latest funding score calculation logic.
- The two frontend files were already dirty and were not touched while creating this summary.
- Local branch count is 9, above the preferred maximum of 5.

## Earlier Request: Update README Funding Logic

User asked:

> 修改 README.md 文件反映最新的 funding score 计算逻辑

Actions taken:

- Read the funding logic implementation in `src/zsxq_pipeline/signals/funding_lead_score.py`.
- Compared it with `README.md` and `tests/test_trend_score.py`.
- Updated `README.md` only.

README changes included:

- Added required funding inputs:
  - `current_leverage_state`
  - `current_leverage_state_duration`
  - `leverage_value`
- Added optional validation explanation for `leverage_value_change_d1`.
- Clarified that the first date with no usable history is skipped because at least 1D velocity is required.
- Corrected maturity score behavior:
  - Day 4 through day 10 is full maturity score 100.
  - The previous README wording implied day 5 through day 10.
- Added the current `maturity_score` piecewise formula:
  - `duration <= 1`: 20
  - `1 < duration <= 4`: linearly from 20 to 100
  - `4 < duration <= 10`: 100
  - `10 < duration <= 20`: linearly from 100 to 50
  - `20 < duration <= 30`: linearly from 50 to 10
  - `duration > 30`: 10
- Added percentile rank details:
  - Ties use average rank.
  - If there is only one valid value, percentile score is 50.

Verification then:

```text
git diff --stat
README.md | 22 ++++++++++++++++++----
```

No tests were run because the change was documentation-only.

## NDX Funding Score Example: 2026-06-15

User asked:

> 举 NDX 为例，他 6/15 日的 funding 分数都是怎么计算的，详细列出来我看下

The first direct calculation attempt over raw `data/series/core/*.csv` failed because default validation detected a mismatch in `leverage_value_change_d1` for another asset:

```text
ValueError: leverage_value_change_d1 mismatch for core/10Y1! ...
```

The processed pipeline behavior was then followed:

- Filter complete funding rows with `_complete_rows_by_asset_date(...)`.
- Call `calculate_funding_lead_score_rows(..., validate_leverage_change=False)`.

Reason:

- Source `leverage_value_change_d1` may follow the vendor calendar or rounded source values.
- The actual pipeline disables this validation for processed generation.

### NDX Source History Around 2026-06-15

```text
2026-06-01: state=加杠杆, duration=37, leverage_value=100, d1=0
2026-06-08: state=加杠杆, duration=42, leverage_value=100, d1=0
2026-06-12: state=去杠杆, duration=1, leverage_value=98.76592766270345, d1=-1.234072337296553
2026-06-15: state=去杠杆, duration=2, leverage_value=94.45285868810917, d1=-4.312985984405984
```

Calculated local 1D velocity for 2026-06-15:

```text
94.45285868810917 - 98.76592766270345 = -4.313068974594273
```

This differs slightly from source `d1` because of source calendar or rounding behavior.

### NDX 2026-06-15 Funding Inputs

Calculation universe:

```text
scope/core assets: 235
```

NDX raw funding fields:

```text
funding_current_leverage_state = 去杠杆
funding_current_leverage_state_duration = 2.0
funding_leverage_value = 94.45285868810917
velocity_1d = -4.313068974594273
velocity_5d = -5.547141311890826
velocity_10d = -5.547141311890826
```

### Percentile Scores

`position_score`:

```text
source value = 94.45285868810917
position = 221 / 235
avg zero-based rank = 220
score = 220 / 234 * 100 = 94.01709401709401
```

`long_velocity_1d_score`:

```text
source value = -4.313068974594273
position = 12 / 235
avg zero-based rank = 11
score = 11 / 234 * 100 = 4.700854700854701
```

`short_velocity_1d_score`:

```text
transformed value = 4.313068974594273
position = 224 / 235
avg zero-based rank = 223
score = 223 / 234 * 100 = 95.2991452991453
```

`long_velocity_5d_score`:

```text
source value = -5.547141311890826
position = 109 / 235
avg zero-based rank = 108
score = 108 / 234 * 100 = 46.15384615384615
```

`short_velocity_5d_score`:

```text
transformed value = 5.547141311890826
position = 127 / 235
avg zero-based rank = 126
score = 126 / 234 * 100 = 53.84615384615385
```

`long_velocity_10d_score`:

```text
source value = -5.547141311890826
position = 131 / 235
avg zero-based rank = 130
score = 130 / 234 * 100 = 55.55555555555556
```

`short_velocity_10d_score`:

```text
transformed value = 5.547141311890826
position = 105 / 235
avg zero-based rank = 104
score = 104 / 234 * 100 = 44.44444444444444
```

### Composite Funding Calculation

Velocity scores:

```text
long_velocity_score
= 0.2 * 4.700854700854701
  + 0.5 * 46.15384615384615
  + 0.3 * 55.55555555555556
= 40.68376068376068

short_velocity_score
= 0.2 * 95.2991452991453
  + 0.5 * 53.84615384615385
  + 0.3 * 44.44444444444444
= 59.31623931623932
```

Maturity score:

```text
duration = 2
maturity_score = 20 + (2 - 1) / 3 * 80 = 46.666666666666664
```

Because NDX was in `去杠杆` state on 2026-06-15, the active score was the short-side score:

```text
short_funding_score
= 0.4 * short_velocity_score
  + 0.4 * maturity_score
  + 0.2 * position_score

= 0.4 * 59.31623931623932
  + 0.4 * 46.666666666666664
  + 0.2 * 94.01709401709401

= 61.19658119658121
```

Final output:

```text
funding_direction = short
funding_score = 61.19658119658121
funding_signal_direction = short_candidate
funding_signal_strength = 61.19658119658121
funding_signal_rank = 90
funding_signal_rank_pct = 0.5421686746987951
funding_signal_bucket = neutral
```

Ranking context:

```text
long_count = 69
short_count = 166
NDX short rank = 90
rank_pct = 90 / 166 = 0.5421686746987951
```

Neighboring short candidates:

```text
US03Y: 62.39
CL1!: 61.59
UAE: 61.38
KOSPI: 61.23
NDX: 61.19658119658121
AG1!: 61.1965811965812
CT1!: 61.08
SI1!: 61.03
IF1!: 60.72
```

Bucket explanation:

- `rank_pct = 0.542...`
- It is not in the top or bottom threshold bands.
- Therefore bucket is `neutral`.

## NDX Recent Trend, RS, And Funding Context

User then observed that NDX had:

- Very high leverage position score.
- Relatively slow deleveraging compared with others.
- Strong trend and relative strength.
- This may indicate a strong asset pulling back less than others, potentially becoming an early rebound or add-position candidate.

A read-only script over `data/processed/series/core/NDX.csv` produced:

```text
2026-06-02 trend=80.39 rs=90.50 state=加杠杆 dur=38 lev=100 v1=0 v5=0 v10=0 short_vel=46.66 mat=10 pos=95.30 funding=26.28 dir=long_candidate
2026-06-03 trend=80.78 rs=90.51 state=加杠杆 dur=39 lev=100 v1=0 v5=0 v10=0 short_vel=50.28 mat=10 pos=94.66 funding=24.96 dir=long_candidate
2026-06-04 trend=81.15 rs=89.79 state=加杠杆 dur=40 lev=100 v1=0 v5=0 v10=0 short_vel=48.37 mat=10 pos=94.66 funding=25.72 dir=long_candidate
2026-06-05 trend=81.49 rs=89.10 state=加杠杆 dur=41 lev=100 v1=0 v5=0 v10=0 short_vel=48.63 mat=10 pos=94.66 funding=25.62 dir=long_candidate
2026-06-08 trend=82.75 rs=86.92 state=加杠杆 dur=42 lev=100 v1=0 v5=0 v10=0 short_vel=40.36 mat=10 pos=95.73 funding=28.71 dir=long_candidate
2026-06-09 trend=83.06 rs=87.08 state=加杠杆 dur=43 lev=100 v1=0 v5=0 v10=0 short_vel=36.69 mat=10 pos=95.94 funding=30.14 dir=long_candidate
2026-06-10 trend=51.97 rs=86.46 state=加杠杆 dur=44 lev=100 v1=0 v5=0 v10=0 short_vel=32.22 mat=10 pos=96.58 funding=31.79 dir=long_candidate
2026-06-11 trend=57.86 rs=85.34 state=加杠杆 dur=45 lev=100 v1=0 v5=0 v10=0 short_vel=30.13 mat=10 pos=97.01 funding=32.55 dir=long_candidate
2026-06-12 trend=57.27 rs=86.89 state=去杠杆 dur=1 lev=98.77 v1=-1.23 v5=-1.23 v10=-1.23 short_vel=39.15 mat=20 pos=94.44 funding=42.55 dir=short_candidate
2026-06-15 trend=57.65 rs=87.19 state=去杠杆 dur=2 lev=94.45 v1=-4.31 v5=-5.55 v10=-5.55 short_vel=59.32 mat=46.67 pos=94.02 funding=61.20 dir=short_candidate
```

Interpretation given:

- The rising funding score does not equal "deleveraging is definitely accelerating".
- It is a mixed score:

```text
short_funding_score =
  0.4 * short_velocity_score
  + 0.4 * maturity_score
  + 0.2 * position_score
```

The 2026-06-12 to 2026-06-15 rise came from three parts:

- `position_score` stayed high, reflecting high leverage level.
- `short_velocity_score` rose from 39.15 to 59.32, showing some acceleration but not an extreme one.
- `maturity_score` rose from 20 to 46.67 because deleveraging duration moved from day 1 to day 2.

The semantic issue:

- Funding score is currently easy to read as "bearish pressure".
- But for a high-trend, high-RS asset like NDX, early deleveraging during a shallow pullback may instead mean "strong asset is releasing leverage while staying relatively resilient".
- This can support a "pullback accumulation" interpretation rather than a pure short-pressure interpretation.

## Latest User Concern: State Transition Semantics

User pointed out a more important issue:

> 当去杠杆状态突然转成加杠杆状态时，根据现在的计算公式，由于 position_score 特别高，funding score 会突然下降。funding 会解读为当前杠杆水平较高、去杠杆压力大，但实际上可能是短暂回调后重回主线。

Current formula:

```text
long_funding_score =
  0.4 * long_velocity_score
  + 0.4 * maturity_score
  + 0.2 * (100 - position_score)

short_funding_score =
  0.4 * short_velocity_score
  + 0.4 * maturity_score
  + 0.2 * position_score
```

Embedded assumptions:

- Low-position levering is treated as a better long opportunity.
- High-position deleveraging is treated as stronger short or deleveraging pressure.

Problem:

- These assumptions work for some crowded-extension cases.
- They break for strong-trend assets that briefly deleverage and then switch back to levering.
- In that case, high `position_score` should not automatically penalize the long setup.
- It may instead indicate a resilient mainline asset resuming after a short pullback.

Suggested semantic split:

1. `funding_pressure_score`
   - Describes the current funding/leverage state itself.
   - Answers: "How strong is the current levering or deleveraging process?"

2. `setup_score` or `accumulation_score`
   - Combines funding state transition, trend score, and relative strength.
   - Answers: "Is this funding behavior bullish continuation, pullback accumulation, crowded top, or deleveraging risk?"

Potential transition-aware logic:

```text
previous_state == 去杠杆
current_state == 加杠杆
trend_score > 50
rs_score > 70
```

In this case:

- High `position_score` should not automatically be treated as a penalty.
- It may deserve a transition or continuation bonus.
- The interpretation may be "pullback ended, mainline recovery" rather than "crowded high-level risk".

## Current Conceptual Conclusion

The current funding score mixes at least two meanings:

- Money/leverage pressure.
- Trading opportunity direction.

That makes the dashboard ambiguous, especially near state transitions.

For NDX-like cases, the more useful interpretation may require a second layer:

- Funding layer: what the leverage state is doing.
- Setup layer: what that leverage behavior means in context of trend and relative strength.

A better dashboard language may be:

- `去杠杆压力`: current deleveraging pressure.
- `加杠杆推进`: current releveraging strength.
- `回调承接/主线回归`: trend and RS are strong, deleveraging was short, and state turns back to levering.
- `拥挤高位`: high position, extended trend, weak RS, or deteriorating transition context.

## Open Implementation Direction

No code changes have been made for this semantic redesign yet.

Recommended next implementation direction:

- Keep current raw funding mechanics as a pressure/flow score.
- Add a separate transition-aware setup classifier or setup score.
- Include previous leverage state and recent state transition in the calculation.
- Use `trend_score` and `rs_score` to interpret whether high leverage is:
  - bullish continuation,
  - pullback accumulation,
  - crowded top,
  - or active deleveraging risk.

