# Software Design Document (SDD) — Interfaz Backend
**Object Detection for In-Store Shelf Inventory Management**

Requerimientos, arquitectura, endpoints y flujos de la capa de Backend de la aplicación.

- **Proyecto final:** Cohort 26-03 - anyone AI
- **Versión:** 0.4 (implementación incremental)
- **Fecha:** Octubre 2026
- **Estado:** Backend operativo — cierre de Docker en progreso

### Estado de implementación (actualizado 19-10-2026)

La Fase 0 (auditoría) y la Fase 1 (sincronización del modelo) están completadas.
La Fase 2 tiene implementado y verificado el núcleo de configuración, modelos
multi-tenant, hashing scrypt, JWT access/refresh/logout, dependencias de
autenticación/RBAC, aislamiento básico por `store_id`, routers de autenticación
y tiendas, migración inicial Alembic, logging JSON, formato global de errores,
CORS configurable y validación de tipo real y resolución de imágenes. La suite
actual ejecuta **23 tests pasando**.

El alcance restante de la Fase 2 es ampliar la matriz de pruebas de tenant/RBAC
para todos los recursos cuando existan sus routers.

La Fase 3 incluye los routers de estantes, cámaras, usuarios y personal. Ya
están disponibles creación, listado, edición, asociación a estante, rotación
de tokens, usuarios de tienda, empleados, turnos sin solapamiento y settings.
El hash del token se persiste en la base de datos y el valor plano solo se
devuelve al crear o rotar el dispositivo. La cámara ya puede autenticarse en
`POST /inference`; la request actualiza `last_seen` y persiste la inspección,
la imagen original y sus detecciones. Faltan pruebas específicas de toda la
gestión y asociación automática del empleado en turno.

La Fase 4 inició con storage local, historial de inspecciones y alertas. Las
imágenes se guardan fuera de Git bajo `app/data/uploads/`, con una clave por
tienda e inspección. Se implementaron filtros, detalle, imagen protegida,
eliminación autorizada, exportación NDJSON, alertas por encima de
`gap_threshold`, anti-spam por estante, contador y transiciones `open`,
`acknowledged` y `closed`. El backend S3 y las pruebas de integración de este
flujo siguen pendientes.

La Fase 5 incluye dashboard de tienda, dashboard global para Super Admin,
resumen por cámara, exportación JSON, exportación masiva NDJSON y métricas de
uso con p50/p95 y costo estimado configurable. Las pruebas focalizadas de
storage, alertas y contrato de exportación están incorporadas. La integración
frontend y pruebas de endpoint completas quedan pendientes.

La Fase 6 está avanzada. `Dockerfile` usa usuario no-root, healthcheck y
volumen persistente para uploads; `docker-compose.yml` valida con PostgreSQL,
volúmenes para datos y variables de entorno. `docker compose build backend`
terminó correctamente y `docker compose config`, Alembic y compilación Python
también fueron verificados. Se añadieron `docs/API.md` y actualizaciones al
README. Falta añadir smoke test Windows y cerrar la matriz final de cobertura.

Cambios de esta versión 0.4:
- La estructura real del backend es `app/backend/`, no `api/`.
- Se añade el estado verificable de implementación por fases.
- Se incorpora la migración inicial para el modelo multi-tenant.
- Se documentan dashboards, exportaciones JSON/NDJSON, métricas y storage local.
- Se verifica el build Docker y se excluyen dependencias locales del contexto.
- Se mantienen los requisitos de la versión 0.2; las extensiones de negocio
  continúan sujetas a implementación en las fases posteriores.

---

### Equipo
- Gustavo Zaracho (Fellow)
- Francisco Peregrina (Fellow)
- Mateo Navas (Fellow)
- Luis González (Fellow)
- Ivan Reyes (Fellow)
- Victoria Chacín (Fellow)
- Jerónimo Riveros (Fellow)
- Jesús Zambrano (Mentor)

