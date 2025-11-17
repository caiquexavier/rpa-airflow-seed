# CURL Examples for request_robot_execution Endpoint

The `request_robot_execution` endpoint now requires `exec_id` as a direct parameter. The saga will be automatically fetched from the database using the `exec_id`.

## Endpoint
```
POST http://localhost:3000/api/v1/execution/request_robot_execution
```

## Basic Usage

### Minimal Request (exec_id only)
```bash
curl -X POST http://localhost:3000/api/v1/execution/request_robot_execution \
  -H "Content-Type: application/json" \
  -d '{
    "exec_id": 1
  }'
```

### With Callback Path
```bash
curl -X POST http://localhost:3000/api/v1/execution/request_robot_execution \
  -H "Content-Type: application/json" \
  -d '{
    "exec_id": 1,
    "callback_path": "/trigger/upload_nf_files_to_s3"
  }'
```

### With Saga (Backward Compatibility)
The saga field is optional and kept for backward compatibility, but the endpoint will use `exec_id` to fetch the latest saga from the database:

```bash
curl -X POST http://localhost:3000/api/v1/execution/request_robot_execution \
  -H "Content-Type: application/json" \
  -d '{
    "exec_id": 1,
    "callback_path": "/trigger/upload_nf_files_to_s3",
    "saga": {
      "saga_id": 1,
      "exec_id": 1,
      "rpa_key_id": "rpa_protocolo_devolucao",
      "data": {},
      "current_state": "PENDING"
    }
  }'
```

## Error Cases

### Missing exec_id (422 Unprocessable Entity)
```bash
curl -X POST http://localhost:3000/api/v1/execution/request_robot_execution \
  -H "Content-Type: application/json" \
  -d '{
    "callback_path": "/trigger/upload_nf_files_to_s3"
  }'
```

Expected response:
```json
{
  "detail": "exec_id is required in request payload"
}
```

### Invalid exec_id (422 Unprocessable Entity)
```bash
curl -X POST http://localhost:3000/api/v1/execution/request_robot_execution \
  -H "Content-Type: application/json" \
  -d '{
    "exec_id": 99999
  }'
```

Expected response:
```json
{
  "detail": "Execution 99999 not found. Execution must be created by saga creation first."
}
```

## Success Response (202 Accepted)
```json
{
  "exec_id": 1,
  "rpa_key_id": "rpa_protocolo_devolucao",
  "status": "ENQUEUED",
  "message": "Execution request created and published to queue",
  "published": true,
  "saga": {
    "saga_id": 1,
    "exec_id": 1,
    "rpa_key_id": "rpa_protocolo_devolucao",
    "data": {},
    "current_state": "PENDING",
    "events": []
  }
}
```

## How It Works

1. The endpoint receives `exec_id` as a required parameter
2. It looks up the execution in the database using `exec_id`
3. It finds the related saga using `get_saga_by_exec_id(exec_id)` - a simple database query
4. It publishes the execution request to RabbitMQ with the saga data
5. Returns a success response with the execution and saga details

## Notes

- **exec_id is required**: The endpoint will return 422 if `exec_id` is missing
- **Saga lookup is automatic**: The saga is fetched from the database by `exec_id`, so you don't need to include it in the request
- **Saga field is optional**: The `saga` field in the request is kept for backward compatibility but is ignored - the database saga is always used
- **Execution must exist**: The execution must be created first (typically by the saga creation endpoint)



