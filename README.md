# Cross Asset Dashboard

Cross Asset Dashboard 是一套本地跨资产观察终端。项目本身不绑定任何数据来源，只约定本地数据的
schema 和存放格式；只要使用方按约定生成本地 CSV 文件，就可以启动后端 API 和前端终端查看横截面、
时间回放和资产详情。

项目由三部分组成：

- `backend/`：FastAPI 服务，读取本地 CSV 并提供终端 API。
- `frontend/`：React + Vite + ECharts 前端，用于筛选、搜索、回放和查看资产详情。
- `dashboard/`：本地数据加载、终端字段映射和展示层辅助代码。

## 依赖

### Python

建议使用 Python `3.12`。当前本地开发环境使用的是 Python `3.12.13`。

创建虚拟环境并安装 Python 依赖：

```bash
python3.12 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
```

如果系统里没有 `python3.12`，可以先确认当前版本：

```bash
python3 --version
```

### Frontend

前端依赖安装在 `frontend/` 目录：

```bash
cd frontend
npm install
cd ..
```

## 本地数据

项目最终目标是 data agnostic：数据生成、清洗和字段准备可以由外部项目完成。本项目只要求终端输入
数据落在固定目录，并满足固定 schema。

### 存放格式

终端读取以下目录中的 CSV 文件：

```text
data/processed/series/core/*.csv
data/processed/series/instruments/*.csv
```

`core` 和 `instruments` 是默认数据集名称，可在 `config.yaml` 的
`dashboard.market_map.dataset_types` 中调整。

CSV 文件可以按日期拆分，也可以按资产拆分。推荐使用每日一个文件，便于外部数据项目增量生成：

```text
data/processed/series/core/2026-06-18.csv
data/processed/series/core/2026-06-19.csv
data/processed/series/instruments/2026-06-18.csv
data/processed/series/instruments/2026-06-19.csv
```

只要目录下是 `.csv` 文件，后端会统一读取并按 `date + dataset_type + asset_code + asset_name`
聚合成终端快照。

### Schema

本地 CSV 使用 long format，每行表示一个资产在某一天的一个字段：

```text
date,dataset_type,asset_code,asset_name,metric_name,metric_value
```

字段说明：

| 字段 | 说明 |
|---|---|
| `date` | 日期，建议使用 `YYYY-MM-DD` |
| `dataset_type` | 数据集名称，例如 `core`、`instruments` |
| `asset_code` | 标的代码 |
| `asset_name` | 标的名称 |
| `metric_name` | 字段名 |
| `metric_value` | 字段值，数值和文本都以 CSV 字符串保存 |

终端默认需要以下 `metric_name`：

| `metric_name` | 用途 |
|---|---|
| `capped_final_trend_score` | 趋势轴或颜色相关字段；duration-only 趋势成熟度分 |
| `state_name` | 趋势状态展示字段 |
| `monthly_trend` | 月频状态展示字段 |
| `weekly_trend` | 周频状态展示字段 |
| `daily_trend` | 日频状态展示字段 |
| `rs_score` | 横轴数值字段 |
| `current_relative_state` | 相对状态筛选和展示字段 |
| `funding_leverage_value` | 纵轴和资金数值展示字段 |
| `funding_signal_direction` | 资金方向筛选字段 |
| `leverage_velocity` | 杠杆速度展示字段 |
| `leverage_velocity_score` | 杠杆速度筛选和展示字段 |

`transition_score`、`raw_transition_score` 和 `transition_label` 可随 processed series 一起产出，
用于后续交易机会筛选；当前终端主页面不读取或展示这些 transition 字段。

示例：

```csv
date,dataset_type,asset_code,asset_name,metric_name,metric_value
2026-06-18,core,SPX,S&P 500,capped_final_trend_score,72.5
2026-06-18,core,SPX,S&P 500,state_name,example_state
2026-06-18,core,SPX,S&P 500,monthly_trend,up
2026-06-18,core,SPX,S&P 500,weekly_trend,up
2026-06-18,core,SPX,S&P 500,daily_trend,neutral
2026-06-18,core,SPX,S&P 500,rs_score,64.2
2026-06-18,core,SPX,S&P 500,current_relative_state,Lead
2026-06-18,core,SPX,S&P 500,funding_leverage_value,58.1
2026-06-18,core,SPX,S&P 500,funding_signal_direction,long_candidate
2026-06-18,core,SPX,S&P 500,leverage_velocity,3.4
2026-06-18,core,SPX,S&P 500,leverage_velocity_score,81.0
```

`data/` 属于本地运行数据，默认不提交到 Git。

## 启动终端

先构建前端：

```bash
cd frontend
npm run build
cd ..
```

启动一体化本地服务：

```bash
scripts/run_market_map_dashboard.sh
```

访问：

```text
http://127.0.0.1:8000
```

开发模式可以分开启动后端和前端：

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
cd frontend
npm run dev
```

Vite 开发服务默认运行在：

```text
http://127.0.0.1:5173
```

## API

本地服务默认运行在 `http://127.0.0.1:8000`。

| Endpoint | 说明 |
|---|---|
| `GET /api/health` | 服务健康检查 |
| `GET /api/config` | 终端配置 |
| `GET /api/dates` | 可用日期 |
| `GET /api/assets` | 资产元数据 |
| `GET /api/snapshot?date=YYYY-MM-DD` | 指定日期快照 |
| `GET /api/playback?start=YYYY-MM-DD&end=YYYY-MM-DD` | 日期区间回放帧 |

示例：

```bash
curl -s http://127.0.0.1:8000/api/health
curl -s http://127.0.0.1:8000/api/dates
curl -s "http://127.0.0.1:8000/api/snapshot?date=2026-06-18"
```

## 配置

默认配置文件是 `config.yaml`。终端相关配置主要位于：

```text
dashboard.market_map
```

常用配置项：

| 配置 | 说明 |
|---|---|
| `storage_root` | 本地数据根目录，默认 `data` |
| `dashboard.market_map.dataset_types` | 终端读取的数据集 |
| `dashboard.market_map.fields` | 终端字段映射 |
| `dashboard.market_map.size` | 图表点位大小范围 |
| `dashboard.market_map.colors` | 前端状态颜色 |
| `dashboard.market_map.symbols` | 不同数据集的图形符号 |

## 测试与构建

Python 测试：

```bash
.venv/bin/python3 -m pytest
```

前端测试与构建：

```bash
cd frontend
npm test
npm run build
```

## 目录结构

```text
backend/                 FastAPI 服务和 API schema
dashboard/               数据加载、配置映射和展示辅助代码
frontend/                React + Vite + ECharts 终端
src/                     本地数据处理相关 Python 模块
analyses/notebooks/      本地分析 notebook
examples/                示例文件
scripts/                 启动和本地运行脚本
tests/                   Python 单元测试与 API 合约测试
```
