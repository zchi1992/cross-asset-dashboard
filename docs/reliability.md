# Reliability and Observability

## 健康模型

- Liveness：`/api/health` 证明 FastAPI 能处理请求。
- Readiness：`/api/ready` 证明 processed data 能形成至少一个日期和一个资产。
- 页面可用性：由 Playwright 验证真实加载、筛选和播放路径。

仅看到 health `200` 不能断言页面可用；还要检查 readiness 和 `/api/playback`。

## 请求日志

每个请求输出一行 JSON：

- `event=http_request`
- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

日志不包含 query string、认证信息或配置内容。响应回传 `X-Request-ID`，用于关联浏览器
错误与后端日志。

## 数据与缓存

- rows 和 playback frames 按配置及 processed CSV 签名缓存。
- 文件修改时间或大小变化会创建新缓存项。
- 大于 1000 bytes 的响应由 GZipMiddleware 压缩。
- 缓存最多保留四个签名，避免本地长期进程无限增长。
- 宏观文件和 source manifest 使用独立签名缓存；单一来源失败时保留 last-good 数据并将
  `/api/macro/ready` 标记为 `degraded`，不清空其他来源，也不影响资产 readiness。
- `scripts/run_macro_poll.sh` 是一次性、带锁的宏观刷新入口；launchd 每天本地时间
  09:00 和 20:30 调用，stdout/stderr 写入 `logs/macro-poll.*.log`。

## 浏览器证据

Playwright 失败时保留 trace、截图和视频；成功运行不保留大体积证据。完整 traces/metrics
栈暂不属于第一阶段，记录在[技术债清单](exec-plans/tech-debt.md)。
