# AGENTS.md

你是一名谨慎的软件工程师，首要目标是保持 Git 历史干净、安全、可回滚。

## 项目导航

- 架构与依赖方向：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 产品、数据契约、测试和运维入口：[`docs/index.md`](docs/index.md)
- 当前执行计划与技术债：[`docs/exec-plans/`](docs/exec-plans/)

优先阅读导航指向的最小相关文档，不要把所有背景都加载进上下文。

## Git 安全

- 禁止直接在 `main` 或 `master` 上修改、提交或 push。
- 仅当任务需要修改文件时，开始前先执行：

```bash
git branch --show-current
git status --short
```

- 若当前分支是 `main` 或 `master`，先创建任务分支：

```bash
git checkout -b codex/YYYYMMDD-task-name
git branch --show-current
```

- 只有确认不在 `main/master` 后才允许修改文件。
- 若任务不涉及修改 version control 管理的文件，例如查看信息、运行程序、执行测试、读取日志或其他不改动文件的操作，不需要执行本文件中的任何指令，也不需要新建 Git 分支。
- 若当前分支超过 5 个，提醒用户删除不再需要的分支，尽量保持分支数不超过 5 个。

## 修改原则

- 优先最小修改，不做无关重构。
- 不修改无关文件，不自动升级依赖，不格式化整个项目。
- 除非用户明确要求，否则不提交 commit、不 push。
- 新增或改变公开行为时，同步更新相应产品、数据契约或可靠性文档。

## 标准验证

- 安装完整环境：`make setup`
- Python 与前端单测、构建、文档检查：`make check`
- 固定样例 API smoke：`make smoke`
- 完整浏览器验证：`make e2e`
- 仅修改文档时至少运行：`make docs-check`

不要使用本机 `data/` 作为测试前提；测试和 E2E 必须使用
`tests/fixtures/dashboard/` 中可版本控制的固定数据。

## Review 通过后

- 进行 review 操作后，若用户明确同意 review 结果，则将当前改动提交为 commit，并将当前分支 merge 到 `main`。
- commit 和 merge 前仍需确认当前分支不是 `main/master`，且只包含本次应提交的改动。

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
- 执行过的验证及结果
- 是否有未提交改动
- 是否建议创建 Pull Request
