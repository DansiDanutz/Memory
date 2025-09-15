"""
WebSocket endpoints for real-time monitoring
Provides live metrics and event streaming
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import psutil
import logging
from collections import deque
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class MetricSnapshot:
    """Snapshot of system metrics"""
    timestamp: float
    active_users: int
    memory_count: int
    request_rate: float
    response_times: Dict[str, float]
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    events: List[Dict[str, Any]]


class MetricsCollector:
    """Collects and aggregates system metrics"""

    def __init__(self):
        self.request_times = deque(maxlen=1000)
        self.response_times = deque(maxlen=1000)
        self.active_users = set()
        self.memory_count = 0
        self.events = deque(maxlen=100)
        self.last_snapshot = None

    def record_request(self, user_id: str, response_time: float):
        """Record a request"""
        self.request_times.append(time.time())
        self.response_times.append(response_time)
        self.active_users.add(user_id)

    def add_event(self, source: str, message: str, event_type: str = "info"):
        """Add an event"""
        self.events.append({
            "timestamp": time.time(),
            "source": source,
            "message": message,
            "type": event_type
        })

    def get_snapshot(self) -> MetricSnapshot:
        """Get current metrics snapshot"""
        now = time.time()

        # Calculate request rate (requests per minute)
        recent_requests = [t for t in self.request_times if now - t < 60]
        request_rate = len(recent_requests)

        # Calculate response time percentiles
        if self.response_times:
            sorted_times = sorted(self.response_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            p50 = p95 = p99 = 0

        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Get recent events
        recent_events = [
            e for e in self.events
            if now - e["timestamp"] < 60
        ]

        snapshot = MetricSnapshot(
            timestamp=now,
            active_users=len(self.active_users),
            memory_count=self.memory_count,
            request_rate=request_rate,
            response_times={
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2)
            },
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            events=recent_events[-5:]  # Last 5 events
        )

        self.last_snapshot = snapshot
        return snapshot

    def cleanup_old_data(self):
        """Clean up old data"""
        now = time.time()
        cutoff = now - 3600  # Keep 1 hour of data

        # Clean request times
        while self.request_times and self.request_times[0] < cutoff:
            self.request_times.popleft()

        # Clean active users (remove if no activity in 5 minutes)
        # This would need more sophisticated tracking in production


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.metrics_collector = MetricsCollector()
        self.broadcast_task = None

    async def connect(self, websocket: WebSocket):
        """Accept new connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send initial data
        snapshot = self.metrics_collector.get_snapshot()
        await self.send_personal_message(websocket, self._format_message(snapshot))

        # Start broadcast task if not running
        if not self.broadcast_task:
            self.broadcast_task = asyncio.create_task(self._broadcast_loop())

    def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

        # Stop broadcast if no connections
        if not self.active_connections and self.broadcast_task:
            self.broadcast_task.cancel()
            self.broadcast_task = None

    async def send_personal_message(self, websocket: WebSocket, message: str):
        """Send message to specific connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    def _format_message(self, snapshot: MetricSnapshot) -> str:
        """Format snapshot as JSON message"""
        data = {
            "timestamp": snapshot.timestamp,
            "activeUsers": snapshot.active_users,
            "memoryCount": snapshot.memory_count,
            "requestRate": snapshot.request_rate,
            "responseTime": snapshot.response_times,
            "cpu": snapshot.cpu_usage,
            "memory": snapshot.memory_usage,
            "disk": snapshot.disk_usage
        }

        # Add latest event if any
        if snapshot.events:
            data["event"] = snapshot.events[-1]

        return json.dumps(data)

    async def _broadcast_loop(self):
        """Periodic broadcast of metrics"""
        while self.active_connections:
            try:
                # Get snapshot
                snapshot = self.metrics_collector.get_snapshot()

                # Broadcast to all clients
                await self.broadcast(self._format_message(snapshot))

                # Clean old data
                self.metrics_collector.cleanup_old_data()

                # Wait before next broadcast
                await asyncio.sleep(5)  # Broadcast every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")
                await asyncio.sleep(5)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            # Handle commands from client
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "refresh":
                snapshot = manager.metrics_collector.get_snapshot()
                await manager.send_personal_message(
                    websocket,
                    manager._format_message(snapshot)
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# API endpoints for updating metrics
@router.post("/metrics/record")
async def record_metric(
    user_id: str,
    response_time: float,
    endpoint: str
):
    """Record a metric (called internally by middleware)"""
    manager.metrics_collector.record_request(user_id, response_time)

    # Add event for slow requests
    if response_time > 1000:  # More than 1 second
        manager.metrics_collector.add_event(
            "Performance",
            f"Slow request to {endpoint}: {response_time:.0f}ms",
            "warning"
        )

    return {"status": "recorded"}


@router.post("/metrics/event")
async def add_event(
    source: str,
    message: str,
    event_type: str = "info"
):
    """Add an event to the stream"""
    manager.metrics_collector.add_event(source, message, event_type)

    # Broadcast immediately for important events
    if event_type in ["error", "warning"]:
        snapshot = manager.metrics_collector.get_snapshot()
        await manager.broadcast(manager._format_message(snapshot))

    return {"status": "added"}


@router.get("/metrics/snapshot")
async def get_snapshot():
    """Get current metrics snapshot"""
    snapshot = manager.metrics_collector.get_snapshot()
    return {
        "timestamp": snapshot.timestamp,
        "active_users": snapshot.active_users,
        "memory_count": snapshot.memory_count,
        "request_rate": snapshot.request_rate,
        "response_times": snapshot.response_times,
        "system": {
            "cpu": snapshot.cpu_usage,
            "memory": snapshot.memory_usage,
            "disk": snapshot.disk_usage
        },
        "recent_events": snapshot.events
    }


# Middleware to track metrics
class MetricsMiddleware:
    """Middleware to automatically track request metrics"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request, call_next):
        start_time = time.time()

        # Extract user ID from request
        user_id = request.headers.get("X-User-ID", "anonymous")

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        # Record metric
        manager.metrics_collector.record_request(user_id, response_time)

        # Add response time header
        response.headers["X-Response-Time"] = f"{response_time:.2f}ms"

        return response