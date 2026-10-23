# Reto 20 - Bootstrap DynamoDB

Incluye:
- `infra/setup_dynamodb.py`: crea `portal_academico`, el GSI `GSI1` y carga los datos.
- `datos/datos_prueba.json`: dataset sintetico de demo.

## Uso

```powershell
python -m pip install boto3
python .\infra\setup_dynamodb.py
```

Para recrear la tabla desde cero:

```powershell
python .\infra\setup_dynamodb.py --reset
```

No guarda credenciales. Usa las credenciales temporales del Learner Lab ya cargadas en el entorno.
