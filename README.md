# Reto 20 - Portal académico en la nube

Proyecto final de **Computación en la Nube** correspondiente al **Reto 20: Portal académico en la nube**.

La solución implementa un portal académico sobre AWS con control de acceso por rol, almacenamiento privado de entregas, URLs prefirmadas y observabilidad mediante CloudWatch.

## Arquitectura

Servicios principales utilizados:

- **Amazon EC2**: ejecución del portal académico desarrollado en Python/Flask.
- **Amazon DynamoDB**: persistencia de usuarios, cursos, matrículas, actividades, entregas y revisiones.
- **Amazon S3**: almacenamiento privado de archivos de entregas.
- **Amazon CloudWatch**: logs de aplicación, errores y eventos de auditoría.
- **AWS IAM / LabRole**: permisos de acceso desde EC2 hacia DynamoDB, S3 y CloudWatch.
- **Amazon VPC + Security Groups**: aislamiento de red y control de acceso.

En producción dentro de EC2, Flask se ejecuta mediante Gunicorn detrás de Nginx.

## Estructura principal

```text
Proyecto_Final/
├── app/
├── datos/
├── docs/
├── infra/
│   ├── setup_dynamodb.py
│   └── setup_s3.py
├── requirements.txt
├── run.py
└── README.md
```

## Requisitos

- Python 3.11 o compatible
- AWS Academy Learner Lab activo
- Credenciales temporales válidas cargadas en el entorno
- Región AWS: `us-east-1`

## Entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Credenciales AWS

El proyecto **no almacena credenciales AWS**.

Las credenciales temporales del Learner Lab deben cargarse en la sesión de PowerShell:

```powershell
$env:AWS_ACCESS_KEY_ID="..."
$env:AWS_SECRET_ACCESS_KEY="..."
$env:AWS_SESSION_TOKEN="..."
$env:AWS_DEFAULT_REGION="us-east-1"
```

No se deben guardar credenciales en el código, archivos `.env`, documentación ni repositorios públicos.

Para comprobar el acceso:

```powershell
python -c "import boto3; print(boto3.client('sts', region_name='us-east-1').get_caller_identity())"
```

## Aprovisionamiento de DynamoDB

El script crea o reutiliza la tabla:

```text
portal_academico
```

con:

- clave de partición `PK`
- clave de ordenamiento `SK`
- índice global secundario `GSI1`
- modo de facturación `PAY_PER_REQUEST`

Además carga directamente los identificadores finales:

```text
profesor-001
profesor-002
estudiante-001
estudiante-002
estudiante-003
estudiante-004
```

Ejecutar:

```powershell
python .\infra\setup_dynamodb.py
```

El script es idempotente y puede ejecutarse nuevamente sin crear duplicados.

## Aprovisionamiento de S3

El script configura el bucket privado utilizado por el portal con:

- Block Public Access habilitado
- cifrado SSE-S3 (`AES256`)
- versionado habilitado
- archivos PDF con `ContentType=application/pdf`
- rutas finales con identificadores `estudiante-*`

Ejecutar:

```powershell
python .\infra\setup_s3.py
```

Los archivos permanecen privados. El acceso desde el portal se realiza mediante URLs prefirmadas temporales después de superar las validaciones de autorización.

## Ejecución local

Con el entorno virtual activo y credenciales AWS válidas:

```powershell
python run.py
```

El portal queda disponible en:

```text
http://127.0.0.1:5000
```

## Usuarios de demostración

### Estudiante

```text
Usuario: estudiante-001
Contraseña: Demo2026!
```

El estudiante puede consultar únicamente sus propios cursos y entregas.

### Docente

```text
Usuario: profesor-001
Contraseña: Demo2026!
```

El docente puede consultar únicamente los cursos que tiene asignados.

## Prueba de aceptación

La implementación valida los siguientes casos:

```text
✓ Estudiante A → su propia entrega
✗ Estudiante A → entrega de otro estudiante
✓ Docente A → su curso asignado
✗ Docente A → curso de otro docente
```

Los accesos no autorizados son rechazados por el backend.

## Observabilidad

La aplicación registra eventos de auditoría en Amazon CloudWatch, incluyendo:

- `login_success`
- `login_failed`
- `view_submission`
- `presigned_url_generated`
- `forbidden_course`
- `forbidden_submission`
- `forbidden_download`
- `logout`

El grupo de logs utilizado es:

```text
/reto20/portal-academico
```

## Seguridad

La solución aplica:

- S3 completamente privado
- acceso mediante URLs prefirmadas temporales
- autorización en backend por estudiante y docente
- IAM Role asociado a EC2
- ausencia de credenciales AWS estáticas dentro de la aplicación
- Security Groups para limitar exposición de red
- contraseñas almacenadas mediante PBKDF2-SHA256

## Despliegue

En AWS la aplicación se ejecuta en Amazon EC2 con:

```text
Internet
   ↓
Nginx
   ↓
Gunicorn
   ↓
Flask
```

La instancia utiliza `LabInstanceProfile` / `LabRole` para comunicarse con DynamoDB, S3 y CloudWatch.

## Evidencias

Las capturas de arquitectura, configuración, seguridad, pruebas de aceptación y observabilidad se encuentran en:

```text
docs/evidencias/
```

## Repositorio

https://github.com/paul-pinto/reto20-portal-academico

## Autor

**Jhonny Paul Pinto Phillips**  
Maestría en Ciencia de Datos e Inteligencia Artificial  
Universidad Católica Boliviana “San Pablo”  
Computación en la Nube — 2026