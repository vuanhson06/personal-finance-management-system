@echo off
echo ==========================================
echo Starting Backup of 'personal_finance' 
echo ==========================================

REM Ensure mysqldump is available in your PATH
mysqldump -u root -p personal_finance > backup_personal_finance.sql

if %errorlevel% neq 0 (
    echo [ERROR] Backup failed. Check credentials and path.
) else (
    echo [SUCCESS] Database backed up to backup_personal_finance.sql
)

pause
