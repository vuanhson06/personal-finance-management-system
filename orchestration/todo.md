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

---

## Part 2, Step 6: Saving Goals System

**Goal**: Implement a manual, transaction-based Saving Goals system. Each monetary movement between a bank account and a goal is recorded as a standard Income or Expense transaction using reserved system categories (`Savings` and `Savings Withdraw`), ensuring SQL triggers keep bank balances accurate and all goal activity is fully auditable. As defined in `PROJECT_PLAN.md` (Part 2, Step 6), `directives/db_rules.md` (Sections 1–3), and `directives/backend_logic_rules.md` (Section 5).

**Status: ✅ COMPLETE**

**Key Design Decisions:**
- `SavingGoals.CurrentAmount` is managed **by Python** — there are no SQL triggers on this table.
- `BankAccounts.Balance` is still managed **by SQL triggers** on Income/Expenses — no change.
- Reserved categories are resolved **by name** at runtime from the user's `Categories` table — no hardcoded IDs.
- `Savings (Expense)` is **already** in `SystemCategories`. Only `Savings Withdraw (Income)` needs to be inserted.

**Files to be created / modified:**

| Action | File | Change |
|---|---|---|
| MODIFY | `execution/database/master_schemas.sql` | Add `SavingGoals` CREATE TABLE + insert `('Savings Withdraw', 'Income')` into `SystemCategories` |
| MODIFY | `execution/backend/models.py` | Add `SavingGoal` ORM class + `GoalStatus` Enum |
| CREATE | `execution/backend/saving_service.py` | Full service with goal CRUD + Contribute + Withdraw |

**Proposed Steps for Execution:**

- [ ] **Step SG.1 — SQL Schema (`master_schemas.sql`)**:
  - Insert `('Savings Withdraw', 'Income')` into the `SystemCategories` INSERT block.
    - ⚠️ `('Savings', 'Expense')` is ALREADY present — do NOT duplicate it.
  - Add the following `CREATE TABLE` definition after `MonthlyClosures`:
    ```sql
    CREATE TABLE IF NOT EXISTS SavingGoals (
        GoalID        INT AUTO_INCREMENT PRIMARY KEY,
        UserID        INT NOT NULL,
        GoalName      VARCHAR(255) NOT NULL,
        TargetAmount  DECIMAL(15,2) NOT NULL CHECK (TargetAmount > 0),
        CurrentAmount DECIMAL(15,2) NOT NULL DEFAULT 0.00,
        Deadline      DATE NULL,
        Status        ENUM('Active', 'Completed') NOT NULL DEFAULT 'Active',
        CreatedAt     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
    );
    ```
  - Add a performance index: `CREATE INDEX idx_savinggoals_user ON SavingGoals (UserID, Status);`
  - Existing triggers (`After_Income_*`, `After_Expense_*`) are **unaffected** — they only reference `Income` and `Expenses`.

- [ ] **Step SG.2 — ORM Model (`models.py`)**:
  - Add `GoalStatus` Python Enum: values `Active = "Active"`, `Completed = "Completed"`.
  - Add `SavingGoal` ORM class mapped to `SavingGoals` table:
    - `GoalID: Mapped[int]` — PK, autoincrement.
    - `UserID: Mapped[int]` — FK to `Users(UserID)`, `ondelete="CASCADE"`.
    - `GoalName: Mapped[str]` — `String(255)`, `nullable=False`.
    - `TargetAmount: Mapped[Decimal]` — `Numeric(15,2)`, `nullable=False`.
    - `CurrentAmount: Mapped[Decimal]` — `Numeric(15,2)`, `nullable=False`, `default=Decimal("0.00")`.
    - `Deadline: Mapped[Optional[date]]` — `Date`, `nullable=True`.
    - `Status: Mapped[GoalStatus]` — `SAEnum(GoalStatus)`, `nullable=False`, `default=GoalStatus.Active`.
    - `CreatedAt`, `UpdatedAt` — standard timestamps.
    - `__table_args__`: `CheckConstraint("TargetAmount > 0")` + `Index("idx_savinggoals_user", "UserID", "Status")`.
  - Add `saving_goals` relationship to the `User` model (`cascade="all, delete-orphan"`).
  - Add `user` back-reference to `SavingGoal`.

