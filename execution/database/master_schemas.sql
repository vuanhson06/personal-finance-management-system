DROP DATABASE IF EXISTS personal_finance;
CREATE DATABASE personal_finance;
USE personal_finance;

CREATE TABLE IF NOT EXISTS Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    UserName VARCHAR(100) NOT NULL,
    Email VARCHAR(255) NOT NULL UNIQUE,
    PhoneNumber VARCHAR(15) UNIQUE,
    PasswordHash VARCHAR(255) NOT NULL,
    Role ENUM('Admin', 'User') DEFAULT 'User',
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS BankAccounts (
    AccountID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    AccountName VARCHAR(100) NOT NULL,
    Balance DECIMAL(15,2) DEFAULT 0.00,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS SystemCategories (
    SystemCatID INT AUTO_INCREMENT PRIMARY KEY,
    CategoryName VARCHAR(100) NOT NULL,
    Type ENUM('Income', 'Expense') NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Categories (
    CategoryID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    CategoryName VARCHAR(100) NOT NULL,
    Type ENUM('Income', 'Expense') NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Budgets (
    BudgetID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    CategoryID INT NOT NULL,
    LimitAmount DECIMAL(15,2) NOT NULL,
    Period VARCHAR(7) NOT NULL, 
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS MarketWatch (
    WatchID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    AssetSymbol VARCHAR(20) NOT NULL,
    AssetType VARCHAR(50), 
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

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

INSERT INTO SystemCategories (CategoryName, Type) VALUES
('Salary', 'Income'),
('Bonus', 'Income'),
('Investment', 'Income'),
('Housing', 'Expense'),
('Utilities', 'Expense'),
('Food & Dining', 'Expense'),
('Transportation', 'Expense'),
('Health', 'Expense'),
('Education', 'Expense'),
('Entertainment', 'Expense'),
('Shopping', 'Expense'),
('Debt', 'Expense'),
('Savings', 'Expense');

DELIMITER $$
CREATE PROCEDURE InitializeUserCategories(IN p_UserID INT)
BEGIN
    INSERT INTO Categories (UserID, CategoryName, Type)
    SELECT p_UserID, CategoryName, Type FROM SystemCategories;
END$$

DROP TRIGGER IF EXISTS After_User_Insert$$
CREATE TRIGGER After_User_Insert
AFTER INSERT ON Users
FOR EACH ROW
BEGIN
    CALL InitializeUserCategories(NEW.UserID);
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS After_Income_Insert;
DELIMITER $$
CREATE TRIGGER After_Income_Insert
AFTER INSERT ON Income
FOR EACH ROW
BEGIN
    UPDATE BankAccounts 
    SET Balance = Balance + NEW.Amount 
    WHERE AccountID = NEW.AccountID;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS After_Income_Update;
DELIMITER $$
CREATE TRIGGER After_Income_Update
AFTER UPDATE ON Income
FOR EACH ROW
BEGIN
    IF OLD.AccountID != NEW.AccountID THEN
        UPDATE BankAccounts SET Balance = Balance - OLD.Amount WHERE AccountID = OLD.AccountID;
        UPDATE BankAccounts SET Balance = Balance + NEW.Amount WHERE AccountID = NEW.AccountID;
    ELSE
        UPDATE BankAccounts 
        SET Balance = Balance + (NEW.Amount - OLD.Amount) 
        WHERE AccountID = NEW.AccountID;
    END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS After_Income_Delete;
DELIMITER $$
CREATE TRIGGER After_Income_Delete
AFTER DELETE ON Income
FOR EACH ROW
BEGIN
    UPDATE BankAccounts 
    SET Balance = Balance - OLD.Amount 
    WHERE AccountID = OLD.AccountID;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS After_Expense_Insert;
DELIMITER $$
CREATE TRIGGER After_Expense_Insert
AFTER INSERT ON Expenses
FOR EACH ROW
BEGIN
    UPDATE BankAccounts 
    SET Balance = Balance - NEW.Amount 
    WHERE AccountID = NEW.AccountID;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS After_Expense_Update;
DELIMITER $$
CREATE TRIGGER After_Expense_Update
AFTER UPDATE ON Expenses
FOR EACH ROW
BEGIN
    IF OLD.AccountID != NEW.AccountID THEN
        UPDATE BankAccounts SET Balance = Balance + OLD.Amount WHERE AccountID = OLD.AccountID;
        UPDATE BankAccounts SET Balance = Balance - NEW.Amount WHERE AccountID = NEW.AccountID;
    ELSE
        UPDATE BankAccounts 
        SET Balance = Balance - (NEW.Amount - OLD.Amount) 
        WHERE AccountID = NEW.AccountID;
    END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS After_Expense_Delete;
DELIMITER $$
CREATE TRIGGER After_Expense_Delete
AFTER DELETE ON Expenses
FOR EACH ROW
BEGIN
    UPDATE BankAccounts 
    SET Balance = Balance + OLD.Amount 
    WHERE AccountID = OLD.AccountID;
END$$
DELIMITER ;

CREATE TABLE IF NOT EXISTS MonthlyClosures (
    ClosureID INT AUTO_INCREMENT PRIMARY KEY,
    AccountID INT NOT NULL,
    ClosurePeriod VARCHAR(7) NOT NULL, 
    ClosingBalance DECIMAL(15,2) NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (AccountID) REFERENCES BankAccounts(AccountID) ON DELETE CASCADE,
    UNIQUE KEY unique_account_period (AccountID, ClosurePeriod) 
);

DELIMITER $$
CREATE PROCEDURE CalculateMonthlyClosure(IN p_UserID INT, IN p_Period VARCHAR(7))
BEGIN
    INSERT INTO MonthlyClosures (AccountID, ClosurePeriod, ClosingBalance)
    SELECT AccountID, p_Period, Balance
    FROM BankAccounts
    WHERE UserID = p_UserID
    ON DUPLICATE KEY UPDATE ClosingBalance = VALUES(ClosingBalance);
END$$
DELIMITER ;

CREATE OR REPLACE VIEW vw_CategoryWiseSpending AS
SELECT 
    e.UserID,
    c.CategoryName,
    DATE_FORMAT(e.TransactionDate, '%Y-%m') AS SpendMonth,
    SUM(e.Amount) AS TotalSpent
FROM Expenses e
JOIN Categories c ON e.CategoryID = c.CategoryID
GROUP BY e.UserID, c.CategoryName, SpendMonth;


CREATE OR REPLACE VIEW vw_MonthlySummaries AS
SELECT 
    COALESCE(i.UserID, e.UserID) AS UserID,
    COALESCE(i.TransMonth, e.TransMonth) AS SummaryMonth,
    COALESCE(i.TotalIncome, 0) AS TotalIncome,
    COALESCE(e.TotalExpense, 0) AS TotalExpense,
    (COALESCE(i.TotalIncome, 0) - COALESCE(e.TotalExpense, 0)) AS NetCashFlow
FROM 
    (SELECT UserID, DATE_FORMAT(TransactionDate, '%Y-%m') AS TransMonth, SUM(Amount) AS TotalIncome 
     FROM Income GROUP BY UserID, TransMonth) i
LEFT JOIN 
    (SELECT UserID, DATE_FORMAT(TransactionDate, '%Y-%m') AS TransMonth, SUM(Amount) AS TotalExpense 
     FROM Expenses GROUP BY UserID, TransMonth) e 
ON i.UserID = e.UserID AND i.TransMonth = e.TransMonth
UNION
SELECT 
    COALESCE(i.UserID, e.UserID) AS UserID,
    COALESCE(i.TransMonth, e.TransMonth) AS SummaryMonth,
    COALESCE(i.TotalIncome, 0) AS TotalIncome,
    COALESCE(e.TotalExpense, 0) AS TotalExpense,
    (COALESCE(i.TotalIncome, 0) - COALESCE(e.TotalExpense, 0)) AS NetCashFlow
FROM 
    (SELECT UserID, DATE_FORMAT(TransactionDate, '%Y-%m') AS TransMonth, SUM(Amount) AS TotalIncome 
     FROM Income GROUP BY UserID, TransMonth) i
RIGHT JOIN 
    (SELECT UserID, DATE_FORMAT(TransactionDate, '%Y-%m') AS TransMonth, SUM(Amount) AS TotalExpense 
     FROM Expenses GROUP BY UserID, TransMonth) e 
ON i.UserID = e.UserID AND i.TransMonth = e.TransMonth;


DELIMITER $$

CREATE FUNCTION GetTotalSavings(p_UserID INT) 
RETURNS DECIMAL(15,2)
READS SQL DATA
BEGIN
    DECLARE total DECIMAL(15,2);
    SELECT SUM(Balance) INTO total FROM BankAccounts WHERE UserID = p_UserID;
    RETURN COALESCE(total, 0.00);
END$$


CREATE FUNCTION GetBudgetStatus(p_UserID INT, p_CategoryID INT, p_Period VARCHAR(7)) 
RETURNS DECIMAL(15,2)
READS SQL DATA
BEGIN
    DECLARE current_spent DECIMAL(15,2);
    DECLARE budget_limit DECIMAL(15,2);
    
    SELECT LimitAmount INTO budget_limit 
    FROM Budgets 
    WHERE UserID = p_UserID AND CategoryID = p_CategoryID AND Period = p_Period;
    
    IF budget_limit IS NULL THEN
        RETURN 0.00;
    END IF;
    

    SELECT SUM(Amount) INTO current_spent 
    FROM Expenses 
    WHERE UserID = p_UserID 
      AND CategoryID = p_CategoryID 
      AND DATE_FORMAT(TransactionDate, '%Y-%m') = p_Period;
      
    RETURN budget_limit - COALESCE(current_spent, 0);
END$$

DELIMITER ;

CREATE INDEX  idx_income_user_date ON Income (UserID, TransactionDate);

CREATE INDEX  idx_expense_user_cat_date ON Expenses (UserID, CategoryID, TransactionDate);

CREATE INDEX  idx_budgets_user_cat_period ON Budgets (UserID, CategoryID, Period);