# Frontend Architecture & Data Flow Directive
**Layer 1: Standard Operating Procedures**

## 1. Separation of Concerns
The frontend must strictly adhere to a decoupled architecture despite being served by Flask. 
- **Flask (Jinja2):** Responsible *only* for rendering the base HTML layout, injecting session-based `user_id`, and initial scaffolding.
- **REST API (`/api/*`):** Handles all business logic, database queries, and data mutations.
- **Client-Side JS (Fetch API):** Responsible for submitting form data, fetching dynamic content, and updating the DOM asynchronously.

## 2. API Communication Rules
- All API interactions MUST use the native JS `fetch()` API.
- Headers MUST include `Content-Type: application/json`.
- Standardized Response Parsing: Every endpoint returns `{"status": "...", "message": "...", "data": ...}`.
- Do NOT perform page reloads for CRUD operations; update the UI state dynamically.

## 3. Error Handling & Notifications (SweetAlert2)
- Do not use native `alert()` or `confirm()`.
- Bind global fetch error handlers to SweetAlert2 modals.
- **HTTP 422 (Insufficient Funds):** Specifically catch HTTP 422 errors and trigger a SweetAlert2 `warning` or `error` modal displaying the "message" field returned by the API.

## 4. Chart.js Integration
- Charts should reside in their own isolated JS modules/functions.
- Data must be fetched via endpoints (e.g., `/api/reports/monthly-trend`) asynchronously.
- Use CSS variables from the Neumorphism UI Paper System to colorize chart datasets to maintain visual consistency.

## 5. Security
- Never expose the user's raw password or sensitive tokens in JS.
- Rely on Flask-Session cookies for API authentication.
- All forms must be sanitized before submission, though the backend is the ultimate authority on validation.
