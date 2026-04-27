# Project Plan: Professional Personal Finance Management System

## Project Environment & Tech Stack
- **OS Platform:** Windows / Cross-platform
- **Python Version:** 3.13.11 (Strictly enforced)
- **Database:** MySQL Server (8.0+)
- **ORM:** SQLAlchemy 2.0+
- **Frontend UI:** CustomTkinter (Modern UI library for Python)
- **Key Libraries:** - `bcrypt` (Security)
    - `faker` (Data Seeding)
    - `yfinance` (Market Data)
    - `matplotlib` / `customtkinter-charts` (Visual Analytics)
    - `python-dotenv` (Environment Variables)

---

## Part 1: SQL Database (The Foundation)
*Focus: Data integrity, security, and automated financial logic.*

### Step 1: User & Security Schema
- Create `Users` table: `UserID` (PK), `UserName`, `Email` (Unique Index), PhoneNumber (Unique), `PasswordHash`, `Role` (Enum: Admin/User).
- Implement security constraints to ensure account integrity.

### Step 2: Financial Core Implementation
- Define tables: `BankAccounts`, `Income`, `Expenses`, `Categories`, `Budgets`, `MarketWatch`.
- Set up Primary/Foreign Key relationships (All tables must link to `Users.UserID`). Additionally, `Income` and `Expenses` **must link to `BankAccounts.AccountID`** to track which account the funds are moving from/to.
- Implement a System Template mechanism: Create SystemCategories as a master template and ensure the main Categories table is strictly user-owned (UserID NOT NULL).
- This structure allows every user to have a private copy of categories, enabling full individual customization or deletion without affecting the system defaults.

### Step 3: Advanced Automation Logic
- **Triggers:** Automate `BankAccounts.Balance` updates on every Income/Expense entry.
- **Stored Procedures:** Create `MonthlyClosure` to calculate end-of-month balances.
- User Provisioning Logic: Create a Stored Procedure InitializeUserCategories to copy default tags from the system template to new users.
- Automation Trigger: Implement the After_User_Insert trigger on the Users table to automatically fire the initialization procedure upon registration.

### Step 4: Reporting & Analytics Layer
- **SQL Views:** Create views for "Category-wise Spending" and "Monthly Summaries".
- **UDFs:** Write functions for "Total Savings" and "Current Budget Status".

### Step 5: Performance & Data Integrity
- Implement Application-level Data Isolation (Ensure SQL queries always include `WHERE UserID = current_user` to prevent cross-user data access).
- Optimize indexes for reporting queries and establish database backup/restore scripts.
- Establish Role-based data access logic (e.g., Admins can manage global categories, Users manage personal data).

---

## Part 2: Backend (The Brain)
*Focus: Bridging the database to the interface using modern Python logic.*

### Step 1: Connectivity & Security Setup
- Configure SQLAlchemy engine with connection pooling and basic error handling for MySQL connection.
- Implement `.env` file management for DB credentials and API keys.

### Step 2: ORM Data Modeling
- Define Python classes (Models) for all SQL tables, including new fields for PhoneNumber and Role.
- Integrate bcrypt logic within the User model and implement role verification methods.

### Step 3: Data Simulation (100 Records)
- Develop seed.py using Faker to generate 100 realistic transactions and valid synthetic phone numbers for user profiles.
- Ensure data spans the last 12 months for trend analysis.

### Step 4: Market Data Integration
- Build a service using `yfinance` to fetch live prices (Stock, Gold, Crypto).
- Implement basic caching to avoid API rate limits.

### Step 5: Logic Engine Development
- Build core scripts for transaction CRUD, categorization, and balance tracking.
- Develop "Bank Sync Simulation" function.

---

## Part 3: Frontend Python App (The Interface)
*Focus: Modern UI using CustomTkinter for user interaction.*

### Step 1: Authentication & Access Portal
- Build Login and Sign-up screens with fields for Email, PhoneNumber, and Password. (CustomTkinter frames).
- Implement User Profile Management interface.
- Implement Conditional Rendering based on user roles (e.g., hide/show administrative tools based on the Role column).

### Step 2: Primary Financial Dashboard
- High-level overview: Total Balance, Month Spending (Large Labels/Cards).
- Real-time Market Ticker (Horizontal scrolling or auto-updating list).

### Step 3: Transaction & Budget Manager
- Interactive forms for adding/editing transactions.
- Budget Planning UI: Set limits per category.

### Step 4: Visual Reporting System
- **Graphical Reports:** Integrate Matplotlib charts into CustomTkinter frames using `FigureCanvasTkAgg` (Pie/Line charts).
- **Tabular Summaries:** Searchable and filterable table widgets to display daily, monthly, and yearly financial activities.

### Step 5: Alerting & Notification System
- Logic to monitor spending vs. budget in real-time.
- **Visual Alerts:** Progress bars that turn RED when spending > 80% of budget.

---
