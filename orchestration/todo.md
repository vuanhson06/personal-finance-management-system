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

---

### Step 5 — Upgrade: Webhook Simulator (Bank Sync)

**Goal**: Upgrade the bank sync mechanism from random data simulation to a real HTTP Webhook endpoint. The server must receive structured JSON payloads from an external bank system, enforce API key security, apply idempotency checks (Anti-Double Spending), auto-resolve the target account and user from the payload, and commit the transaction through `transaction_service` so all SQL triggers fire. As defined in the updated `PROJECT_PLAN.md` (Part 2, Step 5) and `directives/backend_logic_rules.md` (Section 4).

**Status: ✅ COMPLETE**

**Files created / modified:**

| Action | File | Change |
|---|---|---|
| MODIFIED | `execution/backend/models.py` | `ExternalTransID` added to `Income` + `Expense` models |
| MODIFIED | `execution/database/master_schemas.sql` | `ExternalTransID VARCHAR(255) NULL` + `UNIQUE KEY` added to both tables |
| MODIFIED | `execution/backend/.env` | `WEBHOOK_API_KEY` variable added |
| MODIFIED | `execution/backend/config.py` | `webhook_api_key` field added to `Settings` dataclass |
| MODIFIED | `execution/backend/bank_sync_service.py` | `process_webhook_payload()` added; `simulate_bank_sync()` removed |
| MODIFIED | `execution/backend/transaction_service.py` | `external_trans_id` optional param added to `add_income()` + `add_expense()` |
| CREATED | `execution/backend/webhook_server.py` | Flask server with `POST /webhook/transaction` + `GET /health` |

**Completed Steps:**

- [x] **Step W.1**: Added `ExternalTransID VARCHAR(255) NULL` + `UNIQUE KEY idx_income_ext_trans_id` to `Income` table and `idx_expense_ext_trans_id` to `Expenses` table in `master_schemas.sql`. Mirrored as `Mapped[Optional[str]]` (`String(255)`, `unique=True`, `index=True`) on both ORM models in `models.py`.
- [x] **Step W.2**: Added `WEBHOOK_API_KEY` to `.env`. Added `webhook_api_key: str` field to `Settings` dataclass in `config.py` loaded via `_require_env("WEBHOOK_API_KEY")`.
- [x] **Step W.3**: Implemented `process_webhook_payload(payload, db)` in `bank_sync_service.py` — full 5-step flow: schema validation → idempotency check (Income + Expense ExternalTransID) → account resolution (`bank_sub_acc_id` → BankAccount) → UserID taken from account (never payload) → category auto-select → `add_income()`/`add_expense()` delegation with `external_trans_id` set.
- [x] **Step W.4**: Created `webhook_server.py` — Flask app with `POST /webhook/transaction` (X-API-KEY auth, JSON parse, service delegation, HTTP code mapping, outer try-except guard) and `GET /health` probe. Runs on `0.0.0.0:5050`.
- [x] **Step W.5**: Added `external_trans_id: Optional[str] = None` to `add_income()` and `add_expense()` in `transaction_service.py`. Backward-compatible — existing callers unaffected.


**Files to be created / modified:**

| Action | File | Change |
|---|---|---|
| MODIFY | `execution/backend/models.py` | Add `ExternalTransID` column to `Income` and `Expense` models |
| MODIFY | `execution/database/master_schemas.sql` | Add `ExternalTransID` column + unique index to `Income` and `Expenses` tables |
| MODIFY | `execution/backend/.env.example` | Add `WEBHOOK_API_KEY` variable |
| MODIFY | `execution/backend/config.py` | Add `webhook_api_key` field to `Settings` dataclass |
| MODIFY | `execution/backend/bank_sync_service.py` | Replace `simulate_bank_sync()` with `process_webhook_payload()` |
| CREATE | `execution/backend/webhook_server.py` | Flask server with `POST /webhook/transaction` endpoint |

**Proposed Steps for Execution:**

- [ ] **Step W.1 — Schema update (`master_schemas.sql` + `models.py`)**:
  - Add `ExternalTransID VARCHAR(255) NULL UNIQUE` column to both `Income` and `Expenses` tables in `master_schemas.sql`.
  - Add a named unique index `idx_income_ext_trans_id` on `Income(ExternalTransID)` and `idx_expense_ext_trans_id` on `Expenses(ExternalTransID)`.
  - Mirror these changes in `models.py`: add `ExternalTransID: Mapped[Optional[str]]` with `String(255)`, `unique=True`, `index=True`, `nullable=True` to both `Income` and `Expense` ORM models.

