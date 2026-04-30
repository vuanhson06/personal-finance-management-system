"""
transaction_service.py — Transaction CRUD Logic Engine
=======================================================
Provides the complete Create, Read, Update, Delete lifecycle for both
`Income` and `Expense` financial transactions.

Critical Rules:
    - ALL read queries MUST filter by UserID (Golden Rule — no exceptions).
    - ALL mutations MUST verify record ownership before modifying.
    - Amount validation (> 0) is performed in Python BEFORE touching the ORM.
    - BankAccounts.Balance is NEVER manually updated here — SQL triggers
      (After_Income_Insert/Update/Delete, After_Expense_Insert/Update/Delete)
      handle all balance changes atomically at the database level.
    - Category type is validated: Income transactions require Income-type
      categories; Expense transactions require Expense-type categories.

Directive Reference:
    - directives/backend_logic_rules.md — Section 2 (Data Isolation),
                                          Section 4 (Validation)
    - directives/db_rules.md           — Section 3 (Data Integrity)
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import BankAccount, Category, Expense, Income, TransactionType

logger = logging.getLogger(__name__)


# =============================================================================
# Private Ownership & Validation Guards
# =============================================================================

def _validate_amount(amount: Decimal) -> None:
    """
    Ensures a transaction amount is strictly positive.

    Args:
        amount: The transaction amount to validate.

    Raises:
        ValueError: If amount is zero or negative.
    """
    if amount <= Decimal("0"):
        raise ValueError(
            f"Transaction amount must be greater than 0. Got: {amount}."
        )


def _validate_date(transaction_date: date) -> None:
    """
    Ensures a transaction date is not set in the future.

    Args:
        transaction_date: The date to validate.

    Raises:
        ValueError: If the date is in the future.
    """
    if transaction_date > date.today():
        raise ValueError(
            f"Transaction date cannot be in the future. Got: {transaction_date}."
        )


def _assert_account_ownership(
    account_id: int, user_id: int, db: Session
) -> BankAccount:
    """
    Fetches a BankAccount and verifies it belongs to the given user.
    Implements the FK-level ownership check from backend_logic_rules.md.

    Args:
        account_id: The AccountID to verify.
        user_id:    The UserID of the authenticated user.
        db:         An active SQLAlchemy Session.

    Returns:
        The verified BankAccount ORM object.

    Raises:
        ValueError: If the account does not exist or is not owned by user.
    """
    account: Optional[BankAccount] = db.execute(
        select(BankAccount).where(
            BankAccount.AccountID == account_id,
            BankAccount.UserID == user_id,
        )
    ).scalar_one_or_none()
    if account is None:
        raise ValueError(
            f"AccountID={account_id} not found or not owned by UserID={user_id}."
        )
    return account


def _assert_sufficient_funds(account: BankAccount, amount: Decimal) -> None:
    """
    Ensures a bank account has sufficient funds for a debit operation.

    This is the Application Layer guard (Layer 1 of the two-layer
    Strict Balance Integrity defense — db_rules.md Section 5,
    backend_logic_rules.md Section 6).

    Must be called inside add_expense() AFTER _assert_account_ownership()
    so that the live BankAccount object (with current Balance) is available.

    Do NOT wrap the call in try-except — let the ValueError propagate
    cleanly to the caller (Webhook server, saving_service, frontend handler)
    so each caller can format the appropriate user-facing response.

    Args:
        account: The verified BankAccount ORM object with live Balance.
        amount:  The debit amount to validate against the current balance.

    Raises:
        ValueError: If account.Balance < amount, with a clear message
                    containing "Insufficient funds" (used by webhook_server.py
                    to detect and return HTTP 422).
    """
    if account.Balance < amount:
        raise ValueError(
            f"Insufficient funds: account {account.AccountID} has balance "
            f"{account.Balance}, but the requested debit is {amount}. "
            f"Transaction would result in a negative balance."
        )


def _assert_category_ownership(
    category_id: int, user_id: int, expected_type: TransactionType, db: Session
) -> Category:
    """
    Fetches a Category, verifies user ownership, and confirms the type
    matches the transaction being created (Income or Expense).

    Args:
        category_id:   The CategoryID to verify.
        user_id:       The UserID of the authenticated user.
        expected_type: The TransactionType required (Income or Expense).
        db:            An active SQLAlchemy Session.

    Returns:
        The verified Category ORM object.

    Raises:
        ValueError: If the category is not found, not owned, or wrong type.
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
    if category.Type != expected_type:
        raise ValueError(
            f"CategoryID={category_id} is of type '{category.Type.value}', "
            f"but expected '{expected_type.value}'."
        )
    return category


