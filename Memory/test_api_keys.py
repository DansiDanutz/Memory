"""
API Key Testing Script
Tests all configured API keys to ensure they're working properly
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
        symbol = "✓" if status == "SUCCESS" else "✗" if status == "FAILED" else "⚠"
        print(f"\n{symbol} {service}: {status}")
        if details:
            print(f"  Details: {details}")

    async def test_claude_api(self):
        """Test Claude API key"""
        self.print_header("Testing Claude API Key")

        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            self.print_result("Claude API", "NOT CONFIGURED")
            self.results['claude'] = {'status': 'not_configured', 'error': 'No API key found'}
            return False

        if not api_key.startswith('sk-ant-'):
            self.print_result("Claude API", "INVALID FORMAT", "Key should start with 'sk-ant-'")
            self.results['claude'] = {'status': 'invalid_format', 'error': 'Invalid key format'}
            return False

        try:
            # Test with a simple API call
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
                        'messages': [{'role': 'user', 'content': 'Say "test"'}],
                        'max_tokens': 10
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.print_result("Claude API", "SUCCESS", f"Model: claude-3-haiku")
                        self.results['claude'] = {'status': 'success', 'model': 'claude-3-haiku-20240307'}
                        return True
                    elif response.status == 401:
                        self.print_result("Claude API", "FAILED", "Invalid API key")
                        self.results['claude'] = {'status': 'invalid_key', 'error': 'Authentication failed'}
                        return False
                    elif response.status == 429:
                        self.print_result("Claude API", "RATE LIMITED", "Key is valid but rate limited")
                        self.results['claude'] = {'status': 'rate_limited'}
                        return True
                    else:
                        error_text = await response.text()
                        self.print_result("Claude API", "FAILED", f"Status {response.status}")
                        self.results['claude'] = {'status': 'error', 'error': error_text[:100]}
                        return False

        except Exception as e:
            self.print_result("Claude API", "ERROR", str(e)[:100])
            self.results['claude'] = {'status': 'error', 'error': str(e)[:100]}
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
            # Test token endpoint
            token_url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            headers = {'Ocp-Apim-Subscription-Key': api_key}

            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, headers=headers) as response:
                    if response.status == 200:
                        token = await response.text()
                        self.print_result("Azure Speech", "SUCCESS", f"Region: {region}")
                        self.results['azure'] = {'status': 'success', 'region': region}
                        return True
                    elif response.status == 401:
                        self.print_result("Azure Speech", "FAILED", "Invalid API key")
                        self.results['azure'] = {'status': 'invalid_key'}
                        return False
                    else:
                        self.print_result("Azure Speech", "FAILED", f"Status {response.status}")
                        self.results['azure'] = {'status': 'error', 'code': response.status}
                        return False

        except Exception as e:
            self.print_result("Azure Speech", "ERROR", str(e)[:100])
            self.results['azure'] = {'status': 'error', 'error': str(e)[:100]}
            return False

    async def test_whatsapp_api(self):
        """Test WhatsApp/Meta API credentials"""
        self.print_header("Testing WhatsApp/Meta API")

        access_token = os.getenv('META_ACCESS_TOKEN')
        phone_number_id = os.getenv('WA_PHONE_NUMBER_ID')

        if not access_token or access_token == 'your_meta_access_token_here':
            self.print_result("WhatsApp API", "NOT CONFIGURED", "Access token not set")
            self.results['whatsapp'] = {'status': 'not_configured'}
            return False

        if not phone_number_id or phone_number_id == 'your_whatsapp_phone_number_id_here':
            self.print_result("WhatsApp API", "NOT CONFIGURED", "Phone number ID not set")
            self.results['whatsapp'] = {'status': 'not_configured'}
            return False

        try:
            # Test by getting phone number details
            url = f"https://graph.facebook.com/v17.0/{phone_number_id}"
            headers = {'Authorization': f'Bearer {access_token}'}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.print_result("WhatsApp API", "SUCCESS",
                                        f"Phone: {data.get('display_phone_number', 'N/A')}")
                        self.results['whatsapp'] = {'status': 'success', 'data': data}
                        return True
                    elif response.status == 401:
                        self.print_result("WhatsApp API", "FAILED", "Invalid access token")
                        self.results['whatsapp'] = {'status': 'invalid_token'}
                        return False
                    elif response.status == 404:
                        self.print_result("WhatsApp API", "FAILED", "Invalid phone number ID")
                        self.results['whatsapp'] = {'status': 'invalid_phone_id'}
                        return False
                    else:
                        self.print_result("WhatsApp API", "FAILED", f"Status {response.status}")
                        self.results['whatsapp'] = {'status': 'error', 'code': response.status}
                        return False

        except Exception as e:
            self.print_result("WhatsApp API", "ERROR", str(e)[:100])
            self.results['whatsapp'] = {'status': 'error', 'error': str(e)[:100]}
            return False

    async def test_openai_api(self):
        """Test OpenAI API key (optional)"""
        self.print_header("Testing OpenAI API (Optional)")

        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key or api_key == 'your_openai_api_key_here':
            self.print_result("OpenAI API", "NOT CONFIGURED", "Optional - not required")
            self.results['openai'] = {'status': 'not_configured', 'required': False}
            return True  # Not required, so return True

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.openai.com/v1/models',
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        model_count = len(data.get('data', []))
                        self.print_result("OpenAI API", "SUCCESS", f"{model_count} models available")
                        self.results['openai'] = {'status': 'success', 'models': model_count}
                        return True
                    elif response.status == 401:
                        self.print_result("OpenAI API", "FAILED", "Invalid API key")
                        self.results['openai'] = {'status': 'invalid_key'}
                        return False
                    else:
                        self.print_result("OpenAI API", "FAILED", f"Status {response.status}")
                        self.results['openai'] = {'status': 'error', 'code': response.status}
                        return False

        except Exception as e:
            self.print_result("OpenAI API", "ERROR", str(e)[:100])
            self.results['openai'] = {'status': 'error', 'error': str(e)[:100]}
            return False

    def test_redis_connection(self):
        """Test Redis connection"""
        self.print_header("Testing Redis Connection")

        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            self.print_result("Redis", "SUCCESS", "Connection established")
            self.results['redis'] = {'status': 'success'}
            return True
        except ImportError:
            self.print_result("Redis", "WARNING", "Redis library not installed")
            self.results['redis'] = {'status': 'not_installed'}
            return False
        except Exception as e:
            self.print_result("Redis", "FAILED", "Connection failed - this is optional")
            self.results['redis'] = {'status': 'error', 'error': str(e)[:100]}
            return False

    def check_server_status(self):
        """Check if the FastAPI server is running"""
        self.print_header("Checking Server Status")

        try:
            response = requests.get('http://localhost:8080/health', timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.print_result("FastAPI Server", "SUCCESS", "Server is running")
                self.results['server'] = {'status': 'running', 'data': data}
                return True
            else:
                self.print_result("FastAPI Server", "WARNING", f"Status {response.status_code}")
                self.results['server'] = {'status': 'error', 'code': response.status_code}
                return False
        except requests.exceptions.ConnectionError:
            self.print_result("FastAPI Server", "NOT RUNNING", "Start with: python -m uvicorn app.main:app --port 8080")
            self.results['server'] = {'status': 'not_running'}
            return False
        except Exception as e:
            self.print_result("FastAPI Server", "ERROR", str(e)[:50])
            self.results['server'] = {'status': 'error', 'error': str(e)[:100]}
            return False

    async def run_all_tests(self):
        """Run all API tests"""
        print("\n" + "="*60)
        print("  MEMORY APP - API KEY VALIDATION TEST")
        print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*60)

        # Check server first
        server_ok = self.check_server_status()

        # Test all APIs
        claude_ok = await self.test_claude_api()
        azure_ok = await self.test_azure_speech()
        whatsapp_ok = await self.test_whatsapp_api()
        openai_ok = await self.test_openai_api()
        redis_ok = self.test_redis_connection()

        # Summary
        self.print_header("TEST SUMMARY")

        required_services = {
            'Server': server_ok,
            'Claude API': claude_ok,
            'Azure Speech': azure_ok,
            'WhatsApp API': whatsapp_ok
        }

        optional_services = {
            'OpenAI API': openai_ok,
            'Redis': redis_ok
        }

        print("\nRequired Services:")
        for service, status in required_services.items():
            symbol = "✓" if status else "✗"
            print(f"  {symbol} {service}: {'OK' if status else 'FAILED'}")

        print("\nOptional Services:")
        for service, status in optional_services.items():
            symbol = "✓" if status else "⚠"
            print(f"  {symbol} {service}: {'OK' if status else 'NOT CONFIGURED'}")

        all_required_ok = all(required_services.values())

        print("\n" + "="*60)
        if all_required_ok:
            print("  RESULT: ✓ ALL REQUIRED SERVICES CONFIGURED")
            print("  Your Memory App is ready to use!")
        else:
            print("  RESULT: ✗ SOME REQUIRED SERVICES NEED CONFIGURATION")
            print("  Please configure the missing services in your .env file")
        print("="*60)

        # Save results
        results_file = Path(__file__).parent / 'api_test_results.json'
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results,
                'all_required_ok': all_required_ok
            }, f, indent=2)
        print(f"\nDetailed results saved to: {results_file}")

        return all_required_ok

async def main():
    tester = APIKeyTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    input("\nPress Enter to exit...")
    sys.exit(exit_code)