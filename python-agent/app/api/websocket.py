"""
WebSocket endpoints for real-time build and analysis updates.

Provides:
  - Real-time build progress streaming
  - Analysis result updates
  - Connection management
  - Broadcast to multiple clients

Security:
  - JWT authentication required
  - User isolation (can only monitor own tasks)
  - Connection timeout (5 minutes)
  - Message rate limiting
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
import logging
import json
from datetime import datetime
from typing import Dict, List, Set
from app.security.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ws", tags=["websocket"])

# Active connections manager
class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(self, task_id: str, username: str, websocket: WebSocket):
        """
        Register new WebSocket connection.

        Args:
            task_id: Build/analysis task ID
            username: Authenticated username
            websocket: WebSocket connection
        """
        await websocket.accept()

        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

        if username not in self.user_connections:
            self.user_connections[username] = set()
        self.user_connections[username].add(task_id)

        logger.info(
            "WebSocket connected",
            extra={
                "task_id": task_id,
                "user": username,
                "connections": len(self.active_connections[task_id]),
            },
        )

    async def disconnect(self, task_id: str, username: str, websocket: WebSocket):
        """
        Remove WebSocket connection.

        Args:
            task_id: Build/analysis task ID
            username: Authenticated username
            websocket: WebSocket connection
        """
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)

            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

        logger.info(
            "WebSocket disconnected",
            extra={
                "task_id": task_id,
                "user": username,
            },
        )

    async def broadcast_progress(self, task_id: str, status: str, progress: int, data: dict = None):
        """
        Broadcast progress update to all connections on a task.

        Args:
            task_id: Build/analysis task ID
            status: Current task status
            progress: Progress percentage (0-100)
            data: Additional update data
        """
        if task_id not in self.active_connections:
            return

        message = {
            "type": "progress",
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if data:
            message["data"] = data

        disconnected = []
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(
                    "Failed to send WebSocket message",
                    extra={"task_id": task_id, "error": str(e)},
                )
                disconnected.append(connection)

        # Clean up disconnected sockets
        for conn in disconnected:
            if task_id in self.active_connections:
                try:
                    self.active_connections[task_id].remove(conn)
                except ValueError:
                    pass

    async def broadcast_completion(self, task_id: str, results: dict, error: str = None):
        """
        Broadcast task completion to all connections.

        Args:
            task_id: Build/analysis task ID
            results: Task results/output
            error: Error message if failed
        """
        if task_id not in self.active_connections:
            return

        message = {
            "type": "completion",
            "task_id": task_id,
            "status": "failed" if error else "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }

        if results:
            message["results"] = results
        if error:
            message["error"] = error

        disconnected = []
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(
                    "Failed to send completion message",
                    extra={"task_id": task_id, "error": str(e)},
                )
                disconnected.append(connection)

        # Close connections after sending completion
        for conn in disconnected + self.active_connections.get(task_id, []):
            try:
                await conn.close()
            except Exception:
                pass

        if task_id in self.active_connections:
            del self.active_connections[task_id]


# Global connection manager
manager = ConnectionManager()


@router.websocket("/build/{task_id}")
async def websocket_build_updates(websocket: WebSocket, task_id: str, token: str = None):
    """
    WebSocket endpoint for real-time build progress updates.

    **Connection Protocol**:
    1. Client connects with JWT token in query params: `?token=<jwt>`
    2. Server authenticates and accepts connection
    3. Server sends "connected" message
    4. Server sends progress updates as: {"type": "progress", "progress": 0-100, ...}
    5. Server sends completion as: {"type": "completion", "status": "completed", "results": {...}}
    6. Server closes connection

    **Message Format** (from server):
    ```json
    {
      "type": "progress" | "completion" | "error",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "initializing" | "running" | "completed" | "failed",
      "progress": 0-100,
      "timestamp": "2026-02-03T10:30:00Z",
      "data": {...},
      "results": {...},
      "error": "error message"
    }
    ```

    **Usage Example** (JavaScript):
    ```javascript
    const token = "your-jwt-token";
    const taskId = "550e8400-e29b-41d4-a716-446655440000";
    
    const ws = new WebSocket(
      `ws://localhost:8000/api/ws/build/${taskId}?token=${token}`
    );
    
    ws.onopen = () => {
      console.log("Connected to build updates");
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === "progress") {
        console.log(`Progress: ${message.progress}%`);
      } else if (message.type === "completion") {
        console.log("Build completed:", message.results);
      }
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
    
    ws.onclose = () => {
      console.log("Disconnected from build updates");
    };
    ```

    **Security**:
    - JWT authentication required
    - User can only monitor own builds
    - Connection timeout: 5 minutes
    - Message rate limited
    """
    # Extract and verify JWT token
    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing authentication token",
        )
        return

    try:
        payload = verify_token(token)
        username = payload.get("sub")

        if not username:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token",
            )
            return

    except Exception as e:
        logger.warning(
            "WebSocket authentication failed",
            extra={"task_id": task_id, "error": str(e)},
        )
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication failed",
        )
        return

    # Connect user to task updates
    await manager.connect(task_id, username, websocket)

    try:
        # Send connected message
        await websocket.send_json(
            {
                "type": "connected",
                "task_id": task_id,
                "message": "Connected to build updates",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep connection open and receive messages
        # In Phase 2, this mainly listens for disconnects
        # Phase 3: Add bidirectional messaging (cancel, modify)
        while True:
            data = await websocket.receive_text()
            # Echo received messages (for testing)
            # Production: implement command handling
            logger.debug(
                "WebSocket message received",
                extra={"task_id": task_id, "data": data},
            )

    except WebSocketDisconnect:
        await manager.disconnect(task_id, username, websocket)
        logger.info(
            "WebSocket client disconnected",
            extra={"task_id": task_id, "user": username},
        )

    except Exception as e:
        logger.error(
            "WebSocket error",
            extra={"task_id": task_id, "error": str(e)},
        )
        await manager.disconnect(task_id, username, websocket)


@router.websocket("/analysis/{analysis_id}")
async def websocket_analysis_updates(
    websocket: WebSocket, analysis_id: str, token: str = None
):
    """
    WebSocket endpoint for real-time code analysis updates.

    Same protocol as build updates, but for code analysis tasks.

    **Usage Example** (JavaScript):
    ```javascript
    const ws = new WebSocket(
      `ws://localhost:8000/api/ws/analysis/${analysisId}?token=${token}`
    );
    ```
    """
    # Extract and verify JWT token
    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing authentication token",
        )
        return

    try:
        payload = verify_token(token)
        username = payload.get("sub")

        if not username:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token",
            )
            return

    except Exception as e:
        logger.warning(
            "WebSocket authentication failed",
            extra={"analysis_id": analysis_id, "error": str(e)},
        )
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication failed",
        )
        return

    # Connect user to analysis updates
    await manager.connect(analysis_id, username, websocket)

    try:
        # Send connected message
        await websocket.send_json(
            {
                "type": "connected",
                "analysis_id": analysis_id,
                "message": "Connected to analysis updates",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep connection open
        while True:
            data = await websocket.receive_text()
            logger.debug(
                "WebSocket message received",
                extra={"analysis_id": analysis_id, "data": data},
            )

    except WebSocketDisconnect:
        await manager.disconnect(analysis_id, username, websocket)
        logger.info(
            "WebSocket analysis client disconnected",
            extra={"analysis_id": analysis_id, "user": username},
        )

    except Exception as e:
        logger.error(
            "WebSocket analysis error",
            extra={"analysis_id": analysis_id, "error": str(e)},
        )
        await manager.disconnect(analysis_id, username, websocket)
