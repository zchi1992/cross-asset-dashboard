# Harness Engineering

## 目标

让干净 clone 在没有真实 `data/` 的情况下完成安装、测试、真实 HTTP smoke 和浏览器 E2E，
并让未来 agent 通过仓库导航找到产品、数据、验证和故障排查信息。

## 进度

- [x] Review 并合并 playback 缓存/GZip 基线。
- [x] 创建独立 Harness 分支。
- [x] 建立文档导航和机械检查。
- [x] 建立 fixture、app factory、readiness 和结构化请求日志。
- [x] 建立统一 Make target、Playwright 和 CI。
- [x] 添加仓库级 skills。
- [x] 完成 clean-clone 验收。
- [ ] 恢复 GitHub CLI 认证、推送 CI，并为 `main` 启用 PR/CI 保护规则。

## 决策

- 保持现有 REST 接口兼容，仅新增 `/api/ready`。
- 使用可提交的合成 processed-series fixture，不复制真实市场数据。
- 第一阶段采用轻量日志和 Playwright 证据，不加入完整遥测栈。
- bundle-size 警告登记技术债，不阻断首期交付。

## 最终验证

- 干净临时副本执行 `make setup` 成功。
- `make check`：45 项 Python 测试、4 项 Vitest、Vite 构建和文档检查通过。
- `make smoke`：fixture readiness、health、config、dates、assets 和 playback 通过。
- `make e2e`：2 项 Chromium 场景通过。

## 外部阻塞

本机 `gh auth status` 当前返回 `401 Bad credentials`，且 Harness 分支尚未获得提交/推送
授权。恢复认证并将 CI workflow 推送到远端后，才能配置和验证 `main` 保护规则；完成后再将
本计划移动到 `completed/`。
