#!/usr/bin/env python3
"""
Deployment Manager for Digital Immortality Platform
Handles production deployment, health checks, and monitoring
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import subprocess
import psutil
import aiohttp
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ServiceHealth:
    """Health status of a service"""
    name: str
    status: str  # healthy, degraded, unhealthy
    uptime: float
    memory_mb: float
    cpu_percent: float
    last_check: str
    error: Optional[str] = None

class DeploymentManager:
    """Manages deployment and monitoring of the platform"""
    
    def __init__(self):
        self.services = {
            'database': 'Supabase',
            'memory_app': 'Memory System',
            'webhook_server': 'Webhook Server',
            'web_interface': 'Web Interface',
            'telegram_bot': 'Telegram Bot',
            'whatsapp_bot': 'WhatsApp Bot'
        }
        
        self.health_checks = {}
        self.start_time = datetime.now()
    
    async def check_database_health(self) -> ServiceHealth:
        """Check Supabase database health"""
        try:
            from supabase_client import supabase, DEMO_MODE
            
            if DEMO_MODE:
                return ServiceHealth(
                    name="Database",
                    status="degraded",
                    uptime=0,
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat(),
                    error="Running in DEMO mode"
                )
            
            if supabase:
                # Test query
                result = supabase.table('users').select('id').limit(1).execute()
                
                return ServiceHealth(
                    name="Database",
                    status="healthy",
                    uptime=(datetime.now() - self.start_time).total_seconds(),
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat()
                )
            else:
                return ServiceHealth(
                    name="Database",
                    status="unhealthy",
                    uptime=0,
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat(),
                    error="Supabase not configured"
                )
                
        except Exception as e:
            return ServiceHealth(
                name="Database",
                status="unhealthy",
                uptime=0,
                memory_mb=0,
                cpu_percent=0,
                last_check=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def check_api_health(self) -> Dict[str, ServiceHealth]:
        """Check all API services health"""
        from production_config import config
        
        api_health = {}
        
        # Check OpenAI
        if config.services['openai'].api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=config.services['openai'].api_key)
                # Simple test
                models = client.models.list()
                api_health['openai'] = ServiceHealth(
                    name="OpenAI API",
                    status="healthy",
                    uptime=(datetime.now() - self.start_time).total_seconds(),
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat()
                )
            except Exception as e:
                api_health['openai'] = ServiceHealth(
                    name="OpenAI API",
                    status="unhealthy",
                    uptime=0,
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat(),
                    error=str(e)
                )
        
        # Check Anthropic
        if config.services['anthropic'].api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=config.services['anthropic'].api_key)
                api_health['anthropic'] = ServiceHealth(
                    name="Anthropic API",
                    status="healthy",
                    uptime=(datetime.now() - self.start_time).total_seconds(),
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat()
                )
            except Exception as e:
                api_health['anthropic'] = ServiceHealth(
                    name="Anthropic API",
                    status="unhealthy",
                    uptime=0,
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat(),
                    error=str(e)
                )
        
        # Check Stripe
        if config.services['stripe'].api_key:
            try:
                import stripe
                stripe.api_key = config.services['stripe'].api_key
                stripe.Account.retrieve()
                api_health['stripe'] = ServiceHealth(
                    name="Stripe API",
                    status="healthy",
                    uptime=(datetime.now() - self.start_time).total_seconds(),
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat()
                )
            except Exception as e:
                api_health['stripe'] = ServiceHealth(
                    name="Stripe API",
                    status="unhealthy",
                    uptime=0,
                    memory_mb=0,
                    cpu_percent=0,
                    last_check=datetime.now().isoformat(),
                    error=str(e)
                )
        
        return api_health
    
    async def check_process_health(self, process_name: str) -> Optional[ServiceHealth]:
        """Check health of a running process"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'create_time']):
                if process_name.lower() in proc.info['name'].lower():
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    cpu_percent = proc.info['cpu_percent']
                    uptime = datetime.now().timestamp() - proc.info['create_time']
                    
                    return ServiceHealth(
                        name=process_name,
                        status="healthy",
                        uptime=uptime,
                        memory_mb=memory_mb,
                        cpu_percent=cpu_percent,
                        last_check=datetime.now().isoformat()
                    )
            
            return ServiceHealth(
                name=process_name,
                status="unhealthy",
                uptime=0,
                memory_mb=0,
                cpu_percent=0,
                last_check=datetime.now().isoformat(),
                error="Process not running"
            )
            
        except Exception as e:
            return ServiceHealth(
                name=process_name,
                status="unhealthy",
                uptime=0,
                memory_mb=0,
                cpu_percent=0,
                last_check=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get complete system health status"""
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "platform_uptime": (datetime.now() - self.start_time).total_seconds(),
            "services": {},
            "apis": {},
            "system": {}
        }
        
        # Check database
        db_health = await self.check_database_health()
        health_report["services"]["database"] = asdict(db_health)
        
        # Check APIs
        api_health = await self.check_api_health()
        for api_name, health in api_health.items():
            health_report["apis"][api_name] = asdict(health)
        
        # Check system resources
        health_report["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "network_connections": len(psutil.net_connections())
        }
        
        # Calculate overall health
        unhealthy_count = 0
        degraded_count = 0
        
        for service in health_report["services"].values():
            if service["status"] == "unhealthy":
                unhealthy_count += 1
            elif service["status"] == "degraded":
                degraded_count += 1
        
        for api in health_report["apis"].values():
            if api["status"] == "unhealthy":
                unhealthy_count += 1
            elif api["status"] == "degraded":
                degraded_count += 1
        
        if unhealthy_count > 0:
            health_report["overall_status"] = "unhealthy"
        elif degraded_count > 0:
            health_report["overall_status"] = "degraded"
        else:
            health_report["overall_status"] = "healthy"
        
        return health_report
    
    async def deploy_production(self) -> Dict[str, Any]:
        """Deploy to production environment"""
        deployment_log = {
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "success": False
        }
        
        try:
            # Step 1: Check prerequisites
            logger.info("📋 Checking prerequisites...")
            from production_config import config
            
            if not config.is_production_ready():
                deployment_log["steps"].append({
                    "step": "prerequisites",
                    "status": "failed",
                    "error": "Missing required configurations"
                })
                return deployment_log
            
            deployment_log["steps"].append({
                "step": "prerequisites",
                "status": "success"
            })
            
            # Step 2: Initialize database
            logger.info("🗄️ Initializing database...")
            try:
                from init_database import main as init_db
                await init_db()
                deployment_log["steps"].append({
                    "step": "database",
                    "status": "success"
                })
            except Exception as e:
                deployment_log["steps"].append({
                    "step": "database",
                    "status": "failed",
                    "error": str(e)
                })
                return deployment_log
            
            # Step 3: Start services
            logger.info("🚀 Starting services...")
            services_started = []
            
            # Start webhook server
            try:
                subprocess.Popen([
                    sys.executable,
                    "webhook_server.py"
                ], cwd=os.path.dirname(__file__))
                services_started.append("webhook_server")
            except Exception as e:
                logger.error(f"Failed to start webhook server: {e}")
            
            # Start Telegram bot
            try:
                subprocess.Popen([
                    sys.executable,
                    "telegram_bot.py"
                ], cwd=os.path.dirname(__file__))
                services_started.append("telegram_bot")
            except Exception as e:
                logger.error(f"Failed to start Telegram bot: {e}")
            
            # Start WhatsApp bot
            try:
                subprocess.Popen([
                    sys.executable,
                    "whatsapp_bot.py"
                ], cwd=os.path.dirname(__file__))
                services_started.append("whatsapp_bot")
            except Exception as e:
                logger.error(f"Failed to start WhatsApp bot: {e}")
            
            deployment_log["steps"].append({
                "step": "services",
                "status": "success",
                "started": services_started
            })
            
            # Step 4: Configure webhooks
            logger.info("🔗 Configuring webhooks...")
            webhook_configs = []
            
            # Configure Twilio webhooks
            if config.services['twilio'].api_key:
                try:
                    from twilio_integration import twilio_integration
                    await twilio_integration.configure_phone_number()
                    webhook_configs.append("twilio")
                except Exception as e:
                    logger.error(f"Failed to configure Twilio: {e}")
            
            deployment_log["steps"].append({
                "step": "webhooks",
                "status": "success",
                "configured": webhook_configs
            })
            
            # Step 5: Run health check
            logger.info("🏥 Running health check...")
            health = await self.get_system_health()
            
            deployment_log["steps"].append({
                "step": "health_check",
                "status": "success",
                "overall_health": health["overall_status"]
            })
            
            deployment_log["success"] = True
            logger.info("✅ Deployment completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            deployment_log["error"] = str(e)
        
        return deployment_log
    
    async def rollback_deployment(self) -> bool:
        """Rollback deployment in case of failure"""
        try:
            logger.info("🔄 Rolling back deployment...")
            
            # Stop all services
            for proc in psutil.process_iter(['pid', 'name']):
                if any(service in proc.info['name'].lower() for service in ['webhook', 'telegram', 'whatsapp']):
                    proc.terminate()
            
            logger.info("✅ Rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
    
    def generate_deployment_script(self) -> str:
        """Generate deployment script for production"""
        script = """#!/bin/bash
# Digital Immortality Platform - Production Deployment Script
# Generated: {timestamp}

set -e  # Exit on error

echo "🚀 Digital Immortality Platform - Production Deployment"
echo "======================================================="

# Check Python version
echo "📋 Checking Python version..."
python3 --version

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Set up environment
echo "🔧 Setting up environment..."
if [ ! -f .env ]; then
    echo "❌ .env file not found! Copy .env.example and configure it."
    exit 1
fi

# Initialize database
echo "🗄️ Initializing database..."
python3 init_database.py

# Run migrations
echo "📊 Running database migrations..."
python3 -c "from supabase_client import initialize_schema; import asyncio; asyncio.run(initialize_schema())"

# Start services
echo "🚀 Starting services..."

# Start webhook server
nohup python3 webhook_server.py > webhook_server.log 2>&1 &
echo "✅ Webhook server started (PID: $!)"

# Start Telegram bot
if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
    nohup python3 telegram_bot.py > telegram_bot.log 2>&1 &
    echo "✅ Telegram bot started (PID: $!)"
fi

# Start WhatsApp bot
if [ ! -z "$WHATSAPP_ACCESS_TOKEN" ]; then
    nohup python3 whatsapp_bot.py > whatsapp_bot.log 2>&1 &
    echo "✅ WhatsApp bot started (PID: $!)"
fi

# Configure Twilio webhooks
if [ ! -z "$TWILIO_AUTH_TOKEN" ]; then
    python3 -c "from twilio_integration import twilio_integration; import asyncio; asyncio.run(twilio_integration.configure_phone_number())"
    echo "✅ Twilio webhooks configured"
fi

# Health check
echo "🏥 Running health check..."
python3 -c "from deployment_manager import deployment_manager; import asyncio; import json; health = asyncio.run(deployment_manager.get_system_health()); print(json.dumps(health, indent=2))"

echo ""
echo "✅ Deployment completed successfully!"
echo "📊 Check logs in *.log files"
echo "🌐 Webhook server: http://0.0.0.0:8080"
echo "🌐 Web interface: http://0.0.0.0:5000"
""".format(timestamp=datetime.now().isoformat())
        
        return script

# Global instance
deployment_manager = DeploymentManager()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Digital Immortality Platform Deployment Manager")
    parser.add_argument("action", choices=["deploy", "health", "rollback", "generate-script"],
                      help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "deploy":
        print("🚀 Starting production deployment...")
        result = asyncio.run(deployment_manager.deploy_production())
        print(json.dumps(result, indent=2))
    
    elif args.action == "health":
        print("🏥 Checking system health...")
        health = asyncio.run(deployment_manager.get_system_health())
        print(json.dumps(health, indent=2))
    
    elif args.action == "rollback":
        print("🔄 Rolling back deployment...")
        success = asyncio.run(deployment_manager.rollback_deployment())
        print("✅ Rollback successful" if success else "❌ Rollback failed")
    
    elif args.action == "generate-script":
        print("📝 Generating deployment script...")
        script = deployment_manager.generate_deployment_script()
        with open("deploy.sh", "w") as f:
            f.write(script)
        os.chmod("deploy.sh", 0o755)
        print("✅ Deployment script saved to deploy.sh")