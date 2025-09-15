#!/usr/bin/env python3
"""
Health Monitoring and Metrics for Memory App Platform
Provides comprehensive health checks, metrics collection, and monitoring
"""

import os
import sys
import json
import time
import asyncio
import psutil
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, jsonify, request
import psycopg2
import redis
import requests
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import threading

logger = logging.getLogger(__name__)

# ============================================
# Health Status Enums
# ============================================

class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class CheckType(Enum):
    """Types of health checks"""
    LIVENESS = "liveness"      # Is the service alive?
    READINESS = "readiness"     # Is the service ready to accept traffic?
    STARTUP = "startup"         # Has the service started successfully?

# ============================================
# Metrics Definitions
# ============================================

# Request metrics
request_count = Counter('memory_app_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('memory_app_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_requests = Gauge('memory_app_active_requests', 'Active requests')

# System metrics
cpu_usage = Gauge('memory_app_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('memory_app_memory_usage_bytes', 'Memory usage in bytes')
disk_usage = Gauge('memory_app_disk_usage_percent', 'Disk usage percentage')

# Database metrics
db_connections = Gauge('memory_app_db_connections', 'Active database connections')
db_query_duration = Histogram('memory_app_db_query_duration_seconds', 'Database query duration')
db_errors = Counter('memory_app_db_errors_total', 'Total database errors')

# Business metrics
memories_created = Counter('memory_app_memories_created_total', 'Total memories created')
users_active = Gauge('memory_app_users_active', 'Active users in last 24h')
api_calls = Counter('memory_app_api_calls_total', 'Total API calls', ['service', 'endpoint'])

# ============================================
# Health Check Models
# ============================================

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: ServiceStatus
    message: str
    duration_ms: float
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SystemHealth:
    """Overall system health"""
    status: ServiceStatus
    checks: List[HealthCheckResult]
    version: str
    environment: str
    uptime_seconds: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'environment': self.environment,
            'uptime_seconds': self.uptime_seconds,
            'checks': [
                {
                    'name': check.name,
                    'status': check.status.value,
                    'message': check.message,
                    'duration_ms': check.duration_ms,
                    'metadata': check.metadata
                }
                for check in self.checks
            ]
        }

# ============================================
# Health Check Service
# ============================================

class HealthMonitor:
    """Main health monitoring service"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.start_time = datetime.now()
        self.checks: List[HealthCheckResult] = []
        self.monitoring_thread = None
        self.is_running = False
        
        # Configuration
        self.config = {
            'check_interval': int(os.getenv('HEALTH_CHECK_INTERVAL', '30000')) / 1000,
            'timeout': int(os.getenv('HEALTH_CHECK_TIMEOUT', '5000')) / 1000,
            'failure_threshold': int(os.getenv('HEALTH_CHECK_FAILURE_THRESHOLD', '3')),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'version': os.getenv('APP_VERSION', '1.0.0')
        }
        
        # Track failures for circuit breaking
        self.failure_counts = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize health monitoring with Flask app"""
        self.app = app
        
        # Register health check endpoints
        app.route('/health')(self.health_endpoint)
        app.route('/health/live')(self.liveness_endpoint)
        app.route('/health/ready')(self.readiness_endpoint)
        app.route('/health/startup')(self.startup_endpoint)
        app.route('/metrics')(self.metrics_endpoint)
        
        # Start background monitoring
        self.start_monitoring()
        
        logger.info("✅ Health monitoring initialized")
    
    # ============================================
    # Health Check Methods
    # ============================================
    
    async def check_database(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            # Import database client
            from postgres_db_client import get_connection
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Simple query to check connectivity
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Check table existence
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            
            # Check connection pool status
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            active_connections = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            duration = (time.time() - start_time) * 1000
            
            # Update metrics
            db_connections.set(active_connections)
            
            return HealthCheckResult(
                name="database",
                status=ServiceStatus.HEALTHY,
                message="Database is healthy",
                duration_ms=duration,
                metadata={
                    'tables': table_count,
                    'active_connections': active_connections
                }
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            db_errors.inc()
            
            return HealthCheckResult(
                name="database",
                status=ServiceStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                duration_ms=duration
            )
    
    async def check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity"""
        start_time = time.time()
        
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            r = redis.from_url(redis_url)
            
            # Ping Redis
            r.ping()
            
            # Get info
            info = r.info()
            memory_used = info.get('used_memory', 0)
            connected_clients = info.get('connected_clients', 0)
            
            duration = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="redis",
                status=ServiceStatus.HEALTHY,
                message="Redis is healthy",
                duration_ms=duration,
                metadata={
                    'memory_used_mb': memory_used / 1024 / 1024,
                    'connected_clients': connected_clients
                }
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            # Redis is optional, so degraded not unhealthy
            return HealthCheckResult(
                name="redis",
                status=ServiceStatus.DEGRADED,
                message=f"Redis not available: {str(e)}",
                duration_ms=duration
            )
    
    async def check_api_services(self) -> List[HealthCheckResult]:
        """Check external API services"""
        results = []
        
        # Check OpenAI
        if os.getenv('OPENAI_API_KEY'):
            start_time = time.time()
            try:
                import openai
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                # Use models endpoint as health check
                models = client.models.list()
                duration = (time.time() - start_time) * 1000
                
                results.append(HealthCheckResult(
                    name="openai",
                    status=ServiceStatus.HEALTHY,
                    message="OpenAI API is accessible",
                    duration_ms=duration
                ))
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                results.append(HealthCheckResult(
                    name="openai",
                    status=ServiceStatus.DEGRADED,
                    message=f"OpenAI API check failed: {str(e)}",
                    duration_ms=duration
                ))
        
        # Check Stripe
        if os.getenv('STRIPE_SECRET_KEY'):
            start_time = time.time()
            try:
                import stripe
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                # Simple API call to check connectivity
                stripe.Balance.retrieve()
                duration = (time.time() - start_time) * 1000
                
                results.append(HealthCheckResult(
                    name="stripe",
                    status=ServiceStatus.HEALTHY,
                    message="Stripe API is accessible",
                    duration_ms=duration
                ))
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                results.append(HealthCheckResult(
                    name="stripe",
                    status=ServiceStatus.DEGRADED,
                    message=f"Stripe API check failed: {str(e)}",
                    duration_ms=duration
                ))
        
        return results
    
    async def check_disk_space(self) -> HealthCheckResult:
        """Check available disk space"""
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage('/')
            duration = (time.time() - start_time) * 1000
            
            # Update metrics
            disk_usage.set(disk.percent)
            
            # Determine status based on usage
            if disk.percent > 95:
                status = ServiceStatus.UNHEALTHY
                message = f"Critical: Disk usage at {disk.percent}%"
            elif disk.percent > 85:
                status = ServiceStatus.DEGRADED
                message = f"Warning: Disk usage at {disk.percent}%"
            else:
                status = ServiceStatus.HEALTHY
                message = f"Disk usage at {disk.percent}%"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'total_gb': disk.total / 1024 / 1024 / 1024,
                    'used_gb': disk.used / 1024 / 1024 / 1024,
                    'free_gb': disk.free / 1024 / 1024 / 1024,
                    'percent': disk.percent
                }
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="disk_space",
                status=ServiceStatus.UNKNOWN,
                message=f"Disk check failed: {str(e)}",
                duration_ms=duration
            )
    
    async def check_memory(self) -> HealthCheckResult:
        """Check memory usage"""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            duration = (time.time() - start_time) * 1000
            
            # Update metrics
            memory_usage.set(process_memory.rss)
            
            # Determine status
            if memory.percent > 90:
                status = ServiceStatus.UNHEALTHY
                message = f"Critical: Memory usage at {memory.percent}%"
            elif memory.percent > 80:
                status = ServiceStatus.DEGRADED
                message = f"Warning: Memory usage at {memory.percent}%"
            else:
                status = ServiceStatus.HEALTHY
                message = f"Memory usage at {memory.percent}%"
            
            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'system_total_gb': memory.total / 1024 / 1024 / 1024,
                    'system_available_gb': memory.available / 1024 / 1024 / 1024,
                    'system_percent': memory.percent,
                    'process_rss_mb': process_memory.rss / 1024 / 1024,
                    'process_vms_mb': process_memory.vms / 1024 / 1024
                }
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="memory",
                status=ServiceStatus.UNKNOWN,
                message=f"Memory check failed: {str(e)}",
                duration_ms=duration
            )
    
    async def check_cpu(self) -> HealthCheckResult:
        """Check CPU usage"""
        start_time = time.time()
        
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = os.getloadavg()
            
            duration = (time.time() - start_time) * 1000
            
            # Update metrics
            cpu_usage.set(cpu_percent)
            
            # Determine status
            if cpu_percent > 90:
                status = ServiceStatus.UNHEALTHY
                message = f"Critical: CPU usage at {cpu_percent}%"
            elif cpu_percent > 75:
                status = ServiceStatus.DEGRADED
                message = f"Warning: CPU usage at {cpu_percent}%"
            else:
                status = ServiceStatus.HEALTHY
                message = f"CPU usage at {cpu_percent}%"
            
            return HealthCheckResult(
                name="cpu",
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    'percent': cpu_percent,
                    'cores': cpu_count,
                    'load_1min': load_avg[0],
                    'load_5min': load_avg[1],
                    'load_15min': load_avg[2]
                }
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="cpu",
                status=ServiceStatus.UNKNOWN,
                message=f"CPU check failed: {str(e)}",
                duration_ms=duration
            )
    
    # ============================================
    # Health Check Orchestration
    # ============================================
    
    async def run_all_checks(self) -> SystemHealth:
        """Run all health checks"""
        checks = []
        
        # Run infrastructure checks
        checks.append(await self.check_database())
        checks.append(await self.check_redis())
        checks.append(await self.check_disk_space())
        checks.append(await self.check_memory())
        checks.append(await self.check_cpu())
        
        # Run API service checks
        api_checks = await self.check_api_services()
        checks.extend(api_checks)
        
        # Determine overall status
        unhealthy_count = sum(1 for c in checks if c.status == ServiceStatus.UNHEALTHY)
        degraded_count = sum(1 for c in checks if c.status == ServiceStatus.DEGRADED)
        
        if unhealthy_count > 0:
            overall_status = ServiceStatus.UNHEALTHY
        elif degraded_count > 2:  # More than 2 degraded services
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.HEALTHY
        
        # Calculate uptime
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return SystemHealth(
            status=overall_status,
            checks=checks,
            version=self.config['version'],
            environment=self.config['environment'],
            uptime_seconds=uptime
        )
    
    # ============================================
    # Background Monitoring
    # ============================================
    
    def start_monitoring(self):
        """Start background monitoring thread"""
        if not self.is_running:
            self.is_running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            logger.info("Started background health monitoring")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Stopped background health monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                # Run health checks
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                health = loop.run_until_complete(self.run_all_checks())
                loop.close()
                
                # Store results
                self.checks = health.checks
                
                # Log unhealthy services
                for check in health.checks:
                    if check.status == ServiceStatus.UNHEALTHY:
                        logger.error(f"Health check failed: {check.name} - {check.message}")
                    elif check.status == ServiceStatus.DEGRADED:
                        logger.warning(f"Health check degraded: {check.name} - {check.message}")
                
                # Check for alerts
                self._check_alerts(health)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Sleep for interval
            time.sleep(self.config['check_interval'])
    
    def _check_alerts(self, health: SystemHealth):
        """Check if alerts need to be sent"""
        # Track consecutive failures
        for check in health.checks:
            if check.status == ServiceStatus.UNHEALTHY:
                self.failure_counts[check.name] = self.failure_counts.get(check.name, 0) + 1
                
                # Send alert after threshold
                if self.failure_counts[check.name] == self.config['failure_threshold']:
                    self._send_alert(check)
            else:
                # Reset counter on recovery
                if check.name in self.failure_counts:
                    if self.failure_counts[check.name] >= self.config['failure_threshold']:
                        self._send_recovery_alert(check)
                    del self.failure_counts[check.name]
    
    def _send_alert(self, check: HealthCheckResult):
        """Send alert for failed health check"""
        logger.critical(f"ALERT: Service {check.name} has failed {self.config['failure_threshold']} consecutive checks")
        
        # Send to monitoring service (e.g., PagerDuty, Slack)
        webhook_url = os.getenv('ALERT_WEBHOOK_URL')
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'service': check.name,
                    'status': 'down',
                    'message': check.message,
                    'environment': self.config['environment']
                }, timeout=5)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
    
    def _send_recovery_alert(self, check: HealthCheckResult):
        """Send recovery alert"""
        logger.info(f"RECOVERY: Service {check.name} has recovered")
        
        webhook_url = os.getenv('ALERT_WEBHOOK_URL')
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'service': check.name,
                    'status': 'recovered',
                    'message': f"Service {check.name} has recovered",
                    'environment': self.config['environment']
                }, timeout=5)
            except Exception as e:
                logger.error(f"Failed to send recovery alert: {e}")
    
    # ============================================
    # HTTP Endpoints
    # ============================================
    
    def health_endpoint(self):
        """Main health check endpoint"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        health = loop.run_until_complete(self.run_all_checks())
        loop.close()
        
        status_code = 200 if health.status == ServiceStatus.HEALTHY else 503
        return jsonify(health.to_dict()), status_code
    
    def liveness_endpoint(self):
        """Liveness probe - is the service alive?"""
        # Simple check - if we can respond, we're alive
        return jsonify({
            'status': 'alive',
            'timestamp': datetime.now().isoformat()
        }), 200
    
    def readiness_endpoint(self):
        """Readiness probe - can we accept traffic?"""
        # Check critical dependencies
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Only check database as it's critical
        db_check = loop.run_until_complete(self.check_database())
        loop.close()
        
        if db_check.status == ServiceStatus.HEALTHY:
            return jsonify({
                'status': 'ready',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'not_ready',
                'reason': db_check.message,
                'timestamp': datetime.now().isoformat()
            }), 503
    
    def startup_endpoint(self):
        """Startup probe - has the service started successfully?"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Consider started after 10 seconds
        if uptime > 10:
            return jsonify({
                'status': 'started',
                'uptime_seconds': uptime,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'starting',
                'uptime_seconds': uptime,
                'timestamp': datetime.now().isoformat()
            }), 503
    
    def metrics_endpoint(self):
        """Prometheus metrics endpoint"""
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# ============================================
# Middleware for Metrics Collection
# ============================================

def init_metrics_middleware(app: Flask):
    """Initialize metrics collection middleware"""
    
    @app.before_request
    def before_request():
        request.start_time = time.time()
        active_requests.inc()
    
    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Record metrics
            request_count.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status=response.status_code
            ).inc()
            
            request_duration.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).observe(duration)
        
        active_requests.dec()
        return response

# ============================================
# Export
# ============================================

__all__ = [
    'HealthMonitor',
    'ServiceStatus',
    'CheckType',
    'HealthCheckResult',
    'SystemHealth',
    'init_metrics_middleware'
]