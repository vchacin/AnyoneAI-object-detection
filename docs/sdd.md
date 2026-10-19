# Reestructuración `api/` → `app/` (Backend + Frontend)

Guía y prompt para adaptar el repositorio al SDD v0.2 (*Interfaz Backend ↔ Frontend*).
Objetivo: dejar el **esqueleto** de `app/` listo (carpetas y archivos con indicaciones, sin lógica) para que el equipo reparta el trabajo.

---

## 1. Cómo está planteado el flujo (resumen del SDD)

Léelo antes de tocar nada; la estructura de carpetas existe para soportar este flujo.

**Principio rector:** el ML es una caja negra → *imagen de un estante entra, productos (`object`) y huecos (`missing`) salen*. Todo lo demás (tiendas, cámaras, empleados, turnos, roles, historial, alertas) es la capa de gestión multi-tienda.

**Flujo de negocio**
1. **Super Admin (SA)** crea tiendas y el Admin inicial de cada una.
2. **Admin de tienda (AT)** configura estantes (con `gap_threshold`), cámaras (token que se muestra una sola vez), empleados, turnos y usuarios (Empleado / Viewer).
3. Las imágenes entran por **carga manual** (AT/EM desde la web) o por **cámara con token** (solo puede llamar `POST /inference`).
4. El backend valida credencial, rol y `store_id` → valida imagen → detector + heurística de huecos → guarda imagen en **S3** y metadatos/detecciones en **PostgreSQL** → evalúa umbral del estante → crea **alerta** si corresponde → responde el JSON del contrato.
5. Usuarios autorizados consultan galería, detalle con *overlay* y alertas (`abierta → reconocida → cerrada`, o cierre directo).

**Reglas transversales**
- API versionada bajo `/api/v1`, JWT (access corto + refresh), claims `sub, role, store_id, exp`.
- RBAC por endpoint + aislamiento por `store_id` (recurso de otra tienda → **404**, no 403). SA es la excepción.
- Errores: `{ "detail": "...", "code": "FORBIDDEN_STORE" }`.
- Imágenes servidas por **URL prefirmada** de S3 (corta duración).
- Secretos solo en `.env`. Detector intercambiable sin cambiar el contrato (`source` en cada detección).
- Notificaciones externas **fuera de alcance**: las alertas solo se ven en la interfaz.

---

## 2. Prompt para el agente (Claude Code / Cursor / etc.)

> Copia y pega esto tal cual.

```text
Eres un ingeniero de software senior trabajando en el repo del proyecto final
"Object Detection for In-Store Shelf Inventory Management" (anyone AI, Cohort 26-03).

CONTEXTO
Tenemos un SDD (v0.2) que define la interfaz Backend <-> Frontend. Hoy el servicio
vive en `api/` (main.py, auth.py, db.py, inference.py, gap_heuristic.py, Dockerfile,
static/index.html). Vamos a:
  1) renombrar `api/` a `app/`,
  2) dentro de `app/` crear `backend/` (FastAPI, monolito modular) y `frontend/`,
  3) dejar `frontend/` SOLO como carpeta vacía (con .gitkeep), sin estructura interna,
  4) construir el ESQUELETO completo del backend según el SDD, SIN implementar lógica.

PASO 0 - ENTENDER ANTES DE ACTUAR (obligatorio)
Lee el repo y el archivo ESTRUCTURA_APP.md (sección 1: flujo). Antes de crear nada,
respóndeme en 10-15 líneas cómo entiendes el flujo: roles (SA/AT/EM/VW/Cámara),
multi-tenant por store_id, camino de POST /inference, ciclo de vida de una alerta y
qué partes del código actual (auth.py, db.py, inference.py, gap_heuristic.py, main.py)
corresponden a qué módulo nuevo. Si algo del código actual contradice el SDD, lista
las diferencias. Espera mi confirmación solo si encuentras una contradicción grave.

PASO 1 - MOVER LO EXISTENTE (sin reescribir)
Usa `git mv` para conservar historial:
  api/                  -> app/
  app/main.py           -> app/backend/main.py
  app/auth.py           -> app/backend/core/security.py   (JWT + hashing; la parte de deps va a core/deps.py)
  app/db.py             -> app/backend/db/session.py
  app/inference.py      -> app/backend/services/inference_service.py
  app/gap_heuristic.py  -> app/backend/services/gap_heuristic.py
  app/Dockerfile        -> app/backend/Dockerfile
  app/static/index.html -> app/backend/static/index.html   (transitorio; se elimina cuando exista el frontend)
  app/__init__.py       se mantiene en app/ y se crea app/backend/__init__.py
NO cambies la lógica de esos archivos. Solo ajusta imports/rutas estrictamente
necesarios para que sigan siendo importables, y anota cada ajuste en el reporte final.
Si un archivo mezcla responsabilidades (p. ej. main.py con endpoints), déjalo
completo en su nuevo sitio y agrega un comentario `# TODO(split): mover a routers/<x>.py`.

