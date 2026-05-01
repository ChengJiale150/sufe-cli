---
name: sufe-canvas
description: SUFE Canvas 学习平台技能。当用户提及查看课程、作业、作业提交状态、成绩时，请务必触发此技能
---

# Sufe CLI - Canvas 技能

**⚠️ 重要提示：在执行本技能中的任何命令前，请务必先参考并触发 `sufe-base` 技能，以确保 CLI 环境已正确就绪并获取了有效的用户认证 (Cookie)。**

本技能介绍如何使用 `sufe canvas` 命令组来查询上海财经大学 Canvas 学习平台中的课程与作业信息。

## 1. 核心概念

- **当前课程**: 用户在 Canvas Dashboard 上星标收藏的课程，通常是当前学期正在关注的主要课程。
- **所有课程**: 用户参与的全部课程记录，包含已结课、隐藏及未收藏的课程。
- **作业**: 课程中的各类作业（assignment），包含截止时间、总分等信息。
- **提交状态**: 每个作业对应的提交记录，包含是否已提交、提交时间、得分等。

## 2. 指令与说明

| 指令 | 说明 |
|---|---|
| `sufe canvas course list` | **查看当前课程**：获取用户在 Dashboard 上收藏的课程列表（即当前关注的课程） |
| `sufe canvas course all` | **查看所有课程**：获取用户参与的全部课程历史记录（含已结课），支持排序 |
| `sufe canvas assignment list --course-id <id>` | **查看课程作业及提交状态**：获取指定课程的所有作业及对应的提交/评分状态 |

## 3. 课程查询的选择

- 当用户提及**"当前课程"**、**"这学期课程"**或**"我的课程"**时，优先使用 `sufe canvas course list`。
- 当用户提及**"所有课程"**、**"历史课程"**、**"以前学过的课程"**或需要查看**已结课**时，使用 `sufe canvas course all`。
- `course list` 返回的课程是 `course all` 的子集，前者仅包含用户主动收藏的课程。

## 4. 示例工作流

当用户要求查看课程作业时，推荐的工作流如下：

1. **获取当前课程**：
   ```bash
   sufe canvas course list
   ```
   输出示例：
   ```json
   [
     {
       "id": 40442,
       "name": "深度学习（0875）",
       "workflow_state": "available",
       "created_at": "2026-02-25T04:03:12Z",
       "roles": ["TaEnrollment"]
     }
   ]
   ```

   如需查看所有历史课程：
   ```bash
   sufe canvas course all
   # 或按创建时间降序排列
   sufe canvas course all --sort created_at --order desc
   ```

2. **查看课程作业**：
   使用获取到的课程 ID 查询作业详情：
   ```bash
   sufe canvas assignment list --course-id 40442
   ```
   输出示例：
   ```json
   [
     {
       "id": 30662,
       "name": "Homework 2",
       "due_at": "2025-11-02T14:00:00Z",
       "points_possible": 140,
       "grade": "100",
       "submitted_at": "2025-10-12T09:47:00Z"
     }
   ]
   ```

3. **处理异常**：
   如果命令提示登录状态已过期，请查阅 `sufe-base` 并引导用户运行 `sufe auth` 重新获取门户状态。业务域 Cookie 会在请求时自动静默刷新。
