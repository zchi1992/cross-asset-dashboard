# Dashboard Product Contract

## 目标

Local Asset Terminal 用日期切片展示跨资产的趋势分、相对强度和资金状态。散点图用于
定位强弱组合，播放控制用于观察状态随时间的变化。

## 启动与加载

- 页面启动时读取 config、dates、assets 和 playback。
- 默认定位最新日期，并使用后端返回的默认资产类别及过滤器。
- 后端不可访问时显示可执行的启动提示。
- 数据服务存活但没有 processed data 时，`/api/ready` 返回 `503`；
  `/api/health` 仍返回 `200`。

## 交互

- Asset Class 选择单一类别。
- Funding State 和 Relative Strength State 支持多选。
- Search 按 symbol 或资产名称过滤，并优先于其他过滤条件。
- First、Previous、Play/Pause、Next、Latest、日期滑块和日期输入共同控制播放位置。
- 图表选择资产后显示趋势、比价、资金指标和最近历史。
- Reset 恢复后端给出的默认过滤器并清除选择。

## 状态语义

- Relative Strength：`Lag`、`Weakening`、`Improving`、`Lead`。
- Funding：`Leveraging`、`Deleveraging`。
- 趋势分范围为 `[-100, 100]`；相对强度和资金展示范围由数据计算。
- 空过滤结果显示 empty state，不应被误报为后端离线。

字段来源和传输结构见[数据与 API 契约](../data-contracts.md)。
