# Phase 2 API Documentation

**Version**: 3.0.0  
**Base URL**: `http://localhost:8000`  
**API Version**: `v2.0`  
**Authentication**: JWT Bearer Token  

---

## Quick Start

### 1. Get JWT Token

```bash
# Login (Phase 3 implementation)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Response: {"access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...", "token_type": "bearer"}
```

### 2. Create Build Task

```bash
TOKEN="your-jwt-token"

curl -X POST http://localhost:8000/api/build/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "my-project",
    "goal": "Add authentication module with JWT",
    "parameters": {"framework": "fastapi"}
  }'

# Response: {"task_id": "550e8400...", "status": "initializing", "message": "..."}
```

### 3. Monitor Progress via WebSocket

```javascript
const token = "your-jwt-token";
const taskId = "550e8400...";

const ws = new WebSocket(
  `ws://localhost:8000/api/ws/build/${taskId}?token=${token}`
);

ws.onopen = () => {
  console.log("Connected to build updates");
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(`Progress: ${message.progress}%`);
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("Disconnected");
};
```

---

## Build API Endpoints

### POST /api/build/ - Create Build Task

Create new build task for code generation.

**Request**:
```json
{
  "project_name": "my-project",
  "goal": "Add authentication module with JWT support",
  "parameters": {
    "framework": "fastapi",
    "database": "postgresql",
    "include_tests": true
  }
}
```

**Response** (202 Accepted):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "initializing",
  "message": "Build task created successfully"
}
```

**Error Responses**:
- `400`: Invalid input (validation error)
- `403`: Not authenticated
- `422`: Unprocessable entity

**Security Notes**:
- Requires valid JWT token
- Rate limited: 10 requests/minute per user
- Project name validated against injection patterns

---

### GET /api/build/{task_id} - Get Build Status

Retrieve current status of a build task.

**Path Parameters**:
- `task_id` (UUID): Unique build identifier

**Response** (200 OK):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "my-project",
  "status": "running",
  "progress": 45,
  "created_at": "2026-02-03T10:30:00Z",
  "created_by": "alice",
  "goal": "Add authentication module",
  "results": null,
  "error": null
}
```

**Status Values**:
- `initializing`: Task created, waiting to start
- `running`: Task in progress
- `completed`: Task finished successfully
- `failed`: Task failed with error
- `cancelled`: Task was cancelled by user

**Error Responses**:
- `404`: Build task not found
- `403`: Not authorized to view this build

**Authorization**:
- Users can only view their own builds
- Admins can view any build

---

### GET /api/build/ - Get Build History

Retrieve paginated history of user's builds.

**Query Parameters**:
- `limit` (integer, 1-100, default 20): Number of records per page
- `offset` (integer, default 0): Pagination offset

**Example**: `GET /api/build/?limit=20&offset=0`

**Response** (200 OK):
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "builds": [
    {
      "task_id": "550e8400...",
      "project_name": "my-project",
      "status": "completed",
      "progress": 100,
      "created_at": "2026-02-03T10:30:00Z",
      "created_by": "alice",
      "goal": "Add authentication",
      "results": {...},
      "error": null
    },
    ...
  ]
}
```

**Ordering**: Newest first (reverse chronological)

**Pagination Example**:
```bash
# First page
curl -X GET "http://localhost:8000/api/build/?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Next page
curl -X GET "http://localhost:8000/api/build/?limit=10&offset=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

### DELETE /api/build/{task_id} - Cancel Build

Cancel an in-progress build task.

**Path Parameters**:
- `task_id` (UUID): Build to cancel

**Response** (200 OK):
```json
{
  "message": "Build task cancelled successfully"
}
```

**Cancellable States**:
- `initializing`: Can cancel
- `running`: Can cancel
- `completed`: Cannot cancel
- `failed`: Cannot cancel
- `cancelled`: Already cancelled

**Error Responses**:
- `404`: Build not found
- `403`: Not authorized
- `409`: Build cannot be cancelled (already completed/failed/cancelled)

**Authorization**:
- Task creator can cancel their own builds
- Admins can cancel any build

---

## Code Analysis API Endpoints

### POST /api/analysis/ - Create Analysis Task

Analyze code for quality, security, and type issues.

**Request**:
```json
{
  "project_name": "my-project",
  "analysis_types": ["quality", "security", "types"]
}
```

**Response** (202 Accepted):
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "my-project",
  "timestamp": "2026-02-03T10:30:00Z",
  "performed_by": "alice",
  "quality_score": 8.5,
  "security_issues": [],
  "code_smells": 5,
  "type_errors": 0,
  "coverage_percent": 87.5,
  "recommendations": [
    "Add docstrings to public functions",
    "Extract complex methods"
  ]
}
```

