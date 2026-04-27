-- Part 1: SQL Database - Step 4
-- Reporting & Analytics Layer

USE personal_finance;

-- ==================================================
-- 1. SQL VIEWS
-- ==================================================

-- View: vw_CategoryWiseSpending
-- Aggregates spending by Category, User, and Month.
CREATE OR REPLACE VIEW vw_CategoryWiseSpending AS
SELECT 
    e.UserID,
    c.CategoryName,
    DATE_FORMAT(e.TransactionDate, '%Y-%m') AS SpendMonth,
    SUM(e.Amount) AS TotalSpent
FROM Expenses e
JOIN Categories c ON e.CategoryID = c.CategoryID
GROUP BY e.UserID, c.CategoryName, SpendMonth;


-- View: vw_MonthlySummaries
-- Aggregates total Cash Flow per user per month using a simulated FULL OUTER JOIN.
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


-- ==================================================
-- 2. USER-DEFINED FUNCTIONS (UDFs)
-- ==================================================

DELIMITER $$

-- UDF: GetTotalSavings
-- Scans all BankAccounts for a user and returns cumulative total balance.
CREATE FUNCTION GetTotalSavings(p_UserID INT) 
RETURNS DECIMAL(15,2)
READS SQL DATA
BEGIN
    DECLARE total DECIMAL(15,2);
    SELECT SUM(Balance) INTO total FROM BankAccounts WHERE UserID = p_UserID;
    RETURN COALESCE(total, 0.00);
END$$


-- UDF: GetBudgetStatus
-- Evaluates actual spending against the preset Budgets limit.
-- Returns the REMAINING budget. (Negative = Over Budget).
CREATE FUNCTION GetBudgetStatus(p_UserID INT, p_CategoryID INT, p_Period VARCHAR(7)) 
RETURNS DECIMAL(15,2)
READS SQL DATA
BEGIN
    DECLARE current_spent DECIMAL(15,2);
    DECLARE budget_limit DECIMAL(15,2);
    
    -- Extract the budget limit defined by user for that category and month
    SELECT LimitAmount INTO budget_limit 
    FROM Budgets 
    WHERE UserID = p_UserID AND CategoryID = p_CategoryID AND Period = p_Period;
    
    -- If no budget limit exists, return 0 or NULL to handle it gracefully in the app
    IF budget_limit IS NULL THEN
        RETURN 0.00;
    END IF;
    
    -- Extract what was actually actively spent in that month
    SELECT SUM(Amount) INTO current_spent 
    FROM Expenses 
    WHERE UserID = p_UserID 
      AND CategoryID = p_CategoryID 
      AND DATE_FORMAT(TransactionDate, '%Y-%m') = p_Period;
      
    RETURN budget_limit - COALESCE(current_spent, 0);
END$$

DELIMITER ;
