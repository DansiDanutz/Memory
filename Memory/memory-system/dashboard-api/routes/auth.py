from flask import Blueprint, request, jsonify, session
import os
import sys
import hashlib
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

auth_bp = Blueprint('auth', __name__)

# Database connection
def get_db_connection():
    """Get PostgreSQL connection"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not configured")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Initialize database tables
def init_db():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dashboard_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create memories table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dashboard_memories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES dashboard_users(id),
                content TEXT NOT NULL,
                category VARCHAR(50),
                security_level VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# Initialize database on module load
init_db()

@auth_bp.route('/api/signup', methods=['POST'])
def signup():
    """User signup endpoint"""
    try:
        data = request.get_json()
        name = data.get('name')
        phone_number = data.get('phone_number')
        password = data.get('password')
        
        # Validation
        if not name or not phone_number or not password:
            return jsonify({
                'success': False,
                'message': 'Name, phone number, and password are required'
            }), 400
            
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }), 400
            
        # Check if user exists
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT id FROM dashboard_users WHERE phone_number = %s', (phone_number,))
        existing_user = cur.fetchone()
        
        if existing_user:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Phone number already registered'
            }), 400
            
        # Create user
        password_hash = generate_password_hash(password)
        cur.execute('''
            INSERT INTO dashboard_users (name, phone_number, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id, name, phone_number
        ''', (name, phone_number, password_hash))
        
        new_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        # Set session
        session['user_id'] = new_user['id']
        session['user_name'] = new_user['name']
        session['phone_number'] = new_user['phone_number']
        session.permanent = True
        
        return jsonify({
            'success': True,
            'message': 'Signup successful',
            'user': {
                'id': new_user['id'],
                'name': new_user['name'],
                'phone_number': new_user['phone_number']
            }
        }), 201
        
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during signup'
        }), 500

@auth_bp.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        password = data.get('password')
        
        if not phone_number or not password:
            return jsonify({
                'success': False,
                'message': 'Phone number and password are required'
            }), 400
            
        # Find user in database
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT id, name, phone_number, password_hash 
            FROM dashboard_users 
            WHERE phone_number = %s
        ''', (phone_number,))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({
                'success': False,
                'message': 'Invalid phone number or password'
            }), 401
            
        # Set session
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['phone_number'] = user['phone_number']
        session.permanent = True
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'name': user['name'],
                'phone_number': user['phone_number']
            }
        }), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200

@auth_bp.route('/api/check-session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'user_id' in session:
        return jsonify({
            'success': True,
            'logged_in': True,
            'user': {
                'id': session['user_id'],
                'name': session.get('user_name'),
                'phone_number': session.get('phone_number')
            }
        }), 200
    else:
        return jsonify({
            'success': True,
            'logged_in': False
        }), 200

@auth_bp.route('/api/memories', methods=['GET'])
def get_memories():
    """Get user memories"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT id, content, category, security_level, created_at
            FROM dashboard_memories
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 100
        ''', (session['user_id'],))
        
        memories = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert datetime to string for JSON serialization
        for memory in memories:
            if memory['created_at']:
                memory['created_at'] = memory['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'memories': memories
        }), 200
        
    except Exception as e:
        print(f"Get memories error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve memories'
        }), 500

@auth_bp.route('/api/memories', methods=['POST'])
def create_memory():
    """Create a new memory"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
        
    try:
        data = request.get_json()
        content = data.get('content')
        category = data.get('category', 'general')
        security_level = data.get('security_level', 'normal')
        
        if not content:
            return jsonify({
                'success': False,
                'message': 'Content is required'
            }), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO dashboard_memories (user_id, content, category, security_level)
            VALUES (%s, %s, %s, %s)
            RETURNING id, content, category, security_level, created_at
        ''', (session['user_id'], content, category, security_level))
        
        new_memory = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if new_memory['created_at']:
            new_memory['created_at'] = new_memory['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Memory saved successfully',
            'memory': new_memory
        }), 201
        
    except Exception as e:
        print(f"Create memory error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to save memory'
        }), 500

