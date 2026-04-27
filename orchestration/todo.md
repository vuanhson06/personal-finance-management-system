# Execution Plan

## Part 1: SQL Database
### Step 1: User & Security Schema

**Goal**: Establish the foundational database schema for user authentication and security constraints, adhering to `/directives/db_rules.md`.

**Proposed Steps for Execution:**
- [x] **Step 1.1**: Create the directory `/execution/database/` to hold raw SQL definitions.
- [x] **Step 1.2**: Create the file `/execution/database/01_user_schema.sql`.
- [x] **Step 1.3**: Implement the `Users` table schema:
  - `UserID` (INT AUTO_INCREMENT PRIMARY KEY).
  - `UserName` (VARCHAR(100) NOT NULL).
  - `Email` (VARCHAR(255) UNIQUE NOT NULL).
  - `PasswordHash` (VARCHAR(255) NOT NULL).
  - `CreatedAt` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP).
  - `UpdatedAt` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP).
- [x] **Step 1.4**: Define basic column constraints (e.g., uniqueness on Email, NOT NULL on essential fields) to enforce data integrity at the database level.

This separates the pure database definition from the Python logic (which will be handled later using SQLAlchemy ORM).

### Step 2: Financial Core Implementation

**Goal**: Define the core financial tables (`BankAccounts`, `Income`, `Expenses`, `Categories`, `Budgets`, `MarketWatch`) and their strict relationships, ensuring everything links back to `Users.UserID`.

**Proposed Steps for Execution:**
- [x] **Step 2.1**: Create/update `/execution/database/02_financial_core.sql`.
- [x] **Step 2.2**: Implement the `BankAccounts` table:
  - `AccountID` (PK), `UserID` (FK to `Users`), `AccountName`, `Balance`, timestamps.
- [x] **Step 2.3**: Implement `Categories`, `Budgets`, and `MarketWatch` tables:
  - `Categories`: `CategoryID` (PK), `UserID` (FK to `Users`), `CategoryName`, `Type` (ENUM 'Income'/'Expense').
  - `Budgets`: `BudgetID` (PK), `UserID` (FK to `Users`), `CategoryID` (FK to `Categories`), `LimitAmount`, `Period`.
  - `MarketWatch`: `WatchID` (PK), `UserID` (FK to `Users`), `AssetSymbol`, `AssetType`.
- [x] **Step 2.4**: Implement the `Income` and `Expenses` transaction tables:
  - `TransactionID` (PK).
  - `UserID` (FK to `Users` for isolation).
  - `AccountID` (FK to `BankAccounts` to track funds).
  - `CategoryID` (FK to `Categories`).
  - `Amount` (> 0), `TransactionDate`, `Description`, timestamps.
- [x] **Step 2.5**: Write SQL insertion to seed `Categories` with mandatory tags: `Salary`, `Bonus`, `Investment`, `Housing`, `Utilities`, `Food & Dining`, `Transportation`, `Health`, `Education`, `Entertainment`, `Shopping`, `Debt`, `Savings`.

### Step 3: Advanced Automation Logic

**Goal**: Push business constraints directly into the SQL layer to guarantee that our `BankAccounts` balances remain 100% accurate without relying solely on backend application logic.

**Proposed Steps for Execution:**
- [x] **Step 3.1**: Create `/execution/database/03_advanced_automation.sql`.
- [x] **Step 3.2**: Implement `Income` Triggers:
  - `AFTER INSERT`: Increase `BankAccounts.Balance` by `NEW.Amount`.
  - `AFTER UPDATE`: Adjust balance by `NEW.Amount - OLD.Amount`.
  - `AFTER DELETE`: Decrease `BankAccounts.Balance` by `OLD.Amount`.
- [x] **Step 3.3**: Implement `Expenses` Triggers:
  - `AFTER INSERT`: Decrease `BankAccounts.Balance` by `NEW.Amount`.
  - `AFTER UPDATE`: Adjust balance by `OLD.Amount - NEW.Amount`.
  - `AFTER DELETE`: Increase `BankAccounts.Balance` by `OLD.Amount`.
