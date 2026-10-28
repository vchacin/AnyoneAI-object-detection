# Resumen de cambios y verificaciones

Fecha: 23 de octubre de 2026.

## 1. Corrección del error 500 al guardar reportes

**Archivo modificado:** `C:\subir\.env`.

Se cambió únicamente la ruta de reportes:

```dotenv
# Antes
EXPERIMENT_REPORT_DIR=./training/reports/inference

# Después
EXPERIMENT_REPORT_DIR=/app/app/data/reports/inference
```

**Motivo:** después de ejecutar la inferencia, el backend intentaba crear la carpeta relativa `training` dentro del contenedor y fallaba con `PermissionError: [Errno 13] Permission denied: 'training'`. Esto producía un 500 incluso con «Guardar como inspección» desactivado, porque los reportes se generan independientemente de esa opción.

La nueva ruta corresponde al volumen de reportes configurado en `C:\subir\docker-compose.yml`. Se comprobó que existía y tenía permisos de escritura.

**Aplicación:** se recreó únicamente el servicio `backend` para cargar la nueva variable de entorno.

**Verificación:** la misma petición de inferencia que devolvía 500 respondió 200 y generó su reporte después del cambio.

## 2. Incorporación de `mi-modelo`

**Configuración agregada por el usuario:** `C:\subir\modelos\manifest.json`.

```json
"mi-modelo": {
  "path": "modelos/yolo26m-auto.pt",
  "imgsz": 1280,
  "max_det": 750,
  "default_conf": 0.25
}
```

**Motivo:** el frontend llena el selector mediante el catálogo de la API, que se construye a partir del manifiesto. No hizo falta modificar el selector ni cambiar el modelo predeterminado.

Inicialmente, `C:\subir\modelos\yolo26m-auto.pt` contenía un puntero de Git LFS de 133 bytes. No contenía los pesos, y su carga provocaba `UnpicklingError: invalid load key, 'v'` y un error 500. Posteriormente se verificó que el archivo real ya estaba disponible, con un tamaño de 44,095,309 bytes. El asistente diagnosticó este problema; no descargó ni reemplazó los pesos.

El manifiesto se copia dentro de la imagen Docker, mientras que los pesos se montan desde `C:\subir\modelos`. Los cambios al manifiesto requieren reconstruir la imagen para aplicarse con la configuración actual.

## 3. Normalización de la clase `missing1`

**Archivo modificado:** `C:\subir\app\backend\services\inference_service.py`.

Se leyeron las clases directamente de los pesos de `mi-modelo` y se confirmó:

```text
0: object
1: missing1
```

Se agregó esta conversión antes de crear el registro de detección y separar productos de huecos:

```python
class_name = str(names[int(class_id)]).lower()
if class_name == "missing1":
    class_name = "missing"
```

**Motivo:** el backend y el frontend utilizan `missing` como nombre canónico para los huecos. Antes del cambio, `missing1` entraba en la lista de productos, alterando cajas, conteos y los datos utilizados por las inspecciones y alertas. La normalización se realiza en el backend para mantener consistente la respuesta completa de la API.

Los modelos que ya emiten `missing` conservan su comportamiento. El frontend reconoce automáticamente las detecciones normalizadas; no se modificaron sus componentes.

## 4. Prueba de regresión y despliegue

**Archivo agregado:** `C:\subir\app\backend\tests\test_detection_class_aliases.py`.

La prueba simula detecciones `object`, `missing` y `missing1` y verifica que:

- Solo `object` se clasifique como producto.
- Tanto `missing` como `missing1` se devuelvan como `missing`.
- Se conserven las tres detecciones.
- La heurística de huecos reciba únicamente las cajas de productos.

La prueba falló antes de la corrección y pasó después. Se ejecutó desde `C:\subir` con:

```powershell
python -m unittest app.backend.tests.test_detection_class_aliases
```

Se reconstruyó y recreó el servicio `backend` para aplicar el código:

```powershell
docker compose up -d --no-deps --build backend
```

**Verificación con el modelo real:** se envió una imagen de validación a través del proxy del frontend:

```text
POST /backend/inference?model=mi-modelo&persist=false
Estado: 200 OK
Productos: 94
Huecos: 1
Clases devueltas: object, missing
```

Se comprobó que no se devolviera `missing1`, que el conteo de huecos coincidiera con la lista y que no hubiera huecos dentro de los productos.

**Reporte generado:** `C:\subir\training\reports\inference\d8d1c21186c2.json`.

## 5. Alcance y pendientes

- Se utilizó el acceso existente por API key para las pruebas. No se implementó ningún bypass de autenticación.
- Se diagnosticó el aviso de Next.js `instant-unrendered-segment`: el layout privado omite sus hijos mientras carga la sesión. No se modificó ese comportamiento; el aviso permanece independiente de los errores 500 corregidos.
- Las inferencias de comprobación utilizaron `persist=false`. No se comprobó el flujo completo de guardado de inspecciones y generación de alertas.
- No se recalcularon inspecciones históricas: conservan los resultados guardados antes de la normalización.
- No se ejecutó toda la suite del backend. La validación cubrió la prueba de regresión específica y una inferencia real por HTTP.