- [ ] **Step SG.3 — Service Logic (`saving_service.py`)**:
  - Create `execution/backend/saving_service.py` with:

  **`_resolve_reserved_category(name, type_, user_id, db)` (private helper)**
  - Queries user's `Categories` WHERE `CategoryName == name` AND `Type == type_`.
  - Raises `ValueError` with a clear message if not found (no silent fallback for reserved categories).

  **`create_goal(user_id, goal_name, target_amount, db, deadline=None)` → `SavingGoal`**
  - Validate `target_amount > 0`.
  - Validate `deadline` is in the future if provided.
  - Create and commit a `SavingGoal` record with `Status = Active`, `CurrentAmount = 0`.

  **`get_goals(user_id, db, status_filter=None)` → `list[SavingGoal]`**
  - UserID-scoped query. Optionally filter by `Status` if `status_filter` is provided.
  - Returns list ordered by `CreatedAt DESC`.

  **`get_goal_by_id(user_id, goal_id, db)` → `SavingGoal`**
  - UserID-scoped lookup. Raises `ValueError` if not found or not owned.

  **`contribute_to_goal(user_id, goal_id, account_id, amount, db, description=None)` → `dict`**
  - Step 1: Validate `amount > 0`.
  - Step 2: Assert goal ownership + `Status == "Active"`.
  - Step 3: Assert account ownership (call `_assert_account_ownership` from `transaction_service`).
  - Step 4: Resolve `Savings` (Expense) category via `_resolve_reserved_category`.
  - Step 5: Call `add_expense(user_id, account_id, category_id, amount, date.today(), db, description)` → trigger fires.
  - Step 6: `goal.CurrentAmount += amount`.
  - Step 7: If `goal.CurrentAmount >= goal.TargetAmount` → `goal.Status = GoalStatus.Completed`.
  - Step 8: `db.commit()`, `db.refresh(goal)`.
  - Return summary dict with `goal_id`, `new_current_amount`, `status`, `transaction_id`.

  **`withdraw_from_goal(user_id, goal_id, account_id, amount, db, description=None)` → `dict`**
  - Step 1: Validate `amount > 0`.
  - Step 2: Assert goal ownership.
  - Step 3: Assert `amount <= goal.CurrentAmount` (prevent negative balance).
  - Step 4: Assert account ownership.
  - Step 5: Resolve `Savings Withdraw` (Income) category via `_resolve_reserved_category`.
  - Step 6: Call `add_income(user_id, account_id, category_id, amount, date.today(), db, description)` → trigger fires.
  - Step 7: `goal.CurrentAmount -= amount`.
  - Step 8: If `goal.Status == Completed` and `goal.CurrentAmount < goal.TargetAmount` → revert to `Active`.
  - Step 9: `db.commit()`, `db.refresh(goal)`.
  - Return summary dict with `goal_id`, `new_current_amount`, `status`, `transaction_id`.

  **`delete_goal(user_id, goal_id, db)` → `None`**
  - Assert goal ownership.
  - Assert `CurrentAmount == 0` (must withdraw all funds before deleting).
  - Delete record and commit.

---

## Critical Fix: Strict Balance Integrity

**Goal**: Eliminate the critical flaw where an Expense (manual, Webhook, or Saving Goal Contribution) can exceed `BankAccounts.Balance` and push it negative. Enforce a non-negotiable "no negative balance" policy at two independent layers — the Python service layer (primary fast guard) and the SQL database layer (final atomic guard). As directed by `PROJECT_PLAN.md` (Part 2 Policy Block), `directives/db_rules.md` (Section 5), and `directives/backend_logic_rules.md` (Section 6).

**Status: ✅ COMPLETE**

**Root Cause (Confirmed from source code):**
1. `BankAccounts.Balance DECIMAL(15,2) DEFAULT 0.00` — **no `CHECK (Balance >= 0)` constraint** (line 21, `master_schemas.sql`).
2. `After_Expense_Insert` trigger does `SET Balance = Balance - NEW.Amount` blindly — **no pre-check**.
3. `add_expense()` in `transaction_service.py` (lines 317–320) validates amount, date, ownership, and category — but **never checks if `account.Balance >= amount`**.
4. All three expenditure paths (`add_expense()` direct, Webhook processor, `saving_service.contribute_to_goal()`) share this vulnerability.

