# Frontend

当前已经落地：

- `React + Vite + TypeScript`
- `TanStack Query`
- `React Router`
- `Ant Design`

已接入页面：

- `概览`：健康检查、数据库状态、题目统计、评测统计
- `模型管理`：模型列表、筛选、编辑、快速启停、批量 Probe
- `评测工作台`：输入预览、Payload 预览、单次运行、后端批量任务、最近执行历史
- 评测执行模式已解耦：`仅生成`、`仅判分`、`生成并判分`

本地启动：

```bash
npm install
npm run dev
```

如果从仓库根目录统一启动前后端：

```bash
npm install
npm run dev
```

默认开发代理会把 `/api` 转发到 `http://127.0.0.1:8000`。
前端开发服务默认监听 `http://127.0.0.1:5174`。

如果后端地址不同，可以在 `frontend/.env.local` 里设置：

```env
VITE_DEV_PORT=5174
VITE_BACKEND_ORIGIN=http://127.0.0.1:8000
VITE_API_BASE_URL=/api/v1
```
