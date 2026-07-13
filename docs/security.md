# Security Boundaries

## Secrets

- 不提交 ZSXQ cookie、`FRED_API_KEY`、其他 API token、GitHub token或个人会话文件。
- `config.yaml` 中的凭证字段保持为空；本机凭证通过未跟踪配置或环境提供。
- 日志、测试失败信息和浏览器 trace 不得包含凭证。

## Local service

- Dashboard 默认只监听 `127.0.0.1`。
- 远程访问应使用私有网络，不将开发服务直接暴露到公网。
- CORS 只允许本机 Vite 开发源。

## Dependency and CI policy

- 不在无关任务中升级依赖。
- 依赖变化必须包含 lockfile，并通过 `make check` 和适用的 E2E。
- GitHub `main` 应禁止直接 push 和 force-push，并要求 CI 通过后由人 review PR。

## Data handling

真实 `data/`、`state/` 和 `logs/` 被 Git 忽略。可提交 fixture 必须是最小、合成且不含
个人或供应商敏感信息的数据。

FRED 页面必须显示非背书声明；ICE BofA 顶层指数数据仅用于本地内部展示，不做发布、转售或再分发。
