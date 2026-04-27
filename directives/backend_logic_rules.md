# Backend Logic Directives (Python & SQLAlchemy)

## 1. ORM Modeling & Structure
- **Model Reflection:** Python SQLAlchemy classes must perfectly mirror the updated `master_schemas.sql` tables (`Users`, `BankAccounts`, `SystemCategories`, `Categories`, `Budgets`, `MarketWatch`, `Income`, `Expenses`, `MonthlyClosures`).
- **Data Types:** Ensure `User.PhoneNumber` and `User.Role` are mapped correctly. Consider using Python `Enum` for the Role column.

## 2. Application-Level Data Isolation (CRITICAL)
To strictly enforce secure data isolation across different users sharing the database, the backend application must strictly adhere to these directives:
- **Mandatory User Context:** Every SQLAlchemy API request (read, write, update, or delete) must dynamically resolve the authenticated user, known as `current_user`.
- **The Golden Rule of Querying:** Under absolutely no circumstances should a generic `Session.query(Model).all()` be executed without a filter. **ALL data-fetching queries (except for `SystemCategories`) must imperatively append `.filter(Model.UserID == current_user.id)`**.
- **Foreign Key Logic Verification:** Even when mutating a sub-layer (e.g., updating an `Expense` tied to a `BankAccounts.AccountID`), the Python logic must actively assert that the `AccountID` is genuinely owned by the `current_user`.
- **Registration Flow:** Provide the database the required `Email`, `PhoneNumber`, and `PasswordHash`. The backend doesn't need to manually create the initial `Categories` since the SQL `After_User_Insert` trigger handles it.

## 3. Role-Based Access Control
- **User Roles:** Implement logic to distinguish between `'Admin'` and `'User'` roles. 
- **Administrative Privileges:** Only `Admin` users should be permitted to insert, update, or delete records in the `SystemCategories` table. Standard users only interact with their personal `Categories` table.

## 4. API Data Handling and Formatting
- **Safe Error Propagation:** Database stack traces must **never** leak to the user. All SQLAlchemy exceptions (`IntegrityError`, `OperationalError`) must be enveloped in a standard `try-except` block and output a clean dictionary/JSON payload alongside logging the real error internally.
- **Data Validation:** Before passing data to the ORM session, perform business validation (e.g., verifying `Amount > 0` directly in Python).