*Los puntos marcados como [POR DEFINIR] requieren decisión.*

---

## 1. Introducción

### 1.1. Propósito
Este documento define el diseño de la interfaz entre el Backend y el Frontend de la aplicación: roles, requerimientos, endpoints, modelo de datos, estructura de carpetas y flujos de uso. Es el acuerdo común del equipo sobre qué se construye, cómo se comunican ambas capas y qué queda fuera.

### 1.2. Principio rector
> **Idea central:**  
> A nivel de aplicación de ML, el sistema recibe una imagen de un estante y retorna los productos detectados y los espacios vacíos (huecos) candidatos. Todo lo demás (tiendas, cámaras, empleados, horarios, roles e historial) es la capa de gestión que permite operar ese servicio en varias tiendas.

### 1.3. Cómo funciona el producto
1. Un Super Admin registra las tiendas/minimercados (público objetivo).
2. El Admin de tienda configura cámaras, estantes, empleados y horarios, y crea los usuarios de su tienda.
3. Las imágenes entran por carga manual (Admin o Empleado) o desde una cámara con su token.
4. El sistema retorna productos detectados y huecos, guarda la inspección y genera una alerta si corresponde.
5. Los usuarios autorizados consultan las fotos y sus resultados.

### 1.4. Fuera del alcance de este documento
Entrenamiento y evaluación de modelos, estrategias de etiquetado, comparativas de modelos, costos y dimensionamiento de infraestructura, y análisis de mercado se documentan por separado. Aquí el detector se trata como una caja negra con un contrato claro: imagen de entrada, detecciones de salida.

### 1.5. Glosario
| Término | Definición |
| :--- | :--- |
| `object` | Clase detectada: producto presente en el estante. |
| `missing` | Clase detectada: espacio vacío candidato donde debería haber un producto. |
| Inspección | Resultado de procesar una imagen: imagen original, detecciones, conteos y metadatos. |
| Alerta | Aviso generado cuando los huecos de una inspección superan el umbral del estante. |
| Estante / zona | Unidad física monitoreada; puede asociarse a una o más cámaras. |
| Overlay | Dibujo de las cajas detectadas sobre la imagen en el Frontend. |
| RBAC | *Role-Based Access Control*: permisos según el rol. |
| Tenant / tienda | Aislamiento lógico de datos por `store_id`. |

---

## 2. Actores, roles y permisos

### 2.1. Actores
| Rol | Responsabilidad |
| :--- | :--- |
| **Super Admin (SA)** | Registra y gestiona tiendas y sus administradores; visión global de la plataforma. |
| **Admin de tienda (AT)** | Configura cámaras, estantes, empleados, turnos y usuarios de su tienda; gestiona alertas. |
| **Empleado (EM)** | Personal de la tienda; sube imágenes, consulta inspecciones y atiende alertas. |
| **Usuario / Viewer (VW)** | Solo lectura: consulta fotos e inspecciones con sus detecciones. |
| **Cámara** | Actor técnico; envía imágenes con un token propio y limitado a inferencia. |

### 2.2. Matriz de permisos
| Capacidad | SA | AT | EM | VW |
| :--- | :---: | :---: | :---: | :---: |
| Crear / editar / desactivar tiendas | $\checkmark$ | | | |
| Crear admins de tienda | $\checkmark$ | | | |
| Gestionar cámaras y estantes | | $\checkmark^1$ | | |
| Gestionar empleados y turnos | | $\checkmark^1$ | | |
| Crear usuarios de la tienda | | $\checkmark^1$ | | |
| Subir imagen para inferencia | | $\checkmark^1$ | $\checkmark^1$ | |
| Ver inspecciones y fotos | | $\checkmark^1$ | $\checkmark^1$ | $\checkmark^1$ |
| Reconocer / cerrar alertas | | $\checkmark^1$ | $\checkmark^{*1}$ | |
| Eliminar inspecciones | $\checkmark$ | $\checkmark^1$ | | |

