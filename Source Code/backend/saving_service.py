import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import (
    BankAccount,
    Category,
    GoalStatus,
    SavingGoal,
    TransactionType,
)
from transaction_service import add_expense, add_income

logger = logging.getLogger(__name__)

_CAT_SAVINGS = "Savings"
_CAT_SAVINGS_WITHDRAW = "Savings Withdraw"


def _resolve_reserved_category(name: str, type_: TransactionType, user_id: int, db: Session,) -> Category:
    category: Optional[Category] = db.execute(
        select(Category).where(
            Category.UserID == user_id,
            Category.CategoryName == name,
            Category.Type == type_,
        )
    ).scalar_one_or_none()

    if category is None:
        raise ValueError(
            f"Reserved category '{name}' ({type_.value}) not found for user {user_id}. "
            f"Ensure SystemCategories contains this entry and re-run the schema."
        )

    return category


def _get_goal_owned_by(user_id: int, goal_id: int, db: Session) -> SavingGoal:
    goal: Optional[SavingGoal] = db.execute(
        select(SavingGoal).where(
            SavingGoal.GoalID == goal_id,
            SavingGoal.UserID == user_id,
        )
    ).scalar_one_or_none()

    if goal is None:
        raise ValueError(
            f"Saving goal ID={goal_id} not found or not owned by user {user_id}."
        )

    return goal

