# Sufe CLI 代理与开发指南

## 项目

本项目 (`sufe-cli`) 是一个基于 Python 编写的命令行工具（CLI），旨在通过终端快速与上海财经大学（SUFE）的网页系统进行交互。通过该工具，用户可以进行浏览器自动授权登录、获取并保存 Cookie，以及直接与相关系统的接口交互, 而无需手动操作。

### 架构结构

项目的核心源码均位于 `src/sufe_cli/` 目录下，采用按业务模块划分的架构设计：

- `cli.py` 主命令入口，定义了基础的全局命令（如 `sufe doctor`, `sufe install`, `sufe auth` 等）。
- `config.py` 配置管理模块，使用 Pydantic 对本地保存的 Cookie（位于 `~/.sufe-cli/cookie.json`）等信息进行校验与加载。
- `commands/` 子命令目录，目前包含 `lclibrary` 业务组。
  - `lclibrary/` 包含与 IC 空间管理系统相关的核心子命令组。
- `utils/` 底层网络请求等通用辅助工具。
  - `network.py` 提供获取默认请求伪装头的功能，确保请求能够绕过基础的安全检测。

## 开发指南

### 环境管理

- 必须使用 `uv` 进行 Python 虚拟环境与依赖管理。
- 运行 Python 脚本或 CLI 时，请使用 `uv run`（例如：`uv run sufe --help`）；**请勿直接使用** `python` 或 `python3`。
- 新增依赖时，请使用 `uv add <package>`（例如：`uv add requests`）；**请勿直接手动编辑** `pyproject.toml` 文件。

### 源码风格

- 必须使用与 `mypy --strict` 兼容的严格类型提示（Type Hints）。
- 请使用现代 Python (>=3.12) 语法，例如使用 `str | None` 替代 `Optional[str]`，使用 `list[str]` 替代 `List[str]`。
- 在涉及数据验证和配置架构解析时，应优先考虑使用 Pydantic。
