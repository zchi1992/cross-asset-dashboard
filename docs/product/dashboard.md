# Dashboard Product Contract

## 目标

Local Asset Terminal 默认打开“宏观地图”，展示 G5 利率曲线、固定期限曲线因子和公开信用压力指标。
Market Map 用日期切片展示跨资产的趋势分、相对强度和资金状态；Opportunities 查看当前日期的
多空筛选结果。页签顺序固定为“宏观地图 → Market Map → Opportunities”。

## 启动与加载

- 页面启动时读取 config、dates、assets 和 playback。
- 默认定位最新日期，并使用后端返回的默认资产类别及过滤器。
- Market Map 和交易机会为同页 tab，共用当前日期和底部播放控件。
- 后端不可访问时显示可执行的启动提示。
- 数据服务存活但没有 processed data 时，`/api/ready` 返回 `503`；
  `/api/health` 仍返回 `200`。

## 交互

- 宏观地图按来源分别展示真实数据日期和新鲜度，不把异步市场强制对齐到同一天。
- 每个市场展示 2Y/5Y/10Y/30Y 曲线，以及 `10Y` level、`10Y-2Y` slope 和
  `2×5Y-2Y-10Y` curvature；历史区间支持 1M/3M/1Y/3Y/5Y。
- 信用区展示 HY OAS、IG OAS、HY-IG、NFCI、OFR FSI 和 SLOOS。状态标签是机械诊断，
  不构成交易建议。宏观地图不显示资产 playback，切换页签后保留宏观选择状态。
- Asset Class 选择单一类别；`GS Exempt` 跨 `core` 和 `instruments` 筛出公司批准名单中且当前日期有完整数据的标的。
- Market Map 另提供一级类别、二级类别、三级类别和地区四个多选筛选器；同一维度内取并集、
  不同维度与其他筛选条件取交集。二级选项随一级选择收窄，三级选项随一级和二级选择收窄，
  父级改变后失效的子级选择自动清除。地区独立筛选，空选择表示全部。
- 地区按金融市场区域归并为 `US`、`Canada`、`LatAm`、`Europe`、`JP`、`KR`、`CN`、
  `APAC` 和 `Emerging Markets`；筛选器固定将 `US`、`CN` 放在最前。全球或无法归入
  单一区域的资产不强行贴地区标签，仍保留在 All 视图中。
- 一级类别为股票、债券、外汇、商品和另类资产；缺少分类的新资产保留在全部视图中并标记为
  `Unclassified`，不会因此丢失行情记录。
- Funding State 和 Relative Strength State 支持多选。
- Search 按 symbol 或资产名称过滤，并优先于其他过滤条件。
- Market Map tab 使用筛选器、搜索、散点图和资产详情面板；散点图不再展示独立的排序关注标注，
  而是分色标注当前 Opportunities 资产范围内的强势多头 Top 10 和候选多头 Top 10，重叠标的同时显示两类。
- 交易机会页不套用 Market Map 的 Search、Funding State 或 Relative Strength State；
  也不套用资产分类或地区筛选；自己的 Asset Class 默认为 `All Assets`，并支持 `core`、
  `instruments`、`中国` 和 `GS Exempt`。选择 `中国` 时跨 `core/instruments` 保留 `regions`
  包含 `CN` 的资产。
  而是分色标注当前 Opportunities 资产范围内强势/候选做多和强势/候选做空各自的 Top 10，重叠标的同时显示多类。
  强势做多标签使用红色、候选做多使用橙色；强势做空使用深绿色、候选做空使用浅绿色。
- Opportunities tab 不套用 Market Map 的 Search、Funding State 或 Relative Strength State；
  自己的 Asset Class 默认为 `All Assets`，并支持 `core`、`instruments` 和 `GS Exempt`。
- Opportunity 排名变化在当前 Asset Class 资产范围内计算；切换到 `GS Exempt` 后，当前排名和历史排名都只比较公司名单中的有效标的。
- 切换到 `中国` 后，当前机会排名和历史排名变化都只在中国地区资产范围内计算。
- First、Previous、Play/Pause、Next、Latest、日期滑块和日期输入共同控制播放位置。
- 图表选择资产后显示趋势、比价、资金指标和最近历史；比价分历史以
  `early_reversal`、`strength_momentum`、`relative_strength` 三条分项序列展示。
- 资产详情指标区将标准化的“收盘价对比60日位置”按原值保留 4 位小数展示；旧 processed 数据
  没有该指标时显示 `-`。
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
- 交易机会页同页展示强势/候选多头和强势/候选空头结果。每组先按规则筛出全部机会并显示总数，
  表格只渲染排名前 10 的行；多头和空头分别占一行。点击或用键盘选中任一行后，右侧显示与
- Opportunities tab 同页展示强势/候选做多和强势/候选做空结果。每组先按规则筛出全部机会并显示总数，
  表格只渲染排名前 10 的行；做多和做空分别占一行。点击或用键盘选中任一行后，右侧显示与
  Market Map 相同且可调整宽度的资产详情面板。
- 交易机会页按 `symbol + asset_name` 识别同一标的；`core` 和 `instruments` 同时出现的
  重复标的只保留排序最靠前的一条。
- Reset 恢复后端给出的默认过滤器、清空资产分类和地区筛选并清除选择。

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
