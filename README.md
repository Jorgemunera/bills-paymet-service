# Payment Service (Bills Payment)

Servicio de pagos de servicios (Bills Payment) desarrollado con FastAPI, diseñado con arquitectura hexagonal.

## 📋 Tabla de Contenidos

- [Descripción](#descripción)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Requisitos Previos](#requisitos-previos)
- [Instalación y Ejecución](#instalación-y-ejecución)
- [Endpoints API](#endpoints-api)
- [Escenarios de Prueba](#escenarios-de-prueba)
- [Decisiones Técnicas](#decisiones-técnicas)
- [Estructura del Proyecto](#estructura-del-proyecto)

---

## Descripción

Este servicio implementa un orquestador de pagos que:

1. **Registra solicitudes de pago** con validaciones de negocio
2. **Procesa pagos** con lógica simulada configurable
3. **Garantiza idempotencia** usando Redis con TTL automático
4. **Gestiona estados** del ciclo de vida del pago
5. **Permite reintentos** controlados para pagos fallidos (máximo 3)
6. **Previene duplicados** mediante locks distribuidos

### Flujo Principal

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Cliente    │────▶│   FastAPI    │────▶│   SQLite     │
│              │     │   (API)      │     │   (datos)    │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    Redis     │
                     │ (idempotencia│
                     │   + locks)   │
                     └──────────────┘
```

### Reglas de Procesamiento

| Escenario | Resultado |
|-----------|-----------|
| Monto ≤ 1000 | SUCCESS (éxito inmediato) |
| Monto > 1000 | FAILED (requiere reintento) |
| Reintento | 50% probabilidad de éxito |
| 3 reintentos fallidos | EXHAUSTED (agotado) |

---

## Arquitectura

### Arquitectura Hexagonal

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PAYMENT SERVICE                              │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      DOMAIN LAYER                               │ │
│  │                                                                 │ │
│  │  Payment Entity         PaymentStatus Enum    Domain Errors    │ │
│  │  - payment_id           - PENDING             - PaymentNotFound │ │
│  │  - reference            - SUCCESS             - CannotRetry     │ │
│  │  - amount               - FAILED              - MaxRetries      │ │
│  │  - currency             - EXHAUSTED           - ValidationError │ │
│  │  - status                                                       │ │
│  │  - retries              Repository Interface (ABC)              │ │
│  │  - created_at           - save()                                │ │
│  │  - updated_at           - find_by_id()                          │ │
│  │                         - update()                              │ │
│  │  Comportamiento:        - find_all()                            │ │
│  │  - can_retry()          - count()                               │ │
│  │  - increment_retries()                                          │ │
│  │  - mark_as_success()                                            │ │
│  │  - mark_as_failed()                                             │ │
│  │  - mark_as_exhausted()                                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   APPLICATION LAYER                             │ │
│  │                                                                 │ │
│  │  Use Cases:                      Ports (Interfaces):           │ │
│  │  - CreatePaymentUseCase          - PaymentRepository           │ │
│  │  - GetPaymentUseCase             - PaymentProcessor            │ │
│  │  - RetryPaymentUseCase           - IdempotencyService          │ │
│  │  - ListPaymentsUseCase                                         │ │
│  │                                                                 │ │
│  │  DTOs:                                                          │ │
│  │  - CreatePaymentRequest / Response                              │ │
│  │  - GetPaymentRequest / Response                                 │ │
│  │  - RetryPaymentRequest / Response                               │ │
│  │  - ListPaymentsRequest / Response                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  INFRASTRUCTURE LAYER                           │ │
│  │                                                                 │ │
│  │  Adapters:                       HTTP:                          │ │
│  │  - SQLitePaymentRepository       - Routes (FastAPI Router)     │ │
│  │  - SimulatedPaymentProcessor     - Schemas (Pydantic)          │ │
│  │  - RedisIdempotencyService       - Error Handlers              │ │
│  │                                  - Middlewares                  │ │
│  │  Shared Infrastructure:                                         │ │
│  │  - SQLite connection             - Logging Middleware          │ │
│  │  - Redis client                  - CORS Middleware             │ │
│  │  - FastAPI server                                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Diagrama de Estados del Pago

```
              ┌──────────┐
              │ PENDING  │
              └────┬─────┘
                   │
         ┌─────────┴─────────┐
         │ Procesar pago     │
         │ (simulado)        │
         ▼                   ▼
   ┌──────────┐        ┌──────────┐
   │ SUCCESS  │        │  FAILED  │◄──────────────────────┐
   │ (final)  │        │          │                       │
   └──────────┘        └────┬─────┘                       │
                            │                             │
                   ┌────────┴────────┐                    │
                   │ POST /retry     │                    │
                   │ (retries < 3)   │                    │
                   ▼                 ▼                    │
             ┌──────────┐      ┌──────────┐              │
             │ SUCCESS  │      │ FAILED   │──────────────┘
             │ (final)  │      │(retry++) │
             └──────────┘      └────┬─────┘
                                    │
                                    │ retries == 3
                                    ▼
                              ┌──────────┐
                              │EXHAUSTED │
                              │ (final)  │
                              └──────────┘
```

---

## Tecnologías

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| Python | 3.11 | Lenguaje de programación |
| FastAPI | 0.109 | Framework web async |
| SQLite | 3 | Base de datos (persistencia) |
| Redis | 7 | Idempotencia y locks distribuidos |
| Pydantic | 2.5 | Validación de datos |
| Docker | - | Containerización |
| pytest | 7.4 | Testing |

---

## Requisitos Previos

- **Docker** y **Docker Compose** instalados
- **Git** para clonar el repositorio
- Puerto **8000** disponible (API)
- Puerto **6379** disponible (Redis)

### Para desarrollo local (opcional)

- **Python 3.11+**
- **pyenv** (recomendado para gestión de versiones)

---

## Instalación y Ejecución

### Opción 1: Docker Compose (Recomendada)

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd bills-payment-service

# Levantar todos los servicios
docker-compose up --build

# O en segundo plano
docker-compose up --build -d
```

### Opción 2: Desarrollo Local

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd bills-payment-service

# Crear entorno virtual con Python 3.11
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar Redis (requiere Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Ejecutar la aplicación
python -m src.main
```

### Verificar que todo está corriendo

```bash
# Health check
curl http://localhost:8000/health

# Respuesta esperada:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00.000000",
  "services": {
    "database": { "status": "healthy" },
    "redis": { "status": "healthy" }
  }
}
```

### Acceder a las interfaces

| Servicio | URL |
|----------|-----|
| API Documentation (Swagger) | http://localhost:8000/docs |
| API Documentation (ReDoc) | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

### Comandos útiles

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs solo de la API
docker-compose logs -f api

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (reset completo)
docker-compose down -v

# Ejecutar tests
pytest

# Ejecutar tests con cobertura
pytest --cov=src --cov-report=term-missing
```

---

## Endpoints API

### Payments

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /payments | Crear un nuevo pago |
| GET | /payments | Listar pagos (con filtros) |
| GET | /payments/{payment_id} | Obtener pago por ID |
| POST | /payments/{payment_id}/retry | Reintentar pago fallido |

### Health

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /health | Estado de todas las conexiones |

### Detalle de Endpoints

#### POST /payments

Crea un nuevo pago. Requiere header `Idempotency-Key`.

**Request:**
```bash
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "reference": "FAC-12345",
    "amount": 500,
    "currency": "MXN"
  }'
```

**Response (201 Created):**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "reference": "FAC-12345",
  "amount": 500.0,
  "currency": "MXN",
  "status": "SUCCESS",
  "retries": 0,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

#### GET /payments

Lista pagos con filtros opcionales.

**Request:**
```bash
curl "http://localhost:8000/payments?status=FAILED&limit=10&offset=0"
```

**Response (200 OK):**
```json
{
  "payments": [...],
  "total": 25,
  "limit": 10,
  "offset": 0
}
```

#### GET /payments/{payment_id}

Obtiene un pago por su ID.

**Request:**
```bash
curl http://localhost:8000/payments/550e8400-e29b-41d4-a716-446655440000
```

#### POST /payments/{payment_id}/retry

Reintenta un pago fallido.

**Request:**
```bash
curl -X POST http://localhost:8000/payments/550e8400-e29b-41d4-a716-446655440000/retry
```

---

## Escenarios de Prueba

### Escenario 1: Flujo exitoso (monto ≤ 1000)

**Objetivo:** Verificar que un pago con monto menor o igual a 1000 se procesa exitosamente.

```bash
# Crear un pago con monto ≤ 1000
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-success-001" \
  -d '{
    "reference": "FAC-12345",
    "amount": 500,
    "currency": "MXN"
  }'

# Respuesta esperada (201 Created):
{
  "payment_id": "...",
  "reference": "FAC-12345",
  "amount": 500.0,
  "currency": "MXN",
  "status": "SUCCESS",
  "retries": 0,
  ...
}
```

---

### Escenario 2: Flujo con fallo inicial (monto > 1000)

**Objetivo:** Verificar que un pago con monto mayor a 1000 falla inicialmente.

```bash
# Crear un pago con monto > 1000
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-failed-001" \
  -d '{
    "reference": "FAC-67890",
    "amount": 1500,
    "currency": "MXN"
  }'

# Respuesta esperada (201 Created):
{
  "payment_id": "...",
  "reference": "FAC-67890",
  "amount": 1500.0,
  "currency": "MXN",
  "status": "FAILED",
  "retries": 0,
  ...
}
```

---

### Escenario 3: Idempotencia - evitar pagos duplicados

**Objetivo:** Verificar que el mismo Idempotency-Key no crea pagos duplicados.

```bash
# 1. Crear pago con key específica
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "reference": "FAC-11111",
    "amount": 750,
    "currency": "MXN"
  }'

# Guardar el payment_id retornado

# 2. Intentar crear otro pago con LA MISMA key
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "reference": "FAC-99999",
    "amount": 9999,
    "currency": "USD"
  }'

# Respuesta: Retorna el MISMO pago original (200 OK)
# NO crea un nuevo pago aunque los datos sean diferentes
```

---

### Escenario 4: Reintentos exitosos

**Objetivo:** Verificar que un pago fallido puede ser reintentado y eventualmente tener éxito.

```bash
# 1. Crear un pago que falle (monto > 1000)
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-retry-001" \
  -d '{
    "reference": "FAC-RETRY",
    "amount": 2000,
    "currency": "MXN"
  }'

# Guardar el payment_id (ejemplo: pay_xxx)

# 2. Reintentar el pago (50% probabilidad de éxito)
curl -X POST http://localhost:8000/payments/{payment_id}/retry

# Respuesta posible - éxito:
{
  "payment_id": "...",
  "status": "SUCCESS",
  "retries": 1,
  ...
}

# Respuesta posible - fallo:
{
  "payment_id": "...",
  "status": "FAILED",
  "retries": 1,
  ...
}
```

---

### Escenario 5: Agotar reintentos (EXHAUSTED)

**Objetivo:** Verificar que después de 3 reintentos fallidos, el pago queda en estado EXHAUSTED.

```bash
# 1. Crear pago que falle
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-exhausted-001" \
  -d '{
    "reference": "FAC-EXHAUST",
    "amount": 5000,
    "currency": "MXN"
  }'

# 2. Reintentar hasta agotar (máximo 3 veces)
# Nota: Cada reintento tiene 50% de éxito, puede que logre SUCCESS antes

curl -X POST http://localhost:8000/payments/{payment_id}/retry
curl -X POST http://localhost:8000/payments/{payment_id}/retry
curl -X POST http://localhost:8000/payments/{payment_id}/retry

# Si los 3 fallan, el estado será EXHAUSTED:
{
  "payment_id": "...",
  "status": "EXHAUSTED",
  "retries": 3,
  ...
}

# 3. Intentar un cuarto reintento
curl -X POST http://localhost:8000/payments/{payment_id}/retry

# Respuesta (409 Conflict):
{
  "success": false,
  "error": {
    "code": "CANNOT_RETRY_PAYMENT",
    "message": "Payment '...' cannot be retried. Current status: EXHAUSTED..."
  }
}
```

---

### Escenario 6: Validación de errores

**Objetivo:** Verificar validaciones del API.

```bash
# Sin Idempotency-Key
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"reference": "FAC-123", "amount": 500, "currency": "MXN"}'

# Respuesta (422 Unprocessable Entity):
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "idempotency-key"],
      "msg": "Field required"
    }
  ]
}

# Monto inválido (cero o negativo)
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-validation-001" \
  -d '{"reference": "FAC-123", "amount": -100, "currency": "MXN"}'

# Respuesta (400 Bad Request):
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Amount must be greater than zero"
  }
}

# Currency inválido (no 3 caracteres)
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-validation-002" \
  -d '{"reference": "FAC-123", "amount": 500, "currency": "MEXICAN"}'

# Respuesta (400 Bad Request):
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Currency must be exactly 3 characters"
  }
}
```

---

### Escenario 7: Intentar reintentar pago exitoso

**Objetivo:** Verificar que no se puede reintentar un pago que ya tuvo éxito.

```bash
# 1. Crear pago exitoso
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-no-retry-success" \
  -d '{"reference": "FAC-SUCCESS", "amount": 500, "currency": "MXN"}'

# 2. Intentar reintentar
curl -X POST http://localhost:8000/payments/{payment_id}/retry

# Respuesta (409 Conflict):
{
  "success": false,
  "error": {
    "code": "CANNOT_RETRY_PAYMENT",
    "message": "Payment '...' cannot be retried. Current status: SUCCESS..."
  }
}
```

---

### Escenario 8: Listar pagos con filtros

**Objetivo:** Verificar la funcionalidad de listado y filtrado.

```bash
# Crear varios pagos primero (usar diferentes Idempotency-Keys)

# Listar todos los pagos
curl "http://localhost:8000/payments"

# Listar solo pagos fallidos
curl "http://localhost:8000/payments?status=FAILED"

# Listar con paginación
curl "http://localhost:8000/payments?limit=5&offset=0"

# Combinar filtros
curl "http://localhost:8000/payments?status=SUCCESS&limit=10&offset=0"
```

---

## Decisiones Técnicas

### ¿Por qué Arquitectura Hexagonal?

- **Desacoplamiento:** El dominio no conoce detalles de infraestructura
- **Testabilidad:** Los use cases se pueden probar sin BD real usando mocks
- **Flexibilidad:** Cambiar SQLite por PostgreSQL es trivial (solo cambiar el adapter)
- **Claridad:** Cada capa tiene responsabilidades claras

### ¿Por qué FastAPI?

- **Performance:** Framework async de alto rendimiento
- **Validación automática:** Pydantic integrado para request/response validation
- **Documentación automática:** OpenAPI/Swagger generado automáticamente
- **Dependency Injection:** Sistema nativo de DI con `Depends()`
- **Type hints:** Aprovecha el sistema de tipos de Python 3.11+

### ¿Por qué Redis para Idempotencia?

- **Velocidad:** Verificación O(1) antes de tocar la BD
- **TTL automático:** Las claves expiran sin lógica adicional (24 horas por defecto)
- **Locks distribuidos:** SETNX previene race conditions entre requests concurrentes
- **Atomicidad:** Operaciones atómicas garantizadas

### ¿Por qué SQLite?

- **Simplicidad:** No requiere servidor separado
- **Portabilidad:** Base de datos en un solo archivo
- **Suficiente para el caso de uso:** Adecuado para demostración y pruebas
- **Fácil migración:** La arquitectura hexagonal permite cambiar a PostgreSQL sin modificar el dominio

### ¿Por qué el estado EXHAUSTED?

El documento original solo menciona PENDING, SUCCESS y FAILED. Se añadió EXHAUSTED porque:

- **Claridad operacional:** Distingue "falló pero puede reintentarse" de "agotó todas las opciones"
- **Queries más simples:** `WHERE status = 'EXHAUSTED'` vs `WHERE status = 'FAILED' AND retries >= 3`
- **Valor de negocio:** Permite identificar pagos que requieren intervención manual

### ¿Por qué probabilidad del 50% en reintentos?

- **Realismo:** Simula fallos temporales que se resuelven con el tiempo
- **Demostración:** Permite probar ambos caminos (éxito y fallo)
- **Configurable:** Se puede ajustar via variable de entorno `RETRY_SUCCESS_PROBABILITY`

### ¿Por qué Depends() en lugar de Container manual?

FastAPI tiene su propio sistema de inyección de dependencias. Usar `Depends()`:

- **Es idiomático:** Es el patrón esperado en FastAPI
- **Mejor testing:** `app.dependency_overrides` para tests
- **Lazy loading:** Dependencias se crean por request o cached
- **Integración nativa:** Mejor integración con el framework

---

## Estructura del Proyecto

```
bills-payment-service/
├── docker-compose.yml              # Orquestación de servicios
├── Dockerfile                      # Imagen de la aplicación
├── requirements.txt                # Dependencias Python
├── pytest.ini                      # Configuración de tests
├── .env.example                    # Variables de entorno ejemplo
├── .gitignore                      # Archivos ignorados
├── .python-version                 # Versión de Python (pyenv)
├── README.md                       # Esta documentación
│
├── data/                           # Directorio para SQLite
│   └── .gitkeep
│
├── tests/                          # Tests automatizados
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures compartidos
│   └── unit/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   └── test_payment.py     # Tests de entidad Payment
│       └── application/
│           ├── __init__.py
│           ├── test_create_payment.py
│           ├── test_get_payment.py
│           └── test_retry_payment.py
│
└── src/
    ├── __init__.py
    ├── main.py                     # Entry point FastAPI
    ├── dependencies.py             # Inyección de dependencias (Depends)
    │
    ├── config/
    │   ├── __init__.py
    │   └── settings.py             # Configuración (Pydantic Settings)
    │
    ├── shared/
    │   ├── __init__.py
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── database/
    │   │   │   ├── __init__.py
    │   │   │   └── sqlite.py       # Cliente SQLite async
    │   │   ├── cache/
    │   │   │   ├── __init__.py
    │   │   │   └── redis_client.py # Cliente Redis
    │   │   └── http/
    │   │       ├── __init__.py
    │   │       ├── server.py       # Configuración FastAPI
    │   │       ├── error_handlers.py
    │   │       ├── schemas.py
    │   │       └── middlewares/
    │   │           ├── __init__.py
    │   │           └── logging_middleware.py
    │   └── utils/
    │       ├── __init__.py
    │       └── logger.py           # Logger estructurado
    │
    └── modules/
        └── payments/
            ├── __init__.py
            ├── domain/
            │   ├── __init__.py
            │   ├── payment.py          # Entidad Payment
            │   ├── payment_status.py   # Enum de estados
            │   ├── errors.py           # Errores de dominio
            │   └── repository.py       # Interface repositorio (ABC)
            │
            ├── application/
            │   ├── __init__.py
            │   ├── dtos.py             # Data Transfer Objects
            │   ├── ports/
            │   │   ├── __init__.py
            │   │   ├── payment_processor.py
            │   │   └── idempotency_service.py
            │   └── use_cases/
            │       ├── __init__.py
            │       ├── create_payment.py
            │       ├── get_payment.py
            │       ├── retry_payment.py
            │       └── list_payments.py
            │
            └── infrastructure/
                ├── __init__.py
                ├── persistence/
                │   ├── __init__.py
                │   └── sqlite_payment_repository.py
                ├── services/
                │   ├── __init__.py
                │   ├── simulated_payment_processor.py
                │   └── redis_idempotency_service.py
                └── http/
                    ├── __init__.py
                    ├── routes.py       # Endpoints FastAPI
                    └── schemas.py      # Pydantic schemas
```

---

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Entorno de ejecución | `development` |
| `APP_NAME` | Nombre de la aplicación | `payment-service` |
| `APP_VERSION` | Versión de la aplicación | `1.0.0` |
| `DEBUG` | Modo debug | `true` |
| `HOST` | Host del servidor | `0.0.0.0` |
| `PORT` | Puerto del servidor | `8000` |
| `DATABASE_PATH` | Ruta del archivo SQLite | `data/payments.db` |
| `REDIS_HOST` | Host de Redis | `localhost` |
| `REDIS_PORT` | Puerto de Redis | `6379` |
| `IDEMPOTENCY_TTL_SECONDS` | TTL de claves de idempotencia | `86400` (24h) |
| `MAX_RETRIES` | Máximo de reintentos | `3` |
| `RETRY_SUCCESS_PROBABILITY` | Probabilidad de éxito en reintento | `0.5` |

---

## Testing

### Ejecutar todos los tests

```bash
pytest
```

### Ejecutar con cobertura

```bash
pytest --cov=src --cov-report=term-missing
```

### Ejecutar tests específicos

```bash
# Solo tests de dominio
pytest tests/unit/domain/

# Solo tests de un caso de uso
pytest tests/unit/application/test_create_payment.py

# Test específico
pytest tests/unit/domain/test_payment.py::TestPaymentCreate::test_create_payment_success
```

---

## Autor

Desarrollado como prueba técnica para demostrar conocimientos en:

- Python 3.11+ y FastAPI
- Arquitectura Hexagonal / Ports & Adapters
- Domain-Driven Design (DDD)
- Patrones de resiliencia (idempotencia, reintentos)
- Testing con pytest
- Docker y containerización
- Redis para cache y locks distribuidos
