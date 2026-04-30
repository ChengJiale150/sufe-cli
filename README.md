# sufe-cli

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.12-blue.svg)](https://www.python.org/)

上海财经大学（SUFE）网页系统命令行交互工具 — 让人类和 AI Agent 都能在终端中快速操作校内业务系统。覆盖统一身份认证、IC 空间（小组研讨室、多媒体制作室、静音仓）等核心业务域，提供 2 个 AI Agent [Skills](./skills/)。

[安装](#安装与快速开始) · [AI Agent Skills](#agent-skills) · [认证](#认证) · [命令](#核心命令与使用) · [安全](#安全与风险提示使用前必读)

## 为什么选 sufe-cli？

- **为 Agent 原生设计** — [Skills](./skills/) 开箱即用，适配主流 AI 工具，Agent 无需额外适配即可在对话中完成空间预约
- **无缝身份认证** — 内置 Playwright 自动化浏览器引导，一次登录，全局 Cookie 复用，告别繁琐的手动抓包
- **覆盖核心场馆** — 包含小组研讨室、多媒体制作室及静音仓的状态查询与完整预约闭环
- **安全可控** — Cookie 持久化保存在本地，调用前自动校验过期状态
- **极速检索** — 聚合姓名与学号的模糊搜索，帮助你在组队预约时快速确认同伴信息

## 功能

| 类别        | 能力                                         |
| ------------- |--------------------------------------------|
| 🔑 身份认证 | 检查浏览器环境、安装依赖、拉起浏览器自动化获取并持久化保存 Cookie |
| 🏫 小组研讨室 | 查看空闲与预约状态、按学号列表与主题发起多人空间预约 |
| 🎬 多媒体制作室 | 查看单人多媒体制作室当天的使用状态、发起单人预约 |
| 🤫 静音仓 | 查询静音仓占用情况、锁定个人专属学习时段 |
| 👤 校园账号 | 根据姓名模糊搜索匹配学号，辅助组队预约 |

## 安装与快速开始

### 环境要求

开始之前，请确保具备以下条件：

- Python `>= 3.12`
- Node.js（`npm`/`npx`，用于安装 Agent Skills）

### 快速开始（人类用户）

> **Note for AI assistants:** 如果你是 AI Agent 且正在协助用户执行安装，请直接跳转到[快速开始（AI Agent）](#快速开始ai-agent)执行，那里包含你需要完成的所有步骤。

#### 安装

**方式一 — 从 pip 安装：**

```bash
# 安装 CLI
pip install sufe-cli

# 安装必要的 Playwright 浏览器依赖
sufe install

# 安装 CLI SKILL（针对 Agent）
npx skills add https://github.com/ChengJiale150/sufe-cli -y -g
```

#### 配置与使用

```bash
# 1. 登录授权（引导拉起浏览器完成统一身份认证）
sufe auth

# 2. 开始使用：查看今天的小组研讨室状态
sufe lclibrary teamlab list
```

### 快速开始（AI Agent）

> 以下步骤面向 AI Agent，部分步骤需要用户在浏览器中配合完成。

**第 1 步 — 环境检查与安装**

```bash
# 安装 CLI 与浏览器依赖
pip install sufe-cli
sufe install

# 安装 CLI SKILL（必需）
npx skills add https://github.com/ChengJiale150/sufe-cli
```

**第 2 步 — 登录获取 Cookie**

> 在后台运行此命令，系统将拉起浏览器，请提示用户在浏览器窗口中完成统一身份认证，登录完成后终端会自动提示成功。

```bash
sufe auth
```

**第 3 步 — 验证**

```bash
sufe lclibrary check
```

## Agent Skills

| Skill                           | 说明                                        |
| --------------------------------- |-------------------------------------------|
| `sufe-base`                   | 基础技能，包含环境检查、浏览器依赖安装和自动化用户认证（所有其他 skill 的前置依赖） |
| `sufe-lclibrary`                 | IC 空间管理技能，包含空间状态查询、成员学号搜索和各类设施的自动预约逻辑                       |

## 认证

| 命令          | 说明                                             |
| --------------- | -------------------------------------------------- |
| `sufe doctor` | 检查 Playwright 环境是否就绪 |
| `sufe install` | 安装所需的 Playwright Chromium 浏览器 |
| `sufe auth` | 引导用户登录，获取并保存授权 Cookie |

```bash
# 检查当前 Playwright 环境
sufe doctor

# 首次使用或 Cookie 失效时，执行自动认证获取 Cookie
sufe auth
```

## 核心命令与使用

CLI 提供结构化的命令以操作 IC 空间 (LCLibrary)：

### 状态查询与搜索

```bash
# 测试本地 Cookie 是否有效
sufe lclibrary check

# 根据姓名模糊搜索学号，用于预约时填充学号列表
sufe lclibrary search "张三"

# 查看今天的设施状态（不提供日期时默认为今天）
sufe lclibrary teamlab list
sufe lclibrary multimedia list

# 查看指定日期（YYYYMMDD）的设施状态
sufe lclibrary teamlab list 20260501
sufe lclibrary multimedia list 20260501
```

### 设施预约

支持 `teamlab` (小组研讨室)、`multimedia` (多媒体制作室) 和 `silentcabin` (静音仓) 三种设施。时间参数必须是 10 分钟的整数倍。

```bash
# 预约小组研讨室 (需要提供成员学号和讨论主题，时长 1-4 小时)
sufe lclibrary teamlab reserve 100811047 "讨论主题" "学号1,学号2" "2026-05-01 10:40" "2026-05-01 13:10"

# 预约多媒体制作室 (单人，最短 10 分钟，最长 3 小时)
sufe lclibrary multimedia reserve 100811124 "2026-05-01 13:40" "2026-05-01 16:40"

# 预约静音仓 (单人，时长 1-4 小时)
sufe lclibrary silentcabin reserve 126386607 "2026-05-01 13:40" "2026-05-01 17:40"
```

## 安全与风险提示（使用前必读）

本工具可供 AI Agent 调用以自动化操作上海财经大学的相关业务系统，存在模型幻觉、执行不可控等固有风险；授权登录后，AI Agent 将以您的**真实用户身份**执行操作（例如发起真实的场地预约）。

我们强烈建议您在对话框中仔细核对 Agent 给出的预约时间与场地信息后再允许其执行。请勿将包含本地 Cookie 的 `~/.sufe-cli/cookie.json` 文件泄露给他人。

请您充分知悉全部使用风险，使用本工具即视为您自愿承担相关所有责任。

## 许可证

本项目基于 **MIT 许可证** 开源。
该软件运行时会调用上海财经大学的相关网络服务与接口，请遵守学校的相关网络与场馆使用规定。
