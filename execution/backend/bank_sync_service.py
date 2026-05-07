import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from models import BankAccount, Category, Expense, Income, TransactionType
from transaction_service import add_expense, add_income

logger = logging.getLogger(__name__)

_PERIOD_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

_REQUIRED_WEBHOOK_FIELDS: list[str] = [
    "bank_transaction_id",
    "amount",
    "bank_sub_acc_id",
    "transaction_date",
]

def get_accounts(user_id: int, db: Session) -> list[BankAccount]:
    return db.execute(
        select(BankAccount)
        .where(BankAccount.UserID == user_id)
        .order_by(BankAccount.AccountID)
    ).scalars().all()


def get_total_savings(user_id: int, db: Session) -> Decimal:
    result = db.execute(
        text("SELECT GetTotalSavings(:uid)"),
        {"uid": user_id},
    ).scalar_one_or_none()

    total = Decimal(str(result)) if result is not None else Decimal("0.00")
    logger.info("Total savings for user %d: %s.", user_id, total)
    return total


def _validate_webhook_schema(payload: dict) -> Optional[str]:
    for field in _REQUIRED_WEBHOOK_FIELDS:
        if field not in payload or payload[field] is None:
            return f"Missing required field: '{field}'."

    try:
        Decimal(str(payload["amount"]))
    except InvalidOperation:
        return f"Field 'amount' must be a valid number. Got: '{payload['amount']}'."

    try:
        datetime.strptime(str(payload["transaction_date"]), "%Y-%m-%d")
    except ValueError:
        return (
            f"Field 'transaction_date' must be ISO 8601 format (YYYY-MM-DD). "
            f"Got: '{payload['transaction_date']}'."
        )

    return None


def _check_idempotency(bank_transaction_id: str, db: Session) -> bool:
    existing_income = db.execute(
        select(Income.TransactionID).where(
            Income.ExternalTransID == bank_transaction_id
        )
    ).scalar_one_or_none()

    if existing_income is not None:
        return True

    existing_expense = db.execute(
        select(Expense.TransactionID).where(
            Expense.ExternalTransID == bank_transaction_id
        )
    ).scalar_one_or_none()

    return existing_expense is not None


def process_webhook_payload(payload: dict, db: Session) -> dict:
    schema_error: Optional[str] = _validate_webhook_schema(payload)
    if schema_error:
        logger.warning("Webhook schema validation failed: %s", schema_error)
        return {"status": "INVALID_PAYLOAD", "code": 400, "detail": schema_error}

    bank_transaction_id: str = str(payload["bank_transaction_id"]).strip()
    raw_amount: Decimal = Decimal(str(payload["amount"]))
    bank_sub_acc_id: str = str(payload["bank_sub_acc_id"]).strip()
    description: Optional[str] = payload.get("description")
    transaction_date: date = datetime.strptime(
        str(payload["transaction_date"]), "%Y-%m-%d"
    ).date()

    if _check_idempotency(bank_transaction_id, db):
        logger.info(
            "Webhook duplicate detected: bank_transaction_id='%s'. Skipping.",
            bank_transaction_id,
        )
        return {"status": "ALREADY_PROCESSED", "code": 200}

    account: Optional[BankAccount] = db.execute(
        select(BankAccount).where(
            BankAccount.AccountNumber == bank_sub_acc_id
        )
    ).scalar_one_or_none()

    if account is None:
        logger.warning(
            "Webhook account resolution failed: AccountNumber='%s' not found in BankAccounts.",
            bank_sub_acc_id,
        )
        return {"status": "ACCOUNT_NOT_FOUND", "code": 404}

    resolved_user_id: int = account.UserID
    resolved_account_id: int = account.AccountID

    is_income: bool = raw_amount >= Decimal("0")
    expected_type: TransactionType = (
        TransactionType.Income if is_income else TransactionType.Expense
    )

    category: Optional[Category] = db.execute(
        select(Category).where(
            Category.UserID == resolved_user_id,
            Category.Type == expected_type,
            Category.CategoryName == "Others",
        )
    ).scalar_one_or_none()

    if category is None:
        logger.warning(
            "Webhook categorization: 'Others' (%s) category not found for user %d. "
            "Falling back to first available. Run schema migration to add 'Others' "
            "to SystemCategories.",
            expected_type.value, resolved_user_id,
        )
        category = db.execute(
            select(Category).where(
                Category.UserID == resolved_user_id,
                Category.Type == expected_type,
            ).limit(1)
        ).scalar_one_or_none()

    if category is None:
        logger.error(
            "Webhook category resolution failed: user %d has no %s categories at all.",
            resolved_user_id, expected_type.value,
        )
        return {"status": "CATEGORY_NOT_FOUND", "code": 404}


    try:
        amount_positive: Decimal = abs(raw_amount)

        if is_income:
            record = add_income(
                user_id=resolved_user_id,
                account_id=resolved_account_id,
                category_id=category.CategoryID,
                amount=amount_positive,
                transaction_date=transaction_date,
                db=db,
                description=description,
                external_trans_id=bank_transaction_id,
            )
        else:
            record = add_expense(
                user_id=resolved_user_id,
                account_id=resolved_account_id,
                category_id=category.CategoryID,
                amount=amount_positive,
                transaction_date=transaction_date,
                db=db,
                description=description,
                external_trans_id=bank_transaction_id,
            )

        logger.info(
            "Webhook processed: bank_tx_id='%s' type=%s amount=%s user=%d tx_id=%d.",
            bank_transaction_id, expected_type.value,
            amount_positive, resolved_user_id, record.TransactionID,
        )
        return {
            "status":         "SUCCESS",
            "code":           200,
            "transaction_id": record.TransactionID,
        }

    except ValueError as e:
        logger.error("Webhook validation error: %s", e)
        return {"status": "INVALID_PAYLOAD", "code": 400, "detail": str(e)}

    except Exception as e:
        logger.error("Webhook processing error: %s", e)
        return {
            "status": "PROCESSING_ERROR",
            "code":   500,
            "detail": "An internal error occurred. Please retry later.",
        }



def run_monthly_closure(user_id: int, period: str, db: Session) -> dict:
    if not _PERIOD_REGEX.match(period.strip()):
        raise ValueError(
            f"Invalid period format: '{period}'. Expected 'YYYY-MM'."
        )

    try:
        db.execute(
            text("CALL CalculateMonthlyClosure(:uid, :period)"),
            {"uid": user_id, "period": period.strip()},
        )
        db.commit()
        logger.info(
            "Monthly closure executed: user=%d period='%s'.", user_id, period
        )
        return {"user_id": user_id, "period": period, "status": "CLOSURE_COMPLETE"}

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to run monthly closure for user=%d period='%s': %s",
            user_id, period, e,
        )
        raise RuntimeError(
            f"Monthly closure failed for period '{period}'. See logs for details."
        ) from e
