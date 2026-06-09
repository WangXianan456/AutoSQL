# AutoSQL 部署说明

## 1. 前置条件

远程 Linux 主机需要：

```text
Python 3.11+ 或 Docker
PostgreSQL 13+
能访问 DeepSeek API
能被 Superset 主机本机或内网访问
```

建议 AutoSQL 只监听内网或本机：

```text
127.0.0.1:8000
```

不要直接暴露给浏览器公网访问。

## 2. 建库建表

创建 PostgreSQL 数据库和用户后执行：

```bash
psql "$AUTOSQL_DATABASE_URL" -f sql/001_init.sql
```

生产环境建议把 `AUTOSQL_DATABASE_URL` 指向独立 PostgreSQL，不要使用 Superset 元数据库。

## 3. 环境变量

复制：

```bash
cp .env.example .env
```

关键配置：

```text
AUTOSQL_DATABASE_URL=postgresql://...
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_COMPLETIONS_PATH=/chat/completions
DEEPSEEK_MODEL=deepseek-chat
```

## 4. Python 方式启动

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 5. Docker 方式启动

```bash
cp docker-compose.example.yml docker-compose.yml
docker compose up -d --build autosql
```

如果使用示例里的本地 PostgreSQL：

```bash
docker compose up -d postgres
docker compose up -d --build autosql
```

## 6. 健康检查

```bash
curl http://127.0.0.1:8000/health
```

预期：

```json
{"status":"ok"}
```

## 7. Superset 配置方向

Superset 后续应把 metadata sync/search/generate 指向 AutoSQL：

```python
AI_SQL_ASSISTANT = {
    "enabled": True,
    "endpoint": "http://127.0.0.1:8000/v1/sql/generate",
    "request_format": "generate",
    "timeout_seconds": 60,
}
```

还需要新增 Superset 到 AutoSQL 的 metadata 同步客户端：

```text
POST /v1/metadata/sync
POST /v1/metadata/search
DELETE /v1/metadata/{superset_database_id}
```