@auth_bp.route('/api/voice-search', methods=['POST'])
def voice_search():
    """Voice-authenticated memory search"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
        
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Search memories with pattern matching
        cur.execute('''
            SELECT id, content, category, security_level, created_at
            FROM dashboard_memories
            WHERE user_id = %s 
            AND (content ILIKE %s OR category ILIKE %s)
            ORDER BY created_at DESC
            LIMIT 50
        ''', (session['user_id'], f'%{query}%', f'%{query}%'))
        
        memories = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert datetime to string
        for memory in memories:
            if memory['created_at']:
                memory['created_at'] = memory['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'memories': memories,
            'count': len(memories)
        }), 200
        
    except Exception as e:
        print(f"Voice search error: {e}")
        return jsonify({
            'success': False,
            'message': 'Search failed'
        }), 500

@auth_bp.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get user statistics"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get memory count by category
        cur.execute('''
            SELECT category, COUNT(*) as count
            FROM dashboard_memories
            WHERE user_id = %s
            GROUP BY category
        ''', (session['user_id'],))
        
        categories = cur.fetchall()
        
        # Get total memories
        cur.execute('''
            SELECT COUNT(*) as total
            FROM dashboard_memories
            WHERE user_id = %s
        ''', (session['user_id'],))
        
        total = cur.fetchone()
        
        # Get memory count by security level
        cur.execute('''
            SELECT security_level, COUNT(*) as count
            FROM dashboard_memories
            WHERE user_id = %s
            GROUP BY security_level
        ''', (session['user_id'],))
        
        security_levels = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_memories': total['total'] if total else 0,
                'by_category': categories,
                'by_security_level': security_levels
            }
        }), 200
        
    except Exception as e:
        print(f"Statistics error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get statistics'
        }), 500

@auth_bp.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint for Aria AI assistant"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
        
    try:
        import openai
        from openai import OpenAI
        
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400
            
        # Store the message as a memory
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user's name for personalized response
        user_name = session.get('user_name', 'Friend')
        
        # Save user message
        cur.execute('''
            INSERT INTO dashboard_memories (user_id, content, category, security_level)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (session['user_id'], message, 'chat', 'normal'))
        
        conn.commit()
        
        # Get recent conversation history for context
        cur.execute('''
            SELECT content FROM dashboard_memories 
            WHERE user_id = %s AND category = 'chat'
            ORDER BY created_at DESC LIMIT 10
        ''', (session['user_id'],))
        
        recent_memories = cur.fetchall()
        
        # Build conversation context
        conversation_context = []
        for memory in reversed(recent_memories[1:6]):  # Get last 5 messages for context
            conversation_context.append(memory['content'])
        
        # Generate AI response using OpenAI
        try:
            client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            
            # Create Aria's personality prompt
            system_prompt = f"""You are Aria, a friendly and intelligent AI memory assistant. 
            You help users store, organize, and retrieve their memories. 
            You're warm, empathetic, and always ready to help.
            The user's name is {user_name}.
            
            Your capabilities include:
            - Storing important memories and conversations
            - Helping organize thoughts and experiences
            - Providing a safe space for personal reflection
            - Offering gentle reminders and insights about past memories
            - Being a supportive companion for memory keeping
            
            Always be helpful, encouraging, and respectful of the user's privacy and memories.
            If this is your first interaction with the user, introduce yourself warmly."""
            
            # Check if this is first interaction
            cur.execute('''
                SELECT COUNT(*) as count FROM dashboard_memories 
                WHERE user_id = %s AND category = 'chat'
            ''', (session['user_id'],))
            
            interaction_count = cur.fetchone()['count']
            
            if interaction_count <= 1:
                system_prompt += "\n\nThis is your first interaction with this user. Introduce yourself as Aria and explain how you can help them with their memories."
            
            # Generate response
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            ai_response = completion.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Fallback response if OpenAI fails
            if interaction_count <= 1:
                ai_response = f"Hello {user_name}! I'm Aria, your personal memory assistant. I'm here to help you store and organize your thoughts, memories, and important moments. Feel free to share anything with me - I'll keep it safe and help you remember what matters most. How can I assist you today?"
            else:
                ai_response = f"Thank you for sharing that with me, {user_name}. I've safely stored your memory. Is there anything else you'd like to talk about or remember?"
        
        # Save AI response
        cur.execute('''
            INSERT INTO dashboard_memories (user_id, content, category, security_level)
            VALUES (%s, %s, %s, %s)
        ''', (session['user_id'], f"Aria: {ai_response}", 'chat', 'normal'))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'assistant_name': 'Aria'
        }), 200
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to process message'
        }), 500

@auth_bp.route('/api/memory/pending', methods=['GET'])
def get_pending_memories():
    """Get pending memories for review"""
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
        
    try:
        # For now, return empty list as we don't have a pending status yet
        return jsonify({
            'success': True,
            'memories': []
        }), 200
        
    except Exception as e:
        print(f"Get pending memories error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get pending memories'
        }), 500

@auth_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500