**Analysis Types**:
- `quality`: Code complexity, style, metrics
- `security`: Security vulnerabilities, patterns
- `types`: Type checking with mypy

**Scoring**:
- Quality Score: 0-10 (higher is better)
- Coverage: 0-100% (percentage of code covered by tests)

---

### GET /api/analysis/{analysis_id} - Get Analysis Results

Retrieve completed analysis results.

**Path Parameters**:
- `analysis_id` (UUID): Analysis identifier

**Response** (200 OK):
```json
{
  "analysis_id": "550e8400...",
  "project_name": "my-project",
  "timestamp": "2026-02-03T10:30:00Z",
  "performed_by": "alice",
  "quality_score": 8.5,
  "security_issues": [
    {
      "issue": "SQL Injection",
      "severity": "high",
      "line": 42,
      "recommendation": "Use parameterized queries"
    }
  ],
  "code_smells": 5,
  "type_errors": 0,
  "coverage_percent": 87.5,
  "recommendations": [...]
}
```

**Error Responses**:
- `404`: Analysis not found
- `403`: Not authorized to view

---

## Health Check Endpoints

### GET /api/health/ - Basic Health Check

Simple health status for load balancers.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-02-03T10:30:00Z",
  "version": "3.0.0"
}
```

---

### GET /api/health/ready - Kubernetes Readiness Probe

Indicates if service is ready to accept requests.

**Response** (200 OK): Service ready  
**Response** (503): Service not ready

---

### GET /api/health/live - Kubernetes Liveness Probe

Indicates if service process is running.

**Response** (200 OK): Service alive  
**Response** (503): Service should be restarted

---

### GET /api/health/status - System Status

Detailed system status with components and metrics.

**Response** (200 OK):
```json
{
  "status": "operational",
  "timestamp": "2026-02-03T10:30:00Z",
  "version": "3.0.0",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy",
    "security": "healthy"
  },
  "metrics": {
    "uptime_seconds": 3600,
    "requests_total": 1250,
    "requests_per_second": 0.35,
    "memory_percent": 45.2,
    "cpu_percent": 12.5
  }
}
```

---

## WebSocket Endpoints

### WS /api/ws/build/{task_id} - Build Progress Stream

Real-time progress updates for build tasks.

**Connection**:
```
ws://localhost:8000/api/ws/build/{task_id}?token=<JWT>
```

**Authentication**: JWT token in query parameter required

**Message Types from Server**:

**Connected** (on successful connection):
```json
{
  "type": "connected",
  "task_id": "550e8400...",
  "message": "Connected to build updates",
  "timestamp": "2026-02-03T10:30:00Z"
}
```

**Progress** (during execution):
```json
{
  "type": "progress",
  "task_id": "550e8400...",
  "status": "running",
  "progress": 45,
  "timestamp": "2026-02-03T10:30:00Z",
  "data": {
    "current_step": "Generating code",
    "files_created": 3
  }
}
```

**Completion** (when finished):
```json
{
  "type": "completion",
  "task_id": "550e8400...",
  "status": "completed",
  "timestamp": "2026-02-03T10:30:00Z",
  "results": {
    "generated_files": ["auth.py", "models.py"],
    "tests_passed": 12,
    "test_coverage": 87.5
  }
}
```

**Error** (if build fails):
```json
{
  "type": "error",
  "task_id": "550e8400...",
  "status": "failed",
  "timestamp": "2026-02-03T10:30:00Z",
  "error": "Command execution timeout"
}
```

---

### WS /api/ws/analysis/{analysis_id} - Analysis Progress Stream

Real-time updates for code analysis tasks (same format as build).

**Connection**:
```
ws://localhost:8000/api/ws/analysis/{analysis_id}?token=<JWT>
```

---

## Authentication

### JWT Token Structure

Tokens are JWT format with claims:
```json
{
  "sub": "username",
  "role": "user|admin",
  "permissions": ["build:create", "build:read"],
  "exp": 1707200400,
  "iat": 1707113000
}
```

**Roles**:
- `user`: Regular user (can create/manage own builds)
- `admin`: Administrator (can manage all builds, access control)
- `viewer`: Read-only access

**Permissions**:
- `build:create`: Create new builds
- `build:read`: View builds
- `build:cancel`: Cancel builds
- `analysis:create`: Create analyses
- `analysis:read`: View analyses

### Using JWT Tokens

All API requests (except health) require JWT in `Authorization` header:

```bash
curl -X GET http://localhost:8000/api/build/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

