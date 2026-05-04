from flask import Blueprint, jsonify, session, request
from database import SessionLocal
from routes.utils import admin_required, login_required
from models import User, UserRole, AdminLog, WebhookLog, Income, Expense, Category
from sqlalchemy import select, func, text
from datetime import datetime
from decimal import Decimal

admin_bp = Blueprint("admin", __name__)

# --- Helper: Log Admin Action ---
def log_admin_action(action, target_user_id=None):
    db = SessionLocal()
    try:
        log = AdminLog(
            AdminID=session["user_id"],
            Action=action,
            TargetUserID=target_user_id
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Failed to log admin action: {e}")
    finally:
        db.close()

# =============================================================================
# User Management
# =============================================================================

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    db = SessionLocal()
    try:
        users = db.execute(select(User).order_by(User.UserID)).scalars().all()
        data = [
            {
                "id": u.UserID,
                "username": u.UserName,
                "email": u.Email,
                "role": u.Role.value,
                "is_active": u.IsActive,
                "created_at": u.CreatedAt.isoformat()
            }
            for u in users
        ]
        return jsonify({"status": "success", "message": "Users retrieved.", "data": data}), 200
    finally:
        db.close()

@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["PUT"])
@admin_required
def toggle_user_status(user_id):
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found.", "data": None}), 404
            
        if user.UserID == session["user_id"]:
            return jsonify({"status": "error", "message": "You cannot lock your own account.", "data": None}), 400
            
        user.IsActive = not user.IsActive
        db.commit()
        
        status_text = "Unlocked" if user.IsActive else "Locked"
        log_admin_action(f"{status_text} User #{user_id} ({user.Email})", target_user_id=user_id)
        
        return jsonify({"status": "success", "message": f"User {status_text.lower()} successfully.", "data": {"is_active": user.IsActive}}), 200
    finally:
        db.close()

# =============================================================================
# System Health (Webhook Monitor)
# =============================================================================

@admin_bp.route("/system-health", methods=["GET"])
@admin_required
def get_system_health():
    db = SessionLocal()
    try:
        # Total registered users count
        from models import User
        total_users = db.execute(select(func.count(User.UserID))).scalar()
        
        return jsonify({
            "status": "success",
            "data": {
                "metrics": {
                    "total_users": total_users
                }
            }
        }), 200
    finally:
        db.close()

# =============================================================================
# Global Analytics
# =============================================================================

@admin_bp.route("/analytics/global", methods=["GET"])
@admin_required
def get_global_analytics():
    db = SessionLocal()
    try:
        # 1. Global Spending Distribution (Platform Volume by Category)
        # We'll aggregate Expenses across all users
        dist_query = text("""
            SELECT c.CategoryName, SUM(e.Amount) as TotalAmount
            FROM Expenses e
            JOIN Categories c ON e.CategoryID = c.CategoryID
            GROUP BY c.CategoryName
            ORDER BY TotalAmount DESC
        """)
        dist_results = db.execute(dist_query).mappings().all()
        distribution = [{"category": r["CategoryName"], "amount": str(r["TotalAmount"])} for r in dist_results]
        
        # 2. Activity Heatmap (Transactions per Hour)
        # --- Heatmap Aggregation (Activity Density) ---
        # Returns [ {day: 1..7, hour: 0..23, count: X}, ... ]
        # Note: DAYOFWEEK returns 1 (Sun) to 7 (Sat) in MySQL.
        heatmap_query = text("""
            SELECT DAYOFWEEK(CreatedAt) as Day, HOUR(CreatedAt) as Hour, COUNT(*) as Count
            FROM (
                SELECT CreatedAt FROM Income
                UNION ALL
                SELECT CreatedAt FROM Expenses
            ) as combined
            GROUP BY Day, Hour
            ORDER BY Day, Hour
        """)
        heatmap_results = db.execute(heatmap_query).mappings().all()
        heatmap_data = [
            {"day": r["Day"], "hour": r["Hour"], "count": r["Count"]}
            for r in heatmap_results
        ]
        
        return jsonify({
            "status": "success",
            "data": {
                "distribution": distribution,
                "heatmap": heatmap_data
            }
        }), 200
    finally:
        db.close()

# =============================================================================
# Audit Trail
# =============================================================================

@admin_bp.route("/logs", methods=["GET"])
@admin_required
def get_admin_logs():
    db = SessionLocal()
    try:
        logs = db.execute(select(AdminLog).order_by(AdminLog.Timestamp.desc()).limit(50)).scalars().all()
        data = [
            {
                "id": l.LogID,
                "admin_id": l.AdminID,
                "action": l.Action,
                "target_id": l.TargetUserID,
                "timestamp": l.Timestamp.isoformat()
            }
            for l in logs
        ]
        return jsonify({"status": "success", "data": data}), 200
    finally:
        db.close()
