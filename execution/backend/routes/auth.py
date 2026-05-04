from flask import Blueprint, request, jsonify, session
from auth_service import login_user, register_user, get_user_by_id
from database import SessionLocal
from routes.utils import login_required

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"status": "error", "message": "Email and password are required.", "data": None}), 400

    db = SessionLocal()
    try:
        user = login_user(data["email"], data["password"], db)
        session["user_id"] = user.UserID
        session["role"] = user.Role.value
        session["view_mode"] = "user" # Default context is always 'user'
        return jsonify({
            "status": "success",
            "message": "Login successful.",
            "data": {"user_id": user.UserID, "username": user.UserName, "email": user.Email, "role": user.Role.value, "view_mode": session["view_mode"]}
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@auth_bp.route("/signup", methods=["POST"])
def register():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data or "username" not in data:
        return jsonify({"status": "error", "message": "Username, email, and password are required.", "data": None}), 400

    db = SessionLocal()
    try:
        user = register_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            db=db,
            phone=data.get("phone")
        )
        session["user_id"] = user.UserID
        return jsonify({
            "status": "success",
            "message": "Registration successful.",
            "data": {"user_id": user.UserID, "username": user.UserName, "email": user.Email}
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    from flask import redirect
    return redirect("/login")

@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    db = SessionLocal()
    try:
        user = get_user_by_id(session["user_id"], db)
        return jsonify({
            "status": "success",
            "message": "User profile retrieved.",
            "data": {
                "user_id": user.UserID, 
                "username": user.UserName, 
                "email": user.Email, 
                "phone": user.PhoneNumber, 
                "role": user.Role.value,
                "joined_at": user.CreatedAt.isoformat()
            }
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 404
    finally:
        db.close()

@auth_bp.route("/switch-mode", methods=["POST"])
@login_required
def switch_mode():
    """
    Toggles the session view_mode for Admins.
    """
    db = SessionLocal()
    try:
        from models import User, UserRole
        user = db.get(User, session["user_id"])
        
        if not user or user.Role != UserRole.Admin:
            return jsonify({"status": "error", "message": "Only administrators can switch modes.", "data": None}), 403
            
        current_mode = session.get("view_mode", "user")
        new_mode = "admin" if current_mode == "user" else "user"
        session["view_mode"] = new_mode
        
        return jsonify({
            "status": "success", 
            "message": f"Switched to {new_mode.capitalize()} Mode.", 
            "data": {"view_mode": new_mode}
        }), 200
    finally:
        db.close()

@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json()
    if not data or "current_password" not in data or "new_password" not in data:
        return jsonify({"status": "error", "message": "Current and new passwords are required.", "data": None}), 400

    db = SessionLocal()
    try:
        from auth_service import update_user_password
        update_user_password(
            user_id=session["user_id"],
            current_password=data["current_password"],
            new_password=data["new_password"],
            db=db
        )
        return jsonify({"status": "success", "message": "Password updated successfully.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()
