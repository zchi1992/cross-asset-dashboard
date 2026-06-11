# 知识星球数据采集

本项目实现一条本地数据流水线：

- 按文件名筛选知识星球附件
- 下载并按日期归档原始 Excel
- 解析首个工作表
- 将指标映射成英文 `metric_name`
- 分别写入 `data/series/core/` 和 `data/series/instruments/`

## 快速开始

0. 创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
```

1. 初始化会话配置：

```bash
.venv/bin/python3 zsxq.py auth init
```

2. 用本地样例验证解析和时序汇总：

```bash
.venv/bin/python3 zsxq.py reparse examples
```

3. 查看生成结果：

```bash
find data -maxdepth 3 -type f | sort
```

4. 启动 Local Asset Terminal：

```bash
cd frontend && npm install && npm run build && cd ..
scripts/run_market_map_dashboard.sh
```

本机浏览器访问：

```text
http://127.0.0.1:8000
```

如需开发模式，可分别启动后端和 Vite 前端：

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

5. 轮询知识星球：

```bash
.venv/bin/python3 zsxq.py poll once
.venv/bin/python3 zsxq.py worker run
```

## 自动运行

已提供 macOS `launchd` 配置，可在北京时间工作日每天 18:00 运行一次单次轮询：

```bash
scripts/install_launchd.sh
```

安装后会加载 `com.chizhi.zsxq.daily-poll`，实际执行 `scripts/run_daily_poll.sh`。日志写入：

- `logs/daily-poll.out.log`
- `logs/daily-poll.err.log`

如需取消自动运行：

```bash
scripts/uninstall_launchd.sh
```

6. 回填历史数据（默认从 2026-05-08 开始）：

```bash
.venv/bin/python3 zsxq.py backfill history
.venv/bin/python3 zsxq.py backfill history --since 2026-05-08 --max-pages 100
```

`backfill history` 会优先使用知识星球网页版的文件搜索接口，按 `filename_filter.include_patterns` 中的关键词检索历史附件，再下载符合条件的 `.xlsx/.xls` 文件。

## 配置

默认配置位于 `config.yaml`。当前环境未安装 YAML 解析库，因此该文件使用 JSON 兼容写法保存；文件扩展名依然是 `.yaml`，后续安装 `PyYAML` 后可无缝切换到普通 YAML 风格。

## 目录结构

- `data/raw/YYYY-MM-DD/`：原始 Excel 归档
- `data/series/core/`：核心数据集资产序列
- `data/series/instruments/`：押注工具资产序列

资产序列文件只保留以下列：

- `date`
- `dataset_type`
- `asset_code`
- `asset_name`
- `metric_name`
- `metric_value`

## 存储格式

- 资产序列默认写为 `csv`，避免运行环境安装额外依赖后改变输出格式
- `SeriesStore` 仍保留显式 `backend="parquet"` 能力，供后续需要时单独接入

## 派生指标计算

信号计算模块放在 `src/zsxq_pipeline/signals/`。当前已实现趋势评分计算，输入读取
`data/series/core/` 和 `data/series/instruments/` 中的每资产 long format 序列，输出到：

- `data/processed/series/core/`
- `data/processed/series/instruments/`

processed 文件仍采用现有 schema：

- `date`
- `dataset_type`
- `asset_code`
- `asset_name`
- `metric_name`
- `metric_value`

趋势评分会写入 `trend_combo`、`state_name`、`raw_current_score`、`duration_score`、
`raw_final_trend_score`、`capped_final_trend_score`、`transition_label` 等派生指标。
这些文件是通用 processed 资产序列，后续可以继续加入相对比价、资金流向等计算指标。

当前不新增 CLI 命令，可在 Python 中调用：

```python
from pathlib import Path

from src.zsxq_pipeline.signals import build_processed_series_with_trend_scores

build_processed_series_with_trend_scores(Path("data"))
```

批量构建时会跳过趋势字段不完整或为空的日期，避免单个脏日期阻断整批输出；纯计算函数
`calculate_trend_score_rows` 会对缺失字段和无法识别的趋势值抛出 `ValueError`，便于测试和调试。

## 当前实现范围

- 已实现：配置、筛选、样例 Excel 解析、英文指标映射、分目录时序汇总、下载元数据记录、会话存储、远端客户端骨架
- 未验证：真实知识星球接口字段形状和下载 URL 细节，需要你填入有效 `cookie` 后联调
