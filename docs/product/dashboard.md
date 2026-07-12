# Dashboard Product Contract

## 目标

Local Asset Terminal 用日期切片展示跨资产的趋势分、相对强度和资金状态。散点图用于
定位强弱组合，交易机会页用于查看当前日期的多空筛选结果，播放控制用于观察状态随时间的变化。

## 启动与加载

- 页面启动时读取 config、dates、assets 和 playback。
- 默认定位最新日期，并使用后端返回的默认资产类别及过滤器。
- Market Map 和 Opportunities 为同页 tab，共用当前日期和底部播放控件。
- 后端不可访问时显示可执行的启动提示。
- 数据服务存活但没有 processed data 时，`/api/ready` 返回 `503`；
  `/api/health` 仍返回 `200`。

## 交互

- Asset Class 选择单一类别；`GS Exempt` 跨 `core` 和 `instruments` 筛出公司批准名单中且当前日期有完整数据的标的。
- Funding State 和 Relative Strength State 支持多选。
- Search 按 symbol 或资产名称过滤，并优先于其他过滤条件。
- Market Map tab 使用筛选器、搜索、散点图和资产详情面板；散点图不再展示独立的排序关注标注，
  而是分色标注当前 Opportunities 资产范围内强势/候选做多和强势/候选做空各自的 Top 10，重叠标的同时显示多类。
  强势做多标签使用红色、候选做多使用橙色；强势做空使用深绿色、候选做空使用浅绿色。
- Opportunities tab 不套用 Market Map 的 Search、Funding State 或 Relative Strength State；
  自己的 Asset Class 默认为 `All Assets`，并支持 `core`、`instruments` 和 `GS Exempt`。
- Opportunity 排名变化在当前 Asset Class 资产范围内计算；切换到 `GS Exempt` 后，当前排名和历史排名都只比较公司名单中的有效标的。
- First、Previous、Play/Pause、Next、Latest、日期滑块和日期输入共同控制播放位置。
- 图表选择资产后显示趋势、比价、资金指标和最近历史；比价分历史以
  `early_reversal`、`strength_momentum`、`relative_strength` 三条分项序列展示。
- Market Map marker 不使用动画或光晕；红色边框表示 `Leveraging`，`Deleveraging` 不显示边框。
  marker 填充色按趋势分分段：`≤ -40` 为蓝色弱势、`(-40, 40)` 为灰色中性、`≥ 40` 为橙色强势。
  绘图区（plot area）右上角色阶图例按完整 `[-100, 100]` 区间，在色条 30% 和 70% 位置标记
  `-40` 和 `40` 阈值。
- Market Map 的 Relative Strength Score 显示范围固定为 `70–140`，Leverage Value 显示范围固定为
  `0–100`；支持滚轮缩放、拖拽平移、框选缩放、撤销缩放和恢复完整范围。
- Market Map 缩放工具位于绘图区右上方且仅显示图标；趋势色阶图例从绘图区右上角略向左下方偏移并
  向绘图区内部展开。marker hover tooltip 仅显示 symbol 和资产名称，不显示指标值。
- 资产详情最近历史图使用稀疏日期横轴和数值纵轴；比价分历史标出 `120`、`100`、
  `80` 阈值，并在 `100` 绘制基准横线。
- Opportunities tab 同页展示强势/候选做多和强势/候选做空结果。每组先按规则筛出全部机会并显示总数，
  表格只渲染排名前 10 的行；做多和做空分别占一行。点击或用键盘选中任一行后，右侧显示与
  Market Map 相同且可调整宽度的资产详情面板。
- Opportunities tab 按 `symbol + asset_name` 识别同一标的；`core` 和 `instruments` 同时出现的
  重复标的只保留排序最靠前的一条。
- Reset 恢复后端给出的默认过滤器并清除选择。

## 状态语义

- Relative Strength：`Lag`、`Weakening`、`Improving`、`Lead`。
- Funding：`Leveraging`、`Deleveraging`。
- 趋势分范围为 `[-100, 100]`，表示月/周/日趋势结构的 duration-only 成熟度；
  趋势变化分保留在 processed series 中，不在当前 dashboard 展示。
- `70/-70` 是 dashboard 做多/做空候选和高置信标签阈值，不是趋势分计算公式的一部分。
- 资产详情只生成四种信号标签，且逐条独立判断、可同时出现多个：`高置信做多` 要求趋势分、
  比价强度分和杠杆速率分均 `≥ 70`；`高置信做空` 要求三者均 `≤ -70`；`快速加杠杆` 要求
  杠杆速率分 `≥ 70`；`快速去杠杆` 要求杠杆速率分 `≤ -70`。条件全部不满足时不显示标签区域。
  资产详情不生成资金状态、比价状态或 `观察` 标签；对应原始状态仍在指标区显示。
- Market Map 的相对强度和资金展示范围使用上述固定区间；API 仍返回数据计算范围供其他用途使用。
- 空过滤结果显示 empty state，不应被误报为后端离线。
- 强势做多要求 `current_relative_state` 为 `Lead` 或 `Improving`、`early_reversal > 100`、
  资金状态为 `Leveraging`、`trend_score > 20` 且周趋势为 `up`。排序依次使用杠杆状态持续时间升序、
  资金信号强度降序、趋势分降序和稳定资产身份。
- 候选做多要求 `current_relative_state == "Improving"`、`early_reversal > 100`、
  `trend_score > 20`、日/周趋势不为 `down`，且资金为 `Leveraging` 或温和 `Deleveraging`
  (`leverage_velocity > -5`)。排序优先 `Leveraging`，再按对应资金状态的持续时间或速率及规则中的
  tie-breaker 排列。
- 强势做空要求 `current_relative_state` 为 `Weakening` 或 `Lag`、`early_reversal < 100`、
  资金状态为 `Deleveraging`、`trend_score > 20` 且日趋势为 `down`。排序依次使用去杠杆状态
  持续时间升序、杠杆值降序和稳定资产身份。
- 候选做空要求 `current_relative_state` 为 `Weakening` 或 `Lag`、`early_reversal < 100`、
  `trend_score > 20`，且日趋势与周趋势不能同时为 `up`。资金必须为 `Deleveraging`，或为
  `Leveraging` 且 `leverage_velocity < 5`。排序优先 `Deleveraging`；去杠杆标的按持续时间升序、
  杠杆值降序，加杠杆标的按速率升序、杠杆值降序，最后使用稳定资产身份。筛选不依赖 API 中
  已有的 `short_candidate` 字段。
- 机会表的 `1/5/10日总排名变化` 是同一机会列表当前名次与前 1/5/10 个可用数据日期名次的差值；
  资产当时不在该机会列表时显示 `NEW`。

字段来源和传输结构见[数据与 API 契约](../data-contracts.md)。
