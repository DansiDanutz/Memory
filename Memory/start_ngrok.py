"""
Start ngrok tunnel programmatically
"""
import requests
import json
import time

NGROK_AUTH_TOKEN = "[YOUR_NGROK_AUTH_TOKEN]"
LOCAL_PORT = 3000

def create_ngrok_tunnel():
    """Create ngrok tunnel using API"""

    # First, let's try using pyngrok library
    try:
        from pyngrok import ngrok

        # Set auth token
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)

        # Start tunnel
        public_url = ngrok.connect(LOCAL_PORT, "http")

        print(f"✅ Ngrok tunnel created!")
        print(f"📍 Public HTTPS URL: {public_url.public_url}")
        print(f"🔗 Forwarding to: http://localhost:{LOCAL_PORT}")

        # Replace http with https in the URL
        https_url = public_url.public_url.replace("http://", "https://")
        print(f"\n🔐 Use this HTTPS URL in ElevenLabs:")
        print(f"   {https_url}")

        return https_url

    except ImportError:
        print("Installing pyngrok...")
        import subprocess
        subprocess.run(["pip", "install", "pyngrok"])

        # Try again after installing
        from pyngrok import ngrok
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(LOCAL_PORT, "http")

        https_url = public_url.public_url.replace("http://", "https://")
        print(f"✅ Ngrok tunnel created!")
        print(f"🔐 HTTPS URL: {https_url}")

        return https_url

if __name__ == "__main__":
    print("=" * 60)
    print("STARTING NGROK TUNNEL FOR MCP SERVER")
    print("=" * 60)

    url = create_ngrok_tunnel()

    print("\n" + "=" * 60)
    print("CONFIGURATION FOR ELEVENLABS:")
    print("=" * 60)
    print(f"Server URL: {url}")
    print(f"Server Type: Streamable HTTP")
    print("=" * 60)

    # Keep running
    print("\nNgrok tunnel is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ngrok tunnel...")