def create_goal(user_id: int, goal_name: str, target_amount: Decimal, db: Session, deadline: Optional[date] = None,) -> SavingGoal:
    goal_name = goal_name.strip()
    if not goal_name:
        raise ValueError("Goal name cannot be empty.")

    if target_amount <= Decimal("0"):
        raise ValueError(
            f"TargetAmount must be greater than 0. Got: {target_amount}."
        )

    if deadline is not None and deadline <= date.today():
        raise ValueError(
            f"Deadline must be a future date. Got: {deadline}."
        )

    try:
        goal = SavingGoal(
            UserID=user_id,
            GoalName=goal_name,
            TargetAmount=target_amount,
            CurrentAmount=Decimal("0.00"),
            Deadline=deadline,
            Status=GoalStatus.Active,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        logger.info(
            "Goal created: id=%d name='%s' target=%s user=%d.",
            goal.GoalID, goal.GoalName, goal.TargetAmount, user_id,
        )
        return goal

    except IntegrityError as e:
        db.rollback()
        logger.error("Failed to create goal for user %d: %s", user_id, e)
        raise RuntimeError("Failed to create saving goal. See logs for details.") from e


def get_user_goals(user_id: int, db: Session, status_filter: Optional[GoalStatus] = None,) -> list[SavingGoal]:
    stmt = (
        select(SavingGoal)
        .where(SavingGoal.UserID == user_id)
        .order_by(SavingGoal.CreatedAt.desc())
    )
    if status_filter is not None:
        stmt = stmt.where(SavingGoal.Status == status_filter)

    return db.execute(stmt).scalars().all()


def get_goal_by_id(user_id: int, goal_id: int, db: Session) -> SavingGoal:
    return _get_goal_owned_by(user_id, goal_id, db)

def contribute_to_goal(user_id: int, goal_id: int, account_id: int, amount: Decimal, db: Session, description: Optional[str] = None,) -> dict:
    if amount <= Decimal("0"):
        raise ValueError(f"Contribution amount must be > 0. Got: {amount}.")

    goal: SavingGoal = _get_goal_owned_by(user_id, goal_id, db)
    if goal.Status == GoalStatus.Completed:
        raise ValueError(
            f"Goal '{goal.GoalName}' (ID={goal_id}) is already Completed. "
            "Withdraw funds first if you need to reset the goal."
        )

    category: Category = _resolve_reserved_category(
        _CAT_SAVINGS, TransactionType.Expense, user_id, db
    )

    try:
        expense_record = add_expense(
            user_id=user_id,
            account_id=account_id,
            category_id=category.CategoryID,
            amount=amount,
            transaction_date=date.today(),
            db=db,
            description=description or f"Contribution to goal: {goal.GoalName}",
        )
    except ValueError:
        raise  
    except Exception as e:
        logger.error(
            "Contribute to goal %d failed at expense creation: %s", goal_id, e
        )
        raise RuntimeError("Contribution failed. See logs for details.") from e

    goal.CurrentAmount = (goal.CurrentAmount + amount).quantize(Decimal("0.01"))

    if goal.CurrentAmount >= goal.TargetAmount:
        goal.Status = GoalStatus.Completed
        logger.info(
            "Goal COMPLETED: id=%d name='%s' current=%s target=%s user=%d.",
            goal.GoalID, goal.GoalName,
            goal.CurrentAmount, goal.TargetAmount, user_id,
        )

    db.commit()
    db.refresh(goal)
    logger.info(
        "Contribution: goal=%d amount=%s new_total=%s status=%s user=%d.",
        goal_id, amount, goal.CurrentAmount, goal.Status.value, user_id,
    )

    return {
        "goal_id":            goal.GoalID,
        "new_current_amount": goal.CurrentAmount,
        "status":             goal.Status.value,
        "expense_id":         expense_record.TransactionID,
    }

def withdraw_from_goal(user_id: int, goal_id: int, account_id: int, amount: Decimal, db: Session, description: Optional[str] = None,) -> dict:
    if amount <= Decimal("0"):
        raise ValueError(f"Withdrawal amount must be > 0. Got: {amount}.")

    goal: SavingGoal = _get_goal_owned_by(user_id, goal_id, db)

    if amount > goal.CurrentAmount:
        raise ValueError(
            f"Cannot withdraw {amount} from goal '{goal.GoalName}' — "
            f"only {goal.CurrentAmount} is available."
        )

    category: Category = _resolve_reserved_category(
        _CAT_SAVINGS_WITHDRAW, TransactionType.Income, user_id, db
    )

    try:
        income_record = add_income(
            user_id=user_id,
            account_id=account_id,
            category_id=category.CategoryID,
            amount=amount,
            transaction_date=date.today(),
            db=db,
            description=description or f"Withdrawal from goal: {goal.GoalName}",
        )
    except ValueError:
        raise  
    except Exception as e:
        logger.error(
            "Withdraw from goal %d failed at income creation: %s", goal_id, e
        )
        raise RuntimeError("Withdrawal failed. See logs for details.") from e

    goal.CurrentAmount = (goal.CurrentAmount - amount).quantize(Decimal("0.01"))

    if goal.Status == GoalStatus.Completed and goal.CurrentAmount < goal.TargetAmount:
        goal.Status = GoalStatus.Active
        logger.info(
            "Goal reverted to ACTIVE after withdrawal: id=%d current=%s target=%s.",
            goal.GoalID, goal.CurrentAmount, goal.TargetAmount,
        )

    db.commit()
    db.refresh(goal)
    logger.info(
        "Withdrawal: goal=%d amount=%s new_total=%s status=%s user=%d.",
        goal_id, amount, goal.CurrentAmount, goal.Status.value, user_id,
    )

    return {
        "goal_id":            goal.GoalID,
        "new_current_amount": goal.CurrentAmount,
        "status":             goal.Status.value,
        "income_id":          income_record.TransactionID,
    }


def delete_goal(user_id: int, goal_id: int, db: Session) -> None:
    goal: SavingGoal = _get_goal_owned_by(user_id, goal_id, db)

    if goal.CurrentAmount != Decimal("0.00"):
        raise ValueError(
            f"Cannot delete goal '{goal.GoalName}' (ID={goal_id}) — "
            f"it still holds {goal.CurrentAmount}. "
            "Withdraw all funds before deleting."
        )

    try:
        db.delete(goal)
        db.commit()
        logger.info(
            "Goal deleted: id=%d name='%s' user=%d.",
            goal_id, goal.GoalName, user_id,
        )
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete goal %d for user %d: %s", goal_id, user_id, e)
        raise RuntimeError("Failed to delete saving goal. See logs for details.") from e