PASO 2 - CREAR EL ESQUELETO
Crea todos los archivos de la sección 3 de ESTRUCTURA_APP.md que no existan.
Reglas para cada archivo NUEVO:
  - Contiene ÚNICAMENTE un docstring/comentario de módulo en español que indique:
    responsabilidad, endpoints o clases que debe contener, dependencias con otros
    módulos, roles permitidos y requerimientos del SDD que cubre (RF-xx / RNF-xx).
  - Sin imports funcionales, sin clases ni funciones implementadas, sin `pass` innecesario.
  - Los `__init__.py` quedan vacíos.
`app/frontend/` solo lleva un `.gitkeep`.

PASO 3 - AJUSTAR EL RESTO DEL REPO A LA NUEVA RUTA
  - `docker-compose.yml`: build context = raíz del repo, dockerfile = app/backend/Dockerfile;
    comando `uvicorn app.backend.main:app`; montar `./training/weights` como volumen de
    solo lectura (el modelo NO se copia a la imagen); servicios `db` (PostgreSQL) y,
    para desarrollo, un S3 compatible (MinIO) si no hay S3 real. Dejar un bloque
    comentado/vacío para el futuro servicio `frontend`.
  - `.env.example`: agregar las variables listadas en la sección 4 (solo claves, sin valores reales).
  - `requirements.txt`: solo señala (comentario) las dependencias que faltan según la
    sección 4; no instales nada.
  - `data_pipeline/tests/test_gap_heuristic.py` y cualquier otro archivo que importe
    `api.*`: actualizar el import a `app.backend.services.gap_heuristic`.
  - `README.md`: cambiar referencias `api/` -> `app/` y agregar un bloque corto con
    la nueva estructura.

PASO 4 - VERIFICAR Y REPORTAR
  - `grep -rn "api\." --include="*.py" --include="*.yml" --include="Dockerfile" .` no debe
    dejar referencias rotas al paquete viejo.
  - `python -c "import app.backend.main"` debe seguir funcionando si funcionaba antes.
  - Entrega: (a) árbol final, (b) tabla "archivo viejo -> archivo nuevo", (c) lista de
    ajustes de imports/rutas, (d) discrepancias SDD vs código, (e) dudas abiertas.

RESTRICCIONES
  - No toques `data_pipeline/`, `labeling/` ni `training/` salvo los imports del Paso 3.
  - No implementes endpoints, modelos SQLAlchemy ni UI.
  - No inventes carpetas fuera de la sección 3.
  - Commits pequeños: 1) git mv, 2) esqueleto, 3) ajustes de docker/env/imports.
