from __future__ import annotations

import boto3
from flask import current_app


def generate_download_url(s3_key: str) -> str:
    s3 = boto3.client(
        "s3",
        region_name=current_app.config["AWS_REGION"],
    )
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": current_app.config["S3_BUCKET"],
            "Key": s3_key,
        },
        ExpiresIn=current_app.config["PRESIGNED_TTL"],
    )
