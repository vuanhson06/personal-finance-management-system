# Database Directives (MySQL + SQLAlchemy)

## 1. Schema & Structure
- **Core Entities:** `Users`, `BankAccounts`, `SystemCategories`, `Categories`, `Budgets`, `MarketWatch`, `Income`, `Expenses`, `MonthlyClosures`, `SavingGoals`.
- **Users Table Constraints:** `UserID` (PK), `UserName`, `Email` (Unique), `PhoneNumber` (Unique), `PasswordHash`, and `Role` (Enum: 'Admin', 'User').
- **BankAccounts Table Constraints:** Must include `AccountNumber VARCHAR(20) NOT NULL UNIQUE`. This is the authoritative external identifier used by the Webhook Simulator for account resolution. All seed data must generate realistic, unique 10–15 digit `AccountNumber` strings.
- **SavingGoals Table:** `GoalID` (PK), `UserID` (FK → `Users`), `GoalName VARCHAR(255) NOT NULL`, `TargetAmount DECIMAL(15,2) NOT NULL CHECK > 0`, `CurrentAmount DECIMAL(15,2) NOT NULL DEFAULT 0.00`, `Deadline DATE NULL`, `Status ENUM('Active','Completed') DEFAULT 'Active'`, timestamps. `CurrentAmount` is managed exclusively by the Python service layer — not by triggers.
- **Relationships:** Strict Primary and Foreign Keys. All financial tables must link to `Users(UserID)`. `Income` and `Expenses` link to `BankAccounts(AccountID)`. `SavingGoals` links only to `Users(UserID)` — it is NOT linked to `BankAccounts` directly; the financial link is made through the transaction records.
- **Category Template System:** The `SystemCategories` table holds default system tags. The `Categories` table is strictly user-owned (`UserID` NOT NULL), allowing each user private manipulation without affecting defaults.

## 2. Reserved System Categories (CRITICAL)
The following categories have system-level meaning and must always exist in `SystemCategories`. They are automatically cloned to every user's `Categories` table via the `After_User_Insert` trigger:

| CategoryName      | Type    | Purpose |
|---|---|---|
| `Savings`         | Expense | Transferring money FROM a bank account INTO a Saving Goal. Balance decreases. |
| `Savings Withdraw`| Income  | Returning money FROM a Saving Goal BACK to a bank account. Balance increases. |
| `Others`          | Income  | Default catch-all for Webhook-sourced income with no specific mapping. |
| `Others`          | Expense | Default catch-all for Webhook-sourced expenses with no specific mapping. |

> ⚠️ These are protected system categories. Application code must resolve them **by name** from the user's own `Categories` table — never hardcode a `CategoryID`.

## 3. Automation Logic (SQL Layer)
- **User Provisioning:** An `After_User_Insert` trigger auto-fires the `InitializeUserCategories` stored procedure to populate new user accounts with default tags from `SystemCategories`. All reserved categories are included automatically.
- **Balance Auto-Synchronization:** `AFTER INSERT`, `AFTER UPDATE`, and `AFTER DELETE` triggers on both `Income` and `Expenses` tables automatically keep `BankAccounts.Balance` perfectly synchronized. Saving Goal operations (Contribute/Withdraw) leverage these triggers — no manual balance update is ever needed.
- **SavingGoals.CurrentAmount:** Managed exclusively by the Python service layer (`saving_service.py`). There are **no SQL triggers** on `SavingGoals`. The service is responsible for incrementing on Contribute, decrementing on Withdraw, and clamping to `>= 0`.
- **Monthly Closures:** A stored procedure `CalculateMonthlyClosure` is used to compute and store historical end-of-month balances in the `MonthlyClosures` table.
- **SQL Views & Functions:** `vw_CategoryWiseSpending` and `vw_MonthlySummaries` handle rapid reporting. `GetTotalSavings` and `GetBudgetStatus` User-Defined Functions handle complex aggregations at the database level.