- [x] **Step 3.4**: Create the `MonthlyClosures` snapshot log table (`ClosureID`, `AccountID`, `ClosurePeriod`, `ClosingBalance`).
- [x] **Step 3.5**: Write the `CalculateMonthlyClosure` Stored Procedure, which iterates through a user's accounts and locks in their end-of-month balance snapshot into the new closures table.

### Step 4: Reporting & Analytics Layer

**Goal**: Offload complex analytical aggregations to the database engine using pre-compiled SQL Views and User-Defined Functions (UDFs). This guarantees ultra-fast read operations for the frontend dashboards.

**Proposed Steps for Execution:**
- [x] **Step 4.1**: Create `/execution/database/04_analytics_layer.sql`.
- [x] **Step 4.2**: Implement View `vw_CategoryWiseSpending`: Connects the `Expenses` table to `Categories` to aggregate total spending grouped by `UserID`, `CategoryID`, and `Year/Month`.
- [x] **Step 4.3**: Implement View `vw_MonthlySummaries`: Aggregates the global cash flow (Total Income minus Total Expenses) grouped synchronously by `UserID` and `Year/Month`.
- [x] **Step 4.4**: Implement UDF `GetTotalSavings(p_UserID)`: A function that scans all `BankAccounts` for that user and returns the current sum of all balances.
- [x] **Step 4.5**: Implement UDF `GetBudgetStatus(p_UserID, p_CategoryID, p_Period)`: Calculates the utilized budget directly by summing the total `Expenses` for that period, comparing it against the `Budgets.LimitAmount`, and returning the exact remaining allowance.

### Step 5: Performance & Data Integrity

**Goal**: Apply structural optimizations to ensure fast querying on large datasets and define data backup processes alongside strict data-isolation application rules.

**Proposed Steps for Execution:**
- [x] **Step 5.1**: Create `/execution/database/05_performance_indexes.sql`.
- [x] **Step 5.2**: Add `INDEX` structures to `Income(UserID, TransactionDate)` and `Expenses(UserID, CategoryID, TransactionDate)` to radically optimize the performance of the Views and UDFs we built in Step 4.
- [x] **Step 5.3**: Create database backup and restore utility scripts (`/execution/database/db_backup.bat` and `db_restore.bat` or `.sh`).
- [x] **Step 5.4**: Create `/directives/backend_logic_rules.md` outlining the overarching Application-level strict isolation requirement (i.e., **All** SQLAlchemy queries must imperatively append `WHERE UserID = current_user`).

---

## Part 2: Backend (The Brain)

### Step 1: Connectivity & Security Setup

**Goal**: Establish the foundational Python backend infrastructure. This includes a secure, production-grade SQLAlchemy engine with connection pooling and a `.env`-based configuration system for all sensitive credentials, as required by `directives/backend_logic_rules.md`.

**Status: ✅ COMPLETE**

**Files created:**

| File | Purpose |
|---|---|
| `execution/backend/__init__.py` | Marks the backend directory as a Python package. |
| `execution/backend/.env.example` | Template listing all required environment variables (no real secrets). |
| `execution/backend/config.py` | Loads environment variables from `.env` using `python-dotenv` and exposes a typed `Settings` dataclass. |
| `execution/backend/database.py` | Creates and exposes the SQLAlchemy `Engine` (with pooling), `SessionLocal` factory, `Base`, and `get_db()`. |

**Completed Steps:**

- [x] **Step 1.1**: Created the `execution/backend/` directory and an `__init__.py`.
- [x] **Step 1.2**: Created `execution/backend/.env.example` with `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
- [x] **Step 1.3**: Created `execution/backend/config.py` with a typed `Settings` dataclass and `database_url` property.
- [x] **Step 1.4**: Created `execution/backend/database.py` with `create_engine()` (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`), `OperationalError` handling, `SessionLocal`, `Base`, and `get_db()` generator.

---

### Step 2: ORM Data Modeling

**Goal**: Define Python SQLAlchemy ORM classes that perfectly mirror all 9 tables in `master_schemas.sql`. Integrate `bcrypt` password hashing directly into the `User` model and implement role-verification helper methods, as required by `directives/backend_logic_rules.md` (Section 1 & 3) and `directives/db_rules.md` (Section 4).

