-- Part 1: SQL Database - Step 5
-- Performance Optimization & Indexes

USE personal_finance;

-- INDEX: Optimize Income Reporting (Used heavily in views and queries)
CREATE INDEX IF NOT EXISTS idx_income_user_date ON Income (UserID, TransactionDate);

-- INDEX: Optimize Expense Reporting (Used in Category-wise tracking and Budget matching)
CREATE INDEX IF NOT EXISTS idx_expense_user_cat_date ON Expenses (UserID, CategoryID, TransactionDate);

-- INDEX: Optimize Budget Status lookup (Speeds up checking limits by User, Category, and Period)
CREATE INDEX IF NOT EXISTS idx_budgets_user_cat_period ON Budgets (UserID, CategoryID, Period);
