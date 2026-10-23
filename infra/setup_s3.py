"""
Provisiona el bucket S3 del Reto 20 y carga directamente los objetos finales.

Configuración:
- Block Public Access: habilitado
- Versioning: Enabled
- Cifrado por defecto: SSE-S3 (AES256)
- Objetos PDF válidos
- ContentType: application/pdf
- ContentDisposition: inline
- Rutas únicamente con IDs en español (estudiante-*).

El script es idempotente: volver a ejecutarlo mantiene el estado final correcto.
"""

from __future__ import annotations

import io
import os
from typing import Iterable

import boto3
from botocore.exceptions import ClientError


REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BUCKET = os.getenv("S3_BUCKET", "ucb-reto20-portal-jpp-4194")


OBJECTS = [
    (
        "entregas/CLOUD101/activity-cloud-01/estudiante-001/arquitectura.pdf",
        "Reto 20 - Entrega de estudiante-001 - Arquitectura basica en AWS",
    ),
    (
        "entregas/CLOUD101/activity-cloud-01/estudiante-002/arquitectura.pdf",
        "Reto 20 - Entrega de estudiante-002 - Arquitectura basica en AWS",
    ),
    (
        "entregas/DATA101/activity-data-01/estudiante-003/eda.pdf",
        "Reto 20 - Entrega de estudiante-003 - Exploracion de datos",
    ),
    (
        "entregas/DATA101/activity-data-01/estudiante-004/eda.pdf",
        "Reto 20 - Entrega de estudiante-004 - Exploracion de datos",
    ),
]


def pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def minimal_pdf(text: str) -> bytes:
    """
    Genera un PDF 1.4 pequeño pero válido, sin dependencias externas.
    """
    line = pdf_escape(text)

    stream = (
        "BT\n"
        "/F1 12 Tf\n"
        "72 720 Td\n"
        f"({line}) Tj\n"
        "ET\n"
    ).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>"
        ),
        b"<< /Length %d >>\nstream\n" % len(stream)
        + stream
        + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode("ascii"))
        out.write(obj)
        out.write(b"\nendobj\n")

    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode("ascii"))

    out.write(
        (
            f"trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return out.getvalue()


def bucket_exists(s3) -> bool:
    try:
        s3.head_bucket(Bucket=BUCKET)
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchBucket", "NotFound"}:
            return False
        raise


def create_bucket_if_needed(s3) -> None:
    if bucket_exists(s3):
        print(f"[OK] Bucket {BUCKET!r} ya existe.")
        return

    print(f"[CREATE] Creando bucket {BUCKET!r} en {REGION}...")
    if REGION == "us-east-1":
        s3.create_bucket(Bucket=BUCKET)
    else:
        s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )

    waiter = s3.get_waiter("bucket_exists")
    waiter.wait(Bucket=BUCKET)
    print("[OK] Bucket creado.")


def configure_private_bucket(s3) -> None:
    s3.put_public_access_block(
        Bucket=BUCKET,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    s3.put_bucket_encryption(
        Bucket=BUCKET,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    },
                    "BucketKeyEnabled": False,
                }
            ]
        },
    )

    s3.put_bucket_versioning(
        Bucket=BUCKET,
        VersioningConfiguration={"Status": "Enabled"},
    )

    print("[OK] Block Public Access habilitado.")
    print("[OK] Cifrado SSE-S3 (AES256) configurado.")
    print("[OK] Versioning habilitado.")


def upload_final_objects(s3) -> None:
    for key, title in OBJECTS:
        body = minimal_pdf(title)
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=body,
            ContentType="application/pdf",
            ContentDisposition="inline",
            ServerSideEncryption="AES256",
            Metadata={
                "reto": "20",
                "portal": "academico",
            },
        )
        print(f"[PUT] s3://{BUCKET}/{key} ({len(body)} bytes)")


def verify(s3) -> None:
    print("[VERIFY] Configuracion del bucket:")

    public = s3.get_public_access_block(Bucket=BUCKET)[
        "PublicAccessBlockConfiguration"
    ]
    if not all(public.values()):
        raise RuntimeError("Block Public Access no esta completamente habilitado.")

    encryption = s3.get_bucket_encryption(Bucket=BUCKET)
    algorithm = encryption[
        "ServerSideEncryptionConfiguration"
    ]["Rules"][0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]
    if algorithm != "AES256":
        raise RuntimeError(f"Cifrado inesperado: {algorithm}")

    versioning = s3.get_bucket_versioning(Bucket=BUCKET).get("Status")
    if versioning != "Enabled":
        raise RuntimeError(f"Versioning inesperado: {versioning}")

    listed = s3.list_objects_v2(Bucket=BUCKET, Prefix="entregas/")
    keys = {obj["Key"] for obj in listed.get("Contents", [])}

    for key, _ in OBJECTS:
        if key not in keys:
            raise RuntimeError(f"Falta objeto esperado: {key}")

        head = s3.head_object(Bucket=BUCKET, Key=key)
        if head.get("ContentType") != "application/pdf":
            raise RuntimeError(f"ContentType incorrecto en {key}")
        if head.get("ServerSideEncryption") != "AES256":
            raise RuntimeError(f"SSE incorrecto en {key}")

    # Detecta rutas heredadas si existieran, pero NO borra automáticamente versiones
    # antiguas: en el setup limpio nunca se crean.
    legacy = [
        key
        for key in keys
        if "/student-" in key or "/teacher-" in key
    ]
    if legacy:
        print("[WARN] Se detectaron objetos heredados de una ejecucion antigua:")
        for key in legacy:
            print(f"  - {key}")
        print(
            "[WARN] En un bucket nuevo no apareceran. "
            "No se eliminan automaticamente para evitar borrar datos sin confirmacion."
        )

    print("[OK] Verificacion S3 completada.")


def main() -> None:
    print("=" * 72)
    print("RETO 20 - SETUP S3")
    print("=" * 72)
    print(f"Region : {REGION}")
    print(f"Bucket : {BUCKET}")

    s3 = boto3.client("s3", region_name=REGION)

    try:
        create_bucket_if_needed(s3)
        configure_private_bucket(s3)
        upload_final_objects(s3)
        verify(s3)
        print()
        print("[DONE] S3 listo.")

    except ClientError as exc:
        print(f"[ERROR AWS] {exc}")
        raise


if __name__ == "__main__":
    main()
