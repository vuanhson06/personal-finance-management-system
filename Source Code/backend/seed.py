import random
import sys
from faker import Faker
from sqlalchemy import select, text
from datetime import date, timedelta, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    BankAccount,
    Budget,
    Category,
    Expense,
    Income,
    MarketWatch,
    MonthlyClosure,
    TransactionType,
    User,
    UserRole,
    AdminLog,
)

RANDOM_SEED: int = 42
faker: Faker = Faker("en_US")
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

NUM_USERS: int = 10
HISTORY_MONTHS: int = 24
INCOME_PER_MONTH: int = 5
EXPENSES_PER_MONTH: int = 12
ASSETS_PER_USER: int = 5

ASSET_POOL: list[dict] = [
    {"symbol": "AAPL",    "type": "Stock"},
    {"symbol": "GOOGL",   "type": "Stock"},
    {"symbol": "MSFT",    "type": "Stock"},
    {"symbol": "TSLA",    "type": "Stock"},
    {"symbol": "AMZN",    "type": "Stock"},
    {"symbol": "NVDA",    "type": "Stock"},
    {"symbol": "BTC-USD", "type": "Crypto"},
    {"symbol": "ETH-USD", "type": "Crypto"},
    {"symbol": "BNB-USD", "type": "Crypto"},
    {"symbol": "SOL-USD", "type": "Crypto"},
    {"symbol": "GC=F",    "type": "Gold"},
    {"symbol": "SI=F",    "type": "Silver"},
]

ACCOUNT_TYPES: list[tuple[str, Decimal, Decimal]] = [
    ("Checking Account", Decimal("1000.00"), Decimal("8000.00")),
    ("Savings Account",  Decimal("500.00"),  Decimal("15000.00")),
]

INCOME_CATEGORY_NAMES: list[str] = ["Salary", "Bonus", "Investment"]

EXPENSE_CATEGORY_NAMES: list[str] = [
    "Housing", "Food & Dining", "Transportation",
    "Health", "Entertainment", "Shopping", "Utilities",
]

INCOME_DESCRIPTIONS: dict[str, list[str]] = {
    "Salary":     ["Monthly salary deposit", "Paycheck", "Direct deposit - Employer",
                   "Bi-weekly salary", "Salary transfer"],
    "Bonus":      ["Q1 performance bonus", "Year-end bonus", "Project completion bonus",
                   "Referral bonus", "Holiday bonus"],
    "Investment": ["Dividend payment", "Stock sale proceeds", "ETF distribution",
                   "Crypto staking reward", "Bond coupon payment"],
}

EXPENSE_DESCRIPTIONS: dict[str, list[str]] = {
    "Housing":        ["Monthly rent payment", "Mortgage installment", "Utility deposit",
                       "Rent - April", "HOA fee"],
    "Food & Dining":  ["Grocery shopping", "Restaurant dinner", "Coffee shop",
                       "Food delivery order", "Lunch at work"],
    "Transportation": ["Gas fill-up", "Monthly bus pass", "Uber ride",
                       "Car insurance premium", "Parking fee"],
    "Health":         ["Pharmacy purchase", "Doctor consultation", "Gym membership",
                       "Health insurance premium", "Dental checkup"],
    "Entertainment":  ["Netflix subscription", "Movie tickets", "Spotify subscription",
                       "Concert tickets", "Video game purchase"],
    "Shopping":       ["Clothing purchase", "Amazon order", "Electronics store",
                       "Online shopping", "Department store"],
    "Utilities":      ["Electricity bill", "Water bill", "Internet subscription",
                       "Phone bill", "Gas bill"],
    "Education":      ["Online course fee", "Textbook purchase", "Tuition fee",
                       "Workshop registration", "e-Learning subscription"],
    "Debt":           ["Credit card payment", "Student loan installment",
                       "Personal loan EMI", "Car loan payment", "Debt repayment"],
    "Savings":        ["Savings transfer", "Emergency fund top-up",
                       "Fixed deposit", "Retirement contribution", "Investment top-up"],
}