```

---

## 3. Estructura objetivo

Árbol completo del repo (solo `app/` cambia; el resto queda igual).

```text
├── app/                                  # (antes api/)
│   ├── __init__.py
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── main.py                       # [MOVIDO desde api/main.py]
│   │   ├── Dockerfile                    # [MOVIDO desde api/Dockerfile]
│   │   ├── alembic.ini                   # NUEVO
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                 # NUEVO
│   │   │   ├── security.py               # [MOVIDO desde api/auth.py]
│   │   │   ├── deps.py                   # NUEVO
│   │   │   └── errors.py                 # NUEVO
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py                # [MOVIDO desde api/db.py]
│   │   │   ├── models.py                 # NUEVO
│   │   │   └── migrations/               # NUEVO (Alembic)
│   │   │       ├── env.py
│   │   │       └── versions/
│   │   │           └── .gitkeep
│   │   │
│   │   ├── schemas/                      # NUEVO (Pydantic)
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── auth.py
│   │   │   ├── store.py
│   │   │   ├── user.py
│   │   │   ├── camera.py
│   │   │   ├── shelf.py
│   │   │   ├── employee.py
│   │   │   ├── shift.py
│   │   │   ├── inference.py
│   │   │   ├── inspection.py
│   │   │   └── alert.py
│   │   │
│   │   ├── routers/                      # NUEVO (main.py se divide aquí)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── stores.py
│   │   │   ├── users.py
│   │   │   ├── cameras.py
│   │   │   ├── shelves.py
│   │   │   ├── staff.py
│   │   │   ├── inference.py
│   │   │   ├── inspections.py
│   │   │   ├── alerts.py
│   │   │   └── health.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── inference_service.py      # [MOVIDO desde api/inference.py]
│   │   │   ├── gap_heuristic.py          # [MOVIDO desde api/gap_heuristic.py]
│   │   │   ├── storage_service.py        # NUEVO
│   │   │   ├── alert_service.py          # NUEVO
│   │   │   └── audit_service.py          # NUEVO (RF-17)
│   │   │
│   │   ├── static/
│   │   │   └── index.html                # [MOVIDO] transitorio, se borra con el frontend
│   │   │
│   │   └── tests/                        # NUEVO
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── test_auth.py
│   │       ├── test_tenant_isolation.py
│   │       ├── test_inference_contract.py
│   │       ├── test_alerts.py
│   │       └── test_cameras_tokens.py
│   │
│   └── frontend/                         # VACÍA a propósito
│       └── .gitkeep
│
├── data_pipeline/        # sin cambios (solo import en test_gap_heuristic.py)
├── labeling/             # sin cambios
├── training/             # sin cambios
├── .env.example          # se amplía
├── .gitignore
├── docker-compose.yml    # se ajusta
├── README.md             # se ajusta
└── requirements.txt
```

### 3.1 Qué debe indicar cada archivo nuevo (docstring de módulo)

#### `app/backend/` raíz
| Archivo | Indicación |
|---|---|
| `main.py` | Crea la app FastAPI, monta los routers bajo `/api/v1`, configura CORS (origen = `VITE_API_URL` del front), registra los handlers de `core/errors.py` y logs estructurados (RNF-07, RNF-08). No contiene endpoints. |
| `alembic.ini` | Configuración de Alembic apuntando a `db/migrations`; URL tomada de `core/config.py`. |

#### `core/`
| Archivo | Indicación |
|---|---|
| `config.py` | Clase `Settings` (pydantic-settings) leída desde `.env`: DB, S3, JWT, tamaño máx. de imagen, `conf` por defecto, ruta del modelo (RNF-06). |
| `security.py` | *(existente, ex `auth.py`)* Hash de contraseñas, creación/validación de JWT access y refresh, hash y verificación de token de cámara. Claims: `sub, role, store_id, exp` (RNF-01). |
| `deps.py` | Dependencias FastAPI: `get_db`, `get_current_user`, `require_role(*roles)`, `get_tenant` (filtra por `store_id` del token; SA exento), `get_camera_from_token` (token de dispositivo, solo válido en `POST /inference`) (RF-08, RNF-02). |
| `errors.py` | Excepciones de dominio y handler global con formato `{detail, code}`. Códigos mínimos: `UNAUTHORIZED`, `FORBIDDEN_ROLE`, `FORBIDDEN_STORE`, `NOT_FOUND`, `INVALID_IMAGE`, `VALIDATION_ERROR`. Recurso de otra tienda → 404. |

#### `db/`
| Archivo | Indicación |
|---|---|
| `session.py` | *(existente, ex `db.py`)* Engine y sesión SQLAlchemy sobre PostgreSQL. |
| `models.py` | Tablas: `stores, users, employees, shifts, shelves, cameras, inspections, detections, alerts, audit_log` con los campos del SDD §6. Estados de alerta: `open / acknowledged / closed`. |
| `migrations/` | Alembic: `env.py` + `versions/`. Primera migración = esquema inicial del SDD. |

#### `schemas/` (Pydantic request/response)
| Archivo | Indicación |
|---|---|
| `common.py` | Paginación (`limit`, `offset`), respuesta de error, tipos compartidos (UUID, fechas ISO 8601 UTC). |
| `auth.py` | Login request, par de tokens, refresh, perfil de `/auth/me`. |
| `store.py` | Crear/editar/detalle de tienda (con admin inicial opcional). |
| `user.py` | Crear/editar usuario; roles permitidos por quien crea. |
| `camera.py` | Alta de cámara; la respuesta de alta y de `rotate-token` incluye el token **una sola vez**. |
| `shelf.py` | Estante/zona con `gap_threshold`. |
| `employee.py` | Empleado (con `user_id` opcional). |
| `shift.py` | Turno: `weekday`, `start_time`, `end_time`. |
| `inference.py` | Contrato de `POST /inference` (SDD §8.5.1): `inspection_id, shelf_id, created_at, model_version, image{width,height}, summary{n_objects,n_missing,latency_ms}, detections[{class,confidence,bbox,source?}], alert{created,severity}`. bbox = `[x1,y1,x2,y2]` en píxeles de la imagen original. |
| `inspection.py` | Item de lista, detalle con detecciones, respuesta de URL prefirmada. |
| `alert.py` | Listado con filtros `status`, `severity`; `PATCH` para reconocer/cerrar. |

#### `routers/`
| Archivo | Endpoints (prefijo `/api/v1`) | Roles |
|---|---|---|
| `auth.py` | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` | Público / autenticado |
| `stores.py` | `POST/GET /stores`, `GET/PATCH /stores/{id}` | SA; AT propia (detalle) |
| `users.py` | `POST/GET /stores/{id}/users`, `PATCH /users/{id}` | SA, AT propia |
| `cameras.py` | `POST/GET /stores/{id}/cameras`, `PATCH/DELETE /cameras/{id}`, `POST /cameras/{id}/rotate-token` | SA, AT propia |
| `shelves.py` | `POST/GET /stores/{id}/shelves`, `PATCH /shelves/{id}` | SA, AT propia (GET: cualquier rol de la tienda) |
| `staff.py` | Empleados: `POST/GET /stores/{id}/employees`, `PATCH /employees/{id}`. Turnos: `POST /employees/{id}/shifts`, `GET /stores/{id}/shifts`, `PATCH/DELETE /shifts/{id}` | SA, AT propia |
| `inference.py` | `POST /inference` (multipart: `image`, `camera_id?`, `shelf_id?`, `conf?`). Orquesta: valida imagen → detector → S3 → BD → alerta → respuesta. | SA, AT, EM o token de cámara |
| `inspections.py` | `GET /inspections` (filtros `shelf_id, camera_id, from, to`), `GET /inspections/{id}`, `GET /inspections/{id}/image`, `DELETE /inspections/{id}` | Lectura: rol de la tienda; borrar: SA, AT propia |
| `alerts.py` | `GET /stores/{id}/alerts`, `PATCH /alerts/{id}` | Lectura: rol de la tienda; acción: SA, AT, EM |
| `health.py` | `GET /health` | Público |

