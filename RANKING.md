# Opportunity Screening and Ranking Reference

本文记录 Dashboard 当前 Opportunities 页面的筛选与排名逻辑。实现以
`frontend/src/utils/opportunities.ts` 为准；资产池预筛选由
`frontend/src/App.tsx` 和 `frontend/src/utils/filtering.ts` 完成。

Opportunities 页面包含两个独立榜单：

- **强势多头（Strong Long）**
- **候选多头（Candidate Long）**

两个榜单分别筛选、分别排序。同一标的可以同时出现在两个榜单中。

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
| `leverage_duration` | 当前杠杆状态持续时间 |
| `leverage_velocity` | 杠杆速率 |
| `funding_signal_strength` | 资金信号强度；缺失时使用 `funding_score` |
| `funding_score` | 资金分，作为资金信号强度的兜底值 |

趋势字符串在判断前会执行：

```text
normalizeTrend(value) = trim(lowercase(value))
```

因此当前筛选条件直接使用归一化后的 `up` 和 `down`。

## 2. 资产池预筛选

Opportunity 排名不是固定在全市场资产池上计算。页面会先按照当前的
`Asset Class` 选项过滤每个历史 frame，再在过滤后的资产池内执行两套
Opportunity 筛选和排序。

当前选项包括：

- `All Assets`：不额外限制资产池。
- 普通 Asset Class：只保留对应 `asset_class` 的标的。
- `GS Exempt`：只保留 `is_gs_exempt = true` 且当前 frame 中实际有数据的标的。

当前排名与历史排名使用同一个资产池过滤条件。因此切换 Asset Class 后，
榜单排名和 1/5/10 日排名变化都会在所选资产范围内重新计算。

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

## 7. 排名编号与展示数量

每个榜单在完成完整资产池的筛选和排序后，从 `1` 开始编号：

```text
rank = sorted_index + 1
```

页面只展示每个榜单的前 `10` 名，但页面标题中的 total 数量是该榜单筛选后
的完整数量。Market Map 上的 Opportunity 标记也只取两个榜单各自的前
`10` 名；同时进入两个 Top 10 的标的会保留两个标记。

## 8. 1/5/10 日排名变化

页面分别计算 `1`、`5`、`10` 个可用数据日期之前的榜单排名。这里的偏移量
基于 `availableDates` 的索引，不是自然日差。

每个历史日期都会使用：

1. 当前页面选中的同一资产池过滤条件；
2. 当前榜单的同一套入选条件；
3. 当前榜单的同一套排序规则。

排名变化公式为：

```text
rank_change = previous_rank - current_rank
```

显示规则：

| 情况 | 显示值 |
|---|---|
| 当前排名比历史排名上升 | `+N` |
| 当前排名比历史排名下降 | `-N` |
| 排名未变 | `0` |
| 历史榜单中没有该标的 | `NEW` |
| 历史偏移超出已有日期范围 | `NEW` |

例如：标的从历史第 `5` 名升到当前第 `2` 名，显示 `+3`；从第 `2` 名降到
第 `5` 名，显示 `-3`。

## 9. 标的身份与稳定排序

Opportunity 内部使用以下组合键识别标的：

```text
asset_class::symbol::asset_name
```

这个组合键用于关联当前排名、历史排名变化和 Market Map 标记。排序规则最后
也使用 `asset_class`、`symbol`、`asset_name` 升序作为稳定的确定性兜底，避免
前述排名字段完全相同时结果顺序漂移。

## 10. 实现与验证位置

- 资产池预筛选和页面调用链：`frontend/src/App.tsx`
- Asset Class / GS Exempt 过滤：`frontend/src/utils/filtering.ts`
- 两套筛选、排序、排名变化和 Top 10：`frontend/src/utils/opportunities.ts`
- 固定样例单测：`frontend/src/utils/opportunities.test.ts`

如果本文与代码出现不一致，以当前实现代码为准，并应同步更新本文。
