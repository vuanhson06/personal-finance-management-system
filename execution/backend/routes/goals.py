from flask import Blueprint, request, jsonify, session
from decimal import Decimal
from saving_service import create_goal, get_user_goals, contribute_to_goal, withdraw_from_goal
from database import SessionLocal
from routes.utils import login_required
from datetime import datetime

goals_bp = Blueprint("goals", __name__)

@goals_bp.route("/", methods=["GET"])
@login_required
def get_goals():
    db = SessionLocal()
    try:
        goals = get_user_goals(session["user_id"], db)
        data = [
            {
                "id": g.GoalID, 
                "name": g.GoalName, 
                "target": str(g.TargetAmount), 
                "current": str(g.CurrentAmount), 
                "deadline": g.Deadline.isoformat() if g.Deadline else None,
                "status": g.Status.value
            }
            for g in goals
        ]
        return jsonify({"status": "success", "message": "Goals retrieved.", "data": data}), 200
    finally:
        db.close()

@goals_bp.route("/", methods=["POST"])
@login_required
def add_goal():
    data = request.get_json()
    db = SessionLocal()
    try:
        goal = create_goal(
            user_id=session["user_id"],
            goal_name=data["name"],
            target_amount=Decimal(data["target"]),
            db=db,
            deadline=datetime.fromisoformat(data["deadline"]).date() if data.get("deadline") else None
        )
        return jsonify({"status": "success", "message": "Goal created.", "data": {"id": goal.GoalID}}), 201
    finally:
        db.close()

from saving_service import get_goal_by_id, delete_goal

@goals_bp.route("/<int:id>", methods=["GET"])
@login_required
def get_single_goal(id):
    db = SessionLocal()
    try:
        g = get_goal_by_id(session["user_id"], id, db)
        data = {
            "id": g.GoalID, 
            "name": g.GoalName, 
            "target": str(g.TargetAmount), 
            "current": str(g.CurrentAmount), 
            "deadline": g.Deadline.isoformat() if g.Deadline else None,
            "status": g.Status.value
        }
        return jsonify({"status": "success", "message": "Goal retrieved.", "data": data}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 404
    finally:
        db.close()

@goals_bp.route("/<int:id>/contribute", methods=["POST"])
@login_required
def contribute(id):
    data = request.get_json()
    db = SessionLocal()
    try:
        contribute_to_goal(
            goal_id=id,
            user_id=session["user_id"],
            account_id=data["account_id"],
            amount=Decimal(data["amount"]),
            db=db
        )
        return jsonify({"status": "success", "message": "Contribution successful.", "data": None}), 200
    except ValueError as e:
        msg = str(e)
        status_code = 422 if "Insufficient funds" in msg else 400
        return jsonify({"status": "error", "message": msg, "data": None}), status_code
    finally:
        db.close()

@goals_bp.route("/<int:id>/withdraw", methods=["POST"])
@login_required
def withdraw(id):
    data = request.get_json()
    db = SessionLocal()
    try:
        withdraw_from_goal(
            goal_id=id,
            user_id=session["user_id"],
            account_id=data["account_id"],
            amount=Decimal(data["amount"]),
            db=db
        )
        return jsonify({"status": "success", "message": "Withdrawal successful.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@goals_bp.route("/<int:id>", methods=["DELETE"])
@login_required
def remove_goal(id):
    db = SessionLocal()
    try:
        delete_goal(user_id=session["user_id"], goal_id=id, db=db)
        return jsonify({"status": "success", "message": "Goal deleted.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()
