"""
budget_service.py — Budget Management & Status Tracking
=========================================================
Handles the creation and retrieval of user budgets, and provides real-time
budget consumption status by delegating the heavy aggregation to the
`GetBudgetStatus` SQL User-Defined Function.

Design Notes:
    - `Period` format is strictly 'YYYY-MM' (e.g., '2026-04') to align
      with the DATE_FORMAT pattern used in `vw_CategoryWiseSpending` and
      `GetBudgetStatus` SQL UDF.
    - Budget status is computed at the DB level via a raw SQL UDF call —
      this is intentional to keep the aggregation logic in one place
      (the database), not duplicated in Python.
    - All reads are scoped by UserID (Golden Rule enforced).

Directive Reference:
    - directives/backend_logic_rules.md — Section 2 (Data Isolation),
                                          Section 4 (Validation)
    - directives/db_rules.md           — Section 2 (SQL UDFs), Section 3
"""

import logging
import re
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Budget, Category, TransactionType

logger = logging.getLogger(__name__)

# Regex to validate the 'YYYY-MM' period format
_PERIOD_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# =============================================================================
# Validation Helpers
# =============================================================================

def _validate_period(period: str) -> None:
    """
    Validates that a period string matches the required 'YYYY-MM' format.

    Args:
        period: The period string to validate.

    Raises:
        ValueError: If the format is incorrect.
    """
    if not _PERIOD_REGEX.match(period.strip()):
        raise ValueError(
            f"Invalid period format: '{period}'. Expected format: 'YYYY-MM' (e.g., '2026-04')."
        )


def _assert_expense_category_ownership(
    category_id: int, user_id: int, db: Session
) -> Category:
    """
    Fetches a user-owned Category and confirms it is Expense-type.
    Budgets can only be set against Expense-type categories — it makes
    no financial sense to budget for income.

    Args:
        category_id: The CategoryID to verify.
        user_id:     The UserID of the authenticated user.
        db:          An active SQLAlchemy Session.

    Returns:
        The verified Category ORM object.

    Raises:
        ValueError: If not found, not owned, or not Expense-type.
    """
    category: Optional[Category] = db.execute(
        select(Category).where(
            Category.CategoryID == category_id,
            Category.UserID == user_id,
        )
    ).scalar_one_or_none()

    if category is None:
        raise ValueError(
            f"CategoryID={category_id} not found or not owned by UserID={user_id}."
        )
    if category.Type != TransactionType.Expense:
        raise ValueError(
            f"Budgets can only be assigned to Expense-type categories. "
            f"CategoryID={category_id} is '{category.Type.value}'."
        )
    return category


# =============================================================================
# Step 5.3 — Public Budget Functions
# =============================================================================

def create_budget(
    user_id: int,
    category_id: int,
    limit_amount: Decimal,
    period: str,
    db: Session,
) -> Budget:
    """
    Creates a new Budget cap for a specific Expense-type Category and period.

    Validation chain (Python layer, before touching the DB):
        1. `limit_amount` must be > 0.
        2. `period` must match 'YYYY-MM' format.
        3. `category_id` must exist, be owned by user, and be Expense-type.

    Args:
        user_id:      The authenticated user's UserID.
        category_id:  The CategoryID to set the budget for (Expense-type only).
        limit_amount: The maximum allowed spending for this period. Must be > 0.
        period:       The target budget period in 'YYYY-MM' format.
        db:           An active SQLAlchemy Session.

    Returns:
        The newly created and persisted Budget ORM object.

    Raises:
        ValueError:   If validation fails.
        RuntimeError: If a budget for this user/category/period already exists
                      (duplicate) or other DB-level failure.
    """
    # --- Pre-ORM Validation ---
    if limit_amount <= Decimal("0"):
        raise ValueError(
            f"Budget limit must be greater than 0. Got: {limit_amount}."
        )
    _validate_period(period)
    _assert_expense_category_ownership(category_id, user_id, db)

    try:
        budget = Budget(
            UserID=user_id,
            CategoryID=category_id,
            LimitAmount=limit_amount,
            Period=period.strip(),
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        logger.info(
            "Budget created: id=%d user=%d category=%d period='%s' limit=%s.",
            budget.BudgetID, user_id, category_id, period, limit_amount,
        )
        return budget

    except IntegrityError as e:
        db.rollback()
        logger.error("IntegrityError creating budget: %s", e)
        raise RuntimeError(
            f"A budget for CategoryID={category_id} in period '{period}' "
            "may already exist for this user."
        ) from e


def get_budgets(user_id: int, period: str, db: Session) -> list[Budget]:
    """
    Returns all Budget records for the authenticated user in a given period.

    Joins with Category to include the category name in the ORM objects
    via relationship lazy-loading (accessible via budget.category.CategoryName).

    Data Isolation: UserID filter is MANDATORY.

    Args:
        user_id: The authenticated user's UserID.
        period:  The target period in 'YYYY-MM' format.
        db:      An active SQLAlchemy Session.

    Returns:
        A list of Budget ORM objects for the specified user and period.

    Raises:
        ValueError: If the period format is invalid.
    """
    _validate_period(period)
    return db.execute(
        select(Budget).where(
            Budget.UserID == user_id,
            Budget.Period == period.strip(),
        )
    ).scalars().all()


def get_budget_status(
    user_id: int,
    category_id: int,
    period: str,
    db: Session,
) -> dict:
    """
    Calculates the real-time budget consumption status for a category/period
    by calling the `GetBudgetStatus` SQL User-Defined Function.

    The UDF computes: LimitAmount − SUM(Expenses) for the given period.
    A positive return means budget remaining; negative means over-budget.

    Args:
        user_id:     The authenticated user's UserID.
        category_id: The CategoryID to check budget for.
        period:      The target period in 'YYYY-MM' format.
        db:          An active SQLAlchemy Session.

    Returns:
        A dict with keys:
            - 'category_id'  (int)
            - 'period'       (str)
            - 'remaining'    (Decimal) — positive = under budget, negative = over
            - 'status'       (str)     — 'OK', 'WARNING' (>80%), or 'OVER_BUDGET'

    Raises:
        ValueError: If the period format is invalid or no budget is set.
    """
    _validate_period(period)

    # Call the GetBudgetStatus SQL UDF via raw text — keeps aggregation in DB
    result = db.execute(
        text(
            "SELECT GetBudgetStatus(:uid, :cat_id, :period) AS remaining"
        ),
        {"uid": user_id, "cat_id": category_id, "period": period.strip()},
    ).scalar_one_or_none()

    if result is None:
        raise ValueError(
            f"No budget found for UserID={user_id}, "
            f"CategoryID={category_id}, Period='{period}'."
        )

    remaining = Decimal(str(result))

    # Fetch the budget limit to compute percentage consumed
    budget: Optional[Budget] = db.execute(
        select(Budget).where(
            Budget.UserID == user_id,
            Budget.CategoryID == category_id,
            Budget.Period == period.strip(),
        )
    ).scalar_one_or_none()

    status: str = "OK"
    if budget:
        if remaining < Decimal("0"):
            status = "OVER_BUDGET"
        elif (budget.LimitAmount - remaining) / budget.LimitAmount >= Decimal("0.8"):
            status = "WARNING"

    logger.info(
        "Budget status: user=%d cat=%d period='%s' remaining=%s status=%s.",
        user_id, category_id, period, remaining, status,
    )

    return {
        "category_id": category_id,
        "period":      period,
        "remaining":   remaining,
        "status":      status,
    }
