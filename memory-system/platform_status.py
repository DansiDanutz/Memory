#!/usr/bin/env python3
"""
Digital Immortality Platform - Status Dashboard
Shows real-time status of all platform components
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from colorama import Fore, Back, Style, init
import psutil

# Initialize colorama
init(autoreset=True)

class PlatformStatus:
    """Platform status monitoring dashboard"""
    
    def __init__(self):
        self.components = {}
    
    def print_banner(self):
        """Print platform banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║      🧠 DIGITAL IMMORTALITY PLATFORM - STATUS DASHBOARD 🧠      ║
║                                                                  ║
║         Your Memories. Your Legacy. Forever Preserved.          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
        """
        print(f"{Fore.CYAN}{banner}{Style.RESET_ALL}")
    
    def print_section(self, title: str):
        """Print section header"""
        print(f"\n{Fore.YELLOW}┌─ {title} " + "─" * (60 - len(title) - 4) + "┐{Style.RESET_ALL}")
    
    def print_status_line(self, name: str, status: str, details: str = ""):
        """Print status line with color coding"""
        # Determine status symbol and color
        if status.lower() == "active" or status.lower() == "healthy":
            symbol = "✅"
            color = Fore.GREEN
        elif status.lower() == "degraded" or status.lower() == "warning":
            symbol = "⚠️"
            color = Fore.YELLOW
        elif status.lower() == "inactive" or status.lower() == "unhealthy":
            symbol = "❌"
            color = Fore.RED
        elif status.lower() == "not configured":
            symbol = "⏭️"
            color = Fore.LIGHTBLACK_EX
        else:
            symbol = "❓"
            color = Fore.WHITE
        
        # Format and print
        name_padded = name.ljust(25)
        status_padded = status.ljust(15)
        print(f"│ {symbol} {name_padded} {color}{status_padded}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}{details}{Style.RESET_ALL}")
    
    def print_section_end(self):
        """Print section footer"""
        print(f"{Fore.YELLOW}└" + "─" * 62 + "┘{Style.RESET_ALL}")
    
    async def check_database_status(self) -> Dict[str, Any]:
        """Check database status"""
        try:
            from supabase_client import supabase, DEMO_MODE, SUPABASE_URL
            
            if DEMO_MODE:
                return {
                    "status": "Demo Mode",
                    "url": "Local Storage",
                    "tables": "N/A",
                    "connection": "Local Only"
                }
            
            if supabase:
                # Test connection
                result = supabase.table('users').select('id').limit(1).execute()
                
                # Count tables
                tables = ['users', 'memories', 'contact_profiles', 'secret_memories',
                         'commitments', 'mutual_connections', 'family_access', 'notifications']
                
                return {
                    "status": "Active",
                    "url": SUPABASE_URL[:30] + "...",
                    "tables": f"{len(tables)} tables",
                    "connection": "Connected"
                }
            else:
                return {
                    "status": "Not Configured",
                    "url": "Not Set",
                    "tables": "N/A",
                    "connection": "Disconnected"
                }
        except Exception as e:
            return {
                "status": "Unhealthy",
                "url": "Error",
                "tables": "N/A",
                "connection": str(e)[:30]
            }
    
    async def check_api_status(self) -> Dict[str, Any]:
        """Check API integrations status"""
        from production_config import config
        
        api_status = {}
        
        # Check each API
        for service_id, service_config in config.services.items():
            if service_config.api_key:
                api_status[service_config.name] = {
                    "status": "Active",
                    "configured": True
                }
            else:
                api_status[service_config.name] = {
                    "status": "Not Configured",
                    "configured": False
                }
        
        return api_status
    
    async def check_communication_status(self) -> Dict[str, Any]:
        """Check communication channels status"""
        comm_status = {}
        
        # Twilio
        try:
            from twilio_integration import twilio_integration
            twilio_status = twilio_integration.get_status()
            comm_status["Twilio (Voice/SMS)"] = {
                "status": "Active" if twilio_status['configured'] else "Not Configured",
                "phone": twilio_status.get('phone_number', 'N/A')
            }
        except:
            comm_status["Twilio (Voice/SMS)"] = {"status": "Error", "phone": "N/A"}
        
        # WhatsApp
        try:
            from whatsapp_integration import whatsapp_integration
            wa_status = whatsapp_integration.get_status()
            comm_status["WhatsApp Business"] = {
                "status": "Active" if wa_status['initialized'] else "Not Configured",
                "phone": wa_status.get('phone_number_id', 'N/A')[:15] + "..." if wa_status.get('phone_number_id') else "N/A"
            }
        except:
            comm_status["WhatsApp Business"] = {"status": "Error", "phone": "N/A"}
        
        # Telegram
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        comm_status["Telegram Bot"] = {
            "status": "Active" if telegram_token else "Not Configured",
            "bot": "Configured" if telegram_token else "N/A"
        }
        
        return comm_status
    
    async def check_payment_status(self) -> Dict[str, Any]:
        """Check payment system status"""
        try:
            from stripe_payments import stripe_payments
            status = stripe_payments.get_status()
            
            return {
                "status": "Active" if status['initialized'] else "Not Configured",
                "products": "Configured" if status['products_configured'] else "Not Set",
                "webhook": "Configured" if status['webhook_configured'] else "Not Set",
                "tiers": len([t for t, info in status['pricing_tiers'].items() if info.get('configured', True)])
            }
        except:
            return {
                "status": "Error",
                "products": "N/A",
                "webhook": "N/A",
                "tiers": 0
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        return {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "processes": len(psutil.pids()),
            "network": len(psutil.net_connections())
        }
    
    async def check_workflows(self) -> Dict[str, Any]:
        """Check running workflows"""
        workflows = {
            "Memory System": "Unknown",
            "Webhook Server": "Unknown",
            "Web Interface": "Unknown"
        }
        
        # Check for running processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'memory_app.py' in cmdline:
                    workflows["Memory System"] = "Running"
                elif 'webhook_server.py' in cmdline:
                    workflows["Webhook Server"] = "Running"
                elif 'server.js' in cmdline or 'npm' in cmdline:
                    workflows["Web Interface"] = "Running"
            except:
                pass
        
        return workflows
    
    async def display_status(self):
        """Display complete platform status"""
        self.print_banner()
        print(f"{Fore.LIGHTBLACK_EX}Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        
        # Database Status
        self.print_section("DATABASE STATUS")
        db_status = await self.check_database_status()
        self.print_status_line("Supabase", db_status["status"], f"URL: {db_status['url']}")
        self.print_status_line("Connection", db_status["connection"], db_status.get("tables", ""))
        self.print_section_end()
        
        # API Integrations
        self.print_section("AI & API INTEGRATIONS")
        api_status = await self.check_api_status()
        for api_name, status in api_status.items():
            self.print_status_line(api_name, status["status"])
        self.print_section_end()
        
        # Communication Channels
        self.print_section("COMMUNICATION CHANNELS")
        comm_status = await self.check_communication_status()
        for channel, status in comm_status.items():
            details = status.get('phone', status.get('bot', ''))
            self.print_status_line(channel, status["status"], details)
        self.print_section_end()
        
        # Payment System
        self.print_section("PAYMENT SYSTEM")
        payment_status = await self.check_payment_status()
        self.print_status_line("Stripe", payment_status["status"], 
                              f"{payment_status['tiers']} tiers configured")
        self.print_status_line("Products", payment_status["products"])
        self.print_status_line("Webhooks", payment_status["webhook"])
        self.print_section_end()
        
        # Workflows
        self.print_section("ACTIVE WORKFLOWS")
        workflows = await self.check_workflows()
        for workflow, status in workflows.items():
            self.print_status_line(workflow, status)
        self.print_section_end()
        
        # System Resources
        self.print_section("SYSTEM RESOURCES")
        resources = await self.check_system_resources()
        self.print_status_line("CPU Usage", f"{resources['cpu']:.1f}%", 
                              self.get_usage_bar(resources['cpu']))
        self.print_status_line("Memory Usage", f"{resources['memory']:.1f}%",
                              self.get_usage_bar(resources['memory']))
        self.print_status_line("Disk Usage", f"{resources['disk']:.1f}%",
                              self.get_usage_bar(resources['disk']))
        self.print_status_line("Active Processes", str(resources['processes']))
        self.print_status_line("Network Connections", str(resources['network']))
        self.print_section_end()
        
        # Quick Actions
        print(f"\n{Fore.CYAN}📋 QUICK ACTIONS:{Style.RESET_ALL}")
        print(f"  • Run tests: {Fore.YELLOW}python test_complete_platform.py{Style.RESET_ALL}")
        print(f"  • Deploy: {Fore.YELLOW}python deployment_manager.py deploy{Style.RESET_ALL}")
        print(f"  • Health check: {Fore.YELLOW}python deployment_manager.py health{Style.RESET_ALL}")
        print(f"  • View logs: {Fore.YELLOW}tail -f *.log{Style.RESET_ALL}")
        
        # Configuration Files
        print(f"\n{Fore.CYAN}📁 CONFIGURATION FILES:{Style.RESET_ALL}")
        print(f"  • Environment: {Fore.YELLOW}.env{Style.RESET_ALL}")
        print(f"  • Database: {Fore.YELLOW}complete_supabase_init.sql{Style.RESET_ALL}")
        print(f"  • Production: {Fore.YELLOW}production_config.py{Style.RESET_ALL}")
        
        # Support
        print(f"\n{Fore.CYAN}🆘 SUPPORT:{Style.RESET_ALL}")
        print(f"  • Documentation: {Fore.BLUE}https://github.com/yourusername/digital-immortality{Style.RESET_ALL}")
        print(f"  • Issues: {Fore.BLUE}https://github.com/yourusername/digital-immortality/issues{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}{'='*70}{Style.RESET_ALL}")
    
    def get_usage_bar(self, percentage: float, width: int = 20) -> str:
        """Generate a visual usage bar"""
        filled = int(percentage / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        
        if percentage < 50:
            color = Fore.GREEN
        elif percentage < 80:
            color = Fore.YELLOW
        else:
            color = Fore.RED
        
        return f"{color}{bar}{Style.RESET_ALL}"

async def main():
    """Main entry point"""
    status = PlatformStatus()
    
    # Check for watch mode
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        # Continuous monitoring mode
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            await status.display_status()
            await asyncio.sleep(5)  # Refresh every 5 seconds
    else:
        # Single run
        await status.display_status()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Monitoring stopped.{Style.RESET_ALL}")