# Opportunity Screening and Ranking Reference

本文记录 Dashboard 当前 Opportunities 页面的筛选与排名逻辑。实现以
`frontend/src/utils/opportunities.ts` 为准，页面调用位于 `frontend/src/App.tsx`。

Opportunities 页面包含四个独立榜单：

- **强势多头（Strong Long）**
- **候选多头（Candidate Long）**
- **强势空头（Strong Short）**
- **候选空头（Candidate Short）**

四个榜单分别筛选、分别排序。同一标的可以同时出现在多个榜单中。

## 1. 排名使用的输入字段

| 字段 | 含义 |
|---|---|
| `asset_class` | 标的类型，同时参与最终稳定排序 |
| `symbol` | 标的代码，同时参与最终稳定排序 |
| `asset_name` | 标的名称，同时参与最终稳定排序 |
| `rs_state` | 当前比价状态 |
| `early_reversal` | 早期转折分 |
| `strength_momentum` | 强度动量分 |
| `relative_strength` | 相对强度分 |
| `trend_score` | Dashboard 趋势分 |
| `daily_trend` | 日频趋势方向 |
| `weekly_trend` | 周频趋势方向 |
| `funding_state` | 当前资金状态 |
| `leverage_value` | 当前杠杆资金数值 |
| `leverage_duration` | 当前杠杆状态持续时间 |
| `leverage_velocity` | 杠杆速率 |
| `funding_signal_strength` | 资金信号强度；缺失时使用 `funding_score` |
| `funding_score` | 资金分，作为资金信号强度的兜底值 |

趋势字符串在判断前会执行：

```text
normalizeTrend(value) = trim(lowercase(value))
```

因此当前筛选条件直接使用归一化后的 `up` 和 `down`。

## 2. 资产池

Opportunities 页面不套用 Market Map 的 Search、Funding State 或 Relative
Strength State 过滤器，但拥有独立的 Asset Class 选项：`All Assets`、普通
Asset Class 和 `GS Exempt`。页面先按该选项过滤每个历史 frame，再在同一资产池
中计算四个榜单及排名变化；`GS Exempt` 只保留公司批准名单中且当前 frame 有数据的标的。

## 3. 强势多头筛选

标的必须同时满足以下全部条件：

```text
rs_state in {Lead, Improving}
early_reversal > 100
funding_state == Leveraging
trend_score > 20
normalizeTrend(weekly_trend) == up
```

边界值是严格比较：

- `early_reversal = 100` 不入选。
- `trend_score = 20` 不入选。
- 周频趋势必须为 `up`；`neutral` 和 `down` 都不入选。

## 4. 强势多头排序

筛选通过后，按以下优先级依次排序；只有前一项相同时才比较后一项：

```text
1. leverage_duration asc
2. funding_signal_strength desc
   - funding_signal_strength 不是有限数值时，使用 funding_score
3. trend_score desc
4. asset_class asc
5. symbol asc
6. asset_name asc
```

直觉上，强势多头优先选择刚开始加杠杆的标的；持续时间相同时，优先资金
信号更强者，再比较趋势分。

`leverage_duration` 不是有限数值时按正无穷处理，因此排在有有效持续时间的
标的之后。资金信号没有有效值时按负无穷处理，因此排在有效资金信号之后。

## 5. 候选多头筛选

标的必须同时满足以下全部条件：

```text
rs_state == Improving
early_reversal > 100
trend_score > 20
normalizeTrend(daily_trend) != down
normalizeTrend(weekly_trend) != down

并且满足以下资金条件之一：
  funding_state == Leveraging
  或
  funding_state == Deleveraging and leverage_velocity > -5
```

边界与特殊情况：

- `early_reversal = 100` 不入选。
- `trend_score = 20` 不入选。
- 日频或周频趋势只排除 `down`；`up`、`neutral`，以及空字符串都会通过这一项判断。
- 去杠杆标的必须满足 `leverage_velocity > -5`；等于 `-5` 不入选。
- 去杠杆标的的 `leverage_velocity` 不是有限数值时按负无穷处理，因此不入选。
- 资金状态不是 `Leveraging` 或符合条件的 `Deleveraging` 时不入选。

## 6. 候选多头排序

筛选通过后，按以下优先级依次排序：

```text
1. funding_state
   Leveraging before Deleveraging before other states

2. Leveraging 标的：leverage_duration asc
   非 Leveraging 标的在这一项按正无穷处理

3. Deleveraging 标的：leverage_velocity desc
   非 Deleveraging 标的在这一项按负无穷处理

4. early_reversal desc
5. strength_momentum asc
6. relative_strength asc
7. funding_signal_strength asc
   - funding_signal_strength 不是有限数值时，使用 funding_score
8. leverage_velocity desc
9. asset_class asc
10. symbol asc
11. asset_name asc
```

这意味着所有加杠杆候选都排在温和去杠杆候选之前：