> Cada router **solo** valida/enruta y delega en `services/`; nada de lógica de negocio dentro del router.

#### `services/`
| Archivo | Indicación |
|---|---|
| `inference_service.py` | *(existente)* Carga el modelo desde `MODEL_PATH` (por defecto `training/weights/B_e35/weights/best.pt`), corre el detector y devuelve detecciones. Intercambiable sin tocar el contrato (RNF-04). Expone `model_version`. |
| `gap_heuristic.py` | *(existente, sin cambios funcionales)* Genera huecos candidatos. Sus detecciones llevan `source: "heuristic"`. |
| `storage_service.py` | Subir imagen original a S3 (boto3), generar URL prefirmada de corta duración, borrar objeto. |
| `alert_service.py` | Regla: `n_missing` vs `gap_threshold` del estante → crear alerta y severidad; transiciones `open → acknowledged → closed` y `open → closed` (RF-14, RF-15). Opcional: asociar empleado en turno (RF-18). |
| `audit_service.py` | Registrar acciones administrativas en `audit_log` (RF-17). Prioridad baja. |

#### `tests/`
| Archivo | Indicación |
|---|---|
| `conftest.py` | Fixtures: BD de prueba, cliente HTTP, usuarios por rol, dos tiendas, cámara con token. |
| `test_auth.py` | Login, refresh, expiración, `/auth/me`. |
| `test_tenant_isolation.py` | Ninguna consulta cruza `store_id` (404); matriz de permisos del SDD §2.2. |
| `test_inference_contract.py` | La respuesta cumple el contrato; imagen inválida → 422/400; bbox en píxeles originales. |
| `test_alerts.py` | Se crea alerta solo al superar el umbral; ciclo de vida. |
| `test_cameras_tokens.py` | Token visible una vez, solo hash en BD, solo sirve para `/inference`, rotación invalida el anterior. |

