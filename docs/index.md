# Repository Knowledge Map

从当前任务最相关的文档开始，不要把本目录当成一次性阅读的长手册。

## 核心入口

- [架构与依赖方向](../ARCHITECTURE.md)
- [Dashboard 产品行为](product/dashboard.md)
- [数据与 API 契约](data-contracts.md)
- [测试与标准命令](testing.md)
- [可靠性与可观测性](reliability.md)
- [安全边界](security.md)
- [故障排查](troubleshooting.md)
- [质量评分](quality-score.md)

## 计划与持续治理

- [执行计划目录](exec-plans/)
- [技术债清单](exec-plans/tech-debt.md)

文档链接和标准 Make target 由 `make docs-check` 验证。行为变化必须同步更新对应
文档；反复出现的 review 问题应升级为测试、架构检查或明确规则。
