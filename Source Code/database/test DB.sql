USE personal_finance;
SHOW TABLES;
select * from Users;
DESCRIBE Expenses;
select * from MonthlyClosures;

SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'personal_finance' AND REFERENCED_TABLE_NAME IS NOT NULL;

-- Lệnh này PHẢI báo lỗi "Foreign key constraint fails"
INSERT INTO Expenses (UserID, AccountID, CategoryID, Amount, TransactionDate) 
VALUES (9999, 1, 1, 500, CURDATE());

-- 1. Tạo 1 User test
INSERT INTO Users (UserName, Email, PasswordHash) VALUES ('Tester', 'clean@test.com', '123');
SET @test_user = LAST_INSERT_ID();

-- 2. Tạo 1 tài khoản và 1 khoản chi cho User đó
INSERT INTO BankAccounts (UserID, AccountName, Balance) VALUES (@test_user, 'Ví Test', 1000);
SET @test_acc = LAST_INSERT_ID();

INSERT INTO Expenses (UserID, AccountID, CategoryID, Amount, TransactionDate) 
VALUES (@test_user, @test_acc, 6, 100, CURDATE());

DELETE FROM Users WHERE UserID = @test_user;

SELECT 'BankAccounts' as TableName, COUNT(*) FROM BankAccounts WHERE UserID = @test_user
UNION ALL
SELECT 'Expenses', COUNT(*) FROM Expenses WHERE UserID = @test_user;

SELECT * FROM vw_categorywisespending;

SHOW INDEX FROM Expenses;
INSERT INTO Expenses (Amount) VALUES (-100);

SELECT * FROM Categories WHERE Type = 'Income';  SELECT * FROM Categories WHERE Type = 'Expense';
INSERT INTO Categories (CategoryName, Type) VALUES ('Linh tinh', 'Loan');

DESCRIBE MarketWatch;

INSERT INTO Users (UserName) VALUES ('Kẻ trộm');
select * from Users;
TRUNCATE TABLE Users;

DROP TABLES Expenses;











