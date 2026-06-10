# AgentHub AgentScope

AgentHub AgentScope 是一个前后端分离的多智能体协作项目。

- `agenthub-backend`：基于 `FastAPI` 的后端服务，负责认证、群组、消息、任务编排、Agent/Manager 运行时、预览与部署等能力
- `agenthub-frontend`：基于 `Vue 3 + Vite` 的聊天与任务协作界面

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
- `uv`
- `npm`

可选但强烈建议：

- `Docker`
  用于项目预览、部署、部分沙箱执行能力
- 可用的 LLM API Key
  当前默认按 OpenAI 兼容接口接入，默认示例为阿里云 DashScope 兼容地址

## 快速启动

推荐顺序：先启动后端，再启动前端。

### 1. 启动后端

```bash
cd agenthub-backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

默认地址：

- API：`http://127.0.0.1:8000`
- 健康检查：`http://127.0.0.1:8000/health`
- Swagger：`http://127.0.0.1:8000/docs`

如果 `8000` 端口被占用：

```bash
uv run uvicorn app.main:app --reload --port 8012
```

### 2. 启动前端

```bash
cd agenthub-frontend
cp .env.example .env.local
npm install
npm run dev
```

默认地址：

- 前端：`http://127.0.0.1:5173`

## 默认账号

当后端环境为 `local` 或 `dev` 时，系统会自动确保默认管理员存在：

- 邮箱：`admin@example.com`
- 密码：`admin123456`

注意：

- 这不是“每次启动都重置数据库”
- 只有在显式配置 `AGENTHUB_RESET_DB_ON_STARTUP=true` 时，启动阶段才会清空并重建数据库

## 环境变量

后端所有环境变量都以 `AGENTHUB_` 为前缀，读取文件为 `agenthub-backend/.env`。

### 后端必配

以下变量建议至少配置：

| 变量 | 说明 | 示例 / 默认值 |
| --- | --- | --- |
| `AGENTHUB_DB_URL` | 数据库连接串，默认 SQLite | `sqlite:///./agenthub.db` |
| `AGENTHUB_JWT_SECRET_KEY` | JWT 签名密钥，生产环境必须修改 | `replace-with-a-random-secret-at-least-32-chars` |
| `AGENTHUB_OPENAI_API_KEY` | LLM API Key，不配置则 AI/Agent/Manager 能力不可用 | `sk-xxx` |
| `AGENTHUB_OPENAI_BASE_URL` | OpenAI 兼容接口地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `AGENTHUB_OPENAI_MODEL` | 默认模型名 | `qwen3.6-plus` |

### 后端常用配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `AGENTHUB_ENV` | 运行环境 | `local` |
| `AGENTHUB_APP_NAME` | 服务名 | `AgentHub Backend` |
| `AGENTHUB_API_PREFIX` | API 前缀 | `/api/v1` |
| `AGENTHUB_CORS_ORIGINS` | 允许跨域来源，JSON 数组格式 | `["http://127.0.0.1:5173","http://localhost:5173"]` |
| `AGENTHUB_DATA_ROOT` | 用户/Agent/项目运行数据根目录 | `~/.multiproj-agent` |
| `AGENTHUB_SKILL_POOL_DIR` | 外部技能池目录 | `./skill-pool` |
| `AGENTHUB_RESET_DB_ON_STARTUP` | 启动时是否重置数据库 | `false` |
| `AGENTHUB_JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `AGENTHUB_JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟） | `10080` |
| `AGENTHUB_DEFAULT_AI_SYSTEM_PROMPT` | 默认 AI system prompt | `You are a helpful AI assistant.` |