- 加杠杆组内，优先当前杠杆状态持续时间更短的标的。
- 去杠杆组内，优先 `leverage_velocity` 更高、即更接近重新转正的标的。
- 后续字段用于继续区分同组、同持续时间或同速率的标的。

注意：候选多头排序中 `strength_momentum`、`relative_strength` 和
`funding_signal_strength` 当前使用升序。这是当前代码的实际行为。

## 7. 强势空头筛选

标的必须同时满足以下全部条件：

```text
rs_state in {Weakening, Lag}
early_reversal < 100
funding_state == Deleveraging
trend_score > 20
normalizeTrend(daily_trend) == down
```

边界值是严格比较：

- `early_reversal = 100` 不入选。
- `trend_score = 20` 不入选。
- 日频趋势必须为 `down`；`neutral` 和 `up` 都不入选。

## 8. 强势空头排序

筛选通过后，按以下优先级依次排序：

```text
1. leverage_duration asc
2. leverage_value desc
3. asset_class asc
4. symbol asc
5. asset_name asc
```

强势空头优先选择刚开始去杠杆的标的；持续时间相同时，优先杠杆资金数值
更大的标的。`leverage_duration` 不是有限数值时按正无穷处理，因此排在有效
持续时间之后。

## 9. 候选空头筛选

标的必须同时满足以下全部条件：

```text
rs_state in {Weakening, Lag}
early_reversal < 100
trend_score > 20
not (
  normalizeTrend(daily_trend) == up
  and normalizeTrend(weekly_trend) == up
)

并且满足以下资金条件之一：
  funding_state == Deleveraging
  或
  funding_state == Leveraging and leverage_velocity < 5
```

边界与特殊情况：

- `early_reversal = 100` 不入选。
- `trend_score = 20` 不入选。
- 日频与周频趋势同时为 `up` 时不入选；其中任一为 `neutral` 或 `down` 即通过趋势条件。
- 加杠杆标的必须满足 `leverage_velocity < 5`；等于 `5` 不入选。
- 加杠杆标的的 `leverage_velocity` 不是有限数值时按正无穷处理，因此不入选。
- 筛选根据当前指标派生，不依赖 API 中已有的 `short_candidate` 字段。

## 10. 候选空头排序

筛选通过后，按以下优先级依次排序：

```text
1. funding_state
   Deleveraging before Leveraging before other states

2. Deleveraging 标的：leverage_duration asc
   非 Deleveraging 标的在这一项按正无穷处理

3. Leveraging 标的：leverage_velocity asc
   非 Leveraging 标的在这一项按正无穷处理

4. leverage_value desc
5. asset_class asc
6. symbol asc
7. asset_name asc
```

这意味着去杠杆候选始终排在低速加杠杆候选之前：

- 去杠杆组内，优先当前去杠杆状态持续时间更短的标的。
- 加杠杆组内，优先 `leverage_velocity` 更低、即更接近加杠杆尾声的标的。
- 同组的主要排序值相同时，优先杠杆资金数值更大的标的。

## 11. 排名编号与展示数量

每个榜单在完成当前所选资产池的筛选、排序和去重后，从 `1` 开始编号：

```text
rank = sorted_index + 1
```

页面只展示每个榜单的前 `10` 名，但页面标题中的 total 数量是该榜单筛选后
的完整数量。

## 12. 1/5/10 日排名变化

页面分别计算 `1`、`5`、`10` 个可用数据日期之前的同一榜单排名。这里的
偏移量基于 `availableDates` 的索引，不是自然日差。

每个历史日期都会使用当前榜单的同一套入选条件与排序规则。排名变化公式为：

```text
rank_change = previous_rank - current_rank
```

| 情况 | 显示值 |
|---|---|
| 当前排名比历史排名上升 | `+N` |
| 当前排名比历史排名下降 | `-N` |
| 排名未变 | `0` |
| 历史榜单中没有该标的 | `NEW` |
| 历史偏移超出已有日期范围 | `NEW` |

例如：标的从历史第 `5` 名升到当前第 `2` 名，显示 `+3`；从第 `2` 名降到
第 `5` 名，显示 `-3`。

## 13. 标的身份与稳定排序

Opportunity 内部使用以下组合键识别标的：

```text
symbol::asset_name
```

这个组合键用于关联当前排名、历史排名变化和重复标的。每套榜单先按自己的
完整排序规则排序，再按该组合键去重；同一标的同时存在于 `core` 和 `instruments`
时，只保留排序更靠前的一条。四套排序规则最后都使用 `asset_class`、`symbol`、
`asset_name` 升序作为稳定的确定性兜底，避免前述排名字段完全相同时结果顺序漂移。

## 14. 实现与验证位置

- 页面调用链：`frontend/src/App.tsx`
- 四套筛选、排序、排名变化和 Top 10：`frontend/src/utils/opportunities.ts`
- 固定样例单测：`frontend/src/utils/opportunities.test.ts`

如果本文与代码出现不一致，以当前实现代码为准，并应同步更新本文。
