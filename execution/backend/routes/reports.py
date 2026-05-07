from flask import Blueprint, jsonify, session, request
from database import SessionLocal
from routes.utils import login_required
from sqlalchemy import text

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/category-spending", methods=["GET"])
@login_required
def get_category_spending():
    db = SessionLocal()
    try:
        query = text("""
            SELECT CategoryName, SUM(TotalSpent) AS TotalAmount 
            FROM vw_CategoryWiseSpending 
            WHERE UserID = :user_id 
            GROUP BY CategoryName
        """)
        results = db.execute(query, {"user_id": session["user_id"]}).mappings().all()
        
        data = [{"category": row["CategoryName"], "amount": str(row["TotalAmount"])} for row in results]
        return jsonify({"status": "success", "message": "Category spending retrieved.", "data": data}), 200
    finally:
        db.close()

@reports_bp.route("/monthly-trend", methods=["GET"])
@login_required
def get_monthly_trend():
    db = SessionLocal()
    try:
        query = text("SELECT SummaryMonth AS Month, TotalIncome, TotalExpense FROM vw_MonthlySummaries WHERE UserID = :user_id ORDER BY SummaryMonth ASC")
        results = db.execute(query, {"user_id": session["user_id"]}).mappings().all()
        
        data = [{"month": row["Month"], "income": str(row["TotalIncome"]), "expense": str(row["TotalExpense"])} for row in results]
        return jsonify({"status": "success", "message": "Monthly trend retrieved.", "data": data}), 200
    finally:
        db.close()



from models import MarketWatch
from sqlalchemy import select

@reports_bp.route("/market/watchlist", methods=["POST"])
@login_required
def add_market_watch():
    data = request.get_json()
    symbol = data.get("symbol")
    asset_type = data.get("asset_type", "Stock")
    
    if not symbol:
        return jsonify({"status": "error", "message": "Symbol is required.", "data": None}), 400
        
    db = SessionLocal()
    try:
        existing = db.execute(
            select(MarketWatch).where(
                MarketWatch.UserID == session["user_id"],
                MarketWatch.AssetSymbol == symbol.upper().strip()
            )
        ).scalars().first()
        
        if existing:
            return jsonify({"status": "error", "message": "Asset is already in your watchlist.", "data": None}), 400
            
        new_watch = MarketWatch(
            UserID=session["user_id"],
            AssetSymbol=symbol.upper().strip(),
            AssetType=asset_type
        )
        db.add(new_watch)
        db.commit()
        return jsonify({"status": "success", "message": "Asset added to watchlist.", "data": {"id": new_watch.WatchID}}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()

@reports_bp.route("/market/watchlist/<int:watch_id>", methods=["DELETE"])
@login_required
def delete_market_watch(watch_id):
    db = SessionLocal()
    try:
        watch = db.execute(
            select(MarketWatch).where(
                MarketWatch.WatchID == watch_id,
                MarketWatch.UserID == session["user_id"]
            )
        ).scalars().first()
        
        if not watch:
            return jsonify({"status": "error", "message": "Watchlist entry not found.", "data": None}), 404
            
        db.delete(watch)
        db.commit()
        return jsonify({"status": "success", "message": "Asset removed from watchlist.", "data": None}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()

from market_service import get_user_watchlist_data

@reports_bp.route("/market/ticker", methods=["GET"])
@login_required
def get_market_ticker():
    db = SessionLocal()
    try:
        market_data = get_user_watchlist_data(session["user_id"], db)
        return jsonify({"status": "success", "message": "Market data retrieved.", "data": market_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()