- [ ] **Step W.2 — Config update (`config.py` + `.env.example`)**:
  - Add `WEBHOOK_API_KEY` to `execution/backend/.env.example` (with a placeholder value).
  - Add `webhook_api_key: str` field to the `Settings` dataclass in `config.py`, loaded via `_require_env("WEBHOOK_API_KEY")`.

- [ ] **Step W.3 — Service logic (`bank_sync_service.py`)**:
  - Implement `process_webhook_payload(payload: dict, db: Session) -> dict`:
    - **Schema Validation:** Verify all required fields (`bank_transaction_id`, `amount`, `bank_sub_acc_id`, `transaction_date`) are present and correctly typed. Return a structured error dict on failure.
    - **Idempotency Check:** Query `Income.ExternalTransID` and `Expenses.ExternalTransID` for `bank_transaction_id`. If found in either, return `{"status": "ALREADY_PROCESSED", "code": 200}` immediately.
    - **Account Resolution:** Look up `bank_sub_acc_id` in `BankAccounts`. If not found, return `{"status": "ACCOUNT_NOT_FOUND", "code": 404}`.
    - **UserID Resolution:** Take `UserID` from the matched `BankAccount` record — do NOT trust any `user_id` from the payload.
    - **Category Resolution:** Auto-select the first matching category by type (Income or Expense) owned by the resolved user, to allow uncategorized webhooks to be classified automatically.
    - **Transaction Direction:** Positive `amount` → calls `add_income()` with `ExternalTransID` set. Negative `amount` → calls `add_expense()` with absolute value and `ExternalTransID` set.
    - Return `{"status": "PROCESSED", "code": 200, "transaction_id": <id>}` on success.

- [ ] **Step W.4 — Webhook Server (`webhook_server.py`)**:
  - Create a Flask application with a single route: `POST /webhook/transaction`.
  - **Authentication middleware:** Extract `X-API-KEY` header. Compare against `settings.webhook_api_key`. Return `{"error": "Unauthorized"}` with HTTP `401` if invalid.
  - **Request parsing:** Parse the request body as JSON. Return `{"error": "Invalid JSON"}` with HTTP `400` if malformed.
  - **Delegate to service:** Call `process_webhook_payload(payload, db)` inside a `get_db()` context. Map the returned `code` to the correct HTTP status.
  - **Error guard:** Wrap the entire handler in `try-except Exception` to guarantee no stack traces ever leak in the response body.
  - **Server entry point:** Run with `app.run(host="0.0.0.0", port=5050, debug=False)` under `if __name__ == "__main__"`.

- [ ] **Step W.5 — Update `transaction_service.py`**:
  - Add optional `external_trans_id: Optional[str] = None` parameter to both `add_income()` and `add_expense()`.
  - Assign `income.ExternalTransID = external_trans_id` / `expense.ExternalTransID = external_trans_id` before committing.
  - This is a **backward-compatible** change — existing callers that omit the parameter will continue to work as before (value defaults to `None`).

---

### Step 5 — Architectural Sync: AccountNumber-Based Webhook Mapping

**Goal**: Add `AccountNumber` (`VARCHAR(20)`, `NOT NULL`, `UNIQUE`) to the `BankAccounts` table as the authoritative external identifier for Webhook account resolution. Update all layers — SQL schema, ORM model, seed script, and the Webhook service — so that `bank_sub_acc_id` maps to `BankAccounts.AccountNumber` exclusively. As directed by the updated `PROJECT_PLAN.md` (Part 2, Step 5), `directives/db_rules.md` (Section 1, 3), and `directives/backend_logic_rules.md` (Section 1, 4).

**Status: ✅ COMPLETE**

**Files to be modified:**

| Action | File | Change |
|---|---|---|
| MODIFY | `execution/database/master_schemas.sql` | Add `AccountNumber VARCHAR(20) NOT NULL UNIQUE` to `BankAccounts` table |
| MODIFY | `execution/backend/models.py` | Add `AccountNumber: Mapped[str]` to `BankAccount` ORM model |
| MODIFY | `execution/backend/seed.py` | Generate unique 10–15 digit `AccountNumber` for each seeded account |
| MODIFY | `execution/backend/bank_sync_service.py` | Replace `AccountName` lookup with `AccountNumber` lookup in `process_webhook_payload()` |

**Proposed Steps for Execution:**

- [ ] **Step A.1 — SQL Schema (`master_schemas.sql`)**:
  - Add `AccountNumber VARCHAR(20) NOT NULL` to the `BankAccounts` CREATE TABLE definition, positioned after `AccountName`.
  - Add `UNIQUE KEY idx_bankaccount_number (AccountNumber)` inside the same table definition.
  - Ensure all existing triggers (`After_Income_Insert`, `After_Income_Update`, `After_Income_Delete`, `After_Expense_Insert`, `After_Expense_Update`, `After_Expense_Delete`) reference only `AccountID` and `Balance` — they are unaffected by the new column.