**Status: ✅ COMPLETE**

**Files created:**

| File | Purpose |
|---|---|
| `execution/backend/models.py` | All 9 SQLAlchemy ORM model classes with full column definitions, relationships, `bcrypt` integration, and role-check methods. |

**Completed Steps:**

- [x] **Step 2.1**: Defined `UserRole` and `TransactionType` Python Enums for type-safe role and category-type handling.
- [x] **Step 2.2**: Implemented `User` model with `set_password()`, `verify_password()`, `is_admin()` methods using `bcrypt`, and full relationship declarations.
- [x] **Step 2.3**: Implemented `BankAccount` model with FK → `User`, back-refs to `Income`, `Expenses`, and `MonthlyClosures`.
- [x] **Step 2.4**: Implemented `SystemCategory` model — no `UserID`, Admin-managed global template table.
- [x] **Step 2.5**: Implemented `Category` model with `UserID` NOT NULL and back-refs to `Budgets`, `Income`, `Expenses`.
- [x] **Step 2.6**: Implemented `Budget` model with FK → `User` + `Category`, `Period` as `VARCHAR(7)`, and composite performance index.
- [x] **Step 2.7**: Implemented `MarketWatch` model with FK → `User`.
- [x] **Step 2.8**: Implemented `Income` model with FK → `User` + `BankAccount` + `Category`, `CheckConstraint(Amount > 0)`, and composite index.
- [x] **Step 2.9**: Implemented `Expense` model with FK → `User` + `BankAccount` + `Category`, `CheckConstraint(Amount > 0)`, and composite index.
- [x] **Step 2.10**: Implemented `MonthlyClosure` model with FK → `BankAccount` and `UniqueConstraint` on `(AccountID, ClosurePeriod)`.

---

### Step 3: Data Simulation (100 Records)

**Goal**: Build a `seed.py` script using `Faker` that generates realistic, statistically coherent financial data across the last 12 months. Data must satisfy all FK constraints in the schema and must include valid synthetic phone numbers for user profiles, as required by `PROJECT_PLAN.md` (Part 2, Step 3).

**Status: ✅ COMPLETE**

**Files created:**

| File | Purpose |
|---|---|
| `execution/backend/seed.py` | Standalone seeding script — generates and inserts all user, account, and transaction data via ORM. Safe to re-run (idempotent). |

**Completed Steps:**

- [x] **Step 3.1**: Configured `Faker(locale='en_US')` with `RANDOM_SEED = 42` for full reproducibility.
- [x] **Step 3.2**: Implemented `clear_data(db)` — deletes in FK-safe reverse order: `MonthlyClosures → Income → Expenses → Budgets → MarketWatch → BankAccounts → Categories → Users`.
- [x] **Step 3.3**: Implemented `seed_users(db)` — 1 Admin + 4 Users, each committed individually so the `After_User_Insert` trigger fires and auto-populates their `Categories`.
- [x] **Step 3.4**: Implemented `seed_bank_accounts(db, users)` — 2 accounts per user (Checking + Savings) with randomized opening balances.
- [x] **Step 3.5**: Implemented `seed_market_watches(db, users)` — 3 assets per user drawn from a 12-symbol pool of Stocks, Crypto, and Commodities.
- [x] **Step 3.6**: Implemented `seed_budgets(db, users)` — up to 4 Expense-type budgets per user for the current `YYYY-MM` period, fetched from DB post-trigger.
- [x] **Step 3.7**: Implemented `seed_income(db, users, accounts)` — 3 Income transactions/user/month × 12 months, with realistic Descriptions per category.
- [x] **Step 3.8**: Implemented `seed_expenses(db, users, accounts)` — 4 Expense transactions/user/category/month × 12 months, with realistic Descriptions per category.
- [x] **Step 3.9**: Implemented `run_seed()` orchestrator with `try-except IntegrityError/OperationalError` and `db.rollback()` on failure.
- [x] **Step 3.10**: Printed clean summary table on completion showing all entity counts.

---

### Step 4: Market Data Integration

**Goal**: Build a self-contained `market_service.py` module that fetches live financial asset prices (Stocks, Crypto, Gold) using `yfinance` and implements an in-memory TTL cache to prevent redundant API calls and avoid rate-limiting, as required by `PROJECT_PLAN.md` (Part 2, Step 4).

