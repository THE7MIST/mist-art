# API Reference

Base URL:

```text
http://localhost:8000/api
```

Health check:

```http
GET /health
```

Case management:

```http
POST /api/cases
GET /api/cases
GET /api/cases/{case_id}
```

Evidence:

```http
POST /api/cases/{case_id}/evidence
GET /api/cases/{case_id}/evidence
```

Questions:

```http
POST /api/cases/{case_id}/questions
GET /api/cases/{case_id}/questions
POST /api/cases/{case_id}/questions/import/text
POST /api/cases/{case_id}/questions/import/file
```

Analysis:

```http
POST /api/cases/{case_id}/analyze
```

Reports:

```http
GET /api/cases/{case_id}/reports/latest
GET /api/cases/{case_id}/reports/latest/markdown
GET /api/cases/{case_id}/reports/latest/download
```

Plugins:

```http
GET /api/plugins
```

## Example

```bash
curl -X POST http://localhost:8000/api/cases \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Case 001\",\"examiner\":\"Analyst\"}"
```