**Two-Layer Defense Strategy:**

```
[Caller] → add_expense()
               ↓ Python: _assert_sufficient_funds()  ← Layer 1: Fast, clear error
               ↓ db.add(expense); db.commit()
               ↓ SQL: BEFORE INSERT trigger fires    ← Layer 2: Atomic DB guard
               ↓ AFTER INSERT trigger fires → Balance updated
```

**Files to be modified:**

| Action | File | Change |
|---|---|---|
| MODIFY | `execution/database/master_schemas.sql` | Add `CHECK (Balance >= 0)` to `BankAccounts`; add `BEFORE INSERT` + `BEFORE UPDATE` triggers on `Expenses` |
| MODIFY | `execution/backend/transaction_service.py` | Add `_assert_sufficient_funds()` helper; call it inside `add_expense()` |
| MODIFY | `execution/backend/webhook_server.py` | Map `ValueError` with "Insufficient funds" to `HTTP 422` with `{"status": "INSUFFICIENT_FUNDS"}` |

> **`seed.py` — No changes needed.** Seed income ($1,500–$8,000/month) substantially exceeds seed expenses ($20–$1,200/month). With RANDOM_SEED=42, balances remain positive throughout. The new BEFORE trigger will validate this automatically at seed time.
> **`saving_service.py` — No changes needed.** `contribute_to_goal()` already delegates to `add_expense()` — it inherits the protection for free.

**Proposed Steps for Execution:**

- [ ] **Step BI.1 — SQL Schema: `CHECK` constraint (`master_schemas.sql`)**:
  - Modify `BankAccounts` table definition to add:
    ```sql
    Balance DECIMAL(15,2) DEFAULT 0.00 CHECK (Balance >= 0),
    ```
  - This is the last-resort hard constraint. If the Python layer and BEFORE trigger both fail to catch a case, MySQL will reject the UPDATE outright with an `IntegrityError`.

- [ ] **Step BI.2 — SQL: `BEFORE INSERT` trigger on `Expenses` (`master_schemas.sql`)**:
  - Add a new `BEFORE INSERT` trigger **before** the existing `After_Expense_Insert` trigger:
    ```sql
    DROP TRIGGER IF EXISTS Before_Expense_Insert;
    DELIMITER $$
    CREATE TRIGGER Before_Expense_Insert
    BEFORE INSERT ON Expenses
    FOR EACH ROW
    BEGIN
        DECLARE current_balance DECIMAL(15,2);
        SELECT Balance INTO current_balance
        FROM BankAccounts
        WHERE AccountID = NEW.AccountID;
        IF current_balance < NEW.Amount THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Insufficient funds: transaction would result in negative balance.';
        END IF;
    END$$
    DELIMITER ;
    ```
  - This fires **atomically within the same DB transaction** that commits the Expense row, preventing race conditions.

- [ ] **Step BI.3 — SQL: `BEFORE UPDATE` trigger on `Expenses` (`master_schemas.sql`)**:
  - Add a new `BEFORE UPDATE` trigger to guard against amount increases or account changes:
    ```sql
    DROP TRIGGER IF EXISTS Before_Expense_Update;
    DELIMITER $$
    CREATE TRIGGER Before_Expense_Update
    BEFORE UPDATE ON Expenses
    FOR EACH ROW
    BEGIN
        DECLARE current_balance DECIMAL(15,2);
        -- Only check if the net debit to the target account increases
        IF NEW.AccountID = OLD.AccountID AND NEW.Amount > OLD.Amount THEN
            SELECT Balance INTO current_balance
            FROM BankAccounts WHERE AccountID = NEW.AccountID;
            IF current_balance < (NEW.Amount - OLD.Amount) THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Insufficient funds: expense update would result in negative balance.';
            END IF;
        ELSEIF NEW.AccountID != OLD.AccountID THEN
            SELECT Balance INTO current_balance
            FROM BankAccounts WHERE AccountID = NEW.AccountID;
            IF current_balance < NEW.Amount THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Insufficient funds: expense account change would result in negative balance.';
            END IF;
        END IF;
    END$$
    DELIMITER ;
    ```

