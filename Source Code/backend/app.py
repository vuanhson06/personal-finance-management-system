import logging
from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_session import Session
from routes.auth import auth_bp
from routes.finance import finance_bp
from routes.goals import goals_bp
from routes.reports import reports_bp
from routes.budgets import budgets_bp
from routes.admin import admin_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    app = Flask(__name__, 
                template_folder="../frontend/templates", 
                static_folder="../frontend/static")
    
    app.config["SECRET_KEY"] = "super-secret-finance-key"
    
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    Session(app)
    
    @app.after_request
    def apply_no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(finance_bp, url_prefix="/api")
    app.register_blueprint(goals_bp, url_prefix="/api/goals")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(budgets_bp, url_prefix="/api/budgets")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

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

    @app.errorhandler(ValueError)
    def handle_value_error(e):
        msg = str(e)
        if "Insufficient funds" in msg:
            logger.warning(f"API Blocked: Insufficient funds. Detail: {msg}")
            return jsonify({"status": "error", "message": msg, "data": None}), 422
        
        logger.warning(f"API ValueError: {msg}")
        return jsonify({"status": "error", "message": msg, "data": None}), 400

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        logger.error(f"Unhandled Exception in API: {e}")
        return jsonify({
            "status": "error", 
            "message": "An internal server error occurred.", 
            "data": None
        }), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "success", "message": "API is running.", "data": None}), 200

    return app

if __name__ == "__main__":
    app = create_app()
    logger.info("Starting Flask API Bridge on http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