#### `app/frontend/`
Solo `.gitkeep`. La estructura interna (React + Vite + TS, SDD §13) **se decide después**: el stack sigue como decisión pendiente.

---

## 4. Ajustes fuera de `app/`

**`.env.example`** (solo claves):
```text
DATABASE_URL=
S3_ENDPOINT_URL=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_REGION=
PRESIGNED_URL_TTL_SECONDS=
JWT_SECRET=
JWT_ACCESS_TTL_MINUTES=
JWT_REFRESH_TTL_DAYS=
MODEL_PATH=
DEFAULT_CONF=
MAX_IMAGE_MB=
CORS_ORIGINS=
```

**`requirements.txt`** (verificar que estén): `fastapi`, `uvicorn`, `python-multipart`, `sqlalchemy`, `psycopg2-binary` (o `asyncpg`), `alembic`, `pydantic-settings`, `pyjwt` (o `python-jose`), `passlib[bcrypt]`, `boto3`, `pillow`, `ultralytics`, `pytest`, `httpx`.

**`docker-compose.yml`**: servicios `backend` (context raíz, `app/backend/Dockerfile`, volumen `./training/weights:/models:ro`), `db` (PostgreSQL), `minio` (solo dev), y bloque `frontend` comentado.

**Rutas que se rompen con el renombre** (revisar con grep): `uvicorn api.main:app`, `COPY api/ ...` en el Dockerfile, imports `from api...` en `data_pipeline/tests/test_gap_heuristic.py`, y menciones en `README.md`.

---

## 5. Puntos del SDD a aclarar con el equipo

1. **Quién crea admins:** §8.2 dice que `POST /stores/{id}/users` crea "admin, empleado o viewer" para `SA, AT propia`, pero RF-06 y la matriz de permisos dicen que el AT solo crea Empleado/Viewer y que solo el SA crea admins. Propuesta: el AT no puede asignar rol `admin`.
2. **Alertas para Viewer:** la matriz marca VW sin permiso en alertas, pero §11 le da lectura. Propuesta: VW lee, no actúa.
3. **Estados de alerta:** unificar valores (`open / acknowledged / closed`) entre `models.py`, schemas y front.
4. **Dashboard de tienda:** el SDD no define un endpoint de agregados (alertas abiertas, huecos por estante). Decidir si se calcula en el front con los listados existentes o se agrega un `GET /stores/{id}/dashboard`.
5. **Retención de imágenes/datos de empleados, idioma e umbrales de alerta:** siguen en "Decisiones pendientes" (§16 del SDD); no bloquean el esqueleto.