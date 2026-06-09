# AutoSQL Catalog Service

AutoSQL 是给 Superset AI SQL 助手配套的独立后端应用。

当前目标：

- 保存 Superset 同步过来的脱敏数据库结构元数据。
- 在多个外部库/schema 中检索候选表和字段。
- 基于候选 `schema_context` 调用 DeepSeek API 生成 SQL。
- 不保存业务库连接串、账号、密码、token。
- 不直接连接业务数据库，不执行业务 SQL。

## 技术栈

```text
FastAPI
PostgreSQL
DeepSeek OpenAI-compatible API
```

第一版不依赖 Claude Code SDK，不接旧 `29284_AutoSQL` 技术栈。

## 快速启动

1. 创建表：

```bash
psql "$AUTOSQL_DATABASE_URL" -f sql/001_init.sql
```

2. 配置环境变量：

```bash
cp .env.example .env
```

3. 安装依赖并启动：

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 核心接口

```text
GET    /health
POST   /v1/metadata/sync
POST   /v1/metadata/search
DELETE /v1/metadata/{superset_database_id}
POST   /v1/sql/generate
POST   /generate
POST   /v1/feedback
```

## 安全边界

AutoSQL 只保存：

```text
database_id / schema / table / column / comments / pk / fk / metadata_version
```

AutoSQL 不保存：

```text
数据库连接串
数据库用户名
数据库密码
token
真实业务数据行
未脱敏样例数据
```

Superset 仍然负责：

```text
用户身份
权限校验
数据库连接
元数据读取
最终 SQL 安全收口
```
