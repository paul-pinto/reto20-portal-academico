from __future__ import annotations

import logging
import os

from flask import Flask

from .routes import bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "reto20-demo-change-me")

    app.config.update(
        AWS_REGION=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")),
        DYNAMODB_TABLE=os.environ.get("DYNAMODB_TABLE", "portal_academico"),
        S3_BUCKET=os.environ.get("S3_BUCKET", "ucb-reto20-portal-jpp-4194"),
        PRESIGNED_TTL=int(os.environ.get("PRESIGNED_TTL", "300")),
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app.register_blueprint(bp)

    return app
