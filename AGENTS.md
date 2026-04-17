# 项目说明

## 项目目标

这个目录用于搭建一个面向 PDF 数学题的模型评测平台。

当前仓库已经调整为单仓结构：

- `backend/`：现有 FastAPI 后端
- `frontend/`：预留给后续前端页面

当前目标已经调整为：

- 从 PostgreSQL 读取题目
- 调用已配置的被测模型生成答案
- 再调用独立的校验模型，对被测模型回复和标准答案进行判分
- 将判分结果、模型原始回复、校验模型评价写回数据库

长期目标仍然是把这里演进成一个平台化后端，而不是一次性的脚本工程。

## 新窗口先读什么

如果在新的窗口打开这个项目，建议按下面顺序阅读：

1. [PROJECT_STATUS.md](/D:/AAAproject/benchmark/backend/PROJECT_STATUS.md)
2. [app/main.py](/D:/AAAproject/benchmark/backend/app/main.py)
3. [app/core/config.py](/D:/AAAproject/benchmark/backend/app/core/config.py)
4. [scripts/migrate_eval_results_add_attempt_metadata.py](/D:/AAAproject/benchmark/backend/scripts/migrate_eval_results_add_attempt_metadata.py)
5. 数据库里的 `questions`、`eval_models`、`eval_results` 三张表结构

## 当前技术方向

后端从一开始就按 `FastAPI` 项目来搭建。

当前确定的技术栈：

- `FastAPI`
- `Uvicorn`
- `SQLAlchemy 2`
- `psycopg`
- `Alembic`
- `Pydantic + pydantic-settings`
- `httpx`
- `Redis + Celery`
- `pytest`

不要再引入第二个 Web 框架。

## 当前范围约束

- 代码只在 `D:\\AAAproject\\benchmark` 内实现。
- 当前后端代码统一放在 `D:\\AAAproject\\benchmark\\backend`。
- 被测模型只允许使用 `content_images` 作为图片输入。
- 校验模型只允许接收：被测模型回复、标准答案文本、标准答案图片。
- 不要把 `analysis_images` 传给任何模型。
- 校验模型配置放在环境变量中管理。
- 不要把 API Key 或长期密钥写进提交到仓库的代码和文档里。

## 数据库说明

当前核心表有：

- `questions`
- `eval_models`
- `eval_results`

`eval_results` 当前每次 attempt 关注的字段包括：

- 判分结果
- 模型原始输出
- 校验模型评价
- 错误信息
- 完成时间

## 当前项目结构

目前已经有这些核心目录：

- `backend/app/`：FastAPI 应用代码
- `backend/alembic/`：数据库迁移骨架
- `backend/scripts/`：一次性或运维类脚本
- `backend/images/`：题目相关图片
- `frontend/`：预留给后续前端

当前已经落地的基础模块包括：

- 应用入口：`backend/app/main.py`
- 配置层：`backend/app/core/config.py`
- 数据库层：`backend/app/db/`
- ORM 模型：`backend/app/models/`
- 健康检查接口：`backend/app/api/routes/health.py`
- Celery 入口与任务占位：`backend/app/celery_app.py`、`backend/app/tasks/`

## 协作要求

- 文档保持简洁、可交接、可更新。
- 当优先级或完成状态变化时，更新 [PROJECT_STATUS.md](/D:/AAAproject/benchmark/backend/PROJECT_STATUS.md)。
- 优先建设稳定项目结构，不要堆积一次性脚本。
- 交接文档写“当前状态”，不要写流水账。
