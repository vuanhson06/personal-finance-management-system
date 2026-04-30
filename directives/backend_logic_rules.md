# Backend Logic Directives (Python & SQLAlchemy)

## 1. ORM Modeling & Structure
- **Model Reflection:** Python SQLAlchemy classes must perfectly mirror the updated `master_schemas.sql` tables (`Users`, `BankAccounts`, `SystemCategories`, `Categories`, `Budgets`, `MarketWatch`, `Income`, `Expenses`, `MonthlyClosures`, `SavingGoals`).
- **Data Types:** Ensure `User.PhoneNumber` and `User.Role` are mapped correctly. Consider using Python `Enum` for the Role column.
- **AccountNumber Field:** The `BankAccount` ORM model must include `AccountNumber: Mapped[str]` (`String(20)`, `nullable=False`, `unique=True`, `index=True`). Seed data must use this field with a unique, realistic numeric string (10–15 digits) per account.
- **ExternalTransID Field:** The `Income` and `Expense` ORM models must include an `ExternalTransID: Mapped[Optional[str]]` column (`String(255)`, unique, indexed, nullable). This field stores the idempotency key from inbound Webhook payloads.
- **SavingGoal Model:** Must include `GoalID`, `UserID` (FK), `GoalName`, `TargetAmount`, `CurrentAmount`, `Deadline` (nullable), `Status` (Enum: `Active`/`Completed`), `CreatedAt`, `UpdatedAt`. The `Status` field is managed by the Python service — not by SQL triggers.

## 2. Application-Level Data Isolation (CRITICAL)
To strictly enforce secure data isolation across different users sharing the database, the backend application must strictly adhere to these directives:
- **Mandatory User Context:** Every SQLAlchemy API request (read, write, update, or delete) must dynamically resolve the authenticated user, known as `current_user`.
- **The Golden Rule of Querying:** Under absolutely no circumstances should a generic `Session.query(Model).all()` be executed without a filter. **ALL data-fetching queries (except for `SystemCategories`) must imperatively append `.filter(Model.UserID == current_user.id)`**.
- **Foreign Key Logic Verification:** Even when mutating a sub-layer (e.g., updating an `Expense` tied to a `BankAccounts.AccountID`), the Python logic must actively assert that the `AccountID` is genuinely owned by the `current_user`.
- **Registration Flow:** Provide the database the required `Email`, `PhoneNumber`, and `PasswordHash`. The backend doesn't need to manually create the initial `Categories` since the SQL `After_User_Insert` trigger handles it.

## 3. Role-Based Access Control
- **User Roles:** Implement logic to distinguish between `'Admin'` and `'User'` roles.
- **Administrative Privileges:** Only `Admin` users should be permitted to insert, update, or delete records in the `SystemCategories` table. Standard users only interact with their personal `Categories` table.

## 4. Webhook Simulator — Security & Processing Rules
The Webhook endpoint replaces the old "Bank Sync Simulation". These rules are mandatory for all Webhook-related code:

- **Authentication:** Every inbound POST request to the Webhook endpoint must include the header `X-API-KEY`. The value must match `WEBHOOK_API_KEY` loaded from `.env`. A missing or mismatched key must return an immediate `401 Unauthorized` response with no further processing.
- **Idempotency Check (Anti-Double Spending):** Before processing any payload, the system must query both `Income.ExternalTransID` and `Expenses.ExternalTransID` for the incoming `bank_transaction_id`. If found in either table, return `200 OK` with `{"status": "ALREADY_PROCESSED"}` and terminate — do NOT re-insert.
- **Account Number Mapping (Primary Rule):** The `bank_sub_acc_id` field in the payload maps exclusively to `BankAccounts.AccountNumber`. Use `select(BankAccount).where(BankAccount.AccountNumber == bank_sub_acc_id)`. If no match is found, return `404 Not Found`. Never fall back to matching by `AccountName` or `AccountID`.
- **UserID Resolution:** Take `UserID` exclusively from the matched `BankAccount` record. Never read or trust `user_id` from the payload.
- **Transaction Direction:** A positive `amount` in the payload maps to `Income`; a negative `amount` maps to `Expense`. The absolute value of `amount` is used for the transaction record.
- **Insufficient Funds on Webhook Expense:** If the resolved bank account has insufficient balance, the Webhook processor receives a `ValueError` from `transaction_service.add_expense()`. Map this to `HTTP 422 Unprocessable Entity` with `{"status": "INSUFFICIENT_FUNDS"}` — never `500`.
- **"Others" Fallback Categorization (MANDATORY):** Automated Webhook transactions must NEVER be assigned to an arbitrary first-available category. The category resolution logic must follow this strict two-tier fallback:
  1. **Primary:** Query the user's `Categories` table for a record matching `CategoryName = "Others"` AND the correct `Type` (Income or Expense). If found, use it.
  2. **Last-Resort Fallback:** If `"Others"` does not exist (e.g., legacy account before migration), fall back to the first available category of the correct type. Log a `WARNING` that the "Others" category was missing. This ensures no transaction is ever silently dropped.
  - The `SystemCategories` table must contain `"Others"` for both `Income` and `Expense` types. Because `InitializeUserCategories` clones from `SystemCategories`, all newly registered users will automatically receive both "Others" categories.
