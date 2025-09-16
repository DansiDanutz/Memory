"""
Simple API Key Testing Script (Windows Compatible)
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import aiohttp
import requests

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

class APIKeyTester:
    def __init__(self):
        self.results = {}

    def print_header(self, title):
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60)

    def print_result(self, service, status, details=""):
        symbol = "[OK]" if status == "SUCCESS" else "[FAIL]" if status == "FAILED" else "[WARN]"
        print(f"\n{symbol} {service}: {status}")
        if details:
            print(f"      Details: {details}")

    async def test_claude_api(self):
        """Test Claude API key"""
        self.print_header("Testing Claude API Key")

        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            self.print_result("Claude API", "NOT CONFIGURED")
            self.results['claude'] = {'status': 'not_configured'}
            return False

        print(f"      Key found: {api_key[:15]}...")

        try:
            headers = {
                'anthropic-version': '2023-06-01',
                'x-api-key': api_key,
                'content-type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.anthropic.com/v1/messages',
                    headers=headers,
                    json={
                        'model': 'claude-3-haiku-20240307',
                        'messages': [{'role': 'user', 'content': 'Say test'}],
                        'max_tokens': 10
                    }
                ) as response:
                    if response.status == 200:
                        self.print_result("Claude API", "SUCCESS", "Key is valid!")
                        self.results['claude'] = {'status': 'success'}
                        return True
                    elif response.status == 401:
                        self.print_result("Claude API", "FAILED", "Invalid API key")
                        self.results['claude'] = {'status': 'invalid_key'}
                        return False
                    else:
                        self.print_result("Claude API", "FAILED", f"HTTP {response.status}")
                        self.results['claude'] = {'status': 'error', 'code': response.status}
                        return False

        except Exception as e:
            self.print_result("Claude API", "ERROR", str(e)[:50])
            self.results['claude'] = {'status': 'error'}
            return False

    async def test_azure_speech(self):
        """Test Azure Speech Services key"""
        self.print_header("Testing Azure Speech Services")

        api_key = os.getenv('AZURE_SPEECH_KEY')
        region = os.getenv('AZURE_SPEECH_REGION', 'eastus')

        if not api_key or api_key == 'your_azure_speech_key_here':
            self.print_result("Azure Speech", "NOT CONFIGURED")
            self.results['azure'] = {'status': 'not_configured'}
            return False

        try:
            token_url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            headers = {'Ocp-Apim-Subscription-Key': api_key}

            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, headers=headers) as response:
                    if response.status == 200:
                        self.print_result("Azure Speech", "SUCCESS", f"Region: {region}")
                        self.results['azure'] = {'status': 'success'}
                        return True
                    else:
                        self.print_result("Azure Speech", "FAILED", f"HTTP {response.status}")
                        self.results['azure'] = {'status': 'error'}
                        return False

        except Exception as e:
            self.print_result("Azure Speech", "ERROR", str(e)[:50])
            self.results['azure'] = {'status': 'error'}
            return False

    async def test_whatsapp_api(self):
        """Test WhatsApp/Meta API credentials"""
        self.print_header("Testing WhatsApp/Meta API")

        access_token = os.getenv('META_ACCESS_TOKEN')
        phone_id = os.getenv('WA_PHONE_NUMBER_ID')

        if not access_token or access_token == 'your_meta_access_token_here':
            self.print_result("WhatsApp API", "NOT CONFIGURED")
            self.results['whatsapp'] = {'status': 'not_configured'}
            return False

        try:
            url = f"https://graph.facebook.com/v17.0/{phone_id}"
            headers = {'Authorization': f'Bearer {access_token}'}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        self.print_result("WhatsApp API", "SUCCESS")
                        self.results['whatsapp'] = {'status': 'success'}
                        return True
                    else:
                        self.print_result("WhatsApp API", "FAILED", f"HTTP {response.status}")
                        self.results['whatsapp'] = {'status': 'error'}
                        return False

        except Exception as e:
            self.print_result("WhatsApp API", "ERROR", str(e)[:50])
            self.results['whatsapp'] = {'status': 'error'}
            return False

    def check_server_status(self):
        """Check if the FastAPI server is running"""
        self.print_header("Checking Server Status")

        try:
            response = requests.get('http://localhost:8080/health', timeout=2)
            if response.status_code == 200:
                self.print_result("FastAPI Server", "SUCCESS", "Running on port 8080")
                self.results['server'] = {'status': 'running'}
                return True
        except:
            self.print_result("FastAPI Server", "NOT RUNNING")
            self.results['server'] = {'status': 'not_running'}
            return False

    async def run_all_tests(self):
        """Run all API tests"""
        print("\n" + "="*60)
        print("  MEMORY APP - API KEY VALIDATION")
        print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*60)

        # Test all services
        server_ok = self.check_server_status()
        claude_ok = await self.test_claude_api()
        azure_ok = await self.test_azure_speech()
        whatsapp_ok = await self.test_whatsapp_api()

        # Summary
        self.print_header("TEST SUMMARY")

        print("\nRequired Services:")
        print(f"  {'[OK]' if server_ok else '[FAIL]'} Server: {'Running' if server_ok else 'Not Running'}")
        print(f"  {'[OK]' if claude_ok else '[FAIL]'} Claude API: {'Valid' if claude_ok else 'Invalid/Not Set'}")
        print(f"  {'[OK]' if azure_ok else '[WARN]'} Azure Speech: {'Valid' if azure_ok else 'Not Configured'}")
        print(f"  {'[OK]' if whatsapp_ok else '[WARN]'} WhatsApp: {'Valid' if whatsapp_ok else 'Not Configured'}")

        print("\n" + "="*60)
        if claude_ok and server_ok:
            print("  RESULT: Core services (Server + Claude) are working!")
            print("  Your app can run with basic Claude chat functionality.")
        else:
            print("  RESULT: Core services need configuration")
            if not server_ok:
                print("  - Start server: python -m uvicorn app.main:app --port 8080")
            if not claude_ok:
                print("  - Check your Claude API key in .env file")
        print("="*60)

        # Save results
        with open('test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        return claude_ok and server_ok

async def main():
    tester = APIKeyTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
    input("\nPress Enter to continue...")