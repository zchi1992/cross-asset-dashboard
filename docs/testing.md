# Testing and Validation

## 标准命令

```bash
make setup
make check
make smoke
make e2e
```

- `make check`：全量 Python 测试、Vitest、前端类型检查/构建、文档检查。
- `make smoke`：启动真实 uvicorn 进程，以 fixture 验证 readiness 和核心 API。
- `make e2e`：构建前端、启动 fixture dashboard，并运行 Chromium Playwright。
- `make docs-check`：只检查文档、链接和标准 Make target。

## 测试分层

- 纯计算：评分、过滤和数据映射。
- API 契约：通过 `create_app(fixture_config)` 实例化独立应用。
- 架构：AST 检查禁止的 Python 依赖方向。
- Smoke：真实 loopback HTTP，不使用系统代理。
- E2E：真实静态前端、FastAPI 和可版本控制数据。
- 宏观测试使用 `tests/fixtures/dashboard/processed/macro/` 的合成曲线与信用数据；不得把
  FRED、ICE、ChinaBond 或其他真实供应商值提交为 fixture。

Playwright 失败证据位于 `frontend/test-results/` 和
`frontend/playwright-report/`，这些目录不进入 Git。

## 完成标准

改变 dashboard、API、数据映射或启动方式时必须运行 `make check`。涉及页面交互时再运行
`make e2e`；涉及配置、数据加载或服务启动时再运行 `make smoke`。