def _random_date_in_month(year: int, month: int) -> date:
    import calendar
    _, last_day = calendar.monthrange(year, month)
    day = random.randint(1, last_day)
    return date(year, month, day)


def _random_timestamp_for_date(d: date) -> datetime:
    return datetime.combine(
        d,
        datetime.min.time().replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
    )


def _get_last_n_months(n: int) -> list[tuple[int, int]]:
    today: date = date.today()
    months: list[tuple[int, int]] = []
    for i in range(n - 1, -1, -1):
        month: int = today.month - i
        year: int = today.year
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))
    return months


def _random_decimal(low: float, high: float, places: int = 2) -> Decimal:
    raw: float = random.uniform(low, high)
    quantize_str: str = "0." + "0" * places
    return Decimal(str(raw)).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def clear_data(db: Session) -> None:
    print("  Clearing existing seeded data...")
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    
    tables = [
        "AdminLogs", "MonthlyClosures", "Income", 
        "Expenses", "Budgets", "MarketWatch", "BankAccounts", 
        "Categories", "Users"
    ]
    
    for table in tables:
        db.execute(text(f"TRUNCATE TABLE {table};"))
        
    db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    db.commit()
    print("  Cleared successfully.")

def seed_users(db: Session) -> list[User]:
    users_data: list[dict] = [
        {
            "UserName": "Admin System",
            "Email":    "admin@financeapp.com",
            "Phone":    "+1-800-000-0001",
            "Password": "AdminSecure@2026",
            "Role":     UserRole.Admin,
        },
        {
            "UserName": "Alice Johnson",
            "Email":    "alice.johnson@email.com",
            "Phone":    "+1-555-010-1001",
            "Password": "AlicePass@2026",
            "Role":     UserRole.User,
        },
        {
            "UserName": "Bob Martinez",
            "Email":    "bob.martinez@email.com",
            "Phone":    "+1-555-020-2002",
            "Password": "BobPass@2026",
            "Role":     UserRole.User,
        },
        {
            "UserName": "Carol White",
            "Email":    "carol.white@email.com",
            "Phone":    "+1-555-030-3003",
            "Password": "CarolPass@2026",
            "Role":     UserRole.User,
        },
        {
            "UserName": "David Chen",
            "Email":    "david.chen@email.com",
            "Phone":    "+1-555-040-4004",
            "Password": "DavidPass@2026",
            "Role":     UserRole.User,
            "IsActive": False, #locked for testing
        }
    ]

    while len(users_data) < NUM_USERS:
        name = faker.name()
        first_name = name.split()[0].lower()
        users_data.append({
            "UserName": name,
            "Email":    f"{first_name}.{faker.last_name().lower()}@{faker.free_email_domain()}",
            "Phone":    faker.phone_number(),
            "Password": f"{first_name.capitalize()}Pass@2026",
            "Role":     UserRole.User,
        })

    users: list[User] = []
    for data in users_data:
        user = User(
            UserName=data["UserName"],
            Email=data["Email"],
            PhoneNumber=data["Phone"],
            Role=data["Role"],
            IsActive=data.get("IsActive", True),
        )
        user.set_password(data["Password"])  # bcrypt hash
        db.add(user)
        db.commit()
        db.refresh(user)
        users.append(user)

    print(f"  {len(users)} users seeded (1 Admin + {len(users)-1} Users).")
    return users


def seed_bank_accounts(db: Session, users: list[User]) -> list[BankAccount]:
    print("  Seeding bank accounts...")
    accounts: list[BankAccount] = []
    for user_idx, user in enumerate(users, start=1):
        for acc_idx, (account_name, low, high) in enumerate(ACCOUNT_TYPES, start=1):
            suffix: str = str(random.randint(100_000_000, 999_999_999))
            account_number: str = f"190{user_idx}{acc_idx}{suffix}"
            account = BankAccount(
                UserID=user.UserID,
                AccountName=account_name,
                AccountNumber=account_number,
                Balance=_random_decimal(float(low), float(high)),
            )
            db.add(account)
            accounts.append(account)
    db.commit()
    for account in accounts:
        db.refresh(account)
    print(f"  {len(accounts)} bank accounts seeded.")
    return accounts

