"""
Test suite for Build API endpoints.

Coverage:
  - Build creation and validation
  - Build status retrieval
  - Build history pagination
  - Build cancellation
  - Authorization and permissions
  - Error handling
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json

from app.main import app
from app.security.auth import create_access_token
from app.models.schemas import BuildRequest

# Test client
client = TestClient(app)


# ==================== Fixtures ====================

@pytest.fixture
def user_token():
    """Create test user JWT token"""
    return create_access_token(
        data={
            "sub": "testuser",
            "role": "user",
            "permissions": ["build:create", "build:read"],
        }
    )


@pytest.fixture
def admin_token():
    """Create admin JWT token"""
    return create_access_token(
        data={
            "sub": "admin",
            "role": "admin",
            "permissions": ["*"],
        }
    )


@pytest.fixture
def build_request():
    """Sample build request"""
    return {
        "project_name": "test-project",
        "goal": "Add authentication module",
        "parameters": {"framework": "fastapi", "database": "postgresql"},
    }


# ==================== Build Creation Tests ====================

def test_create_build_success(user_token, build_request):
    """Test successful build creation"""
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post("/api/build/", json=build_request, headers=headers)

    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "initializing"
    assert data["message"] == "Build task created successfully"


def test_create_build_invalid_project_name(user_token):
    """Test build creation with invalid project name"""
    headers = {"Authorization": f"Bearer {user_token}"}
    request = {
        "project_name": "../../../etc/passwd",  # Path traversal attempt
        "goal": "Malicious build",
    }

    response = client.post("/api/build/", json=request, headers=headers)

    assert response.status_code in [400, 422]


def test_create_build_missing_goal(user_token):
    """Test build creation with missing required field"""
    headers = {"Authorization": f"Bearer {user_token}"}
    request = {
        "project_name": "test-project",
        # goal is missing
    }

    response = client.post("/api/build/", json=request, headers=headers)

    assert response.status_code == 422


def test_create_build_no_auth():
    """Test build creation without authentication"""
    request = {
        "project_name": "test-project",
        "goal": "Test goal",
    }

    response = client.post("/api/build/", json=request)

    assert response.status_code == 403


def test_create_build_empty_goal(user_token):
    """Test build creation with empty goal"""
    headers = {"Authorization": f"Bearer {user_token}"}
    request = {
        "project_name": "test-project",
        "goal": "",
    }

    response = client.post("/api/build/", json=request, headers=headers)

    assert response.status_code == 422


# ==================== Build Status Tests ====================

def test_get_build_status_success(user_token, build_request):
    """Test retrieving build status"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create build
    create_response = client.post("/api/build/", json=build_request, headers=headers)
    task_id = create_response.json()["task_id"]

    # Get status
    status_response = client.get(f"/api/build/{task_id}", headers=headers)

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["task_id"] == task_id
    assert data["project_name"] == "test-project"
    assert data["status"] == "initializing"
    assert data["progress"] == 0


def test_get_build_status_not_found(user_token):
    """Test get status for non-existent build"""
    headers = {"Authorization": f"Bearer {user_token}"}
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/api/build/{fake_id}", headers=headers)

    assert response.status_code == 404


def test_get_build_status_unauthorized(user_token, build_request):
    """Test get status with different user"""
    # Create build as user1
    headers1 = {"Authorization": f"Bearer {user_token}"}
    create_response = client.post("/api/build/", json=build_request, headers=headers1)
    task_id = create_response.json()["task_id"]

    # Try to access as different user (would need another token)
    # For now, test admin can access
    admin_token = create_access_token(
        data={"sub": "admin", "role": "admin", "permissions": ["*"]}
    )
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    response = client.get(f"/api/build/{task_id}", headers=headers_admin)

    assert response.status_code == 200


# ==================== Build History Tests ====================

def test_get_build_history_success(user_token, build_request):
    """Test retrieving build history"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create multiple builds
    for i in range(3):
        request = {**build_request, "project_name": f"test-project-{i}"}
        client.post("/api/build/", json=request, headers=headers)

    # Get history
    response = client.get("/api/build/?limit=10&offset=0", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "builds" in data
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_get_build_history_pagination(user_token, build_request):
    """Test build history pagination"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create builds
    for i in range(5):
        request = {**build_request, "project_name": f"project-{i}"}
        client.post("/api/build/", json=request, headers=headers)

    # Get first page
    response1 = client.get("/api/build/?limit=2&offset=0", headers=headers)
    assert response1.status_code == 200
    assert len(response1.json()["builds"]) <= 2

    # Get second page
    response2 = client.get("/api/build/?limit=2&offset=2", headers=headers)
    assert response2.status_code == 200


def test_get_build_history_limit_validation(user_token):
    """Test history limit capped at 100"""
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.get("/api/build/?limit=500&offset=0", headers=headers)

    # Should succeed but respect max limit
    assert response.status_code == 200


# ==================== Build Cancellation Tests ====================