$^1$ *Limitado a los datos de su propia tienda (`store_id`).*

---

## 3. Alcance de la versión 1

### 3.1. Dentro del alcance
- Autenticación con JWT y RBAC de cuatro roles, con aislamiento por tienda.
- Registro de tiendas, cámaras, estantes/zonas, empleados, turnos y usuarios.
- Carga manual de imágenes por Admin y Empleado, y envío desde cámara con token.
- Endpoint de inferencia: imagen $\rightarrow$ productos + huecos con confianza y bounding boxes.
- Almacenamiento de imágenes (S3) y de metadatos y resultados (PostgreSQL).
- Historial de inspecciones con overlay y filtros.
- Alertas por huecos, visibles en la interfaz.
- Frontend web responsive con navegación por rol.

### 3.2. Fuera del alcance
- Reconocimiento de SKU, marca o producto específico.
- Inventario valorizado e integraciones con POS/ERP o reposición automática.
- Captura continua por video/streaming (la cámara envía imágenes; no hay pull de RTSP).
- Notificaciones externas (email, SMS, WhatsApp, push): las alertas se muestran solo en la interfaz.
- Aplicación móvil nativa.
- Facturación y planes de cobro.
- Edición manual de cajas o re-etiquetado desde la interfaz.
- Re-entrenamiento o cambio de modelo desde la interfaz.

### 3.3. Candidatos a fase 2
Notificaciones externas, captura programada por pull, tendencias por estante, exportación de reportes y panel de administración de versiones de modelo.

---

## 4. Requerimientos

### 4.1. Requerimientos funcionales
| ID | Requerimiento | Prioridad |
| :--- | :--- | :---: |
| **RF-01** | El SA puede crear, editar, desactivar y listar tiendas. | Alta |
| **RF-02** | El SA puede crear el Admin inicial de cada tienda. | Alta |
| **RF-03** | El AT puede registrar cámaras (nombre, ubicación, estante) y rotar su token. | Alta |
| **RF-04** | El AT puede definir estantes/zonas con su umbral de huecos. | Media |
| **RF-05** | El AT puede registrar empleados y asignar turnos y horarios. | Alta |
| **RF-06** | El AT puede crear usuarios con rol Empleado o Viewer. | Alta |
| **RF-07** | El sistema autentica con correo y contraseña y emite JWT de acceso y de refresco. | Alta |
| **RF-08** | Cada endpoint se restringe por rol y por `store_id`. | Alta |
| **RF-09** | Admin y Empleado pueden subir una imagen desde la web; la cámara puede enviarla con su token. | Alta |
| **RF-10** | El sistema retorna productos (`object`) y huecos (`missing`) con bbox y confianza. | Alta |
| **RF-11** | La inferencia admite parámetros opcionales: `conf`, `camera_id`, `shelf_id`. | Media |
| **RF-12** | El sistema guarda imagen original, detecciones y métricas de cada inspección. | Alta |
| **RF-13** | Los usuarios autorizados listan, filtran y ven inspecciones con overlay. | Alta |
| **RF-14** | Se crea una alerta cuando los huecos superan el umbral del estante. | Media |
| **RF-15** | Admin y Empleado pueden reconocer y cerrar alertas. | Media |
| **RF-16** | Las alertas se muestran en la interfaz (contador y lista). | Media |
| **RF-17** | El sistema registra auditoría de acciones administrativas. | Baja |
| **RF-18** | Los turnos permiten asociar inspecciones y alertas al empleado en turno. | Baja |

