# AgentTrace

AgentTrace 是一个独立实现的 AI Agent 执行追踪与故障诊断平台，参考 Fact0 的公开产品设计，但没有复用 Fact0 源码。项目面向本地开发、调试和面试讲解场景，核心能力包括：Python SDK、幂等事件采集、Trace/Span 查询、调用链树、失败定位和运行统计。

## 快速开始

仓库地址准备发布到 GitHub 后，推荐使用 GitHub Actions 或本地命令执行下面的验证。项目不包含本地数据库文件和依赖目录，首次启动会自动创建 SQLite 数据库。

### 本地运行（推荐）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

另开终端运行前端：

```powershell
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173。首次打开没有数据时，可以运行演示 Agent：

```powershell
python examples/demo_agent.py --base-url http://localhost:8000 --runs 4
```

API 文档地址：http://localhost:8000/docs。

### Docker Compose

```powershell
docker compose up --build
```

Compose 使用 PostgreSQL；本地直接启动默认使用 SQLite，数据文件位于 `data/agenttrace.db`。两种模式共用 SQLAlchemy 模型和 API。

## 项目结构

```text
backend/app/       FastAPI 应用、SQLAlchemy 模型、事件服务
sdk/agenttrace_sdk Python SDK（装饰器和上下文管理器）
examples/          可重复运行的知识库问答演示 Agent
frontend/          React + Vite + TypeScript 控制台
tests/             API、SDK 和一致性测试
```

## 关键设计

- `traces` 表保存一次 Agent 执行的聚合状态和耗时；`spans` 表保存步骤。
- `span_events` 通过 `event_id` 唯一约束实现重复上报幂等。
- Span 可以先于父 Span 到达，查询时按 `parent_span_id` 重新构建树；父任务更新使用状态优先级，子任务不会覆盖已完成父任务。
- 所有时间统一保存为带时区 ISO-8601 字符串对应的 UTC `DateTime(timezone=True)`。
- SDK 对输入输出做长度限制和常见密钥脱敏；上报失败不会吞掉业务异常。
- 模型字段预留 `model_name`、`input_tokens`、`output_tokens`、`cost_usd`。

## 测试

```powershell
pytest -q
```

测试覆盖正常采集、工具失败、重复事件、乱序父子 Span、多层关系、筛选分页、敏感数据脱敏和统计接口。测试默认使用临时 SQLite，不依赖外部数据库。

## 数据库迁移

第一版采用 `Base.metadata.create_all` 保障首次运行零配置；生产环境可将 `DATABASE_URL` 指向 PostgreSQL，并使用 Alembic 生成和执行迁移。当前模型变更点集中在 `backend/app/models.py`，方便后续生成迁移脚本。

## 技术复盘要点

1. 事件写入和聚合查询分离，避免重复上报放大统计。
2. 乱序问题通过事件持久化 + 查询时建树解决，不依赖到达顺序。
3. 状态机使用 `RUNNING < SUCCESS/FAILED`，终态不可被低优先级事件覆盖。
4. 可观测系统最重要的边界是“不改变业务行为”：SDK 上报异常只记录本地日志，业务异常继续向上抛出。

尚存问题：第一版没有鉴权、多租户、流式实时推送和完整 Alembic 迁移历史；前端图视图采用稳定的树形布局，尚未加入大规模 DAG 的画布缩放。

## 诚实说明

这是个人独立实现，参考了 Fact0 的公开产品设计，不代表 Fact0 或其公司经历，也没有伪造任职、商业使用或性能数据。
