from functools import wraps
from flask import session, jsonify

def login_required(f):
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
            
            if session.get("view_mode") != "admin":
                return jsonify({"status": "error", "message": "Access restricted. Switch to Admin Mode.", "data": None}), 403
                
            return f(*args, **kwargs)
        finally:
            db.close()
    return decorated_function
