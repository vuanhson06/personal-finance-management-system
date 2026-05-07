import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import BankAccount, Category, Expense, Income, TransactionType

logger = logging.getLogger(__name__)


def _validate_amount(amount: Decimal) -> None:
    if amount <= Decimal("0"):
        raise ValueError(
            f"Transaction amount must be greater than 0. Got: {amount}."
        )


def _validate_date(transaction_date: date) -> None:
    if transaction_date > date.today():
        raise ValueError(
            f"Transaction date cannot be in the future. Got: {transaction_date}."
        )


def _assert_account_ownership(account_id: int, user_id: int, db: Session) -> BankAccount:
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
    if account.Balance < amount:
        raise ValueError(
            f"Insufficient funds: account {account.AccountID} has balance "
            f"{account.Balance}, but the requested debit is {amount}. "
            f"Transaction would result in a negative balance."
        )


def _assert_category_ownership(category_id: int, user_id: int, expected_type: TransactionType, db: Session) -> Category:
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


def get_income_list(user_id: int, db: Session, limit: int = 50, offset: int = 0,) -> list[Income]:
    return db.execute(
        select(Income)
        .where(Income.UserID == user_id)
        .order_by(Income.TransactionDate.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()


def get_expense_list(user_id: int, db: Session, limit: int = 50, offset: int = 0,) -> list[Expense]:
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

    _validate_amount(amount)
    _validate_date(transaction_date)
    account = _assert_account_ownership(account_id, user_id, db)
    _assert_sufficient_funds(account, amount)       
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
