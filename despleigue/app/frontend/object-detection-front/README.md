# ShelfVision · Front

Panel web (Next.js 16 + shadcn/ui + Zustand) para el API de detección de producto faltante.

## Arranque

```bash
cp .env.example .env.local   # API_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
```

El navegador solo habla con `/backend/*`; Next lo reescribe a `{API_URL}/api/v1/*`
(ver `next.config.ts`), por lo que no hace falta configurar CORS en el backend.

## Estructura

| Ruta | Qué hace | Endpoints |
|---|---|---|
| `/login` | Correo + contraseña, o API key | `auth/login`, `auth/me` |
| `/` | Resumen de tienda (o global para super admin) | `dashboard/*`, `cameras/summary`, `metrics/usage` |
| `/analyze` | Sube una imagen y ve cajas de productos/huecos | `inference`, `models` |
| `/inspections` | Historial, imagen con cajas, export JSON/JSONL, borrar | `inspections*` |
| `/alerts` | Atender/cerrar alertas | `stores/{id}/alerts`, `alerts/{id}` |
| `/cameras` `/shelves` | CRUD, token de cámara (crear/rotar) | `stores/{id}/cameras`, `shelves` |
| `/team` | Usuarios, empleados y turnos semanales | `users`, `employees`, `shifts` |
| `/settings` | Horario, umbral de confianza, enfriamiento | `stores/{id}/settings` |
| `/stores` | Tiendas (super admin) | `stores` |
| `/system` | Health, catálogo de modelos, revisión de comparaciones | `health`, `models`, `comparisons*` |

## Arquitectura

```
services/   llamadas al API, sin React (una por recurso)
hooks/queries/   TanStack Query: useQuery/useMutation + keys (keys.ts)
hooks/      logica de pantalla (use-analyzer, use-camera-manager, use-edit-dialog…)
components/<feature>/   UI presentacional; reciben datos y callbacks
app/(app)/<ruta>/page.tsx   paginas delgadas que solo componen
lib/api/    cliente HTTP (refresh de token en 401) y tipos del backend
stores/     Zustand: sesion + tienda activa, y preferencias de analisis
```

- Los errores de mutaciones y los mensajes de exito salen como toast desde `lib/query-client.ts`
  (`meta: { success }` en cada mutacion).
- Crear/editar invalida las queries afectadas, por eso el selector de tiendas se actualiza solo.
