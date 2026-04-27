"""
bank_sync_service.py — Bank Account & Sync Simulation Service
==============================================================
Provides account retrieval, total savings calculation, bank sync simulation,
and monthly closure operations. This module bridges the SQL stored procedures
and UDFs to the Python application layer.

Key Behaviours:
    - `get_accounts()` / `get_total_savings()` are pure read operations.
    - `simulate_bank_sync()` generates realistic random transactions for the
      current date, delegating through `transaction_service` so all validation
      and SQL trigger logic (balance auto-update) applies correctly.
    - `run_monthly_closure()` calls the `CalculateMonthlyClosure` stored
      procedure via a raw `db.execute(text(...))` call — keeping the closure
      logic in the database where it belongs.
    - All read queries are scoped by UserID (Golden Rule enforced).

Directive Reference:
    - directives/backend_logic_rules.md — Section 2 (Data Isolation)
    - directives/db_rules.md           — Section 2 (Stored Procedures & UDFs)
"""

import logging
import random
import re
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models import BankAccount, Category, TransactionType
from transaction_service import add_expense, add_income

logger = logging.getLogger(__name__)

# Regex to validate YYYY-MM period format (shared pattern)
_PERIOD_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Sync simulation pools — realistic descriptions for synthetic transactions
_SYNC_INCOME_DESCRIPTIONS: list[str] = [
    "Freelance payment received",
    "Bank interest credited",
    "Cashback reward",
    "Peer transfer received",
    "Side project payment",
]

_SYNC_EXPENSE_DESCRIPTIONS: list[str] = [
    "Supermarket purchase",
    "Online subscription renewal",
    "Transport card top-up",
    "Pharmacy purchase",
    "Utility bill payment",
    "Takeaway food order",
    "ATM withdrawal",
]


# =============================================================================
# Step 5.4 — Public Bank Sync Functions
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

    Delegating this to the DB UDF ensures the aggregation stays consistent
    with the trigger-managed Balance values.

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


def simulate_bank_sync(user_id: int, db: Session) -> dict:
    """
    Simulates an incoming bank transaction feed for the authenticated user.

    Generates between 1 and 3 random realistic transactions (a mix of small
    incomes and expenses) dated to today. Each transaction is created via
    `add_income()` or `add_expense()` from `transaction_service`, ensuring:
        - All validation rules apply (amount > 0, date check, ownership).
        - SQL triggers fire and keep BankAccounts.Balance perfectly in sync.

    This function is the "Bank Sync Simulation" feature specified in
    PROJECT_PLAN.md (Part 2, Step 5).

    Args:
        user_id: The authenticated user's UserID.
        db:      An active SQLAlchemy Session.

    Returns:
        A summary dict: {
            'transactions_added': int,
            'income_added':       int,
            'expenses_added':     int,
            'total_income':       Decimal,
            'total_expenses':     Decimal,
        }

    Raises:
        ValueError: If the user has no accounts or no categories to work with.
    """
    accounts: list[BankAccount] = get_accounts(user_id, db)
    if not accounts:
        raise ValueError(
            f"Cannot simulate bank sync: UserID={user_id} has no bank accounts."
        )

    # Fetch user's Income-type and Expense-type categories
    income_cats: list[Category] = db.execute(
        select(Category).where(
            Category.UserID == user_id,
            Category.Type == TransactionType.Income,
        )
    ).scalars().all()

    expense_cats: list[Category] = db.execute(
        select(Category).where(
            Category.UserID == user_id,
            Category.Type == TransactionType.Expense,
        )
    ).scalars().all()

    if not income_cats or not expense_cats:
        raise ValueError(
            f"Cannot simulate bank sync: UserID={user_id} has no categories."
        )

    num_transactions: int = random.randint(1, 3)
    today: date = date.today()
    income_count: int = 0
    expense_count: int = 0
    total_income: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")

    for _ in range(num_transactions):
        account: BankAccount = random.choice(accounts)
        # Randomly decide income (30%) or expense (70%) — mirrors real-world ratio
        if random.random() < 0.30 and income_cats:
            cat: Category = random.choice(income_cats)
            amount: Decimal = Decimal(str(round(random.uniform(50, 800), 2)))
            add_income(
                user_id=user_id,
                account_id=account.AccountID,
                category_id=cat.CategoryID,
                amount=amount,
                transaction_date=today,
                db=db,
                description=random.choice(_SYNC_INCOME_DESCRIPTIONS),
            )
            income_count += 1
            total_income += amount
        else:
            cat = random.choice(expense_cats)
            amount = Decimal(str(round(random.uniform(5, 300), 2)))
            add_expense(
                user_id=user_id,
                account_id=account.AccountID,
                category_id=cat.CategoryID,
                amount=amount,
                transaction_date=today,
                db=db,
                description=random.choice(_SYNC_EXPENSE_DESCRIPTIONS),
            )
            expense_count += 1
            total_expenses += amount

    summary = {
        "transactions_added": income_count + expense_count,
        "income_added":       income_count,
        "expenses_added":     expense_count,
        "total_income":       total_income,
        "total_expenses":     total_expenses,
    }
    logger.info(
        "Bank sync simulated for user %d: %d transactions added.",
        user_id, summary["transactions_added"],
    )
    return summary


def run_monthly_closure(user_id: int, period: str, db: Session) -> dict:
    """
    Executes the `CalculateMonthlyClosure` stored procedure to snapshot
    the current account balances for the given user and period.

    This creates (or idempotently updates) a record in the `MonthlyClosures`
    table for each of the user's accounts, locking in the end-of-month balance.

    The stored procedure uses ON DUPLICATE KEY UPDATE, so calling this
    function multiple times for the same period is always safe.

    Args:
        user_id: The authenticated user's UserID.
        period:  The target closure period in 'YYYY-MM' format.
        db:      An active SQLAlchemy Session.

    Returns:
        A confirmation dict: {
            'user_id': int,
            'period':  str,
            'status':  'CLOSURE_COMPLETE'
        }

    Raises:
        ValueError: If the period format is invalid.
        RuntimeError: If the stored procedure call fails.
    """
    if not _PERIOD_REGEX.match(period.strip()):
        raise ValueError(
            f"Invalid period format: '{period}'. Expected 'YYYY-MM'."
        )

    try:
        # Call the stored procedure via raw SQL text
        db.execute(
            text("CALL CalculateMonthlyClosure(:uid, :period)"),
            {"uid": user_id, "period": period.strip()},
        )
        db.commit()
        logger.info(
            "Monthly closure executed: user=%d period='%s'.", user_id, period
        )
        return {
            "user_id": user_id,
            "period":  period,
            "status":  "CLOSURE_COMPLETE",
        }
    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to run monthly closure for user=%d period='%s': %s",
            user_id, period, e,
        )
        raise RuntimeError(
            f"Monthly closure failed for period '{period}'. "
            "See logs for details."
        ) from e
