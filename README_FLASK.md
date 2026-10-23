# Reto 20 - Aplicación Flask

## Requisitos

- Python 3.11
- Credenciales temporales vigentes de AWS Academy Learner Lab
- Tabla DynamoDB `portal_academico`
- Bucket S3 `ucb-reto20-portal-jpp-4194`

## Instalar

```powershell
python -m pip install -r requirements.txt
```

## Ejecutar localmente

```powershell
$env:AWS_DEFAULT_REGION="us-east-1"
$env:DYNAMODB_TABLE="portal_academico"
$env:S3_BUCKET="ucb-reto20-portal-jpp-4194"
$env:FLASK_SECRET_KEY="reto20-local-demo"
python .\run.py
```

Abrir:

http://127.0.0.1:5000

## Usuarios de prueba

- `student-001` / `Demo2026!`
- `teacher-001` / `Demo2026!`

## Pruebas de aceptación

Con `student-001`:

- Permitido: `/entrega/activity-cloud-01/student-001`
- Denegado: `/entrega/activity-data-01/student-003`

Con `teacher-001`:

- Permitido: `/curso/CLOUD101`
- Denegado: `/curso/DATA101`

Los accesos prohibidos deben responder HTTP 403.

## Auditoría

La aplicación genera eventos estructurados en logging:

- `login_success`
- `login_failed`
- `view_submission`
- `presigned_url_generated`
- `forbidden_course`
- `forbidden_submission`
- `forbidden_download`

En EC2 estos logs se enviarán posteriormente a CloudWatch.