- [ ] **Step BI.4 — Python: `_assert_sufficient_funds()` in `transaction_service.py`**:
  - Add the following private helper after `_assert_account_ownership()`:
    ```python
    def _assert_sufficient_funds(account: BankAccount, amount: Decimal) -> None:
        """
        Ensures the account has sufficient balance for a debit operation.
        Raises ValueError with a clear message if balance < amount.
        This is the Application Layer guard (Layer 1 of two-layer defense).
        """
        if account.Balance < amount:
            raise ValueError(
                f"Insufficient funds: account {account.AccountID} has "
                f"balance {account.Balance}, but requested {amount}. "
                f"Transaction would result in a negative balance."
            )
    ```
  - Modify `add_expense()` — insert the check after `_assert_account_ownership()`:
    ```python
    # existing:
    account = _assert_account_ownership(account_id, user_id, db)
    # ADD THIS LINE:
    _assert_sufficient_funds(account, amount)
    _assert_category_ownership(...)
    ```
  - **Do NOT wrap this in try-except inside `add_expense()`** — let the `ValueError` propagate cleanly to the caller.

- [ ] **Step BI.5 — Python: Webhook 422 mapping (`webhook_server.py`)**:
  - In the `receive_transaction()` route handler, the existing response code mapping handles `200`, `400`, `401`, `404`, and `500`.
  - Add a specific `ValueError` catch block **before** the generic `Exception` guard:
    ```python
    except ValueError as e:
        msg = str(e)
        if "Insufficient funds" in msg:
            return jsonify({"status": "INSUFFICIENT_FUNDS", "detail": msg}), 422
        return jsonify({"status": "INVALID_REQUEST", "detail": msg}), 400
    ```
  - This keeps the Webhook endpoint's error surface clean and returns a meaningful `422` instead of a generic `500`.

---

## Part 2 - Step 7: API Routing Layer (The Bridge)

**Goal**: Implement a REST API using Flask and Blueprints to expose backend logic to the new Web Frontend. Secure routes using Flask-Session (`@login_required`). Standalone webhook server remains unaffected.

**Status: ✅ COMPLETE**

- [x] **Step API.1 — Main App & Setup**: Create `execution/backend/app.py` with Flask, Flask-Session config, and global error handlers (mapping `ValueError` with "Insufficient funds" to `422`).
- [x] **Step API.2 — Auth Blueprint**: Create `routes/auth.py` for `/api/auth/login`, `/api/auth/signup`, `/api/auth/logout`, `/api/auth/me`.
- [x] **Step API.3 — Finance Blueprint**: Create `routes/finance.py` for `/api/accounts`, `/api/transactions/income`, and `/api/transactions/expense`.
- [x] **Step API.4 — Goals Blueprint**: Create `routes/goals.py` for `/api/goals`, `/api/goals/contribute`, and `/api/goals/withdraw`.
- [x] **Step API.5 — Reports Blueprint**: Create `routes/reports.py` for `/api/reports/category-spending`, `/api/reports/monthly-trend`, `/api/budgets/status`, and `/api/market/ticker`.

---

## Part 3: Frontend Web App (The Interface)

### Step 1: Authentication & Session Management

**Goal**: Establish the base frontend layout and implement the Authentication Portal (Login/Sign-up) using the defined Neumorphism design system and Fetch API to communicate with the existing Flask backend.

**Proposed Steps for Execution:**
- [x] **Step F.1.1 — Frontend Structure**: Create the `/execution/frontend/templates/` and `/execution/frontend/static/` directories.
- [x] **Step F.1.2 — Base Layout (`base.html`)**: Create `templates/base.html` containing the Bootstrap 5, SweetAlert2, and Chart.js CDNs, plus our custom stylesheet link.
- [x] **Step F.1.3 — Neumorphic Styles (`style.css`)**: Implement the CSS tokens (`.neu-outset`, `.neu-inset`, `.neu-btn`, etc.) from `directives/ui_paper_system.md` into `static/css/style.css`.
- [x] **Step F.1.4 — Auth UI (`login.html` & `signup.html`)**: Build the Login and Sign-up screens using Bootstrap forms mapped to our `.neu-inset` inputs and `.neu-btn` buttons.
- [x] **Step F.1.5 — Auth Logic (`auth.js`)**: Write the async Fetch API logic in `static/js/auth.js` to handle form submissions to `/api/auth/login` and `/api/auth/signup`. Bind SweetAlert2 for notifications.
- [x] **Step F.1.6 — Flask Template Routing (`app.py`)**: Update `execution/backend/app.py` to point to the frontend folders (`template_folder='../frontend/templates'`, `static_folder='../frontend/static'`) and add the routes to render the login and signup HTML pages.

