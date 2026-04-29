"""
bank_sync_service.py — Bank Account, Sync & Webhook Processing Service
=======================================================================
Provides account retrieval, total savings calculation, monthly closure
operations, and the core Webhook payload processor that replaces the
old "Bank Sync Simulation".

Webhook Processing Flow (process_webhook_payload):
    1. Schema Validation   — Required fields and correct types.
    2. Idempotency Check   — Reject duplicates via ExternalTransID lookup.
    3. Account Resolution  — Map bank_sub_acc_id → BankAccount → UserID.
    4. Category Resolution — Auto-select first matching category by type.
    5. Transaction Commit  — Delegate to transaction_service (triggers fire).

Key Behaviours:
    - `get_accounts()` / `get_total_savings()` are pure read operations.
    - `run_monthly_closure()` calls the `CalculateMonthlyClosure` stored
      procedure via a raw `db.execute(text(...))` call.
    - All read queries are scoped by UserID (Golden Rule enforced).
    - Webhook responses NEVER expose stack traces.

Directive Reference:
    - directives/backend_logic_rules.md — Section 2 (Data Isolation),
                                          Section 4 (Webhook Rules)
    - directives/db_rules.md           — Section 3 (Idempotency), Section 2 (SP/UDFs)
"""

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

# Regex to validate YYYY-MM period format
_PERIOD_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Required fields for a valid Webhook payload
_REQUIRED_WEBHOOK_FIELDS: list[str] = [
    "bank_transaction_id",
    "amount",
    "bank_sub_acc_id",
    "transaction_date",
]


# =============================================================================
# Read-Only Account Functions
# =============================================================================

def get_accounts(user_id: int, db: Session) -> list[BankAccount]:
    """
    Returns all BankAccount records owned by the authenticated user.

    Data Isolation: UserID filter is MANDATORY — no plain .all() queries.

    Args:
        user_id: The authenticated user's UserID.
        db:      An active SQLAlchemy Session.

    Returns:
        A list of BankAccount ORM objects belonging to the user,
        ordered by AccountID ascending.
    """
    return db.execute(
        select(BankAccount)
        .where(BankAccount.UserID == user_id)
        .order_by(BankAccount.AccountID)
    ).scalars().all()


def get_total_savings(user_id: int, db: Session) -> Decimal:
    """
    Returns the total aggregated balance across all of the user's bank
    accounts by calling the `GetTotalSavings` SQL User-Defined Function.

    Args:
        user_id: The authenticated user's UserID.
        db:      An active SQLAlchemy Session.

    Returns:
        A Decimal representing the sum of all account balances for the user.
        Returns Decimal('0.00') if the user has no accounts.
    """
    result = db.execute(
        text("SELECT GetTotalSavings(:uid)"),
        {"uid": user_id},
    ).scalar_one_or_none()

    total = Decimal(str(result)) if result is not None else Decimal("0.00")
    logger.info("Total savings for user %d: %s.", user_id, total)
    return total


# =============================================================================
# Step W.3 — Webhook Payload Processor
# =============================================================================

