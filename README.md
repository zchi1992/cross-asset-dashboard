# Cross Asset Dashboard

本项目是一套本地跨资产观察终端：同步原始数据并解析为资产级 long-format 序列，计算趋势、
相对强度和资金行为派生指标，并通过 FastAPI + React/ECharts 提供可回放的 Local Asset
Terminal。

## 当前能力

- 原始数据同步：初始化本地会话、单次轮询、后台 worker、失败下载重试、历史数据回填。
- Excel 解析与归档：按日期保存原始文件，解析核心数据集和押注工具数据集。
- 标准化序列存储：生成 `data/series/{core,instruments}/` 下的资产 long-format CSV。
- 派生指标构建：生成 `data/processed/series/{core,instruments}/`，包含趋势评分、相对比价评分和资金领先评分。
- Local Asset Terminal：通过散点图查看资产强弱、资金状态、杠杆速度、候选标签、时间回放和资产详情。
- 后端 API：提供健康检查、配置、日期、资产列表、单日快照和全历史回放接口。
- Notebook 分析：`analyses/notebooks/` 保存可版本管理的 Python 分析 notebook。
- macOS 自动运行：提供 `launchd` 配置，在工作日定时执行日常轮询。

## 快速开始

### 1. 安装 Python 依赖

```bash
python3 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
```

如本机使用 `uv` 管理 Python，也可以用项目虚拟环境中的 Python 执行后续命令。

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 初始化数据会话

```bash
.venv/bin/python3 zsxq.py auth init
```

命令会提示输入本地数据会话信息，并保存到 `state/session.json`。

### 4. 生成本地数据

用样例文件验证解析和派生指标：

```bash
.venv/bin/python3 zsxq.py reparse examples
```

同步原始数据：

```bash
.venv/bin/python3 zsxq.py poll once
```

回填历史原始数据，默认从 `2026-05-08` 开始：

```bash
.venv/bin/python3 zsxq.py backfill history
.venv/bin/python3 zsxq.py backfill history --since 2026-05-08 --max-pages 100
```

重试失败下载：

```bash
.venv/bin/python3 zsxq.py retry failed-downloads
```

### 5. 启动终端

构建前端并启动一体化本地服务：

```bash
cd frontend && npm run build && cd ..
scripts/run_market_map_dashboard.sh
```

访问：

```text
http://127.0.0.1:8000
```

开发模式可以分开启动后端和 Vite：

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

## 数据流

```text
原始数据
  -> data/raw/YYYY-MM-DD/*.xlsx
  -> data/series/core/*.csv
  -> data/series/instruments/*.csv
  -> data/processed/series/core/*.csv
  -> data/processed/series/instruments/*.csv
  -> FastAPI API
  -> React Local Asset Terminal
```

原始和加工后的资产序列都采用 long format：

```text
date,dataset_type,asset_code,asset_name,metric_name,metric_value
```

`data/`、`state/`、`logs/` 和前端构建产物属于本地运行状态，默认不提交到 Git。

## 派生指标

派生指标入口位于 `src/zsxq_pipeline/signals/processed_series.py`：

```python
from pathlib import Path

from src.zsxq_pipeline.signals import build_processed_series_with_trend_scores

build_processed_series_with_trend_scores(Path("data"))
```

### 趋势评分

实现位置：`src/zsxq_pipeline/signals/trend_score.py`

- 输入：日、周、月趋势及持续时间。
- 趋势归一：`up`、`neutral`、`down`。
- 权重：月线 `3`、周线 `2`、日线 `1`。
- 输出：趋势组合、中文趋势状态、持续时间成熟度、当前趋势分、变化分和总趋势分。

### 相对比价评分

实现位置：`src/zsxq_pipeline/signals/relative_strength.py`

- 输入：`early_reversal`、`strength_momentum`、`relative_strength`、当前/此前比价状态及持续时间。
- 状态归一：`Lead`、`Weakening`、`Improving`、`Lag`。
- 输出：`rs_score`、状态切换、切换基础分、新鲜度因子、前状态成熟度等。

### 资金领先评分

实现位置：`src/zsxq_pipeline/signals/funding_lead_score.py`

- 输入：当前杠杆资金状态、持续时间、杠杆资金数值及可选的日变化。
- 计算：1/5/10 日杠杆速度、速度分位、成熟度、长短方向资金分。
- 输出：`funding_score`、`leverage_velocity_score`、信号方向、强度、排名和分桶。

