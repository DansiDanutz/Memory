"""
ElevenLabs MCP Server - Quick Setup
====================================
Run this server to connect with ElevenLabs Agent
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from pathlib import Path
import glob

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from ElevenLabs

# Configuration
PORT = 3000
BASE_PATH = r"C:\Users\dansi\Desktop\Memory\Memory"
ELEVENLABS_API_KEY = "[YOUR_API_KEY_HERE]"  # API key with write permissions

# Index MD files
MD_FILES = {}
for md_file in glob.glob(os.path.join(BASE_PATH, "**/*.md"), recursive=True):
    file_name = os.path.basename(md_file)
    MD_FILES[file_name] = md_file

print(f"[OK] Found {len(MD_FILES)} MD files")

# MCP Tools Definition
TOOLS = [
    {
        "name": "read_md_file",
        "description": "Read any MD documentation file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the MD file to read"
                }
            },
            "required": ["file_name"]
        }
    },
    {
        "name": "search_md_files",
        "description": "Search across all MD files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_md_files",
        "description": "List all available MD files",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "store_memory",
        "description": "Store a memory for the user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Memory content"
                },
                "category": {
                    "type": "string",
                    "description": "Category of memory"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_system_info",
        "description": "Get Memory Bot system information",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# In-memory storage for demo
MEMORIES = []

@app.route('/')
def home():
    return jsonify({
        "service": "Memory Bot MCP Server",
        "status": "running",
        "tools_available": len(TOOLS),
        "md_files_indexed": len(MD_FILES)
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/mcp/list-tools', methods=['GET'])
def list_tools():
    """ElevenLabs will call this to discover available tools"""
    return jsonify({
        "tools": TOOLS
    })

@app.route('/mcp/call-tool', methods=['POST'])
def call_tool():
    """Main endpoint for tool execution"""
    try:
        data = request.json
        tool_name = data.get('name')
        arguments = data.get('arguments', {})

        print(f"[TOOL CALL] {tool_name} with args: {arguments}")

        if tool_name == "read_md_file":
            file_name = arguments.get('file_name')
            if file_name in MD_FILES:
                with open(MD_FILES[file_name], 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    "content": [{"type": "text", "text": content[:5000]}]  # Limit for safety
                })
            else:
                return jsonify({
                    "content": [{"type": "text", "text": f"File {file_name} not found. Available files: {', '.join(MD_FILES.keys())}"}]
                })

        elif tool_name == "search_md_files":
            query = arguments.get('query', '').lower()
            results = []
            for file_name, file_path in MD_FILES.items():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if query in content.lower():
                            # Find context around match
                            index = content.lower().find(query)
                            start = max(0, index - 100)
                            end = min(len(content), index + 200)
                            snippet = content[start:end]
                            results.append({
                                "file": file_name,
                                "snippet": snippet
                            })
                except:
                    pass

            return jsonify({
                "content": [{"type": "text", "text": json.dumps(results, indent=2)}]
            })

        elif tool_name == "list_md_files":
            files_list = "\n".join([f"- {name}" for name in sorted(MD_FILES.keys())])
            return jsonify({
                "content": [{"type": "text", "text": f"Available MD files:\n{files_list}"}]
            })

        elif tool_name == "store_memory":
            content = arguments.get('content')
            category = arguments.get('category', 'general')
            memory = {
                "id": len(MEMORIES) + 1,
                "content": content,
                "category": category,
                "timestamp": datetime.now().isoformat()
            }
            MEMORIES.append(memory)
            return jsonify({
                "content": [{"type": "text", "text": f"Memory stored successfully with ID: {memory['id']}"}]
            })

        elif tool_name == "get_system_info":
            info = """
            Memory Bot System Information:
            - Gamification: 5 invites = 1 contact slot + voice avatar
            - Voice Tiers: Free (none) → Invited (Coqui) → Premium (ElevenLabs)
            - Contact Slots: Start with 3, earn more by inviting
            - MD Files Available: {}
            - Features: WhatsApp, Voice, Dashboard, MCP
            """.format(len(MD_FILES))
            return jsonify({
                "content": [{"type": "text", "text": info}]
            })

        else:
            return jsonify({
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]
            }), 400

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/mcp', methods=['POST'])
def mcp_legacy():
    """Legacy endpoint for compatibility"""
    return call_tool()

if __name__ == '__main__':
    print("=" * 60)
    print("MEMORY BOT MCP SERVER FOR ELEVENLABS")
    print("=" * 60)
    print(f"Starting server on http://localhost:{PORT}")
    print(f"MD Files indexed: {len(MD_FILES)}")
    print("\nTo connect from ElevenLabs:")
    print(f"1. Server URL: http://localhost:{PORT}")
    print("2. Transport: HTTP")
    print("3. Test with the health endpoint first")
    print("=" * 60)

    app.run(host='0.0.0.0', port=PORT, debug=True)