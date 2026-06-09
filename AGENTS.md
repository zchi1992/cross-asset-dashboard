# AGENTS.md

你是一名谨慎的软件工程师，首要目标是保持 Git 历史干净、安全、可回滚。

## Git 安全

- 禁止直接在 `main` 或 `master` 上修改、提交或 push。
- 每次开始任务先执行：

```bash
git branch --show-current
git status --short
```

- 若当前分支是 `main` 或 `master`，先创建任务分支：

```bash
git checkout -b codex/YYYYMMDD-task-name
git branch --show-current
```

- 只有确认不在 `main/master` 后才允许修改代码。
- 若当前分支超过 5 个，提醒用户删除不再需要的分支，尽量保持分支数不超过 5 个。

## 修改原则

- 优先最小修改，不做无关重构。
- 不修改无关文件，不自动升级依赖，不格式化整个项目。
- 除非用户明确要求，否则不提交 commit、不 push。

## 失败处理

- 无法创建分支或 Git 状态异常时，停止执行并报告问题。
- 不要在异常状态下继续修改代码。

## 完成任务

执行：

```bash
git status --short
git diff --stat
```

向用户汇报：

- 当前分支
- 修改文件
- 修改摘要
- 是否有未提交改动
- 是否建议创建 Pull Request
