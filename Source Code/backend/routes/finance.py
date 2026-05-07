from flask import Blueprint, request, jsonify, session
from datetime import datetime
from transaction_service import add_income, add_expense, get_income_list, get_expense_list
from database import SessionLocal
from routes.utils import login_required
from decimal import Decimal

finance_bp = Blueprint("finance", __name__)

@finance_bp.route("/accounts", methods=["GET"])
@login_required
def get_accounts():
    db = SessionLocal()
    try:
        from models import BankAccount
        from sqlalchemy import select
        accounts = db.execute(select(BankAccount).where(BankAccount.UserID == session["user_id"])).scalars().all()
        return jsonify({
            "status": "success",
            "message": "Accounts retrieved successfully.",
            "data": [
                {"id": a.AccountID, "name": a.AccountName, "number": a.AccountNumber, "balance": str(a.Balance)} 
                for a in accounts
            ]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()

@finance_bp.route("/accounts/<int:id>", methods=["GET"])
@login_required
def get_account_detail(id):
    db = SessionLocal()
    try:
        from models import BankAccount
        from sqlalchemy import select
        
        stmt = select(BankAccount).where(
            BankAccount.AccountID == id,
            BankAccount.UserID == session["user_id"]
        )
        account = db.execute(stmt).scalars().first()
        
        if not account:
            return jsonify({"status": "error", "message": "Account not found.", "data": None}), 404
            
        return jsonify({
            "status": "success",
            "message": "Account details retrieved.",
            "data": {
                "id": account.AccountID,
                "name": account.AccountName,
                "number": account.AccountNumber,
                "balance": str(account.Balance)
            }
        }), 200
    finally:
        db.close()

@finance_bp.route("/accounts", methods=["POST"])
@login_required
def create_account():
    data = request.get_json()
    db = SessionLocal()
    try:
        from models import BankAccount
        
        acc_num = data.get("account_number")
        if not acc_num or not acc_num.strip():
            raise ValueError("Account Number is required.")
            
        new_acc = BankAccount(
            UserID=session["user_id"],
            AccountName=data["account_name"],
            AccountNumber=acc_num.strip(),
            Balance=Decimal(data.get("initial_balance", "0.00"))
        )
        db.add(new_acc)
        db.commit()
        return jsonify({"status": "success", "message": "Account created.", "data": None}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@finance_bp.route("/categories", methods=["GET"])
@login_required
def get_categories():
    db = SessionLocal()
    try:
        from models import Category, SystemCategory
        from sqlalchemy import select
        
        sys_cats = db.execute(select(SystemCategory.CategoryName)).scalars().all()
        sys_names = set(name.lower() for name in sys_cats)
        
        categories = db.execute(select(Category).where(Category.UserID == session["user_id"])).scalars().all()
        data = [
            {
                "id": c.CategoryID, 
                "name": c.CategoryName, 
                "type": c.Type.value,
                "is_system": c.CategoryName.lower() in sys_names
            } 
            for c in categories
        ]
        return jsonify({"status": "success", "message": "Categories retrieved.", "data": data}), 200
    finally:
        db.close()

@finance_bp.route("/categories", methods=["POST"])
@login_required
def create_category_route():
    data = request.get_json()
    db = SessionLocal()
    try:
        from category_service import create_category
        cat = create_category(
            user_id=session["user_id"],
            name=data.get("name", ""),
            cat_type=data.get("type", ""),
            db=db
        )
        return jsonify({"status": "success", "message": "Category created.", "data": {"id": cat.CategoryID}}), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()

@finance_bp.route("/categories/<int:id>", methods=["DELETE"])
@login_required
def remove_category(id):
    db = SessionLocal()
    try:
        from category_service import delete_category
        delete_category(category_id=id, user_id=session["user_id"], db=db)
        return jsonify({"status": "success", "message": "Category deleted.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()

@finance_bp.route("/sync/simulate", methods=["POST"])
@login_required
def simulate_sync():
    import urllib.request
    import json
    from config import settings
    import uuid
    from datetime import datetime
    
    data = request.get_json()
    payload = {
        "bank_transaction_id": data.get("bank_transaction_id", f"TXN-SIM-{uuid.uuid4().hex[:8]}"),
        "amount": float(data.get("amount", 100.0)),
        "description": data.get("description", "Mock Sync TXN"),
        "bank_sub_acc_id": data.get("account_number", ""),
        "transaction_date": data.get("date", datetime.today().strftime('%Y-%m-%d'))
    }
    
    req = urllib.request.Request(
        "http://127.0.0.1:5050/webhook/transaction",
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "X-API-KEY": settings.webhook_api_key
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = response.read()
            return jsonify({"status": "success", "message": "Simulation successful", "data": json.loads(resp_body)}), 200
    except urllib.error.HTTPError as e:
        resp_body = e.read()
        return jsonify({"status": "error", "message": "Webhook rejected", "data": json.loads(resp_body)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 500

@finance_bp.route("/transactions/income", methods=["GET"])
@login_required
def get_incomes():
    db = SessionLocal()
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    try:
        incomes = get_income_list(session["user_id"], db, limit=limit, offset=offset)
        data = [
            {"id": i.TransactionID, "amount": str(i.Amount), "date": i.TransactionDate.isoformat(), "description": i.Description, "category_id": i.CategoryID, "account_id": i.AccountID, "external_trans_id": i.ExternalTransID}
            for i in incomes
        ]
        return jsonify({"status": "success", "message": "Incomes retrieved.", "data": data}), 200
    finally:
        db.close()

@finance_bp.route("/transactions/expense", methods=["GET"])
@login_required
def get_expenses():
    db = SessionLocal()
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    try:
        expenses = get_expense_list(session["user_id"], db, limit=limit, offset=offset)
        data = [
            {"id": e.TransactionID, "amount": str(e.Amount), "date": e.TransactionDate.isoformat(), "description": e.Description, "category_id": e.CategoryID, "account_id": e.AccountID, "external_trans_id": e.ExternalTransID}
            for e in expenses
        ]
        return jsonify({"status": "success", "message": "Expenses retrieved.", "data": data}), 200
    finally:
        db.close()

@finance_bp.route("/transactions/income", methods=["POST"])
@login_required
def create_income():
    data = request.get_json()
    db = SessionLocal()
    try:
        income = add_income(
            user_id=session["user_id"],
            account_id=data["account_id"],
            category_id=data["category_id"],
            amount=Decimal(data["amount"]),
            transaction_date=datetime.fromisoformat(data["date"]).date(),
            db=db,
            description=data.get("description")
        )
        return jsonify({"status": "success", "message": "Income added.", "data": {"id": income.TransactionID}}), 201
    except ValueError as e:
        msg = str(e)
        status_code = 422 if "Insufficient funds" in msg else 400
        return jsonify({"status": "error", "message": msg, "data": None}), status_code
    finally:
        db.close()

@finance_bp.route("/transactions/expense", methods=["POST"])
@login_required
def create_expense():
    data = request.get_json()
    db = SessionLocal()
    try:
        expense = add_expense(
            user_id=session["user_id"],
            account_id=data["account_id"],
            category_id=data["category_id"],
            amount=Decimal(data["amount"]),
            transaction_date=datetime.fromisoformat(data["date"]).date(),
            db=db,
            description=data.get("description")
        )
        return jsonify({"status": "success", "message": "Expense added.", "data": {"id": expense.TransactionID}}), 201
    except ValueError as e:
        msg = str(e)
        status_code = 422 if "Insufficient funds" in msg else 400
        return jsonify({"status": "error", "message": msg, "data": None}), status_code
    finally:
        db.close()

from transaction_service import update_income, update_expense, delete_income, delete_expense
from bank_sync_service import get_accounts as bank_sync_get_accounts, get_total_savings, run_monthly_closure

@finance_bp.route("/transactions/income/<int:id>", methods=["PUT"])
@login_required
def modify_income(id):
    data = request.get_json()
    db = SessionLocal()
    try:
        updated = update_income(
            transaction_id=id,
            user_id=session["user_id"],
            db=db,
            amount=Decimal(data["amount"]) if "amount" in data else None,
            transaction_date=datetime.fromisoformat(data["date"]).date() if "date" in data else None,
            category_id=data.get("category_id"),
            account_id=data.get("account_id"),
            description=data.get("description")
        )
        return jsonify({"status": "success", "message": "Income updated.", "data": {"id": updated.TransactionID}}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@finance_bp.route("/transactions/expense/<int:id>", methods=["PUT"])
@login_required
def modify_expense(id):
    data = request.get_json()
    db = SessionLocal()
    try:
        updated = update_expense(
            transaction_id=id,
            user_id=session["user_id"],
            db=db,
            amount=Decimal(data["amount"]) if "amount" in data else None,
            transaction_date=datetime.fromisoformat(data["date"]).date() if "date" in data else None,
            category_id=data.get("category_id"),
            account_id=data.get("account_id"),
            description=data.get("description")
        )
        return jsonify({"status": "success", "message": "Expense updated.", "data": {"id": updated.TransactionID}}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@finance_bp.route("/transactions/income/<int:id>", methods=["DELETE"])
@login_required
def remove_income(id):
    db = SessionLocal()
    try:
        delete_income(transaction_id=id, user_id=session["user_id"], db=db)
        return jsonify({"status": "success", "message": "Income deleted.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@finance_bp.route("/transactions/expense/<int:id>", methods=["DELETE"])
@login_required
def remove_expense(id):
    db = SessionLocal()
    try:
        delete_expense(transaction_id=id, user_id=session["user_id"], db=db)
        return jsonify({"status": "success", "message": "Expense deleted.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@finance_bp.route("/accounts/total-savings", methods=["GET"])
@login_required
def total_savings():
    db = SessionLocal()
    try:
        total = get_total_savings(user_id=session["user_id"], db=db)
        return jsonify({"status": "success", "message": "Total savings retrieved.", "data": {"total": str(total)}}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()

@finance_bp.route("/accounts/monthly-closure", methods=["POST"])
@login_required
def monthly_closure():
    data = request.get_json()
    if not data or "period" not in data:
        return jsonify({"status": "error", "message": "Period (YYYY-MM) is required.", "data": None}), 400
    db = SessionLocal()
    try:
        run_monthly_closure(user_id=session["user_id"], period=data["period"], db=db)
        return jsonify({"status": "success", "message": f"Monthly closure completed for {data['period']}.", "data": None}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 400
    finally:
        db.close()

@finance_bp.route("/sync/records", methods=["GET"])
@login_required
def get_sync_records():
    db = SessionLocal()
    try:
        from models import Income, Expense, Category
        from sqlalchemy import select, desc

        uid = session["user_id"]

        inc_q = (
            select(
                Income.TransactionID,
                Income.Amount,
                Income.TransactionDate,
                Income.Description,
                Income.ExternalTransID,
                Income.AccountID,
                Category.CategoryName,
            )
            .join(Category, Income.CategoryID == Category.CategoryID)
            .where(Income.UserID == uid, Income.ExternalTransID.isnot(None))
        )
        inc_rows = db.execute(inc_q).mappings().all()

        exp_q = (
            select(
                Expense.TransactionID,
                Expense.Amount,
                Expense.TransactionDate,
                Expense.Description,
                Expense.ExternalTransID,
                Expense.AccountID,
                Category.CategoryName,
            )
            .join(Category, Expense.CategoryID == Category.CategoryID)
            .where(Expense.UserID == uid, Expense.ExternalTransID.isnot(None))
        )
        exp_rows = db.execute(exp_q).mappings().all()

        def serialize(rows, txn_type):
            return [
                {
                    "id": r["TransactionID"],
                    "type": txn_type,
                    "amount": str(r["Amount"]),
                    "date": r["TransactionDate"].isoformat(),
                    "description": r["Description"] or "",
                    "external_trans_id": r["ExternalTransID"],
                    "account_id": r["AccountID"],
                    "category_name": r["CategoryName"],
                }
                for r in rows
            ]

        records = serialize(inc_rows, "income") + serialize(exp_rows, "expense")
        records.sort(key=lambda x: x["date"], reverse=True)

        return jsonify({"status": "success", "message": "Sync records retrieved.", "data": records}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()
@finance_bp.route("/transactions/<string:type>/<int:id>/category", methods=["PUT"])
@login_required
def update_txn_category(type, id):
    data = request.get_json()
    category_id = data.get("category_id")
    if not category_id:
        return jsonify({"status": "error", "message": "Category ID is required.", "data": None}), 400
    
    db = SessionLocal()
    try:
        from models import Income, Expense
        if type.lower() == "income":
            txn = db.query(Income).filter(Income.TransactionID == id, Income.UserID == session["user_id"]).first()
        else:
            txn = db.query(Expense).filter(Expense.TransactionID == id, Expense.UserID == session["user_id"]).first()
            
        if not txn:
            return jsonify({"status": "error", "message": "Transaction not found.", "data": None}), 404
            
        txn.CategoryID = category_id
        db.commit()
        return jsonify({"status": "success", "message": "Category updated successfully.", "data": None}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e), "data": None}), 500
    finally:
        db.close()
