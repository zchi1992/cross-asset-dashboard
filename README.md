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

4. 轮询知识星球：

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

5. 回填历史数据（默认从 2026-05-08 开始）：

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

- 若环境可用 `pandas + pyarrow`，资产序列优先写为 `parquet`
- 当前仓库环境未安装这些依赖，因此会自动回退为 `csv`

## 当前实现范围

- 已实现：配置、筛选、样例 Excel 解析、英文指标映射、分目录时序汇总、下载元数据记录、会话存储、远端客户端骨架
- 未验证：真实知识星球接口字段形状和下载 URL 细节，需要你填入有效 `cookie` 后联调