### 4.2. Requerimientos no funcionales
| ID | Requerimiento | Categoría |
| :--- | :--- | :--- |
| **RNF-01** | Contraseñas con hash robusto; JWT de acceso con expiración corta y refresco. | Seguridad |
| **RNF-02** | Ninguna consulta cruza datos entre tiendas (`store_id`). | Seguridad |
| **RNF-03** | Validación de imagen (tipo, tamaño máximo, decodificación) antes de inferir. | Robustez |
| **RNF-04** | El detector es intercambiable sin cambiar el contrato de la API. | Mantenibilidad |
| **RNF-05** | El Frontend es responsive y usable desde el celular dentro de la tienda. | Usabilidad |
| **RNF-06** | Secretos solo por variables de entorno (`.env`); nunca en el repositorio. | Seguridad |
| **RNF-07** | API versionada bajo `/api/v1` y documentada con OpenAPI. | Mantenibilidad |
| **RNF-08** | Logs estructurados y endpoint `/health` para operación. | Operación |
| **RNF-09** | Backend y Frontend empaquetados con Docker. | Portabilidad |

---

# Parte I: Backend

## 5. Arquitectura del Backend

### 5.1. Patrón
Monolito modular: un único servicio FastAPI con módulos aislados. Simplifica el despliegue, separa responsabilidades y permite cambiar el detector sin tocar el resto.

#### Esquema de Arquitectura Lógica
- **Frontend web**: Pantallas por rol $\rightarrow$ Cliente API (JWT + refresh)
- **Cámara / Gateway local**: POST Imagen + token
- **Backend FastAPI**:
  - Gateway (Auth + RBAC + Tenant)
  - Gestión (tiendas, cámaras, estantes, empleados, turnos, usuarios) $\rightarrow$ PostgreSQL
  - Inspecciones y alertas $\rightarrow$ PostgreSQL & S3 imágenes
  - Servicio de Inferencia (detector + heurística de huecos)

### 5.2. Módulos
| Módulo | Responsabilidad |
| :--- | :--- |
| `auth` | Login, emisión y validación de JWT, hash de contraseñas, dependencias RBAC. |
| `tenants` | Tiendas, estantes/zonas y aislamiento por `store_id`. |
| `devices` | Cámaras, tokens de dispositivo y su rotación. |
| `staff` | Empleados, turnos y horarios. |
| `inference` | Recibe la imagen, invoca al detector y la heurística de huecos, devuelve detecciones. |
| `inspections` | Persistencia de imágenes y resultados; consulta e historial. |
| `alerts` | Reglas de umbral y ciclo de vida de alertas. |
| `storage/db` | Acceso a S3 (boto3) y PostgreSQL. |

### 5.3. Estructura de carpetas

#### 5.3.1. Estado actual de `api/`
```text
api/
├── static/
│   └── index.html
├── __init__.py
├── auth.py
├── db.py
├── Dockerfile
├── gap_heuristic.py
├── inference.py
└── main.py
```

#### 5.3.2. Estructura propuesta
Los archivos existentes se reubican sin reescribirse; `main.py` se divide en routers por dominio.

```text
api/
├── main.py                   # crea la app, monta routers, CORS
├── core/
│   ├── config.py             # settings desde env
│   ├── security.py           # JWT y hashing (desde auth.py)
│   ├── deps.py               # usuario actual, require_role, tenant
│   └── errors.py             # excepciones y formato de error
├── db/
│   ├── session.py            # engine y sesión (desde db.py)
│   ├── models.py             # tablas SQLAlchemy
│   └── migrations/           # Alembic
├── schemas/                  # Pydantic: request/response por dominio
├── routers/
│   ├── auth.py
│   ├── stores.py
│   ├── users.py
│   ├── cameras.py
│   ├── shelves.py
│   ├── staff.py              # empleados y turnos
│   ├── inference.py
│   ├── inspections.py
│   ├── alerts.py
│   └── health.py
├── services/
│   ├── inference_service.py  # detector (desde inference.py)
│   ├── gap_heuristic.py      # sin cambios funcionales
│   ├── storage_service.py    # S3 y URLs prefirmadas
│   └── alert_service.py
├── tests/
├── Dockerfile
└── __init__.py
```

---

## 6. Modelo de datos