## 4. Webhook & Idempotency Schema Rules
- **AccountNumber Field:** The `BankAccounts` table must include `AccountNumber VARCHAR(20) NOT NULL UNIQUE`. This is the primary external mapping key — the Webhook payload field `bank_sub_acc_id` maps directly to this column. Seed data must generate unique, realistic numeric strings of 10–15 digits per account.
- **ExternalTransID Field:** Both the `Income` and `Expenses` tables must include an `ExternalTransID` column (`VARCHAR(255)`, UNIQUE, Indexed, Nullable). This field stores the `bank_transaction_id` from an inbound Webhook payload.
- **Idempotency Enforcement:** Before inserting any Webhook-sourced transaction, the system must query both `Income.ExternalTransID` and `Expenses.ExternalTransID` to confirm the ID has not been processed before. A duplicate must be silently acknowledged (no error, no re-insert).
- **AccountNumber Resolution:** The `bank_sub_acc_id` string in a Webhook payload maps to `BankAccounts.AccountNumber`. The lookup must use an exact string match and the resolved `UserID` must be taken from the matched account record only.

## 5. Strict Balance Integrity (CRITICAL — NON-NEGOTIABLE)
**No operation shall be allowed to result in `BankAccounts.Balance < 0`.** This is enforced at two independent layers:

### 5a. Database Layer (Last Line of Defense)
- **Column Constraint:** `BankAccounts.Balance` MUST carry `CHECK (Balance >= 0)`. MySQL 8.0+ enforces CHECK constraints natively.
- **`BEFORE INSERT` Trigger on `Expenses`:** Before any row is inserted into `Expenses`, the trigger must read the current `BankAccounts.Balance` for `NEW.AccountID`. If `Balance < NEW.Amount`, it must raise:
  ```sql
  SIGNAL SQLSTATE '45000'
  SET MESSAGE_TEXT = 'Insufficient funds: transaction would result in negative balance.';
  ```
- **`BEFORE UPDATE` Trigger on `Expenses`:** If `NEW.Amount > OLD.Amount` or `NEW.AccountID != OLD.AccountID`, the trigger must verify the target account has sufficient balance for the net change and raise the same `SIGNAL` if not.
- **Why BEFORE, not AFTER?** Only `BEFORE` triggers can abort a DML operation. `AFTER` triggers execute AFTER the row is written — by then the balance has already been changed and can only be caught by the `CHECK` constraint.

### 5b. Application Layer (Primary Guard — Fast Feedback)
- **`_assert_sufficient_funds(account, amount)` helper** in `transaction_service.py`: Must be called inside `add_expense()` after `_assert_account_ownership()` (which returns the `BankAccount` object with its live Balance).
- **Error message:** Raise `ValueError` with: `"Insufficient funds: balance is {account.Balance}, requested amount is {amount}."` — never a generic DB error.
- **Coverage by delegation:** All callers of `add_expense()` — including `saving_service.contribute_to_goal()` and `bank_sync_service.process_webhook_payload()` — automatically receive this protection without any changes to their own code.
- **Race condition safety:** The Python check occurs within the same SQLAlchemy session transaction block that commits the Expense, and the DB-layer `BEFORE` trigger + `CHECK` constraint serve as the atomic final guard.

## 6. Data Integrity and Validation
- **Database Constraints:** Rely on `CHECK (Amount > 0)`, `CHECK (Balance >= 0)`, and `ON DELETE CASCADE` relationships natively in the schema.
- All financial transactions must pass through hard validation logic (e.g., amount > 0, logical date ranges, sufficient funds) before hitting the ORM.
- **SavingGoals Constraints:** `CurrentAmount >= 0` must be enforced at the Python layer before any DB write. `TargetAmount > 0` is enforced by SQL `CHECK` constraint.
- **NEVER** perform an `UPDATE` or `DELETE` without verifying data constraints and ownership explicitly.
- Use `try-except` blocks around **all** database connection and query attempts to catch `IntegrityError`s.

## 7. Security Protocols
- **ORMs Only:** Must strictly use SQLAlchemy ORM 2.0+ for all interactions to prevent SQL injection.
- **Password Hashes:** Never store plain text passwords. `bcrypt` must be used for hashing prior to insertion.
- **Access Controls & Scope:** Enforce role-based behavior. Admins manage `SystemCategories`, while standard Users can only interact with their own data scoped by `UserID`.
- **Environment Parity:** `DB_URL`, `WEBHOOK_API_KEY`, and all API keys must unconditionally load from a `.env` file using `python-dotenv`. Keys must NEVER be hardcoded.

## 8. Coding & Formatting Standards
- **PEP 8:** Follow standard Python style guidelines.
- **Type Hints:** Mandatory for every function and ORM model.
- **Docstrings:** All logic and ORM classes must include standard documentation explaining their financial logic.
