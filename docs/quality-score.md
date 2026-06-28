# Quality Score

评分使用 `0–5`：`0` 表示缺失，`5` 表示可重复、机械强制且有回归证据。

| 领域 | 当前目标 | 证据 |
|---|---:|---|
| Python 计算与 API 测试 | 4 | `make check` |
| 前端单测与构建 | 4 | Vitest、TypeScript、Vite |
| 干净 clone 可复现性 | 4 | fixture、`make setup`、`make smoke` |
| 浏览器端到端验证 | 3 | Chromium Playwright |
| 架构约束 | 3 | `tests/test_architecture.py` |
| 文档可发现性 | 4 | `AGENTS.md` 导航、`make docs-check` |
| 可观测性 | 3 | readiness、JSON 请求日志、失败 trace |
| 安全与合并约束 | 3 | secrets 规则、CI、main 保护要求 |

每次 Harness 改造完成后更新本表和[技术债清单](exec-plans/tech-debt.md)。分数上升必须对应
可执行证据，不能只因为增加了文档。