### Entidades y campos clave
| Entidad | Campos clave |
| :--- | :--- |
| `stores` | `id`, `name`, `address`, `status`, `created_at` |
| `users` | `id`, `store_id` (nulo para SA), `email`, `password_hash`, `role`, `is_active` |
| `employees` | `id`, `store_id`, `user_id` (opcional), `full_name`, `position` |
| `shifts` | `id`, `store_id`, `employee_id`, `weekday`, `start_time`, `end_time` |
| `shelves` | `id`, `store_id`, `name`, `zone`, `gap_threshold` |
| `cameras` | `id`, `store_id`, `shelf_id`, `name`, `location`, `token_hash`, `status`, `last_seen` |
| `inspections` | `id`, `store_id`, `camera_id`, `shelf_id`, `image_key`, `model_version`, `n_objects`, `n_missing`, `latency_ms`, `created_by`, `created_at` |
| `detections` | `id`, `inspection_id`, `class`, `x1`, `y1`, `x2`, `y2`, `confidence` |
| `alerts` | `id`, `store_id`, `inspection_id`, `shelf_id`, `severity`, `status`, `acked_by`, `created_at` |
| `audit_log` | `id`, `actor_id`, `action`, `entity`, `entity_id`, `ts` |

### Relaciones principales (Modelo ER)
- `STORES` registra `CAMERAS`, define `SHELVES`, emplea `EMPLOYEES` y tiene `USERS`.
- `SHELVES` es monitoreada por `CAMERAS` y evalúa `INSPECTIONS`.
- `EMPLOYEES` cumple `SHIFTS`.
- `USERS` sube `INSPECTIONS` y actúa en `AUDIT_LOG`.
- `CAMERAS` genera `INSPECTIONS`.
- `INSPECTIONS` contiene `DETECTIONS` y dispara `ALERTS`.

---

## 7. Seguridad

- **Autenticación:** `POST /auth/login` entrega un *access token* (corto) y un *refresh token*. El cliente envía el header `Authorization: Bearer <jwt>`.
- **Claims del JWT:** `sub`, `role`, `store_id`, `exp`.
- **RBAC:** Cada endpoint declara los roles permitidos.
- **Aislamiento de tienda:** Todo acceso filtra por el `store_id` del token, salvo SA. Un recurso de otra tienda responde `404`.
- **Cámaras:** El token se guarda solo como hash, se muestra una única vez y solo permite `POST /inference`.
- **Imágenes:** Se entregan con URLs prefirmadas de S3 de corta duración.
- **Secretos:** Solo en variables de entorno (plantilla en `.env.example`).

### Flujo de autorización por rol y tienda
1. **Request** con JWT o Token de cámara.
2. ¿Credencial válida?
   - **No:** `401 Unauthorized`.
   - **Sí:** Evaluar rol.
3. ¿Rol permitido en el endpoint?
   - **No:** `403 Forbidden`.
   - **Sí:** Evaluar tienda/tenant.
4. ¿Es Super Admin (`super_admin`)?
   - **Sí:** Ejecutar.
   - **No:** ¿`store_id` del recurso es igual a `store_id` del token?
     - **Sí:** Ejecutar.
     - **No:** `404 Not Found`.

---

## 8. Especificación de endpoints

*Prefijo base `/api/v1`. Formato JSON, salvo la carga de imágenes (`multipart/form-data`). Los listados aceptan `limit` y `offset`. Códigos: 200/201 éxito, 400/422 validación, 401 sin autenticar, 403 sin permiso, 404 no encontrado. Abreviaturas de rol: SA, AT, EM, VW; "propia" = limitado a su tienda.*

### 8.1. Autenticación
| Método | Endpoint | Descripción | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Credenciales $\rightarrow$ `access` y `refresh` token | Público |
| `POST` | `/auth/refresh` | Renueva el `access` token | Autenticado |
| `POST` | `/auth/logout` | Invalida el `refresh` token | Autenticado |
| `GET` | `/auth/me` | Perfil, rol y tienda del usuario | Autenticado |

