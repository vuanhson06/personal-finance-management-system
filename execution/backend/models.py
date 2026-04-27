"""
models.py — SQLAlchemy ORM Data Models
=======================================
Defines all Python ORM classes that perfectly mirror the 9 tables in
`execution/database/master_schemas.sql`. Each model inherits from `Base`
(defined in `database.py`) and uses SQLAlchemy 2.0+ Mapped/mapped_column
syntax for full type-hint support.

Security Notes:
    - The `User` model integrates `bcrypt` directly for password hashing.
    - Plain-text passwords are NEVER stored or passed to the DB layer.
    - Role-based access is enforced via the `is_admin()` helper method.

Directive Reference:
    - directives/backend_logic_rules.md — Section 1 (ORM Modeling), Section 3 (RBAC)
    - directives/db_rules.md — Section 4 (Security Protocols)
"""

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
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# =============================================================================
# Enumerations
# =============================================================================

class UserRole(enum.Enum):
    """
    Defines the two valid roles a user can hold in the system.
    Maps directly to the MySQL ENUM('Admin', 'User') on the Users table.

    Admin : Has elevated privileges, including management of SystemCategories.
    User  : Standard access — can only interact with their own data.
    """
    Admin = "Admin"
    User = "User"


class TransactionType(enum.Enum):
    """
    Defines the two valid category/transaction types.
    Maps to ENUM('Income', 'Expense') used in SystemCategories and Categories.
    """
    Income = "Income"
    Expense = "Expense"


# =============================================================================
# Model 1: User
# =============================================================================

class User(Base):
    """
    ORM model for the `Users` table.

    Represents an authenticated account in the Personal Finance system.
    Each user owns their own BankAccounts, Categories, Budgets, and transactions.
    Passwords are NEVER stored in plain text — use `set_password()` on registration
    and `verify_password()` on login.

    Relationships:
        bank_accounts  → List[BankAccount]
        categories     → List[Category]
        budgets        → List[Budget]
        market_watches → List[MarketWatch]
        incomes        → List[Income]
        expenses       → List[Expense]
    """

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

    # --- Relationships (back-populated from child tables) ---
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
    incomes: Mapped[list["Income"]] = relationship(
        "Income", back_populates="user", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="user", cascade="all, delete-orphan"
    )
  
    # --- Security Methods ---

    def set_password(self, plain_text: str) -> None:
        """
        Hashes a plain-text password using bcrypt and stores the result
        in `self.PasswordHash`. This is the ONLY sanctioned way to set
        a user's password. Never call this with an already-hashed value.

        Args:
            plain_text: The raw password string provided by the user during
                        registration or a password-change operation.
        """
        salt: bytes = bcrypt.gensalt()
        self.PasswordHash = bcrypt.hashpw(
            plain_text.encode("utf-8"), salt
        ).decode("utf-8")

    def verify_password(self, plain_text: str) -> bool:
        """
        Verifies a plain-text login attempt against the stored bcrypt hash.
        Returns True only if the password is correct. Uses constant-time
        comparison to prevent timing attacks.

        Args:
            plain_text: The raw password string provided by the user at login.

        Returns:
            True if the password matches the stored hash, False otherwise.
        """
        return bcrypt.checkpw(
            plain_text.encode("utf-8"),
            self.PasswordHash.encode("utf-8"),
        )

    def is_admin(self) -> bool:
        """
        Checks if this user holds the 'Admin' role.
        Use this guard before permitting any SystemCategories mutation.

        Returns:
            True if the user's role is UserRole.Admin, False otherwise.
        """
        return self.Role == UserRole.Admin

    def __repr__(self) -> str:
        return f"<User id={self.UserID} email='{self.Email}' role={self.Role.value}>"


# =============================================================================
# Model 2: BankAccount
# =============================================================================

class BankAccount(Base):
    """
    ORM model for the `BankAccounts` table.

    Represents a financial account belonging to a User. The `Balance` field
    is managed exclusively by SQL triggers on the Income and Expenses tables
    and must NEVER be updated directly from the Python application layer.

    Relationships:
        user     → User (many-to-one)
        incomes  → List[Income]
        expenses → List[Expense]
        monthly_closures → List[MonthlyClosure]
    """

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

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="bank_accounts")
    incomes: Mapped[list["Income"]] = relationship(
        "Income", back_populates="bank_account", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="bank_account", cascade="all, delete-orphan"
    )
    monthly_closures: Mapped[list["MonthlyClosure"]] = relationship(
        "MonthlyClosure", back_populates="bank_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<BankAccount id={self.AccountID} "
            f"name='{self.AccountName}' balance={self.Balance}>"
        )