def seed_market_watches(db: Session, users: list[User]) -> None:
    print("  Seeding market watchlists...")
    count: int = 0
    for user in users:
        chosen_assets: list[dict] = random.sample(ASSET_POOL, k=min(ASSETS_PER_USER, len(ASSET_POOL)))
        for asset in chosen_assets:
            db.add(MarketWatch(
                UserID=user.UserID,
                AssetSymbol=asset["symbol"],
                AssetType=asset["type"],
            ))
            count += 1
    db.commit()
    print(f"  {count} market watch entries seeded.")

def seed_budgets(db: Session, users: list[User]) -> None:
    current_period: str = date.today().strftime("%Y-%m")
    count: int = 0

    for user in users:
        expense_cats: list[Category] = db.execute(
            select(Category).where(
                Category.UserID == user.UserID,
                Category.Type == TransactionType.Expense,
                Category.CategoryName.in_(EXPENSE_CATEGORY_NAMES),
            )
        ).scalars().all()

        selected: list[Category] = random.sample(
            expense_cats, k=min(6, len(expense_cats))
        )
        for cat in selected:
            db.add(Budget(
                UserID=user.UserID,
                CategoryID=cat.CategoryID,
                LimitAmount=_random_decimal(500, 2500),
                Period=current_period,
            ))
            count += 1

    db.commit()
    print(f"  {count} budgets seeded for period '{current_period}'.")

def seed_income(db: Session, users: list[User], accounts: list[BankAccount],) -> int:
    print(f"  Seeding income transactions ({HISTORY_MONTHS} months)...")
    months: list[tuple[int, int]] = _get_last_n_months(HISTORY_MONTHS)
    total: int = 0

    for user in users:
        income_cats: list[Category] = db.execute(
            select(Category).where(
                Category.UserID == user.UserID,
                Category.Type == TransactionType.Income,
            )
        ).scalars().all()

        if not income_cats:
            continue

        user_accounts: list[BankAccount] = [
            a for a in accounts if a.UserID == user.UserID
        ]
        if not user_accounts:
            continue

        for year, month in months:
            count = random.randint(INCOME_PER_MONTH - 1, INCOME_PER_MONTH + 2)
            for _ in range(count):
                cat: Category = random.choice(income_cats)
                account: BankAccount = random.choice(user_accounts)
                descriptions: list[str] = INCOME_DESCRIPTIONS.get(
                    cat.CategoryName, ["Income deposit"]
                )
                txn_date = _random_date_in_month(year, month)
                db.add(Income(
                    UserID=user.UserID,
                    AccountID=account.AccountID,
                    CategoryID=cat.CategoryID,
                    Amount=_random_decimal(1500, 8000),
                    TransactionDate=txn_date,
                    CreatedAt=_random_timestamp_for_date(txn_date),
                    Description=random.choice(descriptions),
                ))
                total += 1

    db.commit()
    print(f"  {total} income records seeded.")
    return total