### 8.2. Tiendas y usuarios
| Método | Endpoint | Descripción | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/stores` | Crear tienda (con admin inicial opcional) | SA |
| `GET` | `/stores` | Listar tiendas | SA |
| `GET` | `/stores/<id>` | Detalle de tienda | SA, AT propia |
| `PATCH` | `/stores/<id>` | Editar, activar o desactivar | SA |
| `POST` | `/stores/<id>/users` | Crear usuario (admin, empleado o viewer) | SA, AT propia |
| `GET` | `/stores/<id>/users` | Listar usuarios de la tienda | SA, AT propia |
| `PATCH` | `/users/<id>` | Editar rol, estado o contraseña | SA, AT propia |

### 8.3. Cámaras y estantes
| Método | Endpoint | Descripción | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/stores/<id>/cameras` | Registrar cámara; devuelve el token una sola vez | SA, AT propia |
| `GET` | `/stores/<id>/cameras` | Listar cámaras y estado (`last_seen`) | SA, AT propia |
| `PATCH` | `/cameras/<id>` | Editar metadatos, estante o estado | SA, AT propia |
| `POST` | `/cameras/<id>/rotate-token` | Rotar token de dispositivo | SA, AT propia |
| `DELETE` | `/cameras/<id>` | Eliminar cámara | SA, AT propia |
| `POST` | `/stores/<id>/shelves` | Crear estante/zona con `gap_threshold` | SA, AT propia |
| `GET` | `/stores/<id>/shelves` | Listar estantes | Rol de la tienda |
| `PATCH` | `/shelves/<id>` | Editar estante | SA, AT propia |

### 8.4. Empleados y horarios
| Método | Endpoint | Descripción | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/stores/<id>/employees` | Crear empleado | SA, AT propia |
| `GET` | `/stores/<id>/employees` | Listar empleados | SA, AT propia |
| `PATCH` | `/employees/<id>` | Editar o desactivar | SA, AT propia |
| `POST` | `/employees/<id>/shifts` | Crear turno (día, hora inicio y fin) | SA, AT propia |
| `GET` | `/stores/<id>/shifts` | Calendario de turnos de la tienda | SA, AT propia |
| `PATCH` | `/shifts/<id>` | Editar turno | SA, AT propia |
| `DELETE` | `/shifts/<id>` | Eliminar turno | SA, AT propia |

### 8.5. Inferencia e inspecciones
| Método | Endpoint | Descripción | Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/inference` | Imagen $\rightarrow$ detecciones; guarda la inspección | SA, AT, EM o token de cámara |
| `GET` | `/inspections` | Listar con filtros `shelf_id`, `camera_id`, `from`, `to` | Rol de la tienda |
| `GET` | `/inspections/<id>` | Detalle con detecciones | Rol de la tienda |
| `GET` | `/inspections/<id>/image` | URL prefirmada de la imagen original | Rol de la tienda |
| `DELETE` | `/inspections/<id>` | Eliminar inspección y archivo | SA, AT propia |

#### 8.5.1. Contrato de `POST /inference`

**Request** (`multipart/form-data`):
- `image`: archivo JPG o PNG (obligatorio)
- `camera_id`: `uuid` (opcional)
- `shelf_id`: `uuid` (opcional)
- `conf`: `float` entre 0 y 1 (opcional, valor por defecto del servidor)

**Response** (`200 OK`):
```json
{
  "inspection_id": "uuid",
  "shelf_id": "uuid",
  "created_at": "2026-10-08T14:30:00Z",
  "model_version": "yolo26s-B_e35",
  "image": {
    "width": 1024,
    "height": 768
  },
  "summary": {
    "n_objects": 147,
    "n_missing": 3,
    "latency_ms": 55.7
  },
  "detections": [
    {
      "class": "object",
      "confidence": 0.93,
      "bbox": [10, 20, 50, 80]
    },
    {
      "class": "missing",
      "confidence": 0.71,
      "bbox": [55, 20, 95, 80],
      "source": "heuristic"
    }
  ],
  "alert": {
    "created": true,
    "severity": "medium"
  }
}
```

