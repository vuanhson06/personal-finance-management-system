# Database Directives (MySQL + SQLAlchemy)

## 1. Schema & Structure
- **Core Entities:** `Users`, `BankAccounts`, `SystemCategories`, `Categories`, `Budgets`, `MarketWatch`, `Income`, `Expenses`, `MonthlyClosures`.
- **Users Table Constraints:** `UserID` (PK), `UserName`, `Email` (Unique), `PhoneNumber` (Unique), `PasswordHash`, and `Role` (Enum: 'Admin', 'User').
- **Relationships:** Strict Primary and Foreign Keys. All financial tables (`BankAccounts`, `Categories`, `Budgets`, `MarketWatch`, `Income`, `Expenses`) must strictly link to `Users(UserID)`. Additionally, `Income` and `Expenses` must link to `BankAccounts(AccountID)` to track fund movements.
- **Category Template System:** The `SystemCategories` table holds default system tags. The `Categories` table is strictly user-owned (`UserID` NOT NULL), allowing each user private manipulation without affecting defaults.

## 2. Automation Logic (SQL Layer)
- **User Provisioning:** An `After_User_Insert` trigger auto-fires the `InitializeUserCategories` stored procedure to populate new user accounts with default tags from `SystemCategories`.
- **Balance Auto-Synchronization:** `AFTER INSERT`, `AFTER UPDATE`, and `AFTER DELETE` triggers on both `Income` and `Expenses` tables automatically keep `BankAccounts.Balance` perfectly synchronized.
- **Monthly Closures:** A stored procedure `CalculateMonthlyClosure` is used to compute and store historical end-of-month balances in the `MonthlyClosures` table.
- **SQL Views & Functions:** `vw_CategoryWiseSpending` and `vw_MonthlySummaries` handle rapid reporting. `GetTotalSavings` and `GetBudgetStatus` User-Defined Functions handle complex aggregations at the database level.

## 3. Data Integrity and Validation
- **Database Constraints:** Rely on `CHECK (Amount > 0)` and `ON DELETE CASCADE` relationships natively in the schema.
- All financial transactions must pass through hard validation logic (e.g., amount > 0, logical date ranges) before hitting the ORM.
- **NEVER** perform an `UPDATE` or `DELETE` without verifying data constraints and ownership explicitly.
- Use `try-except` blocks around **all** database connection and query attempts to catch `IntegrityError`s.

## 4. Security Protocols
- **ORMs Only:** Must strictly use SQLAlchemy ORM 2.0+ for all interactions to prevent SQL injection.
- **Password Hashes:** Never store plain text passwords. `bcrypt` must be used for hashing prior to insertion.
- **Access Controls & Scope:** Enforce role-based behavior. Admins manage `SystemCategories`, while standard Users can only interact with their own data scoped by `UserID`.
- **Environment Parity:** `DB_URL` and API keys must unconditionally actively load from a `.env` file using `python-dotenv`.

## 5. Coding & Formatting Standards
- **PEP 8:** Follow standard Python style guidelines.
- **Type Hints:** Mandatory for every function and ORM model.
- **Docstrings:** All logic and ORM classes must include standard documentation explaining their financial logic.