- **Delegation to `transaction_service`:** All commits must go through `add_income()` or `add_expense()` from `transaction_service.py` to ensure SQL triggers fire and validation is applied.
- **Webhook Payload Schema:**
  ```json
  {
    "bank_transaction_id": "string (required, unique — maps to ExternalTransID)",
    "amount":              "decimal (positive=income, negative=expense)",
    "description":         "string (optional)",
    "bank_sub_acc_id":     "string (required — maps to BankAccounts.AccountNumber)",
    "transaction_date":    "string (ISO 8601, e.g. 2026-04-27)"
  }
  ```

## 5. Saving Goals Service Rules
The `saving_service.py` module manages all Goal lifecycle operations. These rules are mandatory:

- **Reserved Category Auto-Resolution:** Saving Goal operations must NEVER ask the user to select a category. The service must automatically look up the reserved category by name from the user's own `Categories` table:
  - Contribute: look up `CategoryName = "Savings"`, `Type = "Expense"`.
  - Withdraw: look up `CategoryName = "Savings Withdraw"`, `Type = "Income"`.
  - If the reserved category is not found, raise a `ValueError` (do not silently fall back).
- **Contribute Flow (Deposit to Goal):**
  1. Validate `amount > 0`.
  2. Assert goal exists and is owned by `user_id`.
  3. Assert goal `Status == "Active"` (cannot contribute to a Completed goal without explicit reactivation).
  4. Resolve `Savings` (Expense) category from user's `Categories`.
  5. Call `add_expense()` from `transaction_service` → Python `_assert_sufficient_funds()` fires first → SQL `BEFORE INSERT` trigger fires → `BankAccounts.Balance` decreases.
  6. Increment `SavingGoals.CurrentAmount` by `amount`.
  7. If `CurrentAmount >= TargetAmount`, set `Status = "Completed"`.
  8. Commit within the same session.
- **Withdraw Flow (Return to Bank):**
  1. Validate `amount > 0`.
  2. Assert goal exists and is owned by `user_id`.
  3. Assert `amount <= CurrentAmount` (cannot withdraw more than the goal holds — no negative balances).
  4. Assert account ownership.
  5. Resolve `Savings Withdraw` (Income) category from user's `Categories`.
  6. Call `add_income()` from `transaction_service` → SQL trigger fires → `BankAccounts.Balance` increases.
  7. Decrement `SavingGoals.CurrentAmount` by `amount`.
  8. If `Status == "Completed"` and new `CurrentAmount < TargetAmount`, revert `Status = "Active"`.
  9. Commit within the same session.
- **Goal Ownership:** Every query for a `SavingGoal` must include `.where(SavingGoal.UserID == user_id)`.
- **Status Management:** Only the Python service may change `SavingGoals.Status` — never raw SQL or direct ORM mutation outside `saving_service.py`.

## 6. Strict Balance Integrity — Application Layer Rules (CRITICAL)
**No operation shall be allowed to result in `BankAccounts.Balance < 0`.** The following Python-level rules are mandatory:

- **`_assert_sufficient_funds(account: BankAccount, amount: Decimal)` — Mandatory Helper:**
  - Must exist in `transaction_service.py`.
  - Called inside `add_expense()` immediately after `_assert_account_ownership()` (which returns the live `BankAccount` object).
  - Logic: `if account.Balance < amount: raise ValueError(...)`.
  - Error message must be explicit: `"Insufficient funds: account {account_id} has balance {account.Balance}, but requested {amount}."`.
  - **Do NOT catch this `ValueError` in `add_expense()` — let it propagate** so callers (Webhook server, saving_service, frontend handlers) can map it to the appropriate user-facing message or HTTP response code.

- **Cascading Protection (Zero extra work):** Because `saving_service.contribute_to_goal()` and `bank_sync_service.process_webhook_payload()` both call `add_expense()`, adding the check once in `add_expense()` protects all expenditure paths automatically.

- **Webhook Mapping:** The Webhook server (`webhook_server.py`) must catch `ValueError` from `process_webhook_payload()` and map it to `HTTP 422 Unprocessable Entity` with `{"status": "INSUFFICIENT_FUNDS", "detail": <message>}` when the message contains "Insufficient funds".

- **Seed Data Safety:** The seed script generates expenses only after generating income. Because seed income amounts ($1,500–$8,000/month) significantly exceed seed expense amounts ($20–$1,200/month), the balance will remain positive throughout seeding. No changes to `seed.py` amounts are required — but the `BEFORE INSERT` trigger on Expenses must be present before running `seed.py` to validate this at the DB level.

## 7. API Data Handling and Formatting
- **Safe Error Propagation:** Database stack traces must **never** leak to the user. All SQLAlchemy exceptions (`IntegrityError`, `OperationalError`) must be enveloped in a standard `try-except` block and output a clean dictionary/JSON payload alongside logging the real error internally.
- **Data Validation:** Before passing data to the ORM session, perform business validation (e.g., verifying `Amount > 0`, `Balance >= Amount` directly in Python).
- **Webhook Response Contracts:**
  - `200 OK` — Successfully processed OR already processed (idempotent).
  - `400 Bad Request` — Invalid payload schema or failed validation.
  - `401 Unauthorized` — Missing or invalid `X-API-KEY`.
  - `404 Not Found` — `bank_sub_acc_id` does not match any `AccountNumber` in `BankAccounts`.
  - `422 Unprocessable Entity` — Expense rejected due to insufficient funds.
  - `500 Internal Server Error` — Unexpected failure (safe message only, never stack trace).