# =============================================================================
# Model 3: SystemCategory
# =============================================================================

class SystemCategory(Base):
    """
    ORM model for the `SystemCategories` table.

    This is a GLOBAL system-level table with NO UserID. It serves as the
    master template from which new user categories are cloned automatically
    by the `After_User_Insert` SQL trigger.

    CRITICAL: Only Admin users are permitted to INSERT, UPDATE, or DELETE
    records in this table. Enforce the `user.is_admin()` check in all
    service-layer code that mutates this model.

    Relationships: None — this is a standalone template table.
    """

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


# =============================================================================
# Model 4: Category
# =============================================================================

class Category(Base):
    """
    ORM model for the `Categories` table.

    Represents a privately-owned category tag for a specific User. Every
    user's categories are automatically seeded from `SystemCategories` when
    their account is created (via the `After_User_Insert` SQL trigger).
    Users may then freely add, rename, or delete their own categories without
    affecting the system defaults or other users.

    Business Rule: `UserID` is NOT NULL — a category must always have an owner.

    Relationships:
        user     → User (many-to-one)
        budgets  → List[Budget]
        incomes  → List[Income]
        expenses → List[Expense]
    """

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

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="categories")
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget", back_populates="category", cascade="all, delete-orphan"
    )
    incomes: Mapped[list["Income"]] = relationship(
        "Income", back_populates="category", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Category id={self.CategoryID} "
            f"name='{self.CategoryName}' user_id={self.UserID}>"
        )


# =============================================================================
# Model 5: Budget
# =============================================================================

class Budget(Base):
    """
    ORM model for the `Budgets` table.

    Defines a spending cap for a specific Category within a given period
    for a specific User. The `GetBudgetStatus` SQL UDF is used to compute
    the remaining allowance dynamically at the database level.

    Period format: 'YYYY-MM' (e.g., '2026-04') — aligns with the MySQL
    DATE_FORMAT pattern used in analytics views.

    Relationships:
        user     → User (many-to-one)
        category → Category (many-to-one)
    """

    __tablename__ = "Budgets"

    BudgetID: Mapped[int] = mapped_column(
        "BudgetID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    CategoryID: Mapped[int] = mapped_column(
        "CategoryID",
        ForeignKey("Categories.CategoryID", ondelete="CASCADE"),
        nullable=False,
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

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["Category"] = relationship(
        "Category", back_populates="budgets"
    )

    # --- Performance Index (mirrors master_schemas.sql) ---
    __table_args__ = (
        Index("idx_budgets_user_cat_period", "UserID", "CategoryID", "Period"),
    )

    def __repr__(self) -> str:
        return (
            f"<Budget id={self.BudgetID} "
            f"category_id={self.CategoryID} period='{self.Period}' "
            f"limit={self.LimitAmount}>"
        )


# =============================================================================
# Model 6: MarketWatch
# =============================================================================

class MarketWatch(Base):
    """
    ORM model for the `MarketWatch` table.

    Represents a financial asset (Stock, Crypto, Gold, etc.) that a User
    is monitoring. Live price data is fetched from the `yfinance` service
    in the backend and is NOT stored here — this table only tracks the
    user's watchlist of asset symbols.

    Relationships:
        user → User (many-to-one)
    """

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

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="market_watches")

    def __repr__(self) -> str:
        return (
            f"<MarketWatch id={self.WatchID} "
            f"symbol='{self.AssetSymbol}' type='{self.AssetType}'>"
        )


# =============================================================================
# Model 7: Income
# =============================================================================

