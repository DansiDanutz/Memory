#!/usr/bin/env python3
"""
Admin Dashboard Server
Serves the admin dashboard interface and handles static files
"""

import os
from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='admin-dashboard')
CORS(app)

# Dashboard directory
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), 'admin-dashboard')

@app.route('/admin/')
@app.route('/admin')
def serve_admin_dashboard():
    """Serve the admin dashboard main page"""
    return send_from_directory(DASHBOARD_DIR, 'index.html')

@app.route('/admin/<path:path>')
def serve_admin_files(path):
    """Serve admin dashboard static files"""
    # Check if file exists
    file_path = os.path.join(DASHBOARD_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(DASHBOARD_DIR, path)
    else:
        # Return index.html for client-side routing
        return send_from_directory(DASHBOARD_DIR, 'index.html')

@app.route('/admin/styles.css')
def serve_admin_styles():
    """Serve admin dashboard styles"""
    return send_from_directory(DASHBOARD_DIR, 'styles.css')

@app.route('/admin/admin.js')
def serve_admin_script():
    """Serve admin dashboard JavaScript"""
    return send_from_directory(DASHBOARD_DIR, 'admin.js')

# Add to webhook_server_complete.py instead of running separately
def init_admin_server(flask_app):
    """Initialize admin server routes in main Flask app"""
    
    @flask_app.route('/admin/')
    @flask_app.route('/admin')
    def serve_admin_dashboard():
        """Serve the admin dashboard main page"""
        return send_from_directory(DASHBOARD_DIR, 'index.html')
    
    @flask_app.route('/admin/<path:path>')
    def serve_admin_files(path):
        """Serve admin dashboard static files"""
        file_path = os.path.join(DASHBOARD_DIR, path)
        if os.path.exists(file_path):
            return send_from_directory(DASHBOARD_DIR, path)
        else:
            return send_from_directory(DASHBOARD_DIR, 'index.html')
    
    logger.info("👨‍💼 Admin Dashboard Server initialized")
    logger.info("📍 Admin dashboard available at: /admin")

if __name__ == '__main__':
    logger.info("🚀 Starting Admin Dashboard Server")
    logger.info("📍 Admin dashboard available at: http://localhost:9090/admin")
    app.run(host='0.0.0.0', port=9090, debug=False)