---

## Error Handling

All endpoints return standard error format:

**Format**:
```json
{
  "error": "error_type",
  "detail": "Human readable error message",
  "status_code": 400,
  "timestamp": "2026-02-03T10:30:00Z"
}
```

**HTTP Status Codes**:
- `200`: Success
- `202`: Accepted (async task created)
- `400`: Bad request (validation error)
- `401`: Unauthorized (missing/invalid auth)
- `403`: Forbidden (insufficient permissions)
- `404`: Not found
- `409`: Conflict (invalid state transition)
- `422`: Unprocessable entity (validation error)
- `429`: Too many requests (rate limited)
- `500`: Internal server error
- `503`: Service unavailable

---

## Rate Limiting

All endpoints are rate limited per user:

- **Global**: 60 requests/minute
- **Build creation**: 10 requests/minute
- **Analysis**: 5 requests/minute

**Rate Limit Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1707113600
```

**Rate Limit Exceeded**:
```json
{
  "error": "rate_limit_exceeded",
  "detail": "Too many requests",
  "status_code": 429
}
```

---

## Examples

### Python Example

```python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Create build
build_data = {
    "project_name": "my-app",
    "goal": "Add user authentication",
    "parameters": {"framework": "fastapi"}
}

resp = requests.post(f"{BASE_URL}/api/build/", json=build_data, headers=headers)
build = resp.json()
task_id = build["task_id"]

# Poll for status
while True:
    status_resp = requests.get(
        f"{BASE_URL}/api/build/{task_id}",
        headers=headers
    )
    status_data = status_resp.json()
    
    print(f"Status: {status_data['status']} ({status_data['progress']}%)")
    
    if status_data['status'] in ['completed', 'failed', 'cancelled']:
        print("Build finished:", status_data['results'])
        break
    
    time.sleep(2)
```

### JavaScript Example

```javascript
const BASE_URL = "http://localhost:8000";
const TOKEN = "your-jwt-token";

// Create build
async function createBuild() {
  const response = await fetch(`${BASE_URL}/api/build/`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      project_name: "my-app",
      goal: "Add authentication"
    })
  });
  
  return await response.json();
}

// Connect WebSocket
async function monitorBuild(taskId) {
  const ws = new WebSocket(
    `ws://localhost:8000/api/ws/build/${taskId}?token=${TOKEN}`
  );
  
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log(`Progress: ${message.progress}%`);
  };
}
```

---

## Best Practices

1. **Always use WebSocket for long-running tasks** instead of polling
2. **Handle rate limiting gracefully** with exponential backoff
3. **Store task IDs** for later status checks
4. **Implement reconnection logic** for WebSocket
5. **Use admin token only when necessary** for security
6. **Validate input** before sending to API
7. **Cache health status** to reduce load
8. **Implement circuit breaker** for failed tasks

---

## Troubleshooting

**401 Unauthorized**:
- Token missing or invalid
- Token expired
- Solution: Get new token

**403 Forbidden**:
- Insufficient permissions
- Trying to access another user's build
- Solution: Check user role and permissions

**429 Too Many Requests**:
- Rate limit exceeded
- Solution: Implement backoff and retry

**503 Service Unavailable**:
- Service is down or starting
- Solution: Check health endpoint, retry later

---

## Migration from Phase 1

In Phase 2, these new components are added:
- RESTful API endpoints
- WebSocket real-time updates
- Celery task queue configuration
- LangGraph agent skeleton

Phase 1 security components remain in place:
- JWT authentication
- Input validation
- Rate limiting
- Security headers

---

*Phase 2 API Documentation - February 3, 2026*