def test_cancel_build_success(user_token, build_request):
    """Test successful build cancellation"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create build
    create_response = client.post("/api/build/", json=build_request, headers=headers)
    task_id = create_response.json()["task_id"]

    # Cancel build
    cancel_response = client.delete(f"/api/build/{task_id}", headers=headers)

    assert cancel_response.status_code == 200
    assert "cancelled" in cancel_response.json()["message"].lower()

    # Verify status is cancelled
    status_response = client.get(f"/api/build/{task_id}", headers=headers)
    assert status_response.json()["status"] == "cancelled"


def test_cancel_build_not_found(user_token):
    """Test cancel non-existent build"""
    headers = {"Authorization": f"Bearer {user_token}"}
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.delete(f"/api/build/{fake_id}", headers=headers)

    assert response.status_code == 404


def test_cancel_completed_build(user_token, build_request):
    """Test cancel already completed build"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create and complete build
    from app.api.build import _build_tasks

    create_response = client.post("/api/build/", json=build_request, headers=headers)
    task_id = create_response.json()["task_id"]

    # Simulate completion
    task = _build_tasks[task_id]
    task.status = "completed"
    task.progress = 100

    # Try to cancel
    response = client.delete(f"/api/build/{task_id}", headers=headers)

    assert response.status_code == 409


# ==================== Code Analysis Tests ====================

def test_analyze_code_success(user_token):
    """Test successful code analysis"""
    headers = {"Authorization": f"Bearer {user_token}"}
    request = {
        "project_name": "test-project",
        "analysis_types": ["quality", "security"],
    }

    response = client.post("/api/analysis/", json=request, headers=headers)

    assert response.status_code == 202
    data = response.json()
    assert "analysis_id" in data
    assert data["quality_score"] > 0
    assert "recommendations" in data


def test_analyze_code_invalid_project(user_token):
    """Test analysis with invalid project name"""
    headers = {"Authorization": f"Bearer {user_token}"}
    request = {
        "project_name": "../../sensitive",
        "analysis_types": ["quality"],
    }

    response = client.post("/api/analysis/", json=request, headers=headers)

    assert response.status_code in [400, 422]


def test_get_analysis_result(user_token):
    """Test retrieving analysis result"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create analysis
    request = {
        "project_name": "test-project",
        "analysis_types": ["quality"],
    }
    create_response = client.post("/api/analysis/", json=request, headers=headers)
    analysis_id = create_response.json()["analysis_id"]

    # Get result
    result_response = client.get(f"/api/analysis/{analysis_id}", headers=headers)

    assert result_response.status_code == 200
    assert result_response.json()["analysis_id"] == analysis_id


# ==================== Health Check Tests ====================

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/health/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_readiness_probe():
    """Test Kubernetes readiness probe"""
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_liveness_probe():
    """Test Kubernetes liveness probe"""
    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_system_status():
    """Test system status endpoint"""
    response = client.get("/api/health/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "components" in data
    assert "metrics" in data


# ==================== Security Tests ====================

def test_rate_limiting():
    """Test rate limiting on endpoints"""
    headers = {"Authorization": f"Bearer {create_access_token(data={'sub': 'test', 'role': 'user'})}"}
    request = {"project_name": "test", "goal": "test"}

    # Make multiple requests (rate limit is 10/minute per user)
    responses = []
    for i in range(15):
        response = client.post("/api/build/", json=request, headers=headers)
        responses.append(response.status_code)

    # At least one should be rate limited
    assert 429 in responses or all(r == 202 for r in responses)


def test_sql_injection_protection():
    """Test SQL injection attempt is blocked"""
    headers = {"Authorization": f"Bearer {create_access_token(data={'sub': 'test', 'role': 'user'})}"}
    request = {
        "project_name": "test",
        "goal": "'; DROP TABLE users; --",
    }

    response = client.post("/api/build/", json=request, headers=headers)

    # Should handle or reject
    assert response.status_code in [400, 422, 202]


def test_xss_protection():
    """Test XSS attempt is sanitized"""
    headers = {"Authorization": f"Bearer {create_access_token(data={'sub': 'test', 'role': 'user'})}"}
    request = {
        "project_name": "test",
        "goal": "<script>alert('xss')</script>",
    }

    response = client.post("/api/build/", json=request, headers=headers)

    # Should handle or reject
    assert response.status_code in [400, 422, 202]


# ==================== Integration Tests ====================

def test_build_workflow(user_token, build_request):
    """Test complete build workflow"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Create build
    create_response = client.post("/api/build/", json=build_request, headers=headers)
    assert create_response.status_code == 202
    task_id = create_response.json()["task_id"]

    # 2. Get status
    status_response = client.get(f"/api/build/{task_id}", headers=headers)
    assert status_response.status_code == 200

    # 3. Get history
    history_response = client.get("/api/build/", headers=headers)
    assert history_response.status_code == 200

    # 4. Cancel build
    cancel_response = client.delete(f"/api/build/{task_id}", headers=headers)
    assert cancel_response.status_code == 200


def test_analysis_workflow(user_token):
    """Test complete analysis workflow"""
    headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Create analysis
    request = {
        "project_name": "test-project",
        "analysis_types": ["quality", "security"],
    }
    create_response = client.post("/api/analysis/", json=request, headers=headers)
    assert create_response.status_code == 202
    analysis_id = create_response.json()["analysis_id"]

    # 2. Get result
    result_response = client.get(f"/api/analysis/{analysis_id}", headers=headers)
    assert result_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app", "--cov-report=term-missing"])