*Las coordenadas `bbox` están en píxeles de la imagen original: $[x1, y1, x2, y2]$. El campo `source` indica si el hueco proviene de la heurística o del modelo de dos clases, de modo que el contrato no cambia cuando se actualice el detector.*

**Formato de error ($4xx/5xx$):**
```json
{
  "detail": "Mensaje legible",
  "code": "FORBIDDEN_STORE"
}
```

### 8.6. Alertas y salud
| Método | Endpoint | Descripción | Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/stores/<id>/alerts` | Listar alertas (filtros `status`, `severity`) | Rol de la tienda |
| `PATCH` | `/alerts/<id>` | Reconocer o cerrar alerta | SA, AT, EM |
| `GET` | `/health` | Estado del servicio | Público |

---

## 9. Flujos del Backend

### 9.1. Alta de tienda y configuración (Onboarding)
1. Super Admin inicia sesión.
2. Registra tienda.
3. Crea Admin de tienda.
4. Admin inicia sesión.
5. Define estantes y umbral de huecos.
6. Registra cámaras y recibe token una sola vez.
7. Registra empleados.
8. Asigna turnos y horarios.
9. Crea usuarios: Empleado / Viewer.
10. **Tienda operativa.**

### 9.2. Procesamiento de una imagen
1. **Empleado/Admin / Cámara** $\rightarrow$ Envía `POST /api/v1/inference` (imagen, `shelf_id` / token).
2. **Backend (Gateway)**: Valida credencial, rol y tienda (`store_id`).
3. **Servicio de Inferencia**: Recibe imagen validada $\rightarrow$ Retorna productos + huecos candidatos.
4. **Backend (Gateway)**:
   - Guarda la imagen original en **S3**.
   - Guarda la inspección y detecciones en **PostgreSQL**.
   - Evalúa el umbral del estante y crea alerta en **PostgreSQL** si aplica.
5. **Backend** $\rightarrow$ Devuelve respuesta `200 JSON` (`inspection_id`, `detections`, `summary`, `alert`).

### 9.3. Ciclo de vida de una alerta
- **Disparador:** Una inspección supera el umbral de huecos.
- **Estado Inicial:** `Abierta`
- **Opciones de Transición:**
  1. Empleado o Admin la reconoce $\rightarrow$ Estado: `Reconocida` $\rightarrow$ Se repone el estante $\rightarrow$ Estado: `Cerrada`.
  2. Cierre directo $\rightarrow$ Estado: `Cerrada`.

---

## 15. Contrato de integración Back-Front (Puntos Clave del Backend)

| Aspecto | Acuerdo |
| :--- | :--- |
| **URL base** | Variable `VITE_API_URL`; todas las rutas bajo `/api/v1`. |
| **Autenticación** | Header `Authorization: Bearer <jwt>`; ante 401 el cliente intenta `/auth/refresh` una vez y, si falla, va a Login. |
| **Fechas** | ISO 8601 en UTC; el Frontend convierte a hora local. |
| **Coordenadas** | `bbox` = $[x1, y1, x2, y2]$ en píxeles de la imagen original; el Frontend escala según el tamaño mostrado. |
| **Errores** | Cuerpo `{ detail, code }`; el Frontend mapea `code` a mensajes de usuario. |
| **Paginación** | Parámetros `limit` y `offset`. |
| **Imágenes** | Se solicitan con `/inspections/<id>/image` y expiran (URLs prefirmadas de S3); no se cachean URLs más allá de su vigencia. |

---

## 16. Decisiones pendientes (Relacionadas a Backend)

1. Políticas para la retención de imágenes y de datos de empleados.
2. Idioma por defecto de los mensajes de error/API.
3. Umbral y severidad de alertas: valores por defecto y si son configurables por estante.