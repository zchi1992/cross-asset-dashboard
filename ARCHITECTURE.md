# Cross Asset Dashboard Architecture

本文件是代码导航和依赖边界的入口。产品语义、字段定义和运行手册继续放在
[`docs/`](docs/index.md)。

## 数据流

```text
ZSXQ API / Excel
       |
       v
src/zsxq_pipeline  -> data/raw
       |
       v
data/series/{core,instruments}
       |
       v
src/zsxq_pipeline/signals
       |
       v
data/processed/series/{core,instruments}
       |
       v
dashboard/data_loader.py
       |
       v
backend/app/data_service.py -> FastAPI /api/*
       |
       v
frontend React + ECharts
```

宏观地图使用与资产横截面隔离的数据流：

```text
US Treasury / ECB / ChinaBond / Japan MOF / BoE / FRED / OFR
       |
       v
src/macro_pipeline -> data/{raw,processed}/macro
       |
       v
dashboard/macro_loader.py -> backend /api/macro/* -> frontend 宏观地图
```

宏观来源失败不改变资产 `/api/ready`；宏观数据由 `/api/macro/ready` 独立报告。

运行时 `data/` 是本机数据，不进入 Git。测试和浏览器验证改用
`tests/fixtures/dashboard/` 中的最小 processed-series 数据。

## 依赖方向

允许的主要方向：

```text
src/zsxq_pipeline <- dashboard <- backend <- frontend HTTP client
```

- `src/zsxq_pipeline` 和 `src/macro_pipeline` 不得依赖 `dashboard` 或 `backend`。
- `dashboard` 不得依赖 `backend`。
- `backend` 仅允许 `backend/app/data_service.py` 通过
  `dashboard.config` 和 `dashboard.data_loader` 读取 dashboard 数据层。
- `frontend` 只能通过 `/api/*` 契约访问后端，不读取本机数据文件。

这些规则由 `tests/test_architecture.py` 强制验证。

## 配置边界

- 正常运行默认读取仓库根目录 `config.yaml`。
- `CROSS_ASSET_CONFIG_PATH` 可为测试或独立实例指定另一份配置。
- `backend.app.main.create_app(config_path=None)` 是后端实例化入口。
- 配置文件继续保持 JSON 兼容格式；相对存储路径以配置文件所在目录解析。

## 可观测边界

- `/api/health` 只表示 Web 进程存活。
- `/api/ready` 验证 processed data 是否可生成日期和资产。
- API 请求日志使用 JSON 行，包含 request ID、路径、状态和耗时。
- 浏览器回归的 trace、截图和视频只在失败时保留。

## 进一步阅读

- [Dashboard 产品行为](docs/product/dashboard.md)
- [数据与 API 契约](docs/data-contracts.md)
- [测试策略](docs/testing.md)
- [可靠性](docs/reliability.md)
- [安全边界](docs/security.md)
