# sufe-cli

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-%3E%3D3.12-blue.svg)](https://www.python.org/)

上海财经大学（SUFE）网页系统命令行交互工具 — 让人类和 AI Agent 都能在终端中快速操作校内业务系统。覆盖统一身份认证、IC 空间（小组研讨室、多媒体制作室、静音仓）、教务成绩查询等核心业务域，提供 3 个 AI Agent [Skills](./skills/)。

[安装](#安装与快速开始) · [AI Agent Skills](#agent-skills) · [认证](#认证) · [命令](#核心命令与使用) · [安全](#安全与风险提示使用前必读)

## 为什么选 sufe-cli？

- **为 Agent 原生设计** — [Skills](./skills/) 开箱即用，适配主流 AI 工具，Agent 无需额外适配即可在对话中完成空间预约
- **无缝身份认证** — 内置 Playwright 浏览器认证，支持手动登录与配置账号密码自动登录
- **覆盖核心场景** — 包含图书馆空间预约、成绩查询、校园账号管理等核心业务场景, 并在持续更新中

## 功能

| 类别        | 能力                                         |
| ------------- |--------------------------------------------|
| 🔑 身份认证 | 检查浏览器环境、安装依赖、手动或自动登录并持久化保存门户状态 |
| 📚 图书馆空间 | 查询与预约小组研讨室、多媒体制作室、静音仓（支持空闲状态查看、多人/单人预约） |
| 📊 成绩查询 | 查看各学期成绩汇总、全部课程成绩明细，支持按学期筛选 |
| 👤 校园账号 | 根据姓名模糊搜索匹配学号，辅助组队预约；查看当前登录用户信息 |

## 安装与快速开始

### 环境要求

开始之前，请确保具备以下条件：

- Python `>= 3.12`
- Node.js（`npm`/`npx`，用于安装 Agent Skills）

### 快速开始

#### 安装

**方式一 — 从 pip 安装：**

```bash
pip install sufe-cli

# 安装必要的 CLI 依赖
sufe install

# 安装 CLI SKILL（针对 Agent）
npx skills add https://github.com/ChengJiale150/sufe-cli -y -g
```

**方式二 — 使用 uv 安装 (推荐)：**

```bash
# 安装uv
pip install uv

# 使用 uv tool 独立安装 sufe-cli 与 Playwright
uv tool install sufe-cli
uv tool install playwright

# 安装必要的 CLI 依赖
sufe install

# 安装 CLI SKILL（针对 Agent）
npx skills add https://github.com/ChengJiale150/sufe-cli -y -g
```

#### 配置与使用

```bash
# 可选：设置自动登录模式（设置并保存账号密码）
sufe config set --mode auto --username 2023xxxxxx --password your-password

# 1. 登录授权（默认引导拉起浏览器完成统一身份认证）
sufe auth

# 2. 查看自身基本信息
sufe me

# 3a. 查看今天的小组研讨室状态
sufe lclibrary teamlab list

# 3b. 查看各学期成绩汇总
sufe score summary
```

## Agent Skills

| Skill                           | 说明                                        |
| --------------------------------- |-------------------------------------------|
| `sufe-base`                   | 基础技能，包含环境检查、浏览器依赖安装和用户认证 |
| `sufe-lclibrary`                 | IC 空间管理技能，包含空间状态查询、成员学号搜索和各类设施的自动预约逻辑                       |
| `sufe-score`                    | 成绩查询技能，包含学期汇总、全部课程成绩明细、按学期筛选成绩 |


## 核心命令与使用

CLI 提供结构化的命令以操作 IC 空间 (LCLibrary) 与教务成绩查询：

### 预约状态查询与搜索

```bash
# 查看今天小组研讨室的预约状态（不提供日期时默认为今天）
sufe lclibrary teamlab list

# 查看指定日期（YYYYMMDD）的小组研讨室预约状态
sufe lclibrary teamlab list 20260501
```

### 设施预约

支持 `teamlab` (小组研讨室)、`multimedia` (多媒体制作室) 和 `silentcabin` (静音仓) 三种设施。

```bash
# 根据姓名模糊搜索学号，用于预约时填充学号列表
sufe lclibrary search "张三"

# 预约小组研讨室 (需要提供成员学号和讨论主题，时长 1-4 小时)
sufe lclibrary teamlab reserve 100811047 "讨论主题" "学号1,学号2" "2026-05-01 10:40" "2026-05-01 13:10"

# 预约多媒体制作室 (单人，最短 10 分钟，最长 3 小时)
sufe lclibrary multimedia reserve 100811124 "2026-05-01 13:40" "2026-05-01 16:40"

# 预约静音仓 (单人，时长 1-4 小时)
sufe lclibrary silentcabin reserve 126386607 "2026-05-01 13:40" "2026-05-01 17:40"
```

### 成绩查询

```bash
# 查看各学期成绩汇总（门数、平均成绩、总学分、平均绩点）
sufe score summary

# 查看全部课程成绩明细
sufe score list

# 查看指定学期的课程成绩
sufe score list --semester "2025-2026 1"
```

## 安全与风险提示（使用前必读）

本工具可供 AI Agent 调用以自动化操作上海财经大学的相关业务系统，存在模型幻觉、执行不可控等固有风险；授权登录后，AI Agent 将以您的**真实用户身份**执行操作（例如发起真实的场地预约）。

我们强烈建议您在对话框中仔细核对 Agent 给出的预约时间与场地信息后再允许其执行。请勿将包含本地登录状态的 `~/.sufe-cli/state.json`，或包含明文账号密码的 `~/.sufe-cli/auth.json` 文件泄露给他人。

请您充分知悉全部使用风险，使用本工具即视为您自愿承担相关所有责任。

## 许可证

本项目基于 **MIT 许可证** 开源。
该软件运行时会调用上海财经大学的相关网络服务与接口，请遵守学校的相关网络与场馆使用规定。