- [ ] **Step A.2 — ORM Model (`models.py`)**:
  - Add `AccountNumber: Mapped[str] = mapped_column("AccountNumber", String(20), nullable=False, unique=True, index=True)` to the `BankAccount` class.
  - Position it after `AccountName` to match the column order in `master_schemas.sql`.
  - Update the `BankAccount.__repr__()` to include `AccountNumber` for better debuggability.

- [ ] **Step A.3 — Seed Script (`seed.py`)**:
  - Modify `seed_bank_accounts()` to generate a unique `AccountNumber` per account.
  - Format: prefix `190` + user index (1-digit) + account index (1-digit) + 9 random digits = 14-digit string total. Example: `"19011234567890"`.
  - Must be deterministic given `RANDOM_SEED = 42` — use `random.randint()` within the existing seeded random context.
  - Pass `AccountNumber=generated_number` when constructing each `BankAccount` object.

- [ ] **Step A.4 — Webhook Service (`bank_sync_service.py`)**:
  - In `process_webhook_payload()`, replace the current `AccountName`-based lookup with:
    ```python
    select(BankAccount).where(BankAccount.AccountNumber == bank_sub_acc_id)
    ```
  - Update the warning log message to reference `AccountNumber` rather than `AccountName`.
  - No other logic in the function changes — idempotency, direction, delegation, and response contracts remain identical.

---

### Step 5 — Webhook Refinement: "Others" Fallback Categorization

**Goal**: Replace the arbitrary `.limit(1)` category fetch in `process_webhook_payload()` with a safe, deterministic two-tier fallback that uses the user-owned `"Others"` category (Income-type or Expense-type) as the default assignment for all Webhook-sourced transactions. Ensure every user has this category by adding `"Others"` to `SystemCategories` (the template cloned by `InitializeUserCategories`). As directed by `directives/backend_logic_rules.md` (Section 4: "Others" Fallback Categorization) and `PROJECT_PLAN.md` (Part 2, Step 5).

**Status: ✅ COMPLETE**

**Root Cause:**
The current code at `bank_sync_service.py` lines 262–274 queries:
```python
select(Category).where(
    Category.UserID == resolved_user_id,
    Category.Type == expected_type,
).limit(1)
```
This picks whichever category the database returns first (ORDER BY PK), which is arbitrary and leads to wrong financial classification (e.g., a payroll deposit gets filed under "Housing").

**Files to be modified:**

| Action | File | Change |
|---|---|---|
| MODIFY | `execution/database/master_schemas.sql` | Add `('Others', 'Income')` and `('Others', 'Expense')` to `SystemCategories` INSERT |
| MODIFY | `execution/backend/bank_sync_service.py` | Replace `.limit(1)` fetch with two-tier "Others" fallback logic |

**Proposed Steps for Execution:**

- [ ] **Step C.1 — Seed SystemCategories (`master_schemas.sql`)**:
  - Append two rows to the existing `INSERT INTO SystemCategories` block:
    ```sql
    ('Others', 'Income'),
    ('Others', 'Expense');
    ```
  - Because `InitializeUserCategories` is a `SELECT ... FROM SystemCategories` clone, every user created after this change (or after a schema re-run) will automatically have both "Others" categories in their personal `Categories` table.
  - **No changes to the trigger, stored procedure, or any other SQL object are required.**

- [ ] **Step C.2 — Webhook Category Logic (`bank_sync_service.py`)**:
  - In `process_webhook_payload()`, replace the **entire Step 5 block** (lines 254–274) with the following two-tier logic:
    ```
    Tier 1 (Primary):   Select the user's Category where CategoryName="Others"
                        AND Type=expected_type.
    Tier 2 (Fallback):  If Tier 1 returns None (legacy user without "Others"),
                        fall back to the first available category of the correct
                        type. Log a WARNING that "Others" was missing.
    Final guard:        If both tiers return None, return CATEGORY_NOT_FOUND (404).
    ```
  - Update the Step 5 comment header from "auto-select first matching type" to "'Others' fallback categorization".
  - The resolved `category.CategoryID` continues to flow unchanged into Step 6 (transaction commit).
  - **All other logic in `process_webhook_payload()` is untouched** — no changes to schema validation, idempotency check, account resolution, UserID resolution, or Step 6 transaction commit.

**No other files require changes.** `seed.py` is unaffected because category creation is delegated entirely to the `After_User_Insert` trigger + `InitializeUserCategories` stored procedure, which reads from `SystemCategories`. Re-running `seed.py` after a schema re-run will automatically give all seeded users "Others" in both types.



