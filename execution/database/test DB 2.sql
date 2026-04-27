USE personal_finance;

SHOW tables;

SELECT COUNT(*) FROM Users;

SELECT UserID, COUNT(*) FROM Categories GROUP BY UserID;

SELECT YEAR(TransactionDate), MONTH(TransactionDate), COUNT(*) 
FROM Expenses 
GROUP BY YEAR(TransactionDate), MONTH(TransactionDate)
ORDER BY 1, 2;

SELECT AccountName, Balance FROM BankAccounts;

select * from Users;

select * from marketwatch;