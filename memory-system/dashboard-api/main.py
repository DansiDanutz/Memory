import os
import sys
from datetime import timedelta
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from models.user import db
from routes.user import user_bp
from routes.memory import memory_bp
from routes.auth import auth_bp

# Try to import enhanced memory routes
try:
    from routes.enhanced_memory import enhanced_memory_bp
    ENHANCED_ROUTES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enhanced memory routes not available: {e}")
    ENHANCED_ROUTES_AVAILABLE = False

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'memory_system_secret_key_2024')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_NAME'] = 'memory_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Enable CORS for all routes with proper session support
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'https://*.repl.co', 'https://*.replit.dev', 'https://*.replit.app'])

# Register auth blueprint first for authentication endpoints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(memory_bp, url_prefix='/api')

# Register enhanced memory blueprint if available
if ENHANCED_ROUTES_AVAILABLE:
    app.register_blueprint(enhanced_memory_bp)
    print("✅ Enhanced memory endpoints registered")

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    # Initialize background job manager if available
    # Note: Job manager will be started in a separate thread with its own event loop
    # Don't start it here since Flask is blocking
    
    app.run(host='0.0.0.0', port=3001, debug=True)
