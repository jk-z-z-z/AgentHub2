# AgentHub AgentScope

AgentHub AgentScope 是一个前后端分离的多智能体协作项目：

- `agenthub-backend`：基于 `FastAPI` 的后端服务，负责用户、群组、消息、智能体运行时、任务编排等能力
- `agenthub-frontend`：基于 `Vue 3 + Vite` 的前端界面

## 目录结构

```text
AgentHub-agentscope/
├── agenthub-backend/   # 后端
├── agenthub-frontend/  # 前端
├── docs/               # 项目文档
└── skill/              # 根级技能示例/配置
```

## 环境要求

- Python `3.11+`
- Node.js `20+`
- `uv`（用于管理后端依赖）
- `npm`（用于管理前端依赖）

如果本机还没有安装 `uv`，可以参考官方方式安装后再继续。

## 如何启动项目

推荐按“先后端、再前端”的顺序启动。

### 1. 启动后端

进入后端目录：

```bash
cd agenthub-backend
```

复制环境变量文件：

```bash
cp .env.example .env
```

安装依赖：

```bash
uv sync
```

启动开发服务器：

```bash
uv run uvicorn app.main:app --reload
```

默认地址：

- 服务地址：`http://127.0.0.1:8000`
- 健康检查：`http://127.0.0.1:8000/health`
- Swagger 文档：`http://127.0.0.1:8000/docs`

说明：

- 当前默认环境是 `local`
- 后端首次启动会自动创建 SQLite 表
- 在 `local/dev` 环境下会自动初始化默认管理员

默认管理员账号：

- 邮箱：`admin@example.com`
- 密码：`admin123456`

如果 `8000` 端口被占用，可以改端口启动：

```bash
uv run uvicorn app.main:app --reload --port 8012
```

### 2. 启动前端

新开一个终端，进入前端目录：

```bash
cd agenthub-frontend
```

安装依赖：

```bash
npm install
```

启动开发服务器：

```bash
npm run dev
```

默认地址：

- 前端页面：`http://127.0.0.1:5173`

前端开发环境默认会把 `/api` 和 `/ws` 代理到 `http://127.0.0.1:8000`，所以本地联调时通常只要先启动后端即可。

如果你想显式指定 API 地址，可以创建前端环境变量文件：

```bash
cp .env.example .env.local
```

然后修改：

```env
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

## 初始化演示数据

后端启动后，可以执行下面的脚本写入演示数据：

```bash
cd agenthub-backend
uv run python scripts/seed_demo.py --base-url http://127.0.0.1:8000/api/v1
```

## 常用开发命令

### 后端

```bash
cd agenthub-backend
uv run pytest
```

### 前端

```bash
cd agenthub-frontend
npm run build
npm run lint
```

## 补充说明

- 后端主要配置文件：`agenthub-backend/.env`
- 前端主要配置文件：`agenthub-frontend/.env.local`
- 更详细的模块说明可以查看子目录里的 `README.md` 和根目录 `docs/`
