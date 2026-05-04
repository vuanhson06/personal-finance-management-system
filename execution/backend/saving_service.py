"""
saving_service.py — Saving Goals Service
=========================================
Manages the full lifecycle of user-defined Saving Goals, including creation,
retrieval, contribution (deposit into goal), and withdrawal (return to bank).

Architecture — Transaction-Based Flow:
    ALL monetary movements are recorded as standard Income/Expense transactions
    using reserved system categories. This guarantees:
        - BankAccounts.Balance stays accurate via existing SQL triggers.
        - Every cent moved is auditable through Income/Expenses history.
        - No custom triggers are needed on the SavingGoals table.

    Contribute (deposit → goal):
        Expense record (Category: 'Savings')
        → After_Expense_Insert trigger fires
        → BankAccounts.Balance decreases
        → saving_service increments SavingGoals.CurrentAmount

    Withdraw (goal → bank):
        Income record (Category: 'Savings Withdraw')
        → After_Income_Insert trigger fires
        → BankAccounts.Balance increases
        → saving_service decrements SavingGoals.CurrentAmount

Reserved Categories:
    'Savings'         (Expense) — must exist in user's Categories table.
    'Savings Withdraw'(Income)  — must exist in user's Categories table.
    Both are seeded automatically via SystemCategories → After_User_Insert trigger.

Directive Reference:
    - directives/backend_logic_rules.md — Section 2 (Data Isolation),
                                          Section 5 (Saving Goals Service Rules)
    - directives/db_rules.md           — Sections 1-3 (Schema, Reserved Categories)
"""

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

# Reserved category names — must never be changed without a schema migration
_CAT_SAVINGS = "Savings"
_CAT_SAVINGS_WITHDRAW = "Savings Withdraw"


# =============================================================================
# Private Helpers
# =============================================================================

def _resolve_reserved_category(
    name: str,
    type_: TransactionType,
    user_id: int,
    db: Session,
) -> Category:
    """
    Looks up a reserved system category from the user's personal Categories table.

    Reserved categories ('Savings', 'Savings Withdraw') are seeded automatically
    for every user via SystemCategories → After_User_Insert trigger. If the
    category is missing, it indicates a schema migration gap — raise a clear
    ValueError rather than silently falling back to an unrelated category.

    Args:
        name:    The exact CategoryName to look up (e.g., 'Savings').
        type_:   The TransactionType (Income or Expense) — must match.
        user_id: The authenticated user's UserID.
        db:      An active SQLAlchemy Session.

    Returns:
        The matching Category ORM object.

    Raises:
        ValueError: If the category is not found for this user.
    """
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
    """
    Fetches a SavingGoal record, asserting it exists and belongs to the user.

    Args:
        user_id: The authenticated user's UserID.
        goal_id: The GoalID to look up.
        db:      An active SQLAlchemy Session.

    Returns:
        The SavingGoal ORM object.

    Raises:
        ValueError: If the goal does not exist or is not owned by this user.
    """
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


# =============================================================================
# Goal CRUD
# =============================================================================

def create_goal(
    user_id: int,
    goal_name: str,
    target_amount: Decimal,
    db: Session,
    deadline: Optional[date] = None,
) -> SavingGoal:
    """
    Creates a new Saving Goal for the authenticated user.

    Validation:
        - `target_amount` must be > 0.
        - `deadline`, if provided, must be a future date.
        - `goal_name` must be non-empty after stripping whitespace.

    Args:
        user_id:       The authenticated user's UserID.
        goal_name:     A descriptive name for the goal (e.g., 'Emergency Fund').
        target_amount: The monetary target. Must be > 0.
        db:            An active SQLAlchemy Session.
        deadline:      Optional target completion date. Must be in the future.

    Returns:
        The newly created and persisted SavingGoal ORM object.

    Raises:
        ValueError:   On failed validation.
        RuntimeError: On unexpected DB-level failure.
    """
    # --- Validation ---
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


def get_user_goals(
    user_id: int,
    db: Session,
    status_filter: Optional[GoalStatus] = None,
) -> list[SavingGoal]:
    """
    Returns all Saving Goals owned by the authenticated user.

    Data Isolation: UserID filter is MANDATORY on every query.

    Args:
        user_id:       The authenticated user's UserID.
        db:            An active SQLAlchemy Session.
        status_filter: Optional GoalStatus to filter results (Active/Completed).

    Returns:
        A list of SavingGoal objects ordered by CreatedAt descending (newest first).
    """
    stmt = (
        select(SavingGoal)
        .where(SavingGoal.UserID == user_id)
        .order_by(SavingGoal.CreatedAt.desc())
    )
    if status_filter is not None:
        stmt = stmt.where(SavingGoal.Status == status_filter)

    return db.execute(stmt).scalars().all()


def get_goal_by_id(user_id: int, goal_id: int, db: Session) -> SavingGoal:
    """
    Returns a single SavingGoal by ID, asserting ownership.

    Args:
        user_id: The authenticated user's UserID.
        goal_id: The GoalID to fetch.
        db:      An active SQLAlchemy Session.

    Returns:
        The matching SavingGoal ORM object.

    Raises:
        ValueError: If the goal does not exist or is not owned by this user.
    """
    return _get_goal_owned_by(user_id, goal_id, db)


# =============================================================================
# Contribute (Deposit → Goal)
# =============================================================================

