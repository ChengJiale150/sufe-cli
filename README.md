<div align="center">

<!-- omit in toc -->

# 🎓 sufe-cli

<strong>一句话搞定 Canvas作业提交、成绩查询、研讨室预约 — 上财人自己的 AI 管家</strong>

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/59819763-cf93-40b5-a8b5-14b1b36429eb">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge&logo=open-source-initiative&logoColor=white)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.12-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyPI Version](https://img.shields.io/pypi/v/sufe-cli?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/sufe-cli/)
[![GitHub Stars](https://img.shields.io/github/stars/ChengJiale150/sufe-cli?style=for-the-badge&logo=github&logoColor=white&color=181717)](https://github.com/ChengJiale150/sufe-cli/stargazers)

</div>

## 📖 目录

- [🎯 为什么需要 sufe-cli？](#-为什么需要-sufe-cli)
- [✨ 功能概览](#-功能概览)
- [🚀 快速开始](#-快速开始)
- [🤖 Agent Skills](#-agent-skills)
- [📋 核心指令示例](#-核心指令示例)
- [⚠️ 安全与风险提示（使用前必读）](#️-安全与风险提示使用前必读)
- [📝 许可证](#-许可证)

## 🎯 为什么需要 sufe-cli？

上财门户的业务系统（如 Canvas、IC 空间、教务系统等）分散且操作繁琐，需要人工认证登陆并进行复杂的网站UI操作，这给 AI Agent 自动化操作带来了挑战。

**sufe-cli** 就是为了解决这个问题而开发的。它通过命令行将校内核心业务系统统一封装，让 AI Agent 能够直接操作这些系统，自动化完成空间预约、成绩查询、作业管理等任务，大幅提升日常校园事务的处理效率。

### 🔥 关键亮点

- 🤖 **Agent 原生设计** — 4 个 Skills 开箱即用，适配主流 AI Agent（如 Claude Code、Openclaw 等），无需额外适配即可在对话中完成空间预约
- 🔑 **无缝身份认证** — 内置身份认证系统，支持手动登录与配置账号密码自动登录，一次授权持久使用
- 📚 **覆盖核心场景** — 包含 Canvas、IC 空间预约、成绩查询、校园账号管理等核心业务场景，并在持续更新中

## ✨ 功能概览

| 类别 | 能力 |
| --- | --- |
| 🔑 身份认证 | 检查浏览器环境、安装依赖、手动或自动登录并持久化保存登录状态 |
| 📚 图书馆空间 | 查询与预约小组研讨室、多媒体制作室、静音仓 |
| 📊 成绩查询 | 查看各学期成绩汇总、全部课程成绩明细，支持按学期筛选 |
| 🎓 Canvas | 查看课程列表、查询课程作业及提交/评分状态 |
| 👤 校园账号 | 根据姓名模糊搜索匹配学号；查看当前登录用户信息 |

## 🚀 快速开始

### 环境要求

开始之前，请确保具备以下条件：

- Python `>= 3.12`
- Node.js（`npm`/`npx`，用于安装 Agent Skills）

### 安装

<details>

<summary>方式一: 使用 pip 安装</summary>

```bash
# 直接使用 pip 全局安装 sufe-cli
pip install sufe-cli

# 安装必要的运行时依赖
sufe install

# 安装 CLI SKILL（针对 Agent）
npx skills add https://github.com/ChengJiale150/sufe-cli -y -g
```

</details>

<details open>

<summary>方式二: 使用 uv 安装（推荐）</summary>

```bash
# 安装 uv
pip install uv

# 使用 uv tool 独立安装 sufe-cli 与 Playwright
uv tool install sufe-cli
uv tool install playwright

# 安装必要的运行时依赖
sufe install

# 安装 CLI SKILL（针对 Agent）
npx skills add https://github.com/ChengJiale150/sufe-cli -y -g
```

</details>

### 验证安装

```bash
sufe --version
```

### 配置与使用

```bash
# 可选：设置自动登录模式（设置并保存账号密码）
sufe config set --mode auto --username <学号> --password <密码>

# 登录授权（默认引导启动浏览器完成统一身份认证）
sufe auth

# 检查当前状态
sufe doctor

# 查看自身基本信息
sufe me
```

## 🤖 Agent Skills

我们提供以下 4 个 Skill 方便Agent来了解上财门户系统与Sufe CLI的使用:

| Skill | 说明 |
| --- | --- |
| [`sufe-base`](./skills/sufe-base/SKILL.md) | 基础域，包含环境检查、浏览器依赖安装和用户认证 |
| [`sufe-lclibrary`](./skills/sufe-lclibrary/SKILL.md) | IC 空间管理域，包含各类设施状态查询与预约以及成员学号搜索 |
| [`sufe-score`](./skills/sufe-score/SKILL.md) | 成绩查询域，包含学期汇总、全部课程成绩明细、按学期筛选成绩 |
| [`sufe-canvas`](./skills/sufe-canvas/SKILL.md) | Canvas 平台域，包含课程列表查看、课程作业查询及提交 |

## 📋 核心指令示例

### 📚 空间设施预约查询与管理

支持 `teamlab`（小组研讨室）、`multimedia`（多媒体制作室）和 `silentcabin`（静音仓）三种设施，下面是预约小组研讨室的示例：

```bash
# 查看今天小组研讨室的预约状态
sufe lclibrary teamlab list

# 根据姓名搜索其他组员的学号
sufe lclibrary search <姓名>

# 预约小组研讨室（需要提供至少两名成员学号）
sufe lclibrary teamlab reserve <设施ID> <讨论主题> <成员学号1,成员学号2> <开始时间> <结束时间>
```

### 📊 学业成绩查询

```bash
# 查看各学期成绩汇总（门数、平均成绩、总学分、平均绩点）
sufe score summary

# 查看全部课程成绩明细
sufe score list

# 查看指定学期的课程成绩
sufe score list --semester "2025-2026 1"
```

### 🎓 Canvas 课程与作业

```bash
# 查看当前课程列表
sufe canvas course list

# 查看指定课程的所有作业
sufe canvas assignment list <课程ID>

# 查看指定作业的具体信息
sufe canvas assignment detail <课程ID> <作业ID>

# 下载指定文件
sufe canvas file download <文件ID>

# 提交指定作业（支持多个文件）
sufe canvas assignment submit <课程ID> <作业ID> --file <文件路径>
```

## ⚠️ 安全与风险提示（使用前必读）

> ⚠️ **警告**
>
> 本工具可供 AI Agent 调用以自动化操作上海财经大学的相关业务系统，LLM 存在幻觉、执行不可控等固有风险；授权登录后，AI Agent 将以您的**真实用户身份**执行操作（例如发起预约、提交作业等）。我们强烈建议您仔细核对 Agent 待执行的操作后再允许其执行。
>
> 请勿将包含本地登录状态的 `~/.sufe-cli/state.json` 或包含账号密码的 `~/.sufe-cli/auth.json` 文件泄露给他人。
>
> 请您充分知悉全部使用风险，使用本工具即视为您**自愿**承担相关所有责任。

## 📝 许可证

本项目基于 **MIT 许可证** 开源。
该软件运行时会调用上海财经大学的相关网络服务与接口，请遵守学校的相关网络与场馆使用规定。

---

<div align="center">

**如果这个项目对您有帮助，请给我们一个 ⭐️**

Made with ❤️ by [ChengJiale150](https://github.com/ChengJiale150)

</div>
