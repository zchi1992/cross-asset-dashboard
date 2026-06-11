# Local Asset Scatter Terminal 实施计划

## Summary

将现有 `dashboard/market_map.py` Streamlit/Plotly 面板替换为本地 Web Terminal：React + TypeScript + Vite 前端、FastAPI 后端、ECharts 散点图。保留现有数据采集与 processed series 计算链路，后端复用 `dashboard/data_loader.py` 的数据映射逻辑作为第一版 API 数据源。

## Key Changes

- 新增 `frontend/`：React/Vite/TypeScript 应用，使用 Zustand 管理筛选、选择、播放和偏好状态，使用 TanStack Query 请求并缓存 API 数据。
- 新增 `backend/`：FastAPI 服务，提供 `/api/health`、`/api/config`、`/api/dates`、`/api/assets`、`/api/snapshot`、`/api/playback`，并托管前端 build 后的静态文件。
- 替换旧启动入口：更新 `scripts/run_market_map_dashboard.sh`，从启动 Streamlit 改为启动 FastAPI 本地服务；README 中同步改为 `http://127.0.0.1:8000`。
- 保留但退役旧 Streamlit 代码：第一轮实现期间保留 `dashboard/data_loader.py`、`dashboard/config.py`、`dashboard/scoring_rules.py` 供后端复用；旧 Plotly/Streamlit 页面不再作为默认入口。

## Implementation Plan

1. 建立 API 契约与本地数据源
   - 字段对齐：`asset_id -> symbol`、`flow_score -> funding_score`、`flow_state -> funding_state`。
   - 日期只来自 processed 数据中的有效交易日。
   - 初版继续读取 CSV，DuckDB/Polars/Parquet 留作后续性能阶段。

2. 后端替换 Streamlit
   - 新建 FastAPI app，读取 `config.yaml` 和 processed CSV。
   - API 返回 Pydantic schema。
   - `/api/playback` 按日期组织 frames，播放期间前端不逐帧请求后端。
   - 本地生产模式由 FastAPI 托管 `frontend/dist`。

3. 前端实现单页 Terminal
   - 页面只有 Cross-Asset Scatter Monitor，不做左侧导航、多页面或桌面封装。
   - UI 全英文，Bloomberg 风格深色、高密度、小圆角、细边框。
   - ECharts 只初始化一次；日期、筛选、搜索、选择变化只更新 series/options。
   - 实现筛选、搜索高亮、资产选择、最近 30 个有效交易日轨迹和播放控制。
   - localStorage 持久化资产类别、资金筛选、RS 筛选、播放速度、最近日期；不持久化搜索和 selectedSymbol。

4. 下线旧入口
   - `scripts/run_market_map_dashboard.sh` 改为启动 FastAPI。
   - README 快速开始替换 Streamlit 说明。
   - 旧 Plotly/Streamlit 测试保留到新 API/前端测试覆盖后，再删除或迁移。

## Test Plan

- 后端 Pytest：健康检查、配置、日期、资产、snapshot、playback、无效日期、空数据、score 类型、state 枚举。
- 前端 Vitest：filter store、playback store、搜索匹配、筛选 AND/OR 逻辑、日期边界、选择状态。
- Playwright：页面启动、筛选资产、搜索高亮、点击资产显示轨迹、播放暂停、slider/calendar 切换、刷新后恢复设置。
- 回归检查：`pytest`、`npm test`、`npm run build`、手动访问 `http://127.0.0.1:8000`。

## Assumptions

- 不改动数据采集、Excel 解析、指标计算公式。
- 第一阶段不引入 Next.js、Redux、AG Grid、TradingView、Tauri、Electron、Redis 或微服务。
- 每个 phase 建议单独 commit 或 PR；未得到明确要求前不自动 commit、不 push。
