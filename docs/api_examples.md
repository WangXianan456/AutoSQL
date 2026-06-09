# API 示例

## 1. 同步元数据

```bash
curl -X POST http://127.0.0.1:8000/v1/metadata/sync \
  -H "Content-Type: application/json" \
  -d '{
    "superset_database_id": 3,
    "database_name": "Mysql_bw_hotel",
    "dialect": "mysql",
    "engine": "mysql",
    "catalog": null,
    "schema": "bw_hotel",
    "metadata_version": "2026-06-09T14:00:00+08:00",
    "tables": [
      {
        "name": "hotel_order",
        "table_type": "table",
        "description": "酒店订单表",
        "columns": [
          {"name": "hotel_id", "data_type": "BIGINT", "description": "酒店ID", "ordinal_position": 1},
          {"name": "order_amount", "data_type": "DECIMAL", "description": "订单金额", "ordinal_position": 2},
          {"name": "created_time", "data_type": "DATETIME", "description": "创建时间", "ordinal_position": 3}
        ]
      }
    ]
  }'
```

## 2. 搜索候选表

```bash
curl -X POST http://127.0.0.1:8000/v1/metadata/search \
  -H "Content-Type: application/json" \
  -d '{
    "superset_database_id": 3,
    "schema": "bw_hotel",
    "question": "最近7天订单金额最高的酒店",
    "limit": 5
  }'
```

## 3. 生成 SQL

```bash
curl -X POST http://127.0.0.1:8000/v1/sql/generate \
  -H "Content-Type: application/json" \
  -d '{
    "superset_database_id": 3,
    "schema": "bw_hotel",
    "dialect": "mysql",
    "question": "最近7天订单金额最高的酒店",
    "limit": 5
  }'
```

也兼容旧客户端路径：

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "最近7天订单金额最高的酒店",
    "schema_context": {
      "database_id": 3,
      "dialect": "mysql",
      "schema": "bw_hotel",
      "tables": [
        {
          "name": "hotel_order",
          "columns": [
            {"name": "hotel_id", "data_type": "BIGINT"},
            {"name": "order_amount", "data_type": "DECIMAL"}
          ]
        }
      ]
    }
  }'
```

## 4. 反馈

```bash
curl -X POST http://127.0.0.1:8000/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "00000000-0000-0000-0000-000000000000",
    "user_id": "superset-user-1",
    "copied": true,
    "inserted": true,
    "accepted": true
  }'
```