### Step 2: Primary Financial Dashboard & Market Watch

**Goal**: Build the main user dashboard (`dashboard.html`) utilizing the Neumorphism design system. It will display the user's Total Balance and Monthly Spending overview, alongside a real-time Market Watch ticker fetching live prices via the API.

**Proposed Steps for Execution:**
- [x] **Step F.2.1 — Dashboard Layout (`dashboard.html`)**: Create the `dashboard.html` template extending `base.html`. Construct a grid layout using Bootstrap 5, wrapping content in `.neu-outset` cards for the "Total Balance" and "Monthly Spending" summaries.
- [x] **Step F.2.2 — Dashboard Logic (`dashboard.js`)**: Create `static/js/dashboard.js`. Implement async functions to fetch data from `/api/accounts` (for total balance) and `/api/reports/monthly-trend` (for spending), updating the DOM dynamically.
- [x] **Step F.2.3 — Market Ticker UI**: Design a grid-based or scrolling ticker section within the dashboard using neumorphic cards for individual assets (e.g., Gold, Stocks, Crypto).
- [x] **Step F.2.4 — Market Ticker Logic (`market.js`)**: Create `static/js/market.js` to fetch live prices from `/api/market/ticker`. Update the UI with price values and positive/negative percentage changes (styled with our Success/Danger tokens).
- [x] **Step F.2.5 — Flask Route Update (`app.py`)**: Update the existing `/dashboard` route in `app.py` to render `dashboard.html` instead of the current placeholder text.

### Step 3: Account & Transaction Manager

**Goal**: Build the UI interfaces (`transactions.html`) for managing bank accounts and recording transactions. The transaction entry must integrate with the Strict Balance Guard, displaying localized error modals if the backend detects an overdraw.

**Proposed Steps for Execution:**
- [x] **Step F.3.1 — Transactions Layout (`transactions.html`)**: Create `transactions.html` integrating the sidebar and a two-column grid. The left column lists Accounts and Transactions history, while the right column holds the forms.
- [x] **Step F.3.2 — Account List & Backend Link**: Build the HTML structure for displaying existing bank accounts (including the `AccountNumber`). Ensure the `/api/accounts` endpoint supports creating accounts if not already implemented.
- [x] **Step F.3.3 — Transaction Form UI**: Build the HTML forms for adding Income and Expenses. Include dropdowns for selecting Accounts and Categories.
- [x] **Step F.3.4 — Transactions Logic (`transactions.js`)**: Create `static/js/transactions.js` to handle form submissions via Fetch API to `/api/transactions/income` and `/api/transactions/expense`.
- [x] **Step F.3.5 — Strict Balance Guard UI Binding**: In `transactions.js`, explicitly check for HTTP 422 responses. When received, trigger a bold SweetAlert2 error modal using our `.neu-outset` popup styling to warn the user of "Insufficient Funds".
- [x] **Step F.3.6 — Flask Route Update (`app.py`)**: Update `app.py` to add a UI route for `/transactions` rendering `transactions.html`.

### Step 4: Saving Goals Module

**Goal**: Build the UI interface (`goals.html`) for managing Saving Goals. This includes rendering existing goals with dynamic progress bars and providing actions to "Contribute" and "Withdraw" funds, hooked up to the strict balance-protected backend endpoints.

**Proposed Steps for Execution:**
- [x] **Step F.4.1 — Goals Layout (`goals.html`)**: Create `goals.html` extending `base.html` with the standard sidebar. Establish a layout to display a list of active and completed goals.
- [x] **Step F.4.2 — Goal Cards UI**: Design individual `.neu-outset` cards for each goal. Each card will show the Goal Name, Target Amount, Current Amount, and a Bootstrap progress bar indicating the completion percentage.
- [x] **Step F.4.3 — Goal Actions UI**: Add "Contribute" and "Withdraw" buttons on each goal card. These will open SweetAlert2 modals prompting the user to select an account and enter an amount.
- [x] **Step F.4.4 — Create Goal Form**: Add a section or modal allowing the user to define a new Saving Goal (Name, Target Amount, Deadline).
- [x] **Step F.4.5 — Goals Logic (`goals.js`)**: Create `static/js/goals.js`. Implement async functions to `GET /api/goals` and render the cards. Handle form submissions to create, contribute, and withdraw via Fetch API. Crucially, integrate the HTTP 422 Strict Balance Guard during the contribute action.
- [x] **Step F.4.6 — Flask Route Update (`app.py`)**: Update `app.py` to add a UI route for `/goals` rendering `goals.html`.

