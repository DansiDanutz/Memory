"""
ElevenLabs MCP Server - Proper Protocol Implementation
======================================================
Implements the MCP protocol that ElevenLabs expects
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from pathlib import Path
import glob

app = Flask(__name__)
CORS(app, origins="*", allow_headers="*", methods=["GET", "POST", "OPTIONS"])

# Configuration
PORT = 3000
BASE_PATH = r"C:\Users\dansi\Desktop\Memory\Memory"

# Index MD files
MD_FILES = {}
for md_file in glob.glob(os.path.join(BASE_PATH, "**/*.md"), recursive=True):
    file_name = os.path.basename(md_file)
    MD_FILES[file_name] = md_file

print(f"[OK] Found {len(MD_FILES)} MD files")

# In-memory storage
MEMORIES = []

# MCP Protocol Implementation
@app.route('/', methods=['GET', 'POST'])
def root():
    """Root endpoint for MCP discovery"""
    return jsonify({
        "mcp_version": "1.0",
        "server_name": "Memory Bot MCP Server",
        "server_version": "1.0.0",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        }
    })

@app.route('/initialize', methods=['POST'])
def initialize():
    """Initialize MCP connection"""
    return jsonify({
        "protocolVersion": "1.0",
        "serverInfo": {
            "name": "Memory Bot MCP Server",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {}
        }
    })

@app.route('/tools/list', methods=['GET', 'POST'])
def list_tools():
    """List available tools - MCP standard endpoint"""
    tools = [
        {
            "name": "read_md_file",
            "description": "Read any Memory Bot documentation file",
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
            "description": "Search across all Memory Bot documentation",
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
            "description": "List all available documentation files",
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

    return jsonify({
        "tools": tools
    })

@app.route('/tools/call', methods=['POST'])
def call_tool():
    """Execute a tool - MCP standard endpoint"""
    try:
        data = request.json
        tool_name = data.get('name')
        arguments = data.get('arguments', {})

        print(f"[TOOL CALL] {tool_name} with args: {arguments}")

        if tool_name == "read_md_file":
            file_name = arguments.get('file_name')
            if file_name in MD_FILES:
                with open(MD_FILES[file_name], 'r', encoding='utf-8') as f:
                    content = f.read()[:5000]  # Limit for safety
                return jsonify({
                    "content": [{"type": "text", "text": content}]
                })
            else:
                return jsonify({
                    "content": [{"type": "text", "text": f"File not found. Available: {', '.join(list(MD_FILES.keys())[:10])}..."}]
                })

        elif tool_name == "search_md_files":
            query = arguments.get('query', '').lower()
            results = []
            for file_name, file_path in list(MD_FILES.items())[:20]:  # Limit search
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if query in content.lower():
                            index = content.lower().find(query)
                            start = max(0, index - 100)
                            end = min(len(content), index + 200)
                            results.append({
                                "file": file_name,
                                "match": content[start:end]
                            })
                except:
                    pass

            return jsonify({
                "content": [{"type": "text", "text": json.dumps(results, indent=2)}]
            })

        elif tool_name == "list_md_files":
            files_list = "\n".join([f"- {name}" for name in sorted(MD_FILES.keys())[:50]])
            return jsonify({
                "content": [{"type": "text", "text": f"Available MD files ({len(MD_FILES)} total):\n{files_list}"}]
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
                "content": [{"type": "text", "text": f"Memory stored with ID: {memory['id']}"}]
            })

        elif tool_name == "get_system_info":
            info = f"""Memory Bot System:
- Gamification: 5 invites = 1 slot + voice
- Voice Tiers: Free → Coqui (5 invites) → ElevenLabs (Premium)
- MD Files: {len(MD_FILES)} available
- Features: WhatsApp, Voice, Dashboard, MCP"""
            return jsonify({
                "content": [{"type": "text", "text": info}]
            })

        else:
            return jsonify({
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]
            })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True
        })

# JSON-RPC endpoints for MCP
@app.route('/mcp', methods=['POST'])
def mcp_jsonrpc():
    """JSON-RPC endpoint for MCP"""
    try:
        data = request.json
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id', 1)

        print(f"[MCP-RPC] Method: {method}")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "1.0",
                    "serverInfo": {
                        "name": "Memory Bot MCP Server",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
        elif method == "tools/list":
            tools_response = list_tools()
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": tools_response.json
            }
        elif method == "tools/call":
            tool_result = call_tool()
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": tool_result.json
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "id": request.json.get('id', 1),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        })

# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "md_files": len(MD_FILES)
    })

# Options for CORS preflight
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 204

if __name__ == '__main__':
    print("=" * 60)
    print("MEMORY BOT MCP SERVER - ELEVENLABS PROTOCOL")
    print("=" * 60)
    print(f"Starting server on http://localhost:{PORT}")
    print(f"MD Files indexed: {len(MD_FILES)}")
    print("\nEndpoints available:")
    print("- / (discovery)")
    print("- /initialize (MCP init)")
    print("- /tools/list (list tools)")
    print("- /tools/call (execute tools)")
    print("- /mcp (JSON-RPC)")
    print("=" * 60)

    app.run(host='0.0.0.0', port=PORT, debug=True)