# =============================================================================
# Step 5.2 — Income CRUD
# =============================================================================

def get_income_list(
    user_id: int,
    db: Session,
    limit: int = 50,
    offset: int = 0,
) -> list[Income]:
    """
    Retrieves a paginated list of Income records for the authenticated user.
    Results are ordered by TransactionDate descending (most recent first).

    Data Isolation: UserID filter is MANDATORY — no plain .all() queries.

    Args:
        user_id: The authenticated user's UserID.
        db:      An active SQLAlchemy Session.
        limit:   Maximum number of records to return (default: 50).
        offset:  Number of records to skip for pagination (default: 0).

    Returns:
        A list of Income ORM objects belonging to the user.
    """
    return db.execute(
        select(Income)
        .where(Income.UserID == user_id)
        .order_by(Income.TransactionDate.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()


def get_expense_list(
    user_id: int,
    db: Session,
    limit: int = 50,
    offset: int = 0,
) -> list[Expense]:
    """
    Retrieves a paginated list of Expense records for the authenticated user.
    Results are ordered by TransactionDate descending (most recent first).

    Data Isolation: UserID filter is MANDATORY — no plain .all() queries.

    Args:
        user_id: The authenticated user's UserID.
        db:      An active SQLAlchemy Session.
        limit:   Maximum number of records to return (default: 50).
        offset:  Number of records to skip for pagination (default: 0).

    Returns:
        A list of Expense ORM objects belonging to the user.
    """
    return db.execute(
        select(Expense)
        .where(Expense.UserID == user_id)
        .order_by(Expense.TransactionDate.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()


def add_income(
    user_id: int,
    account_id: int,
    category_id: int,
    amount: Decimal,
    transaction_date: date,
    db: Session,
    description: Optional[str] = None,
    external_trans_id: Optional[str] = None,
) -> Income:
    """
    Validates and inserts a new Income transaction for the user.

    Validation chain (all in Python before touching the DB):
        1. Amount must be > 0.
        2. Date must not be in the future.
        3. AccountID must exist and be owned by user.
        4. CategoryID must exist, be owned by user, and be Income-type.

    Note: BankAccounts.Balance is updated automatically by the
    `After_Income_Insert` SQL trigger — do NOT update it here.

    Args:
        user_id:          The authenticated user's UserID.
        account_id:       The AccountID to credit.
        category_id:      The CategoryID (must be Income-type).
        amount:           The positive transaction amount.
        transaction_date: The date the income was received.
        db:               An active SQLAlchemy Session.
        description:      Optional text description.
        external_trans_id: Optional idempotency key from a Webhook payload
                           (stored as ExternalTransID). Defaults to None for
                           manually entered transactions.

    Returns:
        The newly created and persisted Income ORM object.

    Raises:
        ValueError: If any validation check fails.
        RuntimeError: For unexpected DB-level failures.
    """
    _validate_amount(amount)
    _validate_date(transaction_date)
    _assert_account_ownership(account_id, user_id, db)
    _assert_category_ownership(category_id, user_id, TransactionType.Income, db)

    try:
        income = Income(
            UserID=user_id,
            AccountID=account_id,
            CategoryID=category_id,
            Amount=amount,
            TransactionDate=transaction_date,
            Description=description,
            ExternalTransID=external_trans_id,
        )
        db.add(income)
        db.commit()
        db.refresh(income)
        logger.info(
            "Income added: id=%d user=%d amount=%s date=%s.",
            income.TransactionID, user_id, amount, transaction_date,
        )
        return income

    except IntegrityError as e:
        db.rollback()
        logger.error("IntegrityError adding income: %s", e)
        raise RuntimeError("Failed to save income transaction.") from e


def add_expense(
    user_id: int,
    account_id: int,
    category_id: int,
    amount: Decimal,
    transaction_date: date,
    db: Session,
    description: Optional[str] = None,
    external_trans_id: Optional[str] = None,
) -> Expense:
    """
    Validates and inserts a new Expense transaction for the user.

    Validation chain (all in Python before touching the DB):
        1. Amount must be > 0.
        2. Date must not be in the future.
        3. AccountID must exist and be owned by user.
        4. CategoryID must exist, be owned by user, and be Expense-type.

    Note: BankAccounts.Balance is reduced automatically by the
    `After_Expense_Insert` SQL trigger — do NOT update it here.

    Args:
        user_id:          The authenticated user's UserID.
        account_id:       The AccountID to debit.
        category_id:      The CategoryID (must be Expense-type).
        amount:           The positive transaction amount.
        transaction_date: The date the expense occurred.
        db:               An active SQLAlchemy Session.
        description:      Optional text description.
        external_trans_id: Optional idempotency key from a Webhook payload
                           (stored as ExternalTransID). Defaults to None for
                           manually entered transactions.

    Returns:
        The newly created and persisted Expense ORM object.

    Raises:
        ValueError: If any validation check fails.
        RuntimeError: For unexpected DB-level failures.
    """
    _validate_amount(amount)
    _validate_date(transaction_date)
    account = _assert_account_ownership(account_id, user_id, db)
    _assert_sufficient_funds(account, amount)          # Layer 1: balance guard
    _assert_category_ownership(category_id, user_id, TransactionType.Expense, db)

    try:
        expense = Expense(
            UserID=user_id,
            AccountID=account_id,
            CategoryID=category_id,
            Amount=amount,
            TransactionDate=transaction_date,
            Description=description,
            ExternalTransID=external_trans_id,
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)
        logger.info(
            "Expense added: id=%d user=%d amount=%s date=%s.",
            expense.TransactionID, user_id, amount, transaction_date,
        )
        return expense

    except IntegrityError as e:
        db.rollback()
        logger.error("IntegrityError adding expense: %s", e)
        raise RuntimeError("Failed to save expense transaction.") from e


def update_income(
    transaction_id: int,
    user_id: int,
    db: Session,
    amount: Optional[Decimal] = None,
    transaction_date: Optional[date] = None,
    category_id: Optional[int] = None,
    account_id: Optional[int] = None,
    description: Optional[str] = None,
) -> Income:
    """
    Updates an existing Income transaction after verifying ownership.

    Only fields explicitly provided (non-None) are updated. Ownership is
    verified via a UserID-scoped query before any mutation occurs.

    Note: The `After_Income_Update` SQL trigger automatically re-synchronizes
    BankAccounts.Balance for both the old and new account if AccountID changes.

    Args:
        transaction_id:   The TransactionID of the Income to update.
        user_id:          The authenticated user's UserID (ownership check).
        db:               An active SQLAlchemy Session.
        amount:           New amount (optional). Must be > 0.
        transaction_date: New date (optional). Must not be in the future.
        category_id:      New CategoryID (optional). Must be Income-type.
        account_id:       New AccountID (optional). Must be owned by user.
        description:      New description (optional).

    Returns:
        The updated Income ORM object.

    Raises:
        ValueError: If ownership check fails or any validation fails.
        RuntimeError: For unexpected DB-level failures.
    """
    # Ownership check — must be found AND owned by this user
    income: Optional[Income] = db.execute(
        select(Income).where(
            Income.TransactionID == transaction_id,
            Income.UserID == user_id,
        )
    ).scalar_one_or_none()
    if income is None:
        raise ValueError(
            f"IncomeID={transaction_id} not found or not owned by UserID={user_id}."
        )

    # Apply only provided fields
    if amount is not None:
        _validate_amount(amount)
        income.Amount = amount
    if transaction_date is not None:
        _validate_date(transaction_date)
        income.TransactionDate = transaction_date
    if category_id is not None:
        _assert_category_ownership(category_id, user_id, TransactionType.Income, db)
        income.CategoryID = category_id
    if account_id is not None:
        _assert_account_ownership(account_id, user_id, db)
        income.AccountID = account_id
    if description is not None:
        income.Description = description

    try:
        db.commit()
        db.refresh(income)
        logger.info("Income updated: id=%d user=%d.", transaction_id, user_id)
        return income
    except IntegrityError as e:
        db.rollback()
        raise RuntimeError("Failed to update income transaction.") from e


def update_expense(
    transaction_id: int,
    user_id: int,
    db: Session,
    amount: Optional[Decimal] = None,
    transaction_date: Optional[date] = None,
    category_id: Optional[int] = None,
    account_id: Optional[int] = None,
    description: Optional[str] = None,
) -> Expense:
    """
    Updates an existing Expense transaction after verifying ownership.

    Only fields explicitly provided (non-None) are updated. The
    `After_Expense_Update` SQL trigger re-synchronizes BankAccounts.Balance.

    Args:
        transaction_id:   The TransactionID of the Expense to update.
        user_id:          The authenticated user's UserID (ownership check).
        db:               An active SQLAlchemy Session.
        amount:           New amount (optional). Must be > 0.
        transaction_date: New date (optional). Must not be in the future.
        category_id:      New CategoryID (optional). Must be Expense-type.
        account_id:       New AccountID (optional). Must be owned by user.
        description:      New description (optional).

    Returns:
        The updated Expense ORM object.

    Raises:
        ValueError: If ownership check fails or any validation fails.
        RuntimeError: For unexpected DB-level failures.
    """
    expense: Optional[Expense] = db.execute(
        select(Expense).where(
            Expense.TransactionID == transaction_id,
            Expense.UserID == user_id,
        )
    ).scalar_one_or_none()
    if expense is None:
        raise ValueError(
            f"ExpenseID={transaction_id} not found or not owned by UserID={user_id}."
        )

    if amount is not None:
        _validate_amount(amount)
        expense.Amount = amount
    if transaction_date is not None:
        _validate_date(transaction_date)
        expense.TransactionDate = transaction_date
    if category_id is not None:
        _assert_category_ownership(category_id, user_id, TransactionType.Expense, db)
        expense.CategoryID = category_id
    if account_id is not None:
        _assert_account_ownership(account_id, user_id, db)
        expense.AccountID = account_id
    if description is not None:
        expense.Description = description

    try:
        db.commit()
        db.refresh(expense)
        logger.info("Expense updated: id=%d user=%d.", transaction_id, user_id)
        return expense
    except IntegrityError as e:
        db.rollback()
        raise RuntimeError("Failed to update expense transaction.") from e


def delete_income(transaction_id: int, user_id: int, db: Session) -> None:
    """
    Deletes an Income transaction after verifying ownership.

    Note: The `After_Income_Delete` SQL trigger automatically restores the
    corresponding BankAccounts.Balance by subtracting the deleted amount.

    Args:
        transaction_id: The TransactionID of the Income to delete.
        user_id:        The authenticated user's UserID (ownership check).
        db:             An active SQLAlchemy Session.

    Raises:
        ValueError: If the record is not found or not owned by the user.
        RuntimeError: For unexpected DB-level failures.
    """
    income: Optional[Income] = db.execute(
        select(Income).where(
            Income.TransactionID == transaction_id,
            Income.UserID == user_id,
        )
    ).scalar_one_or_none()
    if income is None:
        raise ValueError(
            f"IncomeID={transaction_id} not found or not owned by UserID={user_id}."
        )
    try:
        db.delete(income)
        db.commit()
        logger.info("Income deleted: id=%d user=%d.", transaction_id, user_id)
    except IntegrityError as e:
        db.rollback()
        raise RuntimeError("Failed to delete income transaction.") from e


def delete_expense(transaction_id: int, user_id: int, db: Session) -> None:
    """
    Deletes an Expense transaction after verifying ownership.

    Note: The `After_Expense_Delete` SQL trigger automatically restores the
    corresponding BankAccounts.Balance by adding back the deleted amount.

    Args:
        transaction_id: The TransactionID of the Expense to delete.
        user_id:        The authenticated user's UserID (ownership check).
        db:             An active SQLAlchemy Session.

    Raises:
        ValueError: If the record is not found or not owned by the user.
        RuntimeError: For unexpected DB-level failures.
    """
    expense: Optional[Expense] = db.execute(
        select(Expense).where(
            Expense.TransactionID == transaction_id,
            Expense.UserID == user_id,
        )
    ).scalar_one_or_none()
    if expense is None:
        raise ValueError(
            f"ExpenseID={transaction_id} not found or not owned by UserID={user_id}."
        )
    try:
        db.delete(expense)
        db.commit()
        logger.info("Expense deleted: id=%d user=%d.", transaction_id, user_id)
    except IntegrityError as e:
        db.rollback()
        raise RuntimeError("Failed to delete expense transaction.") from e
