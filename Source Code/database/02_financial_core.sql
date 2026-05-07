-- Part 1: SQL Database - Step 2
-- Financial Core Implementation

USE personal_finance;

-- BankAccounts Table
CREATE TABLE IF NOT EXISTS BankAccounts (
    AccountID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    AccountName VARCHAR(100) NOT NULL,
    Balance DECIMAL(15,2) DEFAULT 0.00,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

-- Categories Table
-- UserID is NULL for global/system categories, allowing users to inherit them.
CREATE TABLE IF NOT EXISTS Categories (
    CategoryID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NULL,
    CategoryName VARCHAR(100) NOT NULL,
    Type ENUM('Income', 'Expense') NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

-- Budgets Table
CREATE TABLE IF NOT EXISTS Budgets (
    BudgetID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    CategoryID INT NOT NULL,
    LimitAmount DECIMAL(15,2) NOT NULL,
    Period VARCHAR(7) NOT NULL, -- Format: YYYY-MM
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE CASCADE
);

-- MarketWatch Table
CREATE TABLE IF NOT EXISTS MarketWatch (
    WatchID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    AssetSymbol VARCHAR(20) NOT NULL,
    AssetType VARCHAR(50), -- e.g., 'Stock', 'Crypto', 'Gold'
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

-- Income Table
CREATE TABLE IF NOT EXISTS Income (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    AccountID INT NOT NULL,
    CategoryID INT NOT NULL,
    Amount DECIMAL(15,2) NOT NULL CHECK (Amount > 0),
    TransactionDate DATE NOT NULL,
    Description TEXT,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (AccountID) REFERENCES BankAccounts(AccountID) ON DELETE CASCADE,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE CASCADE
);

-- Expenses Table
CREATE TABLE IF NOT EXISTS Expenses (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    AccountID INT NOT NULL,
    CategoryID INT NOT NULL,
    Amount DECIMAL(15,2) NOT NULL CHECK (Amount > 0),
    TransactionDate DATE NOT NULL,
    Description TEXT,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (AccountID) REFERENCES BankAccounts(AccountID) ON DELETE CASCADE,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE CASCADE
);

-- Seeding Default Global Categories
INSERT INTO Categories (UserID, CategoryName, Type) VALUES
(NULL, 'Salary', 'Income'),
(NULL, 'Bonus', 'Income'),
(NULL, 'Investment', 'Income'),
(NULL, 'Housing', 'Expense'),
(NULL, 'Utilities', 'Expense'),
(NULL, 'Food & Dining', 'Expense'),
(NULL, 'Transportation', 'Expense'),
(NULL, 'Health', 'Expense'),
(NULL, 'Education', 'Expense'),
(NULL, 'Entertainment', 'Expense'),
(NULL, 'Shopping', 'Expense'),
(NULL, 'Debt', 'Expense'),
(NULL, 'Savings', 'Expense');
