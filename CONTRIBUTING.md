# Contributing to sufe-cli

感谢您对 sufe-cli 的关注！本文档将帮助您快速了解如何参与项目开发。

## 前置要求

在开始之前，请确保已安装以下工具：

- **Git** — 版本控制（[安装指南](https://git-scm.com/downloads)）
- **just** — 任务运行器（[安装指南](https://github.com/casey/just)）

## 开发环境

本项目使用以下工具链：

- **Python** >= 3.12
- **uv** — Python 包管理器
- **lefthook** — Git 钩子管理器

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/ChengJiale150/sufe-cli.git
cd sufe-cli

# 2. 初始化开发环境（安装 uv、lefthook，同步依赖）
just init

# 3. 安装可编辑模式
just install

# 4. 验证安装
sufe --version
```

## 开发规范

项目的架构设计、全局约定、源码风格、测试规范及开发工作流详见 [`AGENTS.md`](./AGENTS.md)。

参与开发前请务必阅读该文档，核心要点如下：

- **异常处理**：所有业务异常继承 `SufeCliError`，命令层使用 `@cli_error_boundary`
- **网络请求**：优先使用 `network.request_with_refresh()` 与 `DomainSessionSpec`
- **测试原则**：仅锁定关键语义，不追求覆盖率
- **代码提交**：提交前必须运行 `just check`，严禁未通过即提交
- **Skill 同步**：新增/修改 CLI 命令时，同步更新 `skills/` 下对应的 `SKILL.md`

## 新增业务模块

若您需要新增一个业务命令（如 `sufe library`）：

1. 在 `src/sufe_cli/commands/` 下创建子目录（如 `library/`）
2. 实现业务命令，使用 `@cli_error_boundary` 装饰器统一错误处理
3. 在 `src/sufe_cli/cli.py` 中注册子命令：`app.add_typer(library_app, name="library")`
4. 在 `skills/` 下创建对应的 `sufe-library/SKILL.md`
5. 在 `tests/commands/library/` 下编写关键语义测试
6. 更新 `README.md` 的功能概览和指令示例

## 提交 Pull Request

1. 确保分支基于最新的 `main`
2. 填写 PR 模板，说明变更摘要和测试方式
3. 确认 `just check` 全部通过
4. 等待维护者 review

## 代码审查

维护者会关注：
- 是否遵循项目架构和代码风格
- 是否同步更新了 Skill 文档
- 测试是否聚焦关键语义
- `just check` 是否通过

## 许可证

通过向本项目提交代码，您同意将您的贡献在 [MIT 许可证](LICENSE) 下发布。