### Step 5: Webhook Sync Monitor

**Goal**: Build a Sync Dashboard (`sync.html`) to monitor automated transactions pulled via the Webhook Simulator. Provide a user interface to trigger a simulation payload and view idempotency/categorization feedback.

**Proposed Steps for Execution:**
- [x] **Step F.5.1 — Sync Layout (`sync.html`)**: Create `sync.html` extending `base.html` with the standard sidebar. Add a primary data table wrapper using the `.neu-outset` styling to hold the synced transactions.
- [x] **Step F.5.2 — Sync Table UI**: Design a responsive table structure displaying the Date, Description, Amount, and Account. Provide visual indicators (like badges) for items categorized as "Others" or marked as "Duplicate/Ignored" based on idempotency rules.
- [x] **Step F.5.3 — Sync Simulator UI**: Add a manual trigger section (a neumorphic card) with a button to hit a new `/api/sync/simulate` endpoint, allowing the user to forcefully inject a mock bank payload into the webhook server.
- [x] **Step F.5.4 — Backend Simulator Route**: Implement a new backend route `POST /api/sync/simulate` in `routes/finance.py` that constructs a mock JSON payload and POSTs it to the local webhook server (`http://localhost:5050/webhook/transaction`) using the configured `X-API-KEY`.
- [x] **Step F.5.5 — Sync Logic (`sync.js`)**: Create `static/js/sync.js`. Fetch recent transactions to populate the table. Bind the manual trigger button to the simulator endpoint using a SweetAlert2 loading state and handle the responses.
- [x] **Step F.5.6 — Flask Route Update (`app.py`)**: Register the `/sync` UI route in `app.py` to render `sync.html`.

### Step 6: Visual Analytics & Reporting

**Goal**: Build an Analytics Dashboard (`analytics.html`) utilizing `Chart.js` for visual data representation and providing searchable tabular summaries of historical transactions.

**Proposed Steps for Execution:**
- [x] **Step F.6.1 — Analytics Layout (`analytics.html`)**: Create `analytics.html` extending `base.html` with the standard sidebar. Scaffold a grid layout for displaying charts at the top and a full data table at the bottom.
- [x] **Step F.6.2 — Chart.js Integration UI**: Design `.neu-outset` container cards holding `<canvas>` elements for a "Monthly Trend" line/bar chart and a "Category Spending" doughnut chart.
- [x] **Step F.6.3 — Searchable Data Table UI**: Build a large tabular section with an input field for client-side search/filtering of historical transactions.
- [x] **Step F.6.4 — Analytics Logic (`analytics.js`)**: Create `static/js/analytics.js`. Fetch data from `/api/reports/monthly-trend` and `/api/reports/category-spending` to dynamically initialize the Chart.js instances. Fetch historical transactions to populate the data table and bind a simple text-filtering algorithm to the search input.
- [x] **Step F.6.5 — Flask Route Update (`app.py`)**: Register the `/analytics` UI route in `app.py` to render `analytics.html`.

### Step 7: Web Budget Planner & Visual Alerts

**Goal**: Build a Budget Manager (`budgets.html`) that allows users to create/edit monthly category limits and provides visual alerts when spending approaches or exceeds those limits.

