@echo off
echo ==========================================
echo Restoring 'personal_finance' Backup
echo ==========================================

REM Ensure mysql is available in your PATH
mysql -u root -p personal_finance < backup_personal_finance.sql

if %errorlevel% neq 0 (
    echo [ERROR] Restore failed. Check credentials and SQL file.
) else (
    echo [SUCCESS] Database Restored from backup_personal_finance.sql
)

pause
