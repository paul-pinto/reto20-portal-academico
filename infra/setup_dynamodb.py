"""
Provisiona la tabla DynamoDB del Reto 20 y carga los datos sintéticos finales.

Diseño:
- Tabla: portal_academico
- PK: PK
- SK: SK
- GSI1: GSI1PK + GSI1SK
- Billing: PAY_PER_REQUEST
- IDs visibles directamente en español:
  profesor-001, profesor-002,
  estudiante-001 ... estudiante-004

El script es idempotente: puede ejecutarse varias veces sin crear duplicados.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError


REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "portal_academico")
DEMO_PASSWORD = os.getenv("PORTAL_DEMO_PASSWORD", "Demo2026!")
PBKDF2_ITERATIONS = 260_000


def password_fields(password: str) -> dict[str, Any]:
    """Genera los campos de contraseña usados por el portal."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return {
        "password_hash": base64.b64encode(digest).decode("ascii"),
        "password_salt": base64.b64encode(salt).decode("ascii"),
        "password_iterations": PBKDF2_ITERATIONS,
        "password_algorithm": "pbkdf2_sha256",
    }


def create_table_if_needed(dynamodb) -> None:
    existing = dynamodb.meta.client.list_tables()["TableNames"]
    if TABLE_NAME in existing:
        print(f"[OK] La tabla {TABLE_NAME!r} ya existe.")
        return

    print(f"[CREATE] Creando tabla {TABLE_NAME!r}...")
    dynamodb.create_table(
        TableName=TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    dynamodb.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
    print("[OK] Tabla creada.")


def existing_user_password_fields(table, user_id: str) -> dict[str, Any] | None:
    """
    Conserva el hash existente cuando el script se ejecuta nuevamente.
    Así no cambia la contraseña almacenada en cada ejecución.
    """
    response = table.get_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
        ConsistentRead=True,
    )
    item = response.get("Item")
    if not item:
        return None

    keys = (
        "password_hash",
        "password_salt",
        "password_iterations",
        "password_algorithm",
    )
    if all(k in item for k in keys):
        return {k: item[k] for k in keys}
    return None