**Proposed Steps for Execution:**
- [x] **Step F.7.1 — Budgets Layout (`budgets.html`)**: Create `budgets.html` extending `base.html` with the standard sidebar. Design a layout containing a "Create Budget" form section and a list/grid of active budget trackers.
- [x] **Step F.7.2 — Budget Tracker UI**: Design individual `.neu-outset` budget cards. Each card will display the Category, Period (e.g., YYYY-MM), the Target Limit, the Current Spending, and a Bootstrap progress bar.
- [x] **Step F.7.3 — Visual Alerts Logic**: The UI progress bars must dynamically color-code based on the percentage consumed (e.g., Green `< 80%`, Warning Orange `> 80%`, Danger Red `>= 100%`).
- [x] **Step F.7.4 — Budgets Logic (`budgets.js`)**: Create `static/js/budgets.js`. Implement async functions to fetch `/api/budgets` to render the tracker cards. Fetch from `/api/categories` to populate the form, and handle submissions to `POST /api/budgets` via Fetch API.
- [x] **Step F.7.5 — Flask Route Update (`app.py`)**: Register the `/budgets` UI route in `app.py` to render `budgets.html`.

---

## Phase 4: Final QA & Bug Fixing

**Goal**: Systematically verify all features, edge cases, data isolation guarantees, and UI/UX consistency across the entire system before final release.

### Step QA.1 — User Profile & Auth Module
- [ ] **QA-AUTH-01**: Successful registration with all valid fields; verify session is created and redirect to `/dashboard`.
- [ ] **QA-AUTH-02**: Registration with a duplicate email; verify HTTP 400 and SweetAlert2 error message.
- [ ] **QA-AUTH-03**: Registration with missing fields (no username, email, or password); verify HTTP 400.
- [ ] **QA-AUTH-04**: Successful login with valid credentials; verify session and dashboard redirect.
- [ ] **QA-AUTH-05**: Login with incorrect password; verify HTTP 400 and SweetAlert2 error.
- [ ] **QA-AUTH-06**: Accessing a protected route (e.g., `/dashboard`) while unauthenticated; verify redirect to `/login`.
- [ ] **QA-AUTH-07**: Session persistence across page refreshes; verify user remains logged in.
- [ ] **QA-AUTH-08**: Logout clears session; verify `/api/auth/logout` redirects to `/login` and session is destroyed.

### Step QA.2 — Transaction Engine
- [ ] **QA-TXN-01**: Add a valid income transaction; verify balance increases, row appears in history table.
- [ ] **QA-TXN-02**: Add a valid expense transaction; verify balance decreases correctly.
- [ ] **QA-TXN-03**: **Strict Balance Guard** — Attempt to add an expense greater than account balance; verify HTTP 422 response and SweetAlert2 "Insufficient Funds" modal fires.
- [ ] **QA-TXN-04**: **Balance Guard at DB Layer** — Confirm the `BEFORE INSERT` trigger also rejects the transaction at the SQL level if the Python guard were bypassed.
- [ ] **QA-TXN-05**: Auto-categorization via Webhook assigns "Others" category when no matching category is found; verify the orange badge appears in `/sync`.
- [ ] **QA-TXN-06**: Add a transaction with a non-existent `account_id`; verify HTTP 400 and no DB corruption.
- [ ] **QA-TXN-07**: Attempt to add a transaction with a `category_id` belonging to another user; verify HTTP 400 or data isolation rejection.

### Step QA.3 — Bank Account & Balance Tracking
- [ ] **QA-BAL-01**: Create a new bank account; verify it appears in the accounts list with a zero balance.
- [ ] **QA-BAL-02**: After adding income, verify `BankAccounts.Balance` in the DB matches the UI-displayed balance.
- [ ] **QA-BAL-03**: After adding an expense, verify `BankAccounts.Balance` decreases by the exact expense amount via the SQL trigger.
- [ ] **QA-BAL-04**: Historical balance accuracy — run a series of transactions and verify the running balance shown matches manual calculation.

### Step QA.4 — Analytics & Reporting
- [ ] **QA-RPT-01**: Monthly Trend Chart renders with correct bar heights for Income vs. Expense for the current month.
- [ ] **QA-RPT-02**: Category Doughnut Chart correctly slices spending by category; hovering shows correct USD tooltip.
- [ ] **QA-RPT-03**: Historical table lists all transactions; default sort is newest-first.
- [ ] **QA-RPT-04**: Search filter — typing in the search bar instantly filters rows by description, date, and category.
- [ ] **QA-RPT-05**: `/api/reports/monthly-trend` and `/api/reports/category-spending` return correctly aggregated data when called directly.