def _validate_webhook_schema(payload: dict) -> Optional[str]:
    """
    Validates that the inbound Webhook payload contains all required fields
    and that the `amount` is a parseable numeric value.

    Args:
        payload: The raw dict parsed from the JSON request body.

    Returns:
        None if valid. A descriptive error string if validation fails.
    """
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
    """
    Checks whether the given `bank_transaction_id` has already been processed.
    Queries both `Income.ExternalTransID` and `Expenses.ExternalTransID`.

    This is the Anti-Double Spending guard (db_rules.md Section 3).

    Args:
        bank_transaction_id: The unique ID from the Webhook payload.
        db:                  An active SQLAlchemy Session.

    Returns:
        True if already processed (duplicate). False if safe to proceed.
    """
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
    """
    Processes an inbound Webhook payload representing an external bank
    transaction and persists it as an Income or Expense record.

    Processing Steps:
        1. Schema Validation:   All required fields present, correct types.
        2. Idempotency Check:   Queries Income + Expenses by ExternalTransID.
                                Returns 200 ALREADY_PROCESSED on duplicate.
        3. Account Resolution:  Looks up `bank_sub_acc_id` in BankAccounts.
                                Returns 404 ACCOUNT_NOT_FOUND if no match.
        4. UserID Resolution:   Taken from the matched BankAccount — NOT the
                                payload (the payload is untrusted input).
        5. Category Resolution: Auto-selects first matching category owned by
                                the resolved user, by transaction type.
        6. Direction & Commit:  Positive amount → Income; Negative → Expense.
                                Delegates to `add_income()` / `add_expense()`
                                so all SQL triggers fire correctly.

    Response Contract (returned dict, HTTP code set by webhook_server.py):
        - {'status': 'PROCESSED',          'code': 200, 'transaction_id': int}
        - {'status': 'ALREADY_PROCESSED',  'code': 200}
        - {'status': 'INVALID_PAYLOAD',    'code': 400, 'detail': str}
        - {'status': 'ACCOUNT_NOT_FOUND',  'code': 404}
        - {'status': 'CATEGORY_NOT_FOUND', 'code': 404}
        - {'status': 'PROCESSING_ERROR',   'code': 500, 'detail': str}

    Args:
        payload: The validated JSON body dict from the HTTP request.
        db:      An active SQLAlchemy Session (injected by webhook_server.py).

    Returns:
        A structured response dict with 'status' and 'code' keys.
    """
    # -------------------------------------------------------------------------
    # Step 1: Schema Validation
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Step 2: Idempotency Check (Anti-Double Spending)
    # -------------------------------------------------------------------------
    if _check_idempotency(bank_transaction_id, db):
        logger.info(
            "Webhook duplicate detected: bank_transaction_id='%s'. Skipping.",
            bank_transaction_id,
        )
        return {"status": "ALREADY_PROCESSED", "code": 200}

    # -------------------------------------------------------------------------
    # Step 3: Account Resolution (bank_sub_acc_id → BankAccounts.AccountNumber)
    # -------------------------------------------------------------------------
    # Matches the payload's bank_sub_acc_id directly against AccountNumber —
    # the authoritative external key per db_rules.md (Section 3) and
    # backend_logic_rules.md (Section 4: Account Number Mapping).
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

    # -------------------------------------------------------------------------
    # Step 4: UserID Resolution (from matched account — never from payload)
    # -------------------------------------------------------------------------
    resolved_user_id: int = account.UserID
    resolved_account_id: int = account.AccountID

    # -------------------------------------------------------------------------
    # Step 5: Category Resolution — "Others" Fallback Categorization
    # -------------------------------------------------------------------------
    # Rule: Webhook transactions must NEVER be assigned to an arbitrary
    # first-available category (backend_logic_rules.md Section 4).
    #
    # Two-tier fallback strategy:
    #   Tier 1 (Primary)     — Look up the user's "Others" category by name
    #                          matching the correct transaction type.
    #   Tier 2 (Last-resort) — If "Others" doesn't exist (legacy account),
    #                          fall back to the first available category of
    #                          the correct type. Log a WARNING so the operator
    #                          knows the "Others" category needs to be added.
    #   Final guard          — If both tiers fail, return CATEGORY_NOT_FOUND.
    is_income: bool = raw_amount >= Decimal("0")
    expected_type: TransactionType = (
        TransactionType.Income if is_income else TransactionType.Expense
    )

    # Tier 1: Look for the user's "Others" category (correct type)
    category: Optional[Category] = db.execute(
        select(Category).where(
            Category.UserID == resolved_user_id,
            Category.Type == expected_type,
            Category.CategoryName == "Others",
        )
    ).scalar_one_or_none()

    # Tier 2: Last-resort fallback — first available category of correct type
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

    # Final guard: no category of any kind exists for this user + type
    if category is None:
        logger.error(
            "Webhook category resolution failed: user %d has no %s categories at all.",
            resolved_user_id, expected_type.value,
        )
        return {"status": "CATEGORY_NOT_FOUND", "code": 404}


    # -------------------------------------------------------------------------
    # Step 6: Transaction Commit (delegate to transaction_service)
    # -------------------------------------------------------------------------
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
            "status":         "PROCESSED",
            "code":           200,
            "transaction_id": record.TransactionID,
        }

    except ValueError as e:
        # Validation error from transaction_service — safe to expose detail
        logger.error("Webhook validation error: %s", e)
        return {"status": "INVALID_PAYLOAD", "code": 400, "detail": str(e)}

    except Exception as e:
        # Unexpected failure — log internally, never leak stack trace
        logger.error("Webhook processing error: %s", e)
        return {
            "status": "PROCESSING_ERROR",
            "code":   500,
            "detail": "An internal error occurred. Please retry later.",
        }


# =============================================================================
# Monthly Closure (Stored Procedure Bridge)
# =============================================================================

def run_monthly_closure(user_id: int, period: str, db: Session) -> dict:
    """
    Executes the `CalculateMonthlyClosure` stored procedure to snapshot
    the current account balances for the given user and period.

    The stored procedure uses ON DUPLICATE KEY UPDATE, so calling this
    function multiple times for the same period is always safe.

    Args:
        user_id: The authenticated user's UserID.
        period:  The target closure period in 'YYYY-MM' format.
        db:      An active SQLAlchemy Session.

    Returns:
        A confirmation dict: {'user_id': int, 'period': str, 'status': str}

    Raises:
        ValueError:   If the period format is invalid.
        RuntimeError: If the stored procedure call fails.
    """
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
