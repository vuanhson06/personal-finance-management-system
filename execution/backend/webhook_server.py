"""
webhook_server.py — Flask Webhook Endpoint Server
==================================================
Exposes a single HTTP POST endpoint that receives structured JSON payloads
representing external bank transactions and routes them to the processing
logic in `bank_sync_service.process_webhook_payload()`.

Endpoint:
    POST /webhook/transaction

Security:
    - Every request must include the header `X-API-KEY`.
    - The value is compared against `settings.webhook_api_key` (loaded
      from `.env`). Missing or invalid keys return 401 Unauthorized.
    - Stack traces NEVER appear in HTTP responses — all exceptions are
      caught and converted to safe JSON error messages.

Usage (development):
    cd execution/backend
    python webhook_server.py

Test with curl:
    curl -X POST http://localhost:5050/webhook/transaction \\
         -H "Content-Type: application/json" \\
         -H "X-API-KEY: change_this_to_a_strong_random_secret" \\
         -d '{
               "bank_transaction_id": "TXN-2026-001",
               "amount": 1500.00,
               "description": "Payroll deposit",
               "bank_sub_acc_id": "Checking Account",
               "transaction_date": "2026-04-27"
             }'

Directive Reference:
    - directives/backend_logic_rules.md — Section 4 (Webhook Rules),
                                          Section 5 (API Data Handling)
    - directives/db_rules.md           — Section 5 (Security Protocols)
"""

import logging

from flask import Flask, Response, jsonify, request
from sqlalchemy.orm import Session

from bank_sync_service import process_webhook_payload
from config import settings
from database import SessionLocal
from models import WebhookLog

# =============================================================================
# Application Setup
# =============================================================================

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Authentication Helper
# =============================================================================

def _authenticate_request() -> bool:
    """
    Validates the `X-API-KEY` header against the configured secret.

    Compares using equality (constant-time comparison not required here as
    the key is already a long random string with sufficient entropy).

    Returns:
        True if the API key is present and matches. False otherwise.
    """
    provided_key: str = request.headers.get("X-API-KEY", "")
    return provided_key == settings.webhook_api_key


# =============================================================================
# Step W.4 — Webhook Endpoint
# =============================================================================

@app.route("/webhook/transaction", methods=["POST"])
def receive_transaction() -> tuple[Response, int]:
    """
    Receives a bank transaction JSON payload and processes it.

    Workflow:
        1. Validate `X-API-KEY` header → 401 if invalid.
        2. Parse JSON body            → 400 if malformed.
        3. Delegate to service        → process_webhook_payload().
        4. Map service response code  → HTTP status.
        5. Insufficient funds error   → 422 INSUFFICIENT_FUNDS.
        6. Guard with outer try-except → 500 on unexpected failure.

    Returns:
        A Flask JSON response tuple: (response_body, http_status_code).
    """
    # --- Step 1: Authentication ---
    if not _authenticate_request():
        logger.warning(
            "Unauthorized webhook request from %s — invalid or missing X-API-KEY.",
            request.remote_addr,
        )
        return jsonify({"error": "Unauthorized", "detail": "Invalid or missing X-API-KEY."}), 401

    # --- Step 2: JSON Parsing ---
    try:
        payload: dict = request.get_json(force=True, silent=False)
        if payload is None:
            raise ValueError("Request body is empty or not valid JSON.")
    except Exception:
        return jsonify({"error": "Bad Request", "detail": "Request body must be valid JSON."}), 400

    logger.info(
        "Webhook received: bank_transaction_id='%s' from %s.",
        payload.get("bank_transaction_id", "<missing>"),
        request.remote_addr,
    )

    # --- Step 3 & 4: Delegate to service, map response code to HTTP status ---
    db: Session = SessionLocal()
    
    try:
        result: dict = process_webhook_payload(payload, db)
        http_code: int = result.get("code", 200)

        # Log to DB (Dedicated block to prevent silent logging failures)
        try:
            log_entry = WebhookLog(
                ExternalTransID=payload.get("bank_transaction_id"),
                Status=result.get("status", "SUCCESS"),
                StatusCode=http_code,
                Detail=result.get("message") or result.get("detail")
            )
            db.add(log_entry)
            db.commit()
            logger.info("✅ WebhookLog persisted for TXN: %s", payload.get("bank_transaction_id"))
        except Exception as log_err:
            db.rollback()
            logger.error("❌ Failed to persist WebhookLog: %s", log_err)

        # Build clean response — never include internal 'code' key in body
        response_body = {k: v for k, v in result.items() if k != "code"}
        return jsonify(response_body), http_code

    except ValueError as e:
        # --- Step 5: Insufficient Funds or invalid business rule ---
        msg: str = str(e)
        status_str = "INSUFFICIENT_FUNDS" if "Insufficient funds" in msg else "INVALID_REQUEST"
        http_code = 422 if "Insufficient funds" in msg else 400
        
        # Log failure
        log = WebhookLog(
            ExternalTransID=payload.get("bank_transaction_id"),
            Status=status_str,
            StatusCode=http_code,
            Detail=msg
        )
        db.add(log)
        db.commit()

        logger.warning("Webhook rejected (%s): %s", status_str, msg)
        return jsonify({"status": status_str, "detail": msg}), http_code

    except Exception as e:
        # --- Step 6: Outer safety net ---
        db.rollback()
        log = WebhookLog(
            ExternalTransID=payload.get("bank_transaction_id"),
            Status="CRITICAL_ERROR",
            StatusCode=500,
            Detail=str(e)
        )
        db.add(log)
        db.commit()
        
        logger.error("Unhandled exception: %s", e)
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    finally:
        db.close()



# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.route("/health", methods=["GET"])
def health_check() -> tuple[Response, int]:
    """
    Simple liveness probe endpoint. Returns 200 OK if the server is running.
    Does NOT require authentication.

    Returns:
        JSON: {"status": "ok", "service": "webhook_server"}
    """
    return jsonify({"status": "ok", "service": "webhook_server"}), 200


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Webhook Server on http://0.0.0.0:5050 ...")
    logger.info("Endpoint: POST http://localhost:5050/webhook/transaction")
    logger.info("Health:   GET  http://localhost:5050/health")
    app.run(host="0.0.0.0", port=5050, debug=False)
