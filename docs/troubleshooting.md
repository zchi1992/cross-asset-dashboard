# Troubleshooting

## 页面显示 Backend service is offline

1. 运行 `scripts/run_market_map_dashboard.sh`。
2. 使用 `curl --noproxy '*' http://127.0.0.1:8000/api/health` 检查进程。
3. 检查 `curl --noproxy '*' http://127.0.0.1:8000/api/ready`。
4. health 正常但 ready 为 503 时，检查 processed data，而不是重启前端。

## 页面长时间加载

依次检查 `/api/config`、`/api/dates`、`/api/assets` 和 `/api/playback`。playback 是最大
响应，优先查看其耗时、`content-encoding` 和 request ID 对应日志。

## 测试在本机通过但干净环境失败

- 确认测试使用 `tests/fixtures/dashboard/config.json`。
- 不要从测试读取根目录 `data/`。
- 运行 `make smoke` 验证真实 HTTP 路径。

## localhost 返回代理错误

本机代理可能拦截 loopback。诊断时使用 `curl --noproxy '*'`；smoke 脚本已禁用系统代理。

## 文档或架构检查失败

- `make docs-check` 会报告缺失文档、断链或 Make target。
- `make architecture-check` 会报告具体文件和被禁止的 import。
- 优先修复规则指出的边界，不要删除检查来绕过错误。