## Local Asset Terminal

终端前端位于 `frontend/src/`，后端 API 位于 `backend/app/`。主界面支持：

- 资产类别切换：`core` / `instruments`。
- 资金状态筛选：`Leveraging` / `Deleveraging`。
- 相对强度状态筛选：`Lag`、`Weakening`、`Improving`、`Lead`。
- 杠杆速度筛选：全部、快速加杠杆、快速去杠杆、活跃。
- 资产代码或名称搜索。
- 时间轴回放、播放速度控制、跳到首日/前日/后日/最新日。
- 点击资产查看详情、趋势历史、候选标签和指标轨迹。

后端会挂载 `frontend/dist`，因此生产式本地访问只需要启动 FastAPI 服务。

## API

本地服务默认运行在 `http://127.0.0.1:8000`。

| Endpoint | 说明 |
|---|---|
| `GET /api/health` | 服务健康检查 |
| `GET /api/config` | 终端筛选、分数范围和回放配置 |
| `GET /api/dates` | 可用交易日期 |
| `GET /api/assets` | 最新资产元数据 |
| `GET /api/snapshot?date=YYYY-MM-DD` | 指定日期资产快照 |
| `GET /api/playback?start=YYYY-MM-DD&end=YYYY-MM-DD` | 日期区间回放帧 |

示例：

```bash
curl -s http://127.0.0.1:8000/api/health
curl -s http://127.0.0.1:8000/api/dates
curl -s "http://127.0.0.1:8000/api/snapshot?date=2026-06-18"
```

## 配置

默认配置文件是 `config.yaml`。主要配置项包括：

- `storage_root`：数据根目录，默认 `data`。
- `filename_filter`：原始数据文件名匹配规则。
- `market_map.dataset_types`：终端读取的数据集，默认 `core` 和 `instruments`。
- `market_map.fields`：终端所需指标字段映射。
- `market_map.thresholds`：多头/空头候选标签阈值。
- `poll_interval_seconds`：worker 轮询间隔。

## 自动运行

安装 macOS `launchd` 定时任务：

```bash
scripts/install_launchd.sh
```

它会加载 `com.chizhi.zsxq.daily-poll`，在北京时间工作日 18:00 执行
`scripts/run_daily_poll.sh`。日志写入：

- `logs/daily-poll.out.log`
- `logs/daily-poll.err.log`

卸载：

```bash
scripts/uninstall_launchd.sh
```

## Notebook 分析

分析 notebook 放在 `analyses/notebooks/`。当前包含：

- `relative_state_turning_points.ipynb`：分析早期转折、强度动量、相对强度与当前比价状态变化的关系。

Notebook 读取本地 `data/processed/series/`，因此可以版本管理分析逻辑，而不提交本地数据。

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

常用后端冒烟检查：

```bash
curl -s http://127.0.0.1:8000/api/health
curl -s http://127.0.0.1:8000/api/config
curl -s http://127.0.0.1:8000/api/dates
```

## 目录结构

```text
backend/                 FastAPI 服务和 API schema
dashboard/               终端数据装载、过滤、评分规则和旧版绘图辅助
frontend/                React + Vite + ECharts Local Asset Terminal
src/zsxq_pipeline/       原始数据同步、解析、存储和派生指标流水线
analyses/notebooks/      版本管理的 Python 分析 notebook
examples/                本地解析样例 Excel
launchd/                 macOS launchd plist
scripts/                 启动、定时任务安装和日常运行脚本
tests/                   Python 单元测试与 API 合约测试
```

## 故障排查

- `401 Unauthorized`：检查 `state/session.json` 中的数据会话信息是否完整、有效。
- 终端没有数据：确认已经执行 `reparse`、`poll once` 或 `backfill history`，并存在
  `data/processed/series/{core,instruments}/*.csv`。
- 仪表盘数据看起来不是最新：先对照最新原始数据，再执行 `poll once` 或 `backfill history`。
- 移动仓库后数据异常：检查本地状态文件中是否还有旧绝对路径，必要时重新解析 raw 文件。
- 前端显示后端离线：确认 `scripts/run_market_map_dashboard.sh` 已启动，或后端开发服务运行在
  `127.0.0.1:8000`。
