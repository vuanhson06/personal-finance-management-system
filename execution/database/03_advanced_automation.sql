-- Part 1: SQL Database - Step 3
-- Advanced Automation Logic (Triggers & Stored Procedures)

USE personal_finance;

-- ==================================================
-- 1. INCOME TRIGGERS (Auto-adjust BankAccounts)
-- ==================================================

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

DELIMITER $$
CREATE TRIGGER After_Income_Update
AFTER UPDATE ON Income
FOR EACH ROW
BEGIN
    -- Handle changes if the transaction was moved between accounts
    IF OLD.AccountID != NEW.AccountID THEN
        UPDATE BankAccounts SET Balance = Balance - OLD.Amount WHERE AccountID = OLD.AccountID;
        UPDATE BankAccounts SET Balance = Balance + NEW.Amount WHERE AccountID = NEW.AccountID;
    ELSE
        -- Adjust the existing account balance difference
        UPDATE BankAccounts 
        SET Balance = Balance + (NEW.Amount - OLD.Amount) 
        WHERE AccountID = NEW.AccountID;
    END IF;
END$$
DELIMITER ;

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


-- ==================================================
-- 2. EXPENSES TRIGGERS (Auto-adjust BankAccounts)
-- ==================================================

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

DELIMITER $$
CREATE TRIGGER After_Expense_Update
AFTER UPDATE ON Expenses
FOR EACH ROW
BEGIN
    -- Handle changes if the transaction was moved between accounts
    IF OLD.AccountID != NEW.AccountID THEN
        UPDATE BankAccounts SET Balance = Balance + OLD.Amount WHERE AccountID = OLD.AccountID;
        UPDATE BankAccounts SET Balance = Balance - NEW.Amount WHERE AccountID = NEW.AccountID;
    ELSE
        -- Adjust the existing account balance difference
        UPDATE BankAccounts 
        SET Balance = Balance - (NEW.Amount - OLD.Amount) 
        WHERE AccountID = NEW.AccountID;
    END IF;
END$$
DELIMITER ;

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


-- ==================================================
-- 3. MONTHLY CLOSURES SYSTEM & STORED PROCEDURES
-- ==================================================

-- Create a robust Snapshot log table preventing double-logging in the same period
CREATE TABLE IF NOT EXISTS MonthlyClosures (
    ClosureID INT AUTO_INCREMENT PRIMARY KEY,
    AccountID INT NOT NULL,
    ClosurePeriod VARCHAR(7) NOT NULL, -- Format: YYYY-MM
    ClosingBalance DECIMAL(15,2) NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (AccountID) REFERENCES BankAccounts(AccountID) ON DELETE CASCADE,
    UNIQUE KEY unique_account_period (AccountID, ClosurePeriod) 
);

DELIMITER $$
CREATE PROCEDURE CalculateMonthlyClosure(IN p_UserID INT, IN p_Period VARCHAR(7))
BEGIN
    -- Grabs real-time balance of all accounts matching user,
    -- locks the value in the MonthlyClosures snapshot table.
    -- Updates the balance record if run twice in the same month.
    
    INSERT INTO MonthlyClosures (AccountID, ClosurePeriod, ClosingBalance)
    SELECT AccountID, p_Period, Balance
    FROM BankAccounts
    WHERE UserID = p_UserID
    ON DUPLICATE KEY UPDATE ClosingBalance = VALUES(ClosingBalance);
END$$
DELIMITER ;
