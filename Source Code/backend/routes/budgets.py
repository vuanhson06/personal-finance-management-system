from flask import Blueprint, request, jsonify, session
from database import SessionLocal
from routes.utils import login_required
from decimal import Decimal
from budget_service import create_budget, get_budgets as get_user_budgets, get_budget_status as check_budget_status

budgets_bp = Blueprint("budgets", __name__)

@budgets_bp.route("/", methods=["GET"])
@login_required
def list_budgets():
    period = request.args.get("period")
    if not period:
        return jsonify({"status": "error", "message": "Period query parameter (YYYY-MM) is required.", "data": None}), 400
        
    db = SessionLocal()
    try:
        budgets = get_user_budgets(session["user_id"], period, db)
        data = [
            {"id": b.BudgetID, "category_id": b.CategoryID, "limit": str(b.LimitAmount), "period": b.Period}
            for b in budgets
        ]
        return jsonify({"status": "success", "message": "Budgets retrieved.", "data": data}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@budgets_bp.route("/", methods=["POST"])
@login_required
def add_budget():
    data = request.get_json()
    if not data or not all(k in data for k in ["category_id", "limit_amount", "period"]):
        return jsonify({"status": "error", "message": "category_id, limit_amount, and period are required.", "data": None}), 400
        
    db = SessionLocal()
    try:
        budget = create_budget(
            user_id=session["user_id"],
            category_id=data["category_id"],
            limit_amount=Decimal(data["limit_amount"]),
            period=data["period"],
            db=db
        )
        return jsonify({"status": "success", "message": "Budget created.", "data": {"id": budget.BudgetID}}), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@budgets_bp.route("/status/<int:category_id>", methods=["GET"])
@login_required
def status(category_id):
    period = request.args.get("period")
    if not period:
        return jsonify({"status": "error", "message": "Period query parameter (YYYY-MM) is required.", "data": None}), 400
        
    db = SessionLocal()
    try:
        status_data = check_budget_status(
            user_id=session["user_id"],
            category_id=category_id,
            period=period,
            db=db
        )
        status_data["remaining"] = str(status_data["remaining"])
        return jsonify({"status": "success", "message": "Budget status retrieved.", "data": status_data}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

from datetime import date
from budget_service import get_all_budget_statuses

@budgets_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard_budgets():
    current_period = date.today().strftime("%Y-%m")
    db = SessionLocal()
    try:
        statuses = get_all_budget_statuses(
            user_id=session["user_id"],
            period=current_period,
            db=db
        )
        
        for s in statuses:
            s["limit"] = str(s["limit"])
            s["remaining"] = str(s["remaining"])
            s["actual_spending"] = str(s["actual_spending"])
            s["progress_percentage"] = str(s["progress_percentage"])
            
        return jsonify({"status": "success", "message": "Dashboard budgets retrieved.", "data": statuses}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

from budget_service import update_budget, delete_budget

@budgets_bp.route("/<int:id>", methods=["PUT"])
@login_required
def modify_budget(id):
    data = request.get_json()
    if not data or "limit_amount" not in data:
        return jsonify({"status": "error", "message": "limit_amount is required.", "data": None}), 400
        
    db = SessionLocal()
    try:
        updated = update_budget(
            budget_id=id,
            user_id=session["user_id"],
            limit_amount=Decimal(data["limit_amount"]),
            db=db
        )
        return jsonify({"status": "success", "message": "Budget updated.", "data": {"id": updated.BudgetID}}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@budgets_bp.route("/<int:id>", methods=["DELETE"])
@login_required
def remove_budget(id):
    db = SessionLocal()
    try:
        delete_budget(budget_id=id, user_id=session["user_id"], db=db)
        return jsonify({"status": "success", "message": "Budget deleted.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()
