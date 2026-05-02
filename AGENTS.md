# Sufe CLI 代理与开发指南

## 项目

一个基于 Python 编写的命令行工具（CLI），旨在通过终端快速与上海财经大学（SUFE）的网页系统进行交互。通过该工具，用户可以进行浏览器自动授权登录、获取并保存 Cookie，以及直接与相关系统的接口交互, 而无需手动操作。

### 架构结构

项目采用**三层源码架构 + 技能定义层**的组合设计：

```text
src/sufe_cli/
├── cli.py              # 主命令入口，注册全局命令与所有子命令组
├── config.py           # 应用路径配置（~/.sufe-cli/ 下的状态与认证文件）
├── runtime.py          # 全局 CLI 上下文（timeout、debug 等运行时参数）
├── errors.py           # 自定义异常体系（SufeCliError 及其子类）
├── cli_helpers.py      # CLI 错误边界装饰器，统一异常格式化与退出码
├── client/             # 认证与网络层
│   ├── auth/           # 浏览器认证流程
│   ├── state.py        # 解析 Playwright storage_state，提取 Cookie 与 Token
│   ├── network.py      # 浏览器风格请求头与通用域名会话管理
│   └── portal.py       # 门户 Token 换取用户身份信息
└── commands/           # 业务命令层
    ├── config.py       # 查看/设置认证配置
    ├── canvas/         # Canvas LMS 集成（课程、作业、文件）
    ├── lclibrary/      # IC 空间管理系统（研讨室/多媒体/静音仓预约）
    └── score/          # 教务成绩查询

skills/                 # AI Agent 技能定义层
├── sufe-base/          # 基础技能：环境检查、浏览器依赖安装、用户认证
├── sufe-canvas/        # Canvas 技能：课程查看、作业查询与提交
├── sufe-lclibrary/     # IC 空间技能：设施状态查询与预约
└── sufe-score/         # 成绩查询技能：学期汇总与课程明细
```

**核心层**：提供 CLI 框架、配置管理、异常处理和运行时上下文。  
**认证与网络层**：封装浏览器自动化、状态持久化和跨域 Cookie 自动刷新。  
**业务命令层**：实现具体业务逻辑，每个子目录对应一个 `sufe <command>` 子命令。  
**AI Agent 技能层**：位于 `skills/`，每个技能包含 `SKILL.md`，描述 Agent 可识别的命令集与工作流。新增业务命令时，需同步创建或更新对应的技能文档。

## 全局约定

### 认证状态与会话管理

- 登录状态保存在 `~/.sufe-cli/state.json`，由 Playwright `storage_state` 生成
- 业务模块**不应直接读取该文件**，应通过 `network.py` 的 `DomainSessionSpec` + `request_with_refresh` 获取自动刷新的 Cookie
- 若需要调用新域名 API，需在 `network.py` 中定义对应的 `DomainSessionSpec`

### 错误处理

- 所有业务异常必须继承 `SufeCliError`，命令层函数使用 `@cli_error_boundary` 装饰
- 错误信息通过抛出异常传递，**禁止在命令函数内直接调用 `typer.secho(..., fg=RED)` 打印错误后 return**
- 调试信息使用 `runtime.debug_log()`，仅在 `--debug` 模式下输出

### 网络请求模式

- 调用外部 API 时，优先使用 `network.request_with_refresh()`，它会自动处理 Cookie 过期与静默刷新
- 需要为每个目标域名定义 `DomainSessionSpec`（含 host、entry_url、cookie_names）
- 判断登录超时应传入 `is_login_timeout` 回调（通常是检查响应中是否包含特定重定向或错误码）

## 开发指南

### 环境管理

- 必须使用 `uv` 进行 Python 虚拟环境与依赖管理。
- 运行 Python 脚本或 CLI 时，请使用 `uv run`（例如：`uv run sufe --help`）；**请勿直接使用** `python` 或 `python3`。
- 新增依赖时，请使用 `uv add <package>`（例如：`uv add requests`）；**请勿直接手动编辑** `pyproject.toml` 文件。

### 源码风格

- 必须使用与 `mypy` 兼容的类型提示（Type Hints）。
- 请使用现代 Python (>=3.12) 语法，例如使用 `str | None` 替代 `Optional[str]`，使用 `list[str]` 替代 `List[str]`。
- 在涉及数据验证和配置架构解析时，应优先考虑使用 Pydantic。

### 测试规范

- **仅锁定关键语义**，不追求代码覆盖率或全面测试。
- 测试目标是为核心业务规则而不是网络请求或 CLI 命令本身。
- 避免为 CLI 终端输出、纯数据传递层或第三方库行为编写冗余测试。

## 开发工作流

任何功能迭代或缺陷修复均应遵循以下四步：

1. **调研** —— 阅读相关源码、`SKILL.md` 或外部文档，确认需求边界与已有实现。
2. **添加必要测试** —— 若改动涉及关键语义，先写或补充最小测试；若仅为配置或文档调整，可跳过。
3. **实现** —— 按源码风格完成修改，保持与现有代码库一致, 并同步更新 `skills/` 目录下对应的 `SKILL.md` 文档，确保技能描述与代码实现保持一致。编写或更新技能文档时，请参考 [`docs/skills.md`](./docs/skills.md) 中的规范。
4. **运行 `just check`** —— 执行格式化、静态检查、类型检查与测试套件，确保全部通过。

> **严禁**在 `just check` 未通过的情况下提交代码。

## 常用开发指令

我们使用 [`just`](./justfile) 作为任务运行器，常见开发命令如下：

| 命令 | 说明 |
|---|---|
| `just sync` | 同步所有依赖 |
| `just check` | 执行代码格式化、静态检查、类型检查与测试套件 |
| `just update <patch/minor/major>` | 更新版本号，自动提交并推送对应 git tag |
