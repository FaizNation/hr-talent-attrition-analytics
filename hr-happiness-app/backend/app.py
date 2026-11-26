"""Application factory for the Employee Happiness Index backend."""

import logging

from flask import Flask, jsonify
from flask_cors import CORS

import config
from routes.api import api
from services.model_service import ModelService


def create_app(test_config=None):
    """Build the Flask app, loading artifacts once at startup."""
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__)
    app.config.from_object(config)
    if test_config:
        app.config.update(test_config)

    CORS(app, origins=app.config["CORS_ORIGINS"])
    app.extensions["model_service"] = ModelService(
        app.config["MODEL_PATH"], app.config["SUMMARY_PATH"]
    )
    app.register_blueprint(api, url_prefix="/api")

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": getattr(error, "description", "Bad request")}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": getattr(error, "description", "Not found")}), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error("Unhandled server error: %s", error)
        return jsonify({"error": "Internal server error."}), 500

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=config.PORT)
