import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import bcrypt
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    Boolean,
    text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserRole(enum.Enum):
    Admin = "Admin"
    User = "User"


class TransactionType(enum.Enum):
    Income = "Income"
    Expense = "Expense"


class GoalStatus(enum.Enum):
    Active = "Active"
    Completed = "Completed"


class User(Base):
    __tablename__ = "Users"

    UserID: Mapped[int] = mapped_column(
        "UserID", primary_key=True, autoincrement=True
    )
    UserName: Mapped[str] = mapped_column(
        "UserName", String(100), nullable=False
    )
    Email: Mapped[str] = mapped_column(
        "Email", String(255), nullable=False, unique=True, index=True
    )
    PhoneNumber: Mapped[Optional[str]] = mapped_column(
        "PhoneNumber", String(15), nullable=True, unique=True
    )
    PasswordHash: Mapped[str] = mapped_column(
        "PasswordHash", String(255), nullable=False
    )
    Role: Mapped[UserRole] = mapped_column(
        "Role",
        SAEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserRole.User,
        server_default="User",
    )
    IsActive: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True, server_default=text("1")
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )
    UpdatedAt: Mapped[datetime] = mapped_column(
        "UpdatedAt",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    bank_accounts: Mapped[list["BankAccount"]] = relationship(
        "BankAccount", back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    market_watches: Mapped[list["MarketWatch"]] = relationship(
        "MarketWatch", back_populates="user", cascade="all, delete-orphan"
    )
    admin_logs: Mapped[list["AdminLog"]] = relationship(
        "AdminLog", foreign_keys="[AdminLog.AdminID]", back_populates="admin", cascade="all, delete-orphan"
    )
    incomes: Mapped[list["Income"]] = relationship(
        "Income", back_populates="user", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="user", cascade="all, delete-orphan"
    )
    saving_goals: Mapped[list["SavingGoal"]] = relationship(
        "SavingGoal", back_populates="user", cascade="all, delete-orphan"
    )
  

    def set_password(self, plain_text: str) -> None:
        salt: bytes = bcrypt.gensalt()
        self.PasswordHash = bcrypt.hashpw(
            plain_text.encode("utf-8"), salt
        ).decode("utf-8")

    def verify_password(self, plain_text: str) -> bool:
        return bcrypt.checkpw(
            plain_text.encode("utf-8"),
            self.PasswordHash.encode("utf-8"),
        )

    def is_admin(self) -> bool:
        return self.Role == UserRole.Admin

    def __repr__(self) -> str:
        return f"<User id={self.UserID} email='{self.Email}' role={self.Role.value}>"

class AdminLog(Base):
    __tablename__ = "AdminLogs"

    LogID: Mapped[int] = mapped_column("LogID", primary_key=True, autoincrement=True)
    AdminID: Mapped[int] = mapped_column("AdminID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False)
    Action: Mapped[str] = mapped_column("Action", String(255), nullable=False)
    TargetUserID: Mapped[Optional[int]] = mapped_column("TargetUserID", ForeignKey("Users.UserID", ondelete="SET NULL"), nullable=True)
    Timestamp: Mapped[datetime] = mapped_column("Timestamp", DateTime, nullable=False, server_default=func.now())

    admin: Mapped["User"] = relationship("User", foreign_keys=[AdminID], back_populates="admin_logs")
    target_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[TargetUserID])


class BankAccount(Base):
    __tablename__ = "BankAccounts"

    AccountID: Mapped[int] = mapped_column(
        "AccountID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    AccountName: Mapped[str] = mapped_column(
        "AccountName", String(100), nullable=False
    )
    AccountNumber: Mapped[str] = mapped_column(
        "AccountNumber",
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique external account identifier. Webhook bank_sub_acc_id maps to this.",
    )
    Balance: Mapped[Decimal] = mapped_column(
        "Balance", Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )
    UpdatedAt: Mapped[datetime] = mapped_column(
        "UpdatedAt",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="bank_accounts")
    incomes: Mapped[list["Income"]] = relationship(
        "Income", back_populates="bank_account", cascade="all, delete-orphan",
        overlaps="incomes"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="bank_account", cascade="all, delete-orphan",
        overlaps="expenses"
    )
    monthly_closures: Mapped[list["MonthlyClosure"]] = relationship(
        "MonthlyClosure", back_populates="bank_account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "UserID", "AccountID",
            name="uq_bankaccount_user_account",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<BankAccount id={self.AccountID} "
            f"number='{self.AccountNumber}' "
            f"name='{self.AccountName}' balance={self.Balance}>"
        )

class SystemCategory(Base):
    __tablename__ = "SystemCategories"

    SystemCatID: Mapped[int] = mapped_column(
        "SystemCatID", primary_key=True, autoincrement=True
    )
    CategoryName: Mapped[str] = mapped_column(
        "CategoryName", String(100), nullable=False
    )
    Type: Mapped[TransactionType] = mapped_column(
        "Type",
        SAEnum(TransactionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<SystemCategory id={self.SystemCatID} "
            f"name='{self.CategoryName}' type={self.Type.value}>"
        )

class Category(Base):
    __tablename__ = "Categories"

    CategoryID: Mapped[int] = mapped_column(
        "CategoryID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    CategoryName: Mapped[str] = mapped_column(
        "CategoryName", String(100), nullable=False
    )
    Type: Mapped[TransactionType] = mapped_column(
        "Type",
        SAEnum(TransactionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="categories")
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget", back_populates="category", cascade="all, delete-orphan",
        overlaps="budgets"
    )
    incomes: Mapped[list["Income"]] = relationship(
        "Income", back_populates="category", cascade="all, delete-orphan",
        overlaps="incomes,incomes"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="category", cascade="all, delete-orphan",
        overlaps="expenses,expenses"
    )

    __table_args__ = (
        UniqueConstraint(
            "UserID", "CategoryID",
            name="uq_category_user_category",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Category id={self.CategoryID} "
            f"name='{self.CategoryName}' user_id={self.UserID}>"
        )

class Budget(Base):
    __tablename__ = "Budgets"

    BudgetID: Mapped[int] = mapped_column(
        "BudgetID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    CategoryID: Mapped[int] = mapped_column(
        "CategoryID",
        nullable=False,
        comment="Must match UserID in Categories (enforced by composite FK).",
    )
    LimitAmount: Mapped[Decimal] = mapped_column(
        "LimitAmount", Numeric(15, 2), nullable=False
    )
    Period: Mapped[str] = mapped_column(
        "Period", String(7), nullable=False, comment="Format: YYYY-MM"
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )
    UpdatedAt: Mapped[datetime] = mapped_column(
        "UpdatedAt",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="budgets",
        overlaps="budgets"
    )
    category: Mapped["Category"] = relationship(
        "Category", back_populates="budgets",
        overlaps="budgets,user"
    )

    __table_args__ = (
        Index("idx_budgets_user_cat_period", "UserID", "CategoryID", "Period"),
        ForeignKeyConstraint(
            ["UserID", "CategoryID"],
            ["Categories.UserID", "Categories.CategoryID"],
            ondelete="CASCADE",
            name="fk_budget_user_category_composite",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Budget id={self.BudgetID} "
            f"category_id={self.CategoryID} period='{self.Period}' "
            f"limit={self.LimitAmount}>"
        )

class MarketWatch(Base):
    __tablename__ = "MarketWatch"

    WatchID: Mapped[int] = mapped_column(
        "WatchID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    AssetSymbol: Mapped[str] = mapped_column(
        "AssetSymbol", String(20), nullable=False, comment="e.g., AAPL, BTC-USD, GC=F"
    )
    AssetType: Mapped[Optional[str]] = mapped_column(
        "AssetType", String(50), nullable=True, comment="e.g., Stock, Crypto, Gold"
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="market_watches")

    def __repr__(self) -> str:
        return (
            f"<MarketWatch id={self.WatchID} "
            f"symbol='{self.AssetSymbol}' type='{self.AssetType}'>"
        )

class Income(Base):
    __tablename__ = "Income"

    TransactionID: Mapped[int] = mapped_column(
        "TransactionID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    AccountID: Mapped[int] = mapped_column(
        "AccountID",
        nullable=False,
        comment="Must match UserID in BankAccounts (enforced by composite FK).",
    )
    CategoryID: Mapped[int] = mapped_column(
        "CategoryID",
        nullable=False,
        comment="Must match UserID in Categories (enforced by composite FK).",
    )
    Amount: Mapped[Decimal] = mapped_column(
        "Amount",
        Numeric(15, 2),
        nullable=False,
        comment="Must be > 0. Enforced by CHECK constraint and Python validation.",
    )
    TransactionDate: Mapped[date] = mapped_column(
        "TransactionDate", Date, nullable=False
    )
    Description: Mapped[Optional[str]] = mapped_column(
        "Description", Text, nullable=True
    )
    ExternalTransID: Mapped[Optional[str]] = mapped_column(
        "ExternalTransID",
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Idempotency key from inbound Webhook payload (bank_transaction_id).",
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="incomes",
        overlaps="bank_account,category,incomes"
    )
    bank_account: Mapped["BankAccount"] = relationship(
        "BankAccount", back_populates="incomes",
        overlaps="category,incomes,user"
    )
    category: Mapped["Category"] = relationship(
        "Category", back_populates="incomes",
        overlaps="bank_account,incomes,user"
    )

    __table_args__ = (
        CheckConstraint("Amount > 0", name="chk_income_amount_positive"),
        Index("idx_income_user_date", "UserID", "TransactionDate"),
        ForeignKeyConstraint(
            ["UserID", "AccountID"],
            ["BankAccounts.UserID", "BankAccounts.AccountID"],
            ondelete="CASCADE",
            name="fk_income_user_account_composite",
        ),
        ForeignKeyConstraint(
            ["UserID", "CategoryID"],
            ["Categories.UserID", "Categories.CategoryID"],
            ondelete="CASCADE",
            name="fk_income_user_category_composite",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Income id={self.TransactionID} "
            f"amount={self.Amount} date={self.TransactionDate}>"
        )

class Expense(Base):
    __tablename__ = "Expenses"

    TransactionID: Mapped[int] = mapped_column(
        "TransactionID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    AccountID: Mapped[int] = mapped_column(
        "AccountID",
        nullable=False,
        comment="Must match UserID in BankAccounts (enforced by composite FK).",
    )
    CategoryID: Mapped[int] = mapped_column(
        "CategoryID",
        nullable=False,
        comment="Must match UserID in Categories (enforced by composite FK).",
    )
    Amount: Mapped[Decimal] = mapped_column(
        "Amount",
        Numeric(15, 2),
        nullable=False,
        comment="Must be > 0. Enforced by CHECK constraint and Python validation.",
    )
    TransactionDate: Mapped[date] = mapped_column(
        "TransactionDate", Date, nullable=False
    )
    Description: Mapped[Optional[str]] = mapped_column(
        "Description", Text, nullable=True
    )
    ExternalTransID: Mapped[Optional[str]] = mapped_column(
        "ExternalTransID",
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Idempotency key from inbound Webhook payload (bank_transaction_id).",
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="expenses",
        overlaps="bank_account,category,expenses"
    )
    bank_account: Mapped["BankAccount"] = relationship(
        "BankAccount", back_populates="expenses",
        overlaps="category,expenses,user"
    )
    category: Mapped["Category"] = relationship(
        "Category", back_populates="expenses",
        overlaps="bank_account,expenses,user"
    )

    __table_args__ = (
        CheckConstraint("Amount > 0", name="chk_expense_amount_positive"),
        Index("idx_expense_user_cat_date", "UserID", "CategoryID", "TransactionDate"),
        ForeignKeyConstraint(
            ["UserID", "AccountID"],
            ["BankAccounts.UserID", "BankAccounts.AccountID"],
            ondelete="CASCADE",
            name="fk_expense_user_account_composite",
        ),
        ForeignKeyConstraint(
            ["UserID", "CategoryID"],
            ["Categories.UserID", "Categories.CategoryID"],
            ondelete="CASCADE",
            name="fk_expense_user_category_composite",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Expense id={self.TransactionID} "
            f"amount={self.Amount} date={self.TransactionDate}>"
        )

class MonthlyClosure(Base):
    __tablename__ = "MonthlyClosures"

    ClosureID: Mapped[int] = mapped_column(
        "ClosureID", primary_key=True, autoincrement=True
    )
    AccountID: Mapped[int] = mapped_column(
        "AccountID",
        ForeignKey("BankAccounts.AccountID", ondelete="CASCADE"),
        nullable=False,
    )
    ClosurePeriod: Mapped[str] = mapped_column(
        "ClosurePeriod", String(7), nullable=False, comment="Format: YYYY-MM"
    )
    ClosingBalance: Mapped[Decimal] = mapped_column(
        "ClosingBalance", Numeric(15, 2), nullable=False
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    bank_account: Mapped["BankAccount"] = relationship(
        "BankAccount", back_populates="monthly_closures"
    )

    __table_args__ = (
        UniqueConstraint(
            "AccountID", "ClosurePeriod", name="unique_account_period"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MonthlyClosure id={self.ClosureID} "
            f"account_id={self.AccountID} period='{self.ClosurePeriod}' "
            f"balance={self.ClosingBalance}>"
        )

class SavingGoal(Base):
    __tablename__ = "SavingGoals"

    GoalID: Mapped[int] = mapped_column(
        "GoalID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    GoalName: Mapped[str] = mapped_column(
        "GoalName", String(255), nullable=False
    )
    TargetAmount: Mapped[Decimal] = mapped_column(
        "TargetAmount",
        Numeric(15, 2),
        nullable=False,
        comment="Must be > 0. Enforced by CHECK constraint.",
    )
    CurrentAmount: Mapped[Decimal] = mapped_column(
        "CurrentAmount",
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Managed by saving_service.py — never updated by triggers.",
    )
    Deadline: Mapped[Optional[date]] = mapped_column(
        "Deadline", Date, nullable=True
    )
    Status: Mapped[GoalStatus] = mapped_column(
        "Status",
        SAEnum(GoalStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=GoalStatus.Active,
        server_default="Active",
    )
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )
    UpdatedAt: Mapped[datetime] = mapped_column(
        "UpdatedAt",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="saving_goals")

    __table_args__ = (
        CheckConstraint("TargetAmount > 0", name="chk_savinggoal_target_positive"),
        Index("idx_savinggoals_user", "UserID", "Status"),
    )

    def __repr__(self) -> str:
        return (
            f"<SavingGoal id={self.GoalID} "
            f"name='{self.GoalName}' "
            f"current={self.CurrentAmount}/{self.TargetAmount} "
            f"status={self.Status.value}>"
        )
