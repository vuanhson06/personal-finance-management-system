import logging

from flask import Flask, Response, jsonify, request
from sqlalchemy.orm import Session

from bank_sync_service import process_webhook_payload
from config import settings
from database import SessionLocal


app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

def _authenticate_request() -> bool:
    provided_key: str = request.headers.get("X-API-KEY", "")
    return provided_key == settings.webhook_api_key


@app.route("/webhook/transaction", methods=["POST"])
def receive_transaction() -> tuple[Response, int]:
    if not _authenticate_request():
        logger.warning(
            "Unauthorized webhook request from %s — invalid or missing X-API-KEY.",
            request.remote_addr,
        )
        return jsonify({"error": "Unauthorized", "detail": "Invalid or missing X-API-KEY."}), 401


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

    db: Session = SessionLocal()

    try:
        result: dict = process_webhook_payload(payload, db)
        http_code: int = result.get("code", 200)

        response_body = {k: v for k, v in result.items() if k != "code"}
        return jsonify(response_body), http_code

    except ValueError as e:
        msg: str = str(e)
        status_str = "INSUFFICIENT_FUNDS" if "Insufficient funds" in msg else "INVALID_REQUEST"
        http_code = 422 if "Insufficient funds" in msg else 400
        
        logger.warning("Webhook rejected (%s): %s", status_str, msg)
        return jsonify({"status": status_str, "detail": msg}), http_code

    except Exception as e:
        db.rollback()
        logger.error("Unhandled exception: %s", e)
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    finally:
        db.close()


@app.route("/health", methods=["GET"])
def health_check() -> tuple[Response, int]:
    return jsonify({"status": "ok", "service": "webhook_server"}), 200


if __name__ == "__main__":
    logger.info("Starting Webhook Server on http://0.0.0.0:5050 ...")
    logger.info("Endpoint: POST http://localhost:5050/webhook/transaction")
    logger.info("Health:   GET  http://localhost:5050/health")
    app.run(host="0.0.0.0", port=5050, debug=False)
