from functools import wraps
from flask import session, jsonify

def login_required(f):
    """
    Decorator to protect API routes.
    Checks if 'user_id' is in the session.
    If not, returns a 401 Unauthorized response.
    
    This enforces the Golden Rule (Isolation): 'user_id' is strictly
    retrieved from the Flask session, never from the request payload.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "status": "error",
                "message": "Unauthorized. Please log in.",
                "data": None
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator for Admin-Mode only routes.
    Checks:
    1. User is logged in.
    2. User's role in DB is 'Admin'.
    3. User has explicitly switched to 'admin' view_mode in session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from database import SessionLocal
        from models import User, UserRole
        
        if "user_id" not in session:
            return jsonify({"status": "error", "message": "Unauthorized. Please log in.", "data": None}), 401
            
        db = SessionLocal()
        try:
            user = db.get(User, session["user_id"])
            if not user or user.Role != UserRole.Admin:
                return jsonify({"status": "error", "message": "Forbidden. Admin access required.", "data": None}), 403
            
            # Strict check: Must have toggled to admin mode
            if session.get("view_mode") != "admin":
                return jsonify({"status": "error", "message": "Access restricted. Switch to Admin Mode.", "data": None}), 403
                
            return f(*args, **kwargs)
        finally:
            db.close()
    return decorated_function
