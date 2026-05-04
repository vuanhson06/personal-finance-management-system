"""
app.py — Main Flask Application (API Bridge)
=============================================
This is the primary entry point for the Web Frontend to access backend logic.
It implements the 3-Layer Architecture by bridging REST API calls to the
existing Python services.

Features:
- Flask-Session for secure, server-side session management.
- Global Error Handler to map `ValueError("Insufficient funds...")` to HTTP 422.
- Blueprint registration for modular routing (auth, finance, goals, reports).
- Strict adherence to data isolation: `user_id` is ONLY retrieved from `session`.
"""

import logging
from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_session import Session

# Import Blueprints
from routes.auth import auth_bp
from routes.finance import finance_bp
from routes.goals import goals_bp
from routes.reports import reports_bp
from routes.budgets import budgets_bp
from routes.admin import admin_bp

# Set up global logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    # Point Flask to the frontend folders
    app = Flask(__name__, 
                template_folder="../frontend/templates", 
                static_folder="../frontend/static")
    
    # --- App Configuration ---
    # In a production environment, SECRET_KEY should be loaded from config/ENV.
    # For this architecture, we define it directly or fallback to a hardcoded string.
    app.config["SECRET_KEY"] = "super-secret-finance-key"
    
    # Configure Flask-Session (using filesystem for simplicity in this bridge)
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    Session(app)
    
    # --- Security: Prevent browser from caching sensitive pages ---
    @app.after_request
    def apply_no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # --- Blueprint Registration ---
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(finance_bp, url_prefix="/api")
    app.register_blueprint(goals_bp, url_prefix="/api/goals")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(budgets_bp, url_prefix="/api/budgets")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # --- UI Routes ---
    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login_page"))

    @app.route("/login")
    def login_page():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.route("/signup")
    def signup_page():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return render_template("signup.html")

    @app.route("/dashboard")
    def dashboard():
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        if session.get("view_mode") == "admin":
            return redirect(url_for("admin_page"))
        return render_template("dashboard.html")

    @app.route("/admin")
    def admin_page():
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        if session.get("view_mode") != "admin":
            return redirect(url_for("dashboard"))
        return render_template("admin.html")

    @app.route("/transactions")
    def transactions_page():
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return render_template("transactions.html")

    @app.route("/goals")
    def goals_page():
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return render_template("goals.html")

    @app.route("/sync")
    def sync_page():
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return render_template("sync.html")

    @app.route("/analytics")
    def analytics_page():
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return render_template("analytics.html")

    @app.route("/budgets")
    def budgets_page():
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return render_template("budgets.html")

    # --- Global Error Handlers ---
    @app.errorhandler(ValueError)
    def handle_value_error(e):
        """
        Global handler for business logic exceptions raised by services.
        Specifically maps Strict Balance Guard errors to HTTP 422.
        """
        msg = str(e)
        if "Insufficient funds" in msg:
            logger.warning(f"API Blocked: Insufficient funds. Detail: {msg}")
            return jsonify({"status": "error", "message": msg, "data": None}), 422
        
        # General business logic error
        logger.warning(f"API ValueError: {msg}")
        return jsonify({"status": "error", "message": msg, "data": None}), 400

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """
        Safety net for unexpected errors. Never leaks stack traces to the frontend.
        """
        logger.error(f"Unhandled Exception in API: {e}")
        return jsonify({
            "status": "error", 
            "message": "An internal server error occurred.", 
            "data": None
        }), 500

    # --- Health Check ---
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "success", "message": "API is running.", "data": None}), 200

    return app

if __name__ == "__main__":
    app = create_app()
    logger.info("Starting Flask API Bridge on http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
