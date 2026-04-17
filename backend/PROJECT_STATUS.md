# 项目当前状态

## 项目概览

这个项目正在建设一个基于 PostgreSQL 的数学题模型评测后端平台。

当前评测流程已经调整为两阶段：

- 第一阶段：调用被测模型生成答案
- 第二阶段：调用独立的校验模型，根据被测模型回复和标准答案进行判分，并给出评价说明

当前整体方向仍然是基于 `FastAPI` 的后端项目。

当前仓库结构已调整为单仓：

- `backend/`：后端项目
- `frontend/`：平台前端控制台

## 当前数据库状态

- 目标数据库：`pdf_question_bank`
- 已确认核心表存在：`questions`、`eval_models`、`eval_results`
- 已确认当前数据量：`questions=136`、`eval_models=8`、`eval_results=1088`
- `eval_models` 仍作为被测模型配置来源
- 校验模型配置已迁移到 `backend/.env`
- `eval_models.api_style` 迁移脚本已补充，默认值为 `chat_completions`
- `eval_models.release_date` 迁移脚本已补充，用于记录模型发布时间

## 已完成事项

- 已搭建 FastAPI 项目骨架
- 已补充 SQLAlchemy 2 数据库连接与 ORM 模型
- 已补充健康检查、模型列表、概览接口
- 已补充本地同步批量评测脚本
- 已补充模型探活接口
- 已补充 payload 预览接口
- 已把被测模型输入约束为：只使用 `content_images`
- 已把评测流程改为“被测模型生成 + 校验模型判分”
- 已支持 `chat/completions` 与 `responses` 双协议调用
- 已支持通过 `eval_models.api_style` 和 `JUDGE_API_STYLE` 选择协议
- `payload-preview` 已改为返回最终 `request_url` 和最终 payload
- 已支持在 `eval_models.release_date` 记录模型发布时间
- 已完成后端目录下沉，当前后端统一位于 `backend/`
- 已搭建 `frontend/` 页面骨架并接入核心接口
- 前端已形成平台级控制台壳层，统一导航与页头信息，并优化左侧导航可读性
- 前端模型页已支持筛选、快速启停和批量 Probe
- 后端已支持批量评测任务创建、进度查询和取消
- 前端评测页已收敛为仅保留后端批量任务的工作台，手动题号与范围模式可覆盖单题场景，且已移除最近单题运行记录
- 前端概览页已收敛为运营看板，模型页已收敛为模型池控制面，评测页已收敛为执行工作台
- 前端已移除低价值说明卡片、页头状态卡片和侧栏底部约束区，整体页面高度与信息噪音已进一步收敛
- 前端左侧导航已支持桌面端收缩，结果页和比对抽屉可获得更大内容宽度
- 前端已按页面路由拆包，降低首页主包压力并为后续继续拆分结果页打基础
- 前端已升级为按依赖家族拆包：`react/react-dom`、`react-router`、`react-query`
- 后端已补充结果查询接口与按 attempt 清除生成数据 / 质检数据接口
- 后端已补充结果查询接口、按 attempt 清理数据接口，以及按 attempt 人工更改结果的 override 持久化字段与接口
- 前端已补充独立结果查询页，支持按题号、模型、轮次筛选，支持多状态组合筛选，支持三轮状态总览、单轮结果比对抽屉、人工更改结果、按轮清理数据和按当前查询顺序切换下一条结果
- 前端结果比对已支持 Markdown / LaTeX 渲染和图片预览，后端已提供 `backend/images` 的静态访问能力
- 已支持通过 `BACKEND_ACCESS_LOG` 关闭 Uvicorn access log，避免批量任务轮询日志刷屏
- 已统一后端开发日志输出为 UTF-8，避免 Windows 下中文日志乱码
- 已修复 judge 供应商异常导致整批任务中断的问题，单题失败后批量任务会继续执行
- 已支持解析 `responses` 事件流返回，并为 judge 请求增加有限重试以缓解上游瞬时断连
- 评测执行已解耦为 `仅生成`、`仅判分`、`生成并判分`
- 已将 `*_normalized_text` 语义替换为 `*_judge_feedback`
- 已补充针对已存 `response_text` 的 judge 回填脚本
- 已补充 judge service 相关测试