**Status: ✅ COMPLETE**

**Files created:**

| File | Purpose |
|---|---|
| `execution/backend/market_service.py` | Fetches live prices via `yfinance`, applies TTL caching, returns clean typed data dicts for the frontend dashboard. |

**Completed Steps:**

- [x] **Step 4.1**: Defined `CacheEntry` dataclass with `symbol`, `price`, `currency`, `exchange`, `fetched_at` fields and a `to_dict()` serializer. Set `CACHE_TTL_SECONDS = 300`.
- [x] **Step 4.2**: Implemented module-level `_cache: dict[str, CacheEntry]` — pure in-memory store, no external dependency.
- [x] **Step 4.3**: Implemented `_is_cache_valid(entry)` — compares `fetched_at` age against `CACHE_TTL_SECONDS` using `timedelta`.
- [x] **Step 4.4**: Implemented `fetch_price(symbol)` — cache-first → `yfinance.Ticker.fast_info` fallback → safe `try-except` → returns `None` on any failure.
- [x] **Step 4.5**: Implemented `fetch_watchlist_prices(symbols)` — batch fetch with per-symbol failure isolation; skips failed symbols without blocking the rest.
- [x] **Step 4.6**: Implemented `get_user_watchlist_data(user_id, db)` — DB-scoped by `UserID` (Golden Rule enforced), merges live price data with DB `AssetType` and `WatchID` metadata.
- [x] **Step 4.7**: Implemented `clear_cache(symbol?)` — single-symbol or full cache invalidation utility.

---

### Step 5: Logic Engine Development

**Goal**: Build the core business logic layer as a collection of focused service modules. Each module handles one domain (auth, transactions, budgets, bank sync) and acts as the bridge between the ORM models and the future frontend. Every function must enforce data ownership (`UserID` scoping), apply pre-ORM validation, and return clean result dicts — never raw exceptions. Directed by `PROJECT_PLAN.md` (Part 2, Step 5) and `directives/backend_logic_rules.md`.

**Status: ✅ COMPLETE**

**Files created:**

| File | Purpose |
|---|---|
| `execution/backend/auth_service.py` | User registration, login, and user retrieval with bcrypt and format validation |
| `execution/backend/transaction_service.py` | Full Income/Expense CRUD with pre-ORM validation and ownership guards |
| `execution/backend/budget_service.py` | Budget creation, retrieval, and status via `GetBudgetStatus` SQL UDF |
| `execution/backend/bank_sync_service.py` | Account retrieval, bank sync simulation, monthly closure SP call, total savings UDF |

**Completed Steps:**

- [x] **Step 5.1 — `auth_service.py`**: `register_user()` (email/phone format + uniqueness validation, bcrypt hash, trigger-aware commit) · `login_user()` (constant-time bcrypt verify, generic error to prevent enumeration) · `get_user_by_id()`.
- [x] **Step 5.2 — `transaction_service.py`**: `get_income_list()` / `get_expense_list()` (paginated, UserID-scoped) · `add_income()` / `add_expense()` (full validation chain: amount > 0, date, account ownership, category type) · `update_income()` / `update_expense()` (ownership check + partial field update) · `delete_income()` / `delete_expense()` (ownership check before delete; triggers handle balance restoration).
- [x] **Step 5.3 — `budget_service.py`**: `create_budget()` (amount > 0, YYYY-MM period, Expense-type category guard) · `get_budgets()` (UserID-scoped) · `get_budget_status()` (calls `GetBudgetStatus` UDF, returns remaining + 'OK'/'WARNING'/'OVER_BUDGET' status string).
- [x] **Step 5.4 — `bank_sync_service.py`**: `get_accounts()` (UserID-scoped) · `get_total_savings()` (calls `GetTotalSavings` UDF) · `simulate_bank_sync()` (1–3 random transactions today, 30% income / 70% expense ratio, delegates through `transaction_service` so triggers fire) · `run_monthly_closure()` (calls `CALL CalculateMonthlyClosure(:uid, :period)` via `db.execute(text(...))`).