### Step QA.5 — Budget Planner & Visual Alerts
- [ ] **QA-BDG-01**: Create a new budget for a category/period; verify it appears as a tracker card.
- [ ] **QA-BDG-02**: **Healthy State** — spending below 80% shows a Teal/Green progress bar.
- [ ] **QA-BDG-03**: **Warning State** — spending at 82% shows an Orange progress bar and the "⚠️ Approaching Limit" badge.
- [ ] **QA-BDG-04**: **Danger State** — spending at or above 100% shows a Red progress bar at full width and the "⚠️ Budget Exceeded" badge.
- [ ] **QA-BDG-05**: Duplicate budget for same category/period; verify the backend returns an appropriate error.

### Step QA.6 — Market Watch Dashboard
- [ ] **QA-MKT-01**: Market Ticker on `/dashboard` loads and displays at least one asset (Gold, Stock, or Crypto).
- [ ] **QA-MKT-02**: Market data auto-refreshes every 60 seconds without a page reload.
- [ ] **QA-MKT-03**: If the external API is unreachable, verify the UI shows a graceful "Unavailable" state rather than crashing.

### Step QA.7 — Webhook Sync Security & Idempotency
- [ ] **QA-WBH-01**: Send a valid webhook payload to `POST /webhook/transaction`; verify transaction is created.
- [ ] **QA-WBH-02**: **Idempotency** — Send the same `bank_transaction_id` twice; verify the second request returns a non-500 response and no duplicate transaction is created.
- [ ] **QA-WBH-03**: **API Key Security** — Send a webhook request with an invalid/missing `X-API-KEY`; verify HTTP 401 response.
- [ ] **QA-WBH-04**: **Simulator UI** — Click "Trigger Webhook" on `/sync`; verify the table updates and SweetAlert2 confirmation fires.
- [ ] **QA-WBH-05**: **Idempotency via UI** — Click "Trigger Webhook" with the same Transaction ID twice; verify the SweetAlert2 "Idempotency Guard" info modal fires.
- [ ] **QA-WBH-06**: Webhook with an expense exceeding account balance; verify HTTP 422 is returned by the webhook server.

### Step QA.8 — Saving Goals
- [ ] **QA-GOL-01**: Create a new goal; verify it appears as a card with 0% progress.
- [ ] **QA-GOL-02**: Contribute to a goal; verify progress bar increases and account balance decreases.
- [ ] **QA-GOL-03**: **Balance Guard for Goals** — Attempt to contribute more than account balance; verify HTTP 422 and SweetAlert2 "Insufficient Funds" modal.
- [ ] **QA-GOL-04**: Withdraw from a goal; verify progress bar decreases and account balance increases.
- [ ] **QA-GOL-05**: Withdraw more than the goal's `CurrentAmount`; verify HTTP 400 error.
- [ ] **QA-GOL-06**: Contribute the exact remaining amount to reach 100%; verify goal status auto-changes to "Completed" and progress bar turns Green.

### Step QA.9 — Data Isolation
- [ ] **QA-ISO-01**: Log in as User A, get the ID of one of User A's accounts. Log in as User B and attempt `GET /api/accounts/<user_a_account_id>`; verify HTTP 403 or 404 (not 200).
- [ ] **QA-ISO-02**: Attempt `POST /api/transactions/expense` as User B using User A's `account_id`; verify the transaction is rejected.
- [ ] **QA-ISO-03**: Verify `/api/goals` for User B contains zero goals from User A.
- [ ] **QA-ISO-04**: URL manipulation — navigate to `/api/budgets/<user_a_budget_id>` while authenticated as User B; verify 404 or access denied.

### Step QA.10 — UI/UX & Neumorphism Consistency
- [ ] **QA-UI-01**: All pages use the correct surface color `#E7E5E4`.
- [ ] **QA-UI-02**: `.neu-outset` cards display the correct light-source box-shadow (top-left light, bottom-right dark).
- [ ] **QA-UI-03**: `.neu-inset` inputs display the inverted shadow (pressed-in effect).
- [ ] **QA-UI-04**: All buttons show the correct hover state (shadow reduction / inset transition).
- [ ] **QA-UI-05**: SweetAlert2 modals inherit the Neumorphic surface `#E7E5E4` background and `.neu-outset` CSS class.
- [ ] **QA-UI-06**: All pages are responsive — sidebar collapses gracefully on smaller viewport widths.
- [ ] **QA-UI-07**: No `favicon.ico` 404 errors appear in the server log.