## 当前 `eval_results` 字段语义

每次 attempt 当前包含：

- `*_result`
- `*_result_override`
- `*_result_overridden_at`
- `*_response_text`
- `*_judge_feedback`
- `*_error`
- `*_finished_at`

其中：

- `*_response_text` 保存被测模型原始回复
- `*_judge_feedback` 保存校验模型的评价说明
- `*_result` 保存校验模型原始给出的 1 / 0 判分
- `*_result_override` 保存人工修正后的判分；结果查询页展示时优先使用 override 后的有效结果

## 当前可用接口与命令

接口：

- `/api/v1/health`
- `/api/v1/health/db`
- `/api/v1/models`
- `/api/v1/models/{model_id}`
- `PATCH /api/v1/models/{model_id}`
- `POST /api/v1/models/{model_id}/probe`
- `/api/v1/overview/questions`
- `/api/v1/overview/evaluations`
- `POST /api/v1/evaluations/preview`
- `POST /api/v1/evaluations/payload-preview`
- `POST /api/v1/evaluations/generate`
- `POST /api/v1/evaluations/judge`
- `POST /api/v1/evaluations/run`
- `GET /api/v1/evaluations/batch-jobs`
- `POST /api/v1/evaluations/batch-jobs`
- `GET /api/v1/evaluations/batch-jobs/{job_id}`
- `POST /api/v1/evaluations/batch-jobs/{job_id}/cancel`
- `GET /api/v1/evaluations/results`
- `POST /api/v1/evaluations/results/{eval_result_id}/clear`
- `POST /api/v1/evaluations/results/{eval_result_id}/override`

本地命令：

- 在仓库根目录执行：`npm install`
- 在仓库根目录执行：`npm run dev`
- 在 `backend/` 目录执行：`python scripts/run_batch_eval.py --model-id <id>`
- 在 `backend/` 目录执行：`python scripts/run_judge_backfill.py --model-id <id> --attempt <n>`
- 在 `backend/` 目录执行：`python scripts/reset_eval_results.py --eval-result-id <id>`
- 在 `backend/` 目录执行：`python scripts/migrate_eval_models_add_api_style.py`
- 在 `backend/` 目录执行：`python scripts/migrate_eval_models_add_release_date.py`
- 在 `backend/` 目录执行：`python scripts/migrate_eval_results_add_result_overrides.py`
- 在 `frontend/` 目录执行：`npm install`
- 在 `frontend/` 目录执行：`npm run dev`

## 当前未完成内容

- 面向不同厂商差异的更完整 provider 适配
- judge 模型输出格式的进一步稳健化
- 批量任务编排与 Celery 异步执行
- 评测结果查询与任务管理 API 的进一步完善
- 更完整的数据库集成测试和 provider mock 测试

## 前端打包策略

- 顶层页面通过 `React.lazy + Suspense` 按路由拆包
- `vite.config.js` 已通过 `manualChunks` 固定核心依赖家族，其余依赖交给 Rollup 自动归并，避免回到单一 vendor 大包
- UI 组件相关依赖当前不做手工 vendor 合并，交给 Rollup 按真实页面依赖自动拆分，避免把模型页和评测页的重组件提前塞进首页
- Markdown / LaTeX 渲染链已单独拆成 `vendor-markdown`，避免结果页把渲染器直接打进主路由 chunk
- 当前推荐做法是：新增前端页面时优先沿用现有 chunk family；新增重型依赖时先评估是否需要单独拆包

## 当前约束

- 当前实现必须放在 `D:\\AAAproject\\benchmark`
- 当前后端实现统一放在 `D:\\AAAproject\\benchmark\\backend`
- 被测模型只允许接收 `content_images`
- 校验模型允许接收标准答案文本和 `answer_images`
- 不向任何模型传 `analysis_images`
- 不把长期密钥写进提交到仓库的代码和文档

## 当前最直接的下一步

- 对已存历史 `response_text` 执行 judge 回填
- 继续收敛 judge prompt 和输出 JSON 解析
- 为结果查询页继续补充更细的筛选项、批量清理能力和图像展示能力
- 再决定是否接通 Redis / Celery