def contribute_to_goal(
    user_id: int,
    goal_id: int,
    account_id: int,
    amount: Decimal,
    db: Session,
    description: Optional[str] = None,
) -> dict:
    """
    Moves money FROM a bank account INTO a saving goal.

    Flow:
        1. Validate amount > 0.
        2. Assert goal ownership and Active status.
        3. Create an Expense (Category: 'Savings') via transaction_service.
           → After_Expense_Insert trigger fires → BankAccounts.Balance decreases.
        4. Increment SavingGoals.CurrentAmount.
        5. Auto-complete goal if CurrentAmount >= TargetAmount.
        6. Commit and refresh.

    Args:
        user_id:     The authenticated user's UserID.
        goal_id:     The target GoalID.
        account_id:  The source BankAccount's AccountID.
        amount:      A positive Decimal — the amount to move into the goal.
        db:          An active SQLAlchemy Session.
        description: Optional memo for the Expense transaction record.

    Returns:
        A summary dict: {
            'goal_id':            int,
            'new_current_amount': Decimal,
            'status':             str,
            'expense_id':         int,
        }

    Raises:
        ValueError:   On validation failure or missing reserved category.
        RuntimeError: On unexpected DB-level failure.
    """
    # Step 1: Validate amount
    if amount <= Decimal("0"):
        raise ValueError(f"Contribution amount must be > 0. Got: {amount}.")

    # Step 2: Assert goal ownership + Active status
    goal: SavingGoal = _get_goal_owned_by(user_id, goal_id, db)
    if goal.Status == GoalStatus.Completed:
        raise ValueError(
            f"Goal '{goal.GoalName}' (ID={goal_id}) is already Completed. "
            "Withdraw funds first if you need to reset the goal."
        )

    # Step 3: Resolve reserved 'Savings' (Expense) category
    category: Category = _resolve_reserved_category(
        _CAT_SAVINGS, TransactionType.Expense, user_id, db
    )

    # Step 4: Create Expense → triggers update BankAccounts.Balance
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
        raise  # Re-raise clean validation errors from transaction_service
    except Exception as e:
        logger.error(
            "Contribute to goal %d failed at expense creation: %s", goal_id, e
        )
        raise RuntimeError("Contribution failed. See logs for details.") from e

    # Step 5: Increment CurrentAmount
    goal.CurrentAmount = (goal.CurrentAmount + amount).quantize(Decimal("0.01"))

    # Step 6: Auto-complete if target reached
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


# =============================================================================
# Withdraw (Goal → Bank)
# =============================================================================

def withdraw_from_goal(
    user_id: int,
    goal_id: int,
    account_id: int,
    amount: Decimal,
    db: Session,
    description: Optional[str] = None,
) -> dict:
    """
    Returns money FROM a saving goal BACK to a bank account.

    Flow:
        1. Validate amount > 0.
        2. Assert goal ownership.
        3. Assert amount <= CurrentAmount (no negative balances allowed).
        4. Create an Income (Category: 'Savings Withdraw') via transaction_service.
           → After_Income_Insert trigger fires → BankAccounts.Balance increases.
        5. Decrement SavingGoals.CurrentAmount.
        6. Revert Status to Active if was Completed and balance fell below target.
        7. Commit and refresh.

    Args:
        user_id:     The authenticated user's UserID.
        goal_id:     The source GoalID.
        account_id:  The destination BankAccount's AccountID.
        amount:      A positive Decimal — the amount to withdraw from the goal.
        db:          An active SQLAlchemy Session.
        description: Optional memo for the Income transaction record.

    Returns:
        A summary dict: {
            'goal_id':            int,
            'new_current_amount': Decimal,
            'status':             str,
            'income_id':          int,
        }

    Raises:
        ValueError:   On validation failure or missing reserved category.
        RuntimeError: On unexpected DB-level failure.
    """
    # Step 1: Validate amount
    if amount <= Decimal("0"):
        raise ValueError(f"Withdrawal amount must be > 0. Got: {amount}.")

    # Step 2: Assert goal ownership
    goal: SavingGoal = _get_goal_owned_by(user_id, goal_id, db)

    # Step 3: Prevent negative goal balance
    if amount > goal.CurrentAmount:
        raise ValueError(
            f"Cannot withdraw {amount} from goal '{goal.GoalName}' — "
            f"only {goal.CurrentAmount} is available."
        )

    # Step 4: Resolve reserved 'Savings Withdraw' (Income) category
    category: Category = _resolve_reserved_category(
        _CAT_SAVINGS_WITHDRAW, TransactionType.Income, user_id, db
    )

    # Step 5: Create Income → triggers update BankAccounts.Balance
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
        raise  # Re-raise clean validation errors from transaction_service
    except Exception as e:
        logger.error(
            "Withdraw from goal %d failed at income creation: %s", goal_id, e
        )
        raise RuntimeError("Withdrawal failed. See logs for details.") from e

    # Step 6: Decrement CurrentAmount
    goal.CurrentAmount = (goal.CurrentAmount - amount).quantize(Decimal("0.01"))

    # Step 7: Revert status if below target
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


# =============================================================================
# Delete Goal
# =============================================================================

def delete_goal(user_id: int, goal_id: int, db: Session) -> None:
    """
    Permanently deletes a Saving Goal owned by the authenticated user.

    Safety Rule: The goal's CurrentAmount must be exactly 0.00 before deletion.
    Use `withdraw_from_goal()` to return any remaining funds to a bank account
    before calling this function.

    Args:
        user_id: The authenticated user's UserID.
        goal_id: The GoalID to delete.
        db:      An active SQLAlchemy Session.

    Raises:
        ValueError:   If the goal is not found, not owned, or has remaining funds.
        RuntimeError: On unexpected DB-level failure.
    """
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
