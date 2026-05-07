import logging
import re
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Budget, Category, TransactionType

logger = logging.getLogger(__name__)

_PERIOD_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validate_period(period: str) -> None:
    if not _PERIOD_REGEX.match(period.strip()):
        raise ValueError(
            f"Invalid period format: '{period}'. Expected format: 'YYYY-MM' (e.g., '2026-04')."
        )


def _assert_expense_category_ownership(category_id: int, user_id: int, db: Session) -> Category:
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


def create_budget(user_id: int, category_id: int, limit_amount: Decimal, period: str, db: Session,) -> Budget:
    if limit_amount <= Decimal("0"):
        raise ValueError(
            f"Budget limit must be greater than 0. Got: {limit_amount}."
        )
    _validate_period(period)
    _assert_expense_category_ownership(category_id, user_id, db)

    existing = db.execute(
        select(Budget).where(
            Budget.UserID == user_id,
            Budget.CategoryID == category_id,
            Budget.Period == period.strip(),
        )
    ).scalars().first()
    
    if existing:
        raise ValueError(
            f"A budget for this category already exists for the period {period}."
        )

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
    _validate_period(period)
    return db.execute(
        select(Budget).where(
            Budget.UserID == user_id,
            Budget.Period == period.strip(),
        )
    ).scalars().all()


def get_budget_status(user_id: int, category_id: int, period: str, db: Session,) -> dict:
    _validate_period(period)

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


def get_all_budget_statuses(user_id: int, period: str, db: Session) -> list[dict]:
    _validate_period(period)
    
    query = text("""
        SELECT 
            b.BudgetID, 
            b.CategoryID, 
            c.CategoryName, 
            b.LimitAmount, 
            GetBudgetStatus(:uid, b.CategoryID, :period) AS remaining
        FROM Budgets b
        JOIN Categories c ON b.CategoryID = c.CategoryID
        WHERE b.UserID = :uid AND b.Period = :period
    """)
    
    results = db.execute(query, {"uid": user_id, "period": period.strip()}).mappings().all()
    
    statuses = []
    for row in results:
        limit = Decimal(str(row["LimitAmount"]))
        remaining = Decimal(str(row["remaining"]))
        actual_spending = limit - remaining
        
        if limit > 0:
            percentage = (actual_spending / limit) * 100
        else:
            percentage = Decimal("0")
            
        status = "OK"
        if remaining < Decimal("0"):
            status = "OVER_BUDGET"
        elif percentage >= Decimal("80"):
            status = "WARNING"
            
        statuses.append({
            "budget_id": row["BudgetID"],
            "category_id": row["CategoryID"],
            "category_name": row["CategoryName"],
            "limit": limit,
            "remaining": remaining,
            "actual_spending": actual_spending,
            "progress_percentage": min(percentage, Decimal("100")), 
            "status": status
        })
        
    return statuses



def update_budget(budget_id: int, user_id: int, limit_amount: Decimal, db: Session,) -> Budget:
    if limit_amount <= Decimal("0"):
        raise ValueError("Budget limit must be greater than 0.")
        
    budget: Optional[Budget] = db.execute(
        select(Budget).where(Budget.BudgetID == budget_id, Budget.UserID == user_id)
    ).scalar_one_or_none()
    
    if budget is None:
        raise ValueError(f"BudgetID={budget_id} not found or not owned by user.")
        
    budget.LimitAmount = limit_amount
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(budget_id: int, user_id: int, db: Session) -> None:
    budget: Optional[Budget] = db.execute(
        select(Budget).where(Budget.BudgetID == budget_id, Budget.UserID == user_id)
    ).scalar_one_or_none()
    
    if budget is None:
        raise ValueError(f"BudgetID={budget_id} not found or not owned by user.")
        
    db.delete(budget)
    db.commit()
