# Technical Debt

| 项目 | 影响 | 后续动作 |
|---|---|---|
| 前端主 bundle 约 1.30 MB | 首次下载和解析成本较高 | 评估 ECharts 按需引入和代码分割，建立独立预算后再设 CI gate |
| Python/TypeScript API 类型双写 | 契约可能漂移 | 评估从 OpenAPI 生成前端类型 |
| E2E 仅覆盖 Chromium | 浏览器差异未覆盖 | 出现实际兼容需求后再加入 WebKit |
| 尚无 traces/metrics 聚合 | 长期性能趋势不可查询 | 在轻量日志稳定后评估 OpenTelemetry |
| 文档新鲜度依赖行为修改同步 | 可能出现语义漂移 | 定期运行质量 review，将重复问题升级为检查 |
| npm registry 当前可能由本机配置改写 | 安装链路安全性和可复现性受影响 | CI 使用 HTTPS 默认 registry，并审计本机 npm 配置 |