def seed_expenses(db: Session, users: list[User], accounts: list[BankAccount],) -> int:
    print(f"  Seeding expense transactions ({HISTORY_MONTHS} months)...")
    months: list[tuple[int, int]] = _get_last_n_months(HISTORY_MONTHS)
    total: int = 0

    for user in users:
        expense_cats: list[Category] = db.execute(
            select(Category).where(
                Category.UserID == user.UserID,
                Category.Type == TransactionType.Expense,
                Category.CategoryName.in_(EXPENSE_CATEGORY_NAMES),
            )
        ).scalars().all()

        if not expense_cats:
            continue

        user_expense_cats: list[Category] = random.sample(
            expense_cats, k=min(4, len(expense_cats))
        )

        user_accounts: list[BankAccount] = [
            a for a in accounts if a.UserID == user.UserID
        ]
        if not user_accounts:
            continue

        for year, month in months:
            count = random.randint(EXPENSES_PER_MONTH - 3, EXPENSES_PER_MONTH + 5)
            for _ in range(count):
                cat = random.choice(user_expense_cats)
                account: BankAccount = random.choice(user_accounts)
                descriptions: list[str] = EXPENSE_DESCRIPTIONS.get(
                    cat.CategoryName, ["Expense payment"]
                )
                
                txn_date = _random_date_in_month(year, month)
                db.add(Expense(
                    UserID=user.UserID,
                    AccountID=account.AccountID,
                    CategoryID=cat.CategoryID,
                    Amount=_random_decimal(20, 1200),
                    TransactionDate=txn_date,
                    CreatedAt=_random_timestamp_for_date(txn_date),
                    Description=random.choice(descriptions),
                ))
                total += 1

    db.commit()
    print(f"  expense records seeded.")
    return total

def seed_admin_logs(db: Session, users: list[User]):
    admin = next(u for u in users if u.Role == UserRole.Admin)
    other_users = [u for u in users if u.Role == UserRole.User]
    
    actions = [
        "Updated System Category", "Viewed Global Analytics", 
        "Exported Database Backup", "Modified Interest Rates",
        "Reviewed Security Audit", "Updated Webhook Endpoint"
    ]
    
    for _ in range(20):
        target = random.choice(other_users)
        action = random.choice(actions)
        db.add(AdminLog(
            AdminID=admin.UserID,
            Action=f"{action} (Target: {target.Email})",
            TargetUserID=target.UserID,
            Timestamp=datetime.now() - timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))
        ))
    db.commit()

    db.commit()

def run_seed() -> None:
    db: Session = SessionLocal()
    try:
        print("  PERSONAL FINANCE - DATA SEEDER")

        clear_data(db)

        users: list[User] = seed_users(db)
        accounts: list[BankAccount] = seed_bank_accounts(db, users)
        seed_market_watches(db, users)
        seed_budgets(db, users)
        income_count: int = seed_income(db, users, accounts)
        expense_count: int = seed_expenses(db, users, accounts)
        
        seed_admin_logs(db, users)
        
        total_categories: int = db.query(Category).count()
        total_budgets: int = db.query(Budget).count()
        total_watches: int = db.query(MarketWatch).count()

        print("\n" + "=" * 60)
        print("  SEEDING COMPLETE - SUMMARY")
        print("=" * 60)
        print(f"  {'Entity':<25} {'Count':>8}")
        print(f"  {'-'*25} {'-'*8}")
        print(f"  {'Users':<25} {len(users):>8}")
        print(f"  {'BankAccounts':<25} {len(accounts):>8}")
        print(f"  {'Categories (auto)':<25} {total_categories:>8}")
        print(f"  {'Budgets':<25} {total_budgets:>8}")
        print(f"  {'MarketWatch Entries':<25} {total_watches:>8}")
        print(f"  {'Income Transactions':<25} {income_count:>8}")
        print(f"  {'Expense Transactions':<25} {expense_count:>8}")
        print(f"  {'-'*25} {'-'*8}")
        print(f"  {'TOTAL TRANSACTIONS':<25} {income_count + expense_count:>8}")
        print("=" * 60 + "\n")
        print("Dataset ready for platform demonstration.")

    except (IntegrityError, OperationalError) as e:
        db.rollback()
        print(f"\n  DATABASE ERROR — Seed rolled back.")
        print(f"     Reason: {type(e).__name__}")
        print(f"     Detail: {str(e.orig) if hasattr(e, 'orig') else str(e)}")
        sys.exit(1)

    except Exception as e:
        db.rollback()
        print(f"\n  UNEXPECTED ERROR - Seed rolled back.")
        print(f"Detail: {e}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