### 后端运行时配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `AGENTHUB_PROJECT_COMMAND_TIMEOUT_SECONDS` | 普通项目命令超时 | `120` |
| `AGENTHUB_EXECUTION_COMMAND_TIMEOUT_SECONDS` | 执行节点命令超时 | `600` |
| `AGENTHUB_DEPLOYMENT_COMMAND_TIMEOUT_SECONDS` | 预览/部署命令超时 | `1800` |
| `AGENTHUB_AI_SHORT_TERM_HISTORY_LIMIT` | 对话短期历史条数 | `50` |
| `AGENTHUB_MEMORY_COMPRESS_TRIGGER_TOKENS` | 记忆压缩触发 token 阈值 | `3500` |
| `AGENTHUB_MEMORY_COMPRESS_KEEP_RECENT_MESSAGES` | 压缩时保留最近消息数 | `12` |
| `AGENTHUB_MESSAGE_EVENT_RECOVERY_ENABLED` | 是否启用消息事件恢复轮询 | `true` |
| `AGENTHUB_MESSAGE_EVENT_RECOVERY_INTERVAL_SECONDS` | 恢复轮询间隔 | `2.0` |
| `AGENTHUB_MESSAGE_EVENT_RECOVERY_BATCH_SIZE` | 单轮恢复批量大小 | `32` |
| `AGENTHUB_MANAGER_REACT_MAX_ITERS` | Manager 最大推理轮数 | `60` |
| `AGENTHUB_AGENT_REACT_MAX_ITERS` | 子 Agent 最大推理轮数 | `40` |
| `AGENTHUB_COMMAND_OUTPUT_LIMIT_CHARS` | 命令输出截断上限 | `50000` |

### ACP / 外部执行器配置

如果你要让 Agent 通过 ACP 调用外部执行器，可以配置：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `AGENTHUB_ACP_CODEX_COMMAND` | Codex ACP 启动命令 | `npx -y @zed-industries/codex-acp` |
| `AGENTHUB_ACP_CLAUDE_COMMAND` | Claude ACP 启动命令 | `python -m claude_code_acp` |

说明：

- `AGENTHUB_ACP_CODEX_COMMAND` 依赖本机可用的 `npx`
- `AGENTHUB_ACP_CLAUDE_COMMAND` 依赖本机存在 `claude_code_acp`

### Docker / 预览 / 部署配置

如果你会使用“项目预览”“部署”“沙箱执行”等能力，建议确认：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `AGENTHUB_DOCKER_SANDBOX_DEFAULT_IMAGE` | 默认 Docker 镜像 | `node:20-bookworm` |
| `AGENTHUB_DOCKER_SANDBOX_MEMORY_LIMIT` | 沙箱内存限制 | `2g` |
| `AGENTHUB_DOCKER_SANDBOX_CPU_LIMIT` | 沙箱 CPU 限制 | `2.0` |

另外还需要：

- 本机安装并启动 Docker
- 当前用户有执行 `docker` 命令的权限

### 前端环境变量

前端读取 `agenthub-frontend/.env.local`。

目前主要变量：

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `VITE_API_BASE` | 前端请求的后端 API 基地址 | `http://127.0.0.1:8000/api/v1` |

说明：

- WebSocket 地址默认根据浏览器当前 `location.host` 自动推导，不需要单独配置
- 如果你把后端启动在别的端口，记得同步修改这里

## 推荐的本地开发配置

后端 `.env` 可以从下面开始：

```env
AGENTHUB_ENV=local
AGENTHUB_DB_URL=sqlite:///./agenthub.db
AGENTHUB_JWT_SECRET_KEY=replace-with-a-random-secret-at-least-32-chars
AGENTHUB_OPENAI_API_KEY=your_key
AGENTHUB_OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AGENTHUB_OPENAI_MODEL=qwen3.6-plus
AGENTHUB_CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]
```

前端 `.env.local`：

```env
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

## 初始化演示数据

后端启动后，可以执行：

```bash
cd agenthub-backend
uv run python scripts/seed_demo.py --base-url http://127.0.0.1:8000/api/v1
```

这个脚本会补充演示用户、群组、任务和示例 skill pool。

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

## 常见问题

### 1. 登录成功但 AI 不回复

优先检查：

- `AGENTHUB_OPENAI_API_KEY` 是否已配置
- `AGENTHUB_OPENAI_BASE_URL` / `AGENTHUB_OPENAI_MODEL` 是否与当前服务匹配
- 后端日志里是否有模型调用失败或工具执行失败

### 2. WebSocket 403

通常是当前登录用户不属于该群组，或前端连接到了过期 token。

可以检查：

- 该用户是否已被加入当前 group
- 浏览器本地 token 是否过期，必要时重新登录

### 3. 预览/部署失败

通常与 Docker 环境有关：

- Docker 未启动
- 当前用户无 Docker 权限
- 默认镜像拉取失败
- 本机端口被占用

## 补充说明

- 根 README 只覆盖快速启动与关键配置
- 更详细的运行时说明可以查看：
  - [agenthub-backend/README.md](/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/README.md)
  - [agenthub-frontend/README.md](/Users/youtao/Projects/AgentHub-agentscope/agenthub-frontend/README.md)