def build_items(table) -> list[dict[str, Any]]:
    users = [
        ("profesor-001", "Ana Perez", "docente"),
        ("profesor-002", "Carlos Rojas", "docente"),
        ("estudiante-001", "Juan Mendoza", "estudiante"),
        ("estudiante-002", "Maria Flores", "estudiante"),
        ("estudiante-003", "Pedro Vargas", "estudiante"),
        ("estudiante-004", "Lucia Romero", "estudiante"),
    ]

    items: list[dict[str, Any]] = []

    for user_id, name, role in users:
        credentials = existing_user_password_fields(table, user_id)
        if credentials is None:
            credentials = password_fields(DEMO_PASSWORD)

        items.append(
            {
                "PK": f"USER#{user_id}",
                "SK": "PROFILE",
                "entity_type": "USER",
                "user_id": user_id,
                "name": name,
                "role": role,
                **credentials,
            }
        )

    # Cursos
    items.extend(
        [
            {
                "PK": "COURSE#CLOUD101",
                "SK": "META",
                "entity_type": "COURSE",
                "course_id": "CLOUD101",
                "name": "Computacion en la Nube",
                "teacher_id": "profesor-001",
                "GSI1PK": "TEACHER#profesor-001",
                "GSI1SK": "COURSE#CLOUD101",
            },
            {
                "PK": "COURSE#DATA101",
                "SK": "META",
                "entity_type": "COURSE",
                "course_id": "DATA101",
                "name": "Ciencia de Datos",
                "teacher_id": "profesor-002",
                "GSI1PK": "TEACHER#profesor-002",
                "GSI1SK": "COURSE#DATA101",
            },
        ]
    )

    # Matrículas
    enrollments = [
        ("CLOUD101", "estudiante-001"),
        ("CLOUD101", "estudiante-002"),
        ("DATA101", "estudiante-003"),
        ("DATA101", "estudiante-004"),
    ]
    for course_id, student_id in enrollments:
        items.append(
            {
                "PK": f"COURSE#{course_id}",
                "SK": f"STUDENT#{student_id}",
                "entity_type": "ENROLLMENT",
                "course_id": course_id,
                "student_id": student_id,
                "GSI1PK": f"STUDENT#{student_id}",
                "GSI1SK": f"COURSE#{course_id}",
            }
        )

    # Actividades
    activities = [
        ("CLOUD101", "activity-cloud-01", "Arquitectura basica en AWS"),
        ("CLOUD101", "activity-cloud-02", "Despliegue de aplicacion"),
        ("DATA101", "activity-data-01", "Exploracion de datos"),
        ("DATA101", "activity-data-02", "Modelo predictivo"),
    ]
    for course_id, activity_id, title in activities:
        items.append(
            {
                "PK": f"COURSE#{course_id}",
                "SK": f"ACTIVITY#{activity_id}",
                "entity_type": "ACTIVITY",
                "course_id": course_id,
                "activity_id": activity_id,
                "title": title,
            }
        )

    # Entregas
    submissions = [
        (
            "CLOUD101",
            "activity-cloud-01",
            "estudiante-001",
            "entregas/CLOUD101/activity-cloud-01/estudiante-001/arquitectura.pdf",
        ),
        (
            "CLOUD101",
            "activity-cloud-01",
            "estudiante-002",
            "entregas/CLOUD101/activity-cloud-01/estudiante-002/arquitectura.pdf",
        ),
        (
            "DATA101",
            "activity-data-01",
            "estudiante-003",
            "entregas/DATA101/activity-data-01/estudiante-003/eda.pdf",
        ),
        (
            "DATA101",
            "activity-data-01",
            "estudiante-004",
            "entregas/DATA101/activity-data-01/estudiante-004/eda.pdf",
        ),
    ]
    for course_id, activity_id, student_id, s3_key in submissions:
        items.append(
            {
                "PK": f"ACTIVITY#{activity_id}",
                "SK": f"STUDENT#{student_id}",
                "entity_type": "SUBMISSION",
                "course_id": course_id,
                "activity_id": activity_id,
                "student_id": student_id,
                "s3_key": s3_key,
                "status": "submitted",
                "GSI1PK": f"STUDENT#{student_id}",
                "GSI1SK": f"SUBMISSION#{activity_id}",
            }
        )

    # Revisiones sintéticas de ejemplo
    reviews = [
        ("CLOUD101", "activity-cloud-01", "estudiante-001", "profesor-001", 90),
        ("DATA101", "activity-data-01", "estudiante-003", "profesor-002", 88),
    ]
    for course_id, activity_id, student_id, teacher_id, score in reviews:
        items.append(
            {
                "PK": f"ACTIVITY#{activity_id}",
                "SK": f"REVIEW#{student_id}",
                "entity_type": "REVIEW",
                "course_id": course_id,
                "activity_id": activity_id,
                "student_id": student_id,
                "teacher_id": teacher_id,
                "score": score,
                "comment": "Revision academica de demostracion",
            }
        )

    return items


def put_items(table, items: list[dict[str, Any]]) -> None:
    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f"[OK] {len(items)} registros cargados/actualizados.")


def verify(table) -> None:
    response = table.scan(
        ProjectionExpression="PK, SK, entity_type",
    )
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.scan(
            ProjectionExpression="PK, SK, entity_type",
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    counts: dict[str, int] = {}
    for item in items:
        entity = item.get("entity_type", "UNKNOWN")
        counts[entity] = counts.get(entity, 0) + 1

    print("[VERIFY] Conteo por entidad:")
    for entity in ("USER", "COURSE", "ENROLLMENT", "ACTIVITY", "SUBMISSION", "REVIEW"):
        print(f"  {entity:10s}: {counts.get(entity, 0)}")

    expected = {
        "USER": 6,
        "COURSE": 2,
        "ENROLLMENT": 4,
        "ACTIVITY": 4,
        "SUBMISSION": 4,
        "REVIEW": 2,
    }
    for entity, minimum in expected.items():
        if counts.get(entity, 0) < minimum:
            raise RuntimeError(
                f"Verificacion fallida: {entity}={counts.get(entity, 0)}, "
                f"esperado al menos {minimum}"
            )

    print("[OK] Verificacion DynamoDB completada.")


def main() -> None:
    print("=" * 72)
    print("RETO 20 - SETUP DYNAMODB")
    print("=" * 72)
    print(f"Region : {REGION}")
    print(f"Tabla  : {TABLE_NAME}")

    dynamodb = boto3.resource("dynamodb", region_name=REGION)

    try:
        create_table_if_needed(dynamodb)
        table = dynamodb.Table(TABLE_NAME)
        table.load()

        items = build_items(table)
        put_items(table, items)
        verify(table)

        print()
        print("[DONE] DynamoDB listo.")
        print("Credenciales demo:")
        print("  estudiante-001 / Demo2026!")
        print("  profesor-001   / Demo2026!")

    except ClientError as exc:
        print(f"[ERROR AWS] {exc}")
        raise


if __name__ == "__main__":
    main()