class Income(Base):
    """
    ORM model for the `Income` table.

    Records a single income-type financial transaction for a User.
    The `Amount` must be strictly greater than 0 — enforced at both the
    SQL layer (CHECK constraint) and the Python service layer before insertion.

    IMPORTANT: Do NOT manually update `BankAccounts.Balance` after inserting
    an Income record. The `After_Income_Insert` SQL trigger handles this
    automatically and atomically.

    Relationships:
        user         → User (many-to-one)
        bank_account → BankAccount (many-to-one)
        category     → Category (many-to-one)
    """

    __tablename__ = "Income"

    TransactionID: Mapped[int] = mapped_column(
        "TransactionID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    AccountID: Mapped[int] = mapped_column(
        "AccountID",
        ForeignKey("BankAccounts.AccountID", ondelete="CASCADE"),
        nullable=False,
    )
    CategoryID: Mapped[int] = mapped_column(
        "CategoryID",
        ForeignKey("Categories.CategoryID", ondelete="CASCADE"),
        nullable=False,
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
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="incomes")
    bank_account: Mapped["BankAccount"] = relationship(
        "BankAccount", back_populates="incomes"
    )
    category: Mapped["Category"] = relationship(
        "Category", back_populates="incomes"
    )

    # --- Performance Index + Amount Validation (mirrors master_schemas.sql) ---
    __table_args__ = (
        CheckConstraint("Amount > 0", name="chk_income_amount_positive"),
        Index("idx_income_user_date", "UserID", "TransactionDate"),
    )

    def __repr__(self) -> str:
        return (
            f"<Income id={self.TransactionID} "
            f"amount={self.Amount} date={self.TransactionDate}>"
        )


# =============================================================================
# Model 8: Expense
# =============================================================================

class Expense(Base):
    """
    ORM model for the `Expenses` table.

    Records a single expense-type financial transaction for a User.
    The `Amount` must be strictly greater than 0 — enforced at both the
    SQL layer (CHECK constraint) and the Python service layer before insertion.

    IMPORTANT: Do NOT manually update `BankAccounts.Balance` after inserting
    an Expense record. The `After_Expense_Insert` SQL trigger handles this
    automatically and atomically.

    Relationships:
        user         → User (many-to-one)
        bank_account → BankAccount (many-to-one)
        category     → Category (many-to-one)
    """

    __tablename__ = "Expenses"

    TransactionID: Mapped[int] = mapped_column(
        "TransactionID", primary_key=True, autoincrement=True
    )
    UserID: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False
    )
    AccountID: Mapped[int] = mapped_column(
        "AccountID",
        ForeignKey("BankAccounts.AccountID", ondelete="CASCADE"),
        nullable=False,
    )
    CategoryID: Mapped[int] = mapped_column(
        "CategoryID",
        ForeignKey("Categories.CategoryID", ondelete="CASCADE"),
        nullable=False,
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
    CreatedAt: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime, nullable=False, server_default=func.now()
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="expenses")
    bank_account: Mapped["BankAccount"] = relationship(
        "BankAccount", back_populates="expenses"
    )
    category: Mapped["Category"] = relationship(
        "Category", back_populates="expenses"
    )

    # --- Performance Index + Amount Validation (mirrors master_schemas.sql) ---
    __table_args__ = (
        CheckConstraint("Amount > 0", name="chk_expense_amount_positive"),
        Index("idx_expense_user_cat_date", "UserID", "CategoryID", "TransactionDate"),
    )

    def __repr__(self) -> str:
        return (
            f"<Expense id={self.TransactionID} "
            f"amount={self.Amount} date={self.TransactionDate}>"
        )


# =============================================================================
# Model 9: MonthlyClosure
# =============================================================================

class MonthlyClosure(Base):
    """
    ORM model for the `MonthlyClosures` table.

    Stores a historical snapshot of a BankAccount's closing balance at the
    end of a given calendar month. Records are created by calling the
    `CalculateMonthlyClosure` stored procedure — do not insert into this
    table directly from the application layer.

    The `UniqueConstraint` on `(AccountID, ClosurePeriod)` ensures only one
    snapshot per account per month ever exists. The SQL procedure uses
    ON DUPLICATE KEY UPDATE to maintain idempotency.

    Relationships:
        bank_account → BankAccount (many-to-one)
    """

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

    # --- Relationships ---
    bank_account: Mapped["BankAccount"] = relationship(
        "BankAccount", back_populates="monthly_closures"
    )

    # --- Unique Constraint (mirrors master_schemas.sql) ---
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
