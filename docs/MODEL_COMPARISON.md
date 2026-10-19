# Comparacion de modelos

Este documento explica la propuesta de ShelfVision frente al modelo oficial de
AnyoneAI. Distingue los datos comprobados en archivos de los aspectos que no
pueden conocerse sin el proyecto de entrenamiento original.

## Resumen corto

El modelo oficial es un detector YOLO de dos clases (`object`, `missing`) al
que el backend añade una heurística geométrica para proponer huecos. ShelfVision
no es un único checkpoint equivalente: es un pipeline compuesto por dos
detectores YOLO, geometría de filas, análisis OpenCV y una etapa opcional de
embeddings.

Por eso ShelfVision puede ser mejor como sistema de revisión de estanterías,
pero no se puede demostrar mirando sólo el tamaño de los pesos ni comparando
directamente sus mAP históricos. Hay que ejecutar ambos sobre las mismas
imágenes y revisar los resultados con el mismo criterio.

## Modelo oficial

### Entrenamiento verificado

El run histórico `B_e35` está documentado en
`training/weights/B_e35/args.yaml`:

| Parámetro | Valor |
|---|---|
| Base | `training/weights/yolo26s.pt` |
| Dataset | `training/configs/data_arm_b.yaml` |
| Clases | `object`, `missing` |
| Épocas | 35 |
| Batch | 7 |
| Tamaño de imagen | 1024 |
| Seed | 42 |
| Max detecciones | 750 |
| Workers | 8 |
| Optimizer | `auto` |

La configuración `data_arm_b.yaml` se genera a partir de etiquetas de
`missing` propuestas por geometría. No son etiquetas manuales puras: el script
`labeling/generate_missing_labels.py` calcula filas, pitch y huecos, y el
exportador construye el brazo B.

El informe histórico de `B_e35` registra:

- Precision: `0.85140`
- Recall: `0.43405`
- mAP50: `0.40443`
- mAP50-95: `0.25002`

Estos números son referencia del run histórico. No deben presentarse como una
evaluación nueva del checkpoint desplegado sin volver a ejecutar la validación.

### Cómo sirve el backend oficial

El flujo está en
`app/backend/services/inference_service.py`:

1. Carga un único checkpoint `modelos/best.pt`.
2. Detecta cajas `object` y `missing`.
3. Ejecuta `gap_heuristic.py` sobre las cajas de objetos.
4. Fusiona los faltantes aprendidos con los huecos geométricos.
5. Usa opcionalmente un modelo COCO para filtrar oclusores.
6. Devuelve el origen de cada detección: `model` o `heuristic`.

El baseline aprende directamente la clase `missing`, pero depende también de
la calidad de las etiquetas geométricas generadas durante el entrenamiento.

## Propuesta ShelfVision

### Pesos disponibles

ShelfVision entrega dos archivos:

```text
modelos/shelfvision/product_best.pt
modelos/shelfvision/missing_best.pt
```

Cada archivo mide aproximadamente 19.16 MB. Sus hashes están en el manifiesto
del proyecto compañero y se verificaron antes de copiarlos al proyecto
oficial.

El significado funcional sí está claro:

- `product_best.pt`: detecta productos visibles.
- `missing_best.pt`: detecta regiones de faltantes.

Lo que no está disponible en el paquete es la arquitectura exacta, dataset de
entrenamiento, épocas, batch, resolución, hiperparámetros y métricas de
validación. El manifiesto sólo contiene tamaño y SHA-256. No se deben inventar
esos datos a partir del nombre del archivo.

### Flujo de inferencia

El adaptador está en
`app/backend/services/shelfvision_service.py` y sigue esta secuencia:

1. Ejecuta `product_best.pt` sobre la imagen.
2. Agrupa las cajas en filas.
3. Busca separaciones anormalmente grandes entre productos.
4. Ejecuta `missing_best.pt` sobre la imagen.
5. Analiza candidatos con OpenCV.
6. Fusiona score geométrico, score OpenCV y score del detector de faltantes.
7. Conserva faltantes directos del modelo cuando superan el umbral.

El proyecto compañero original también tiene modos `precise`, `balanced` y
`fast`, y embeddings ResNet18 opcionales. La integración inicial oficial
mantiene el núcleo de dos modelos + geometría + OpenCV; los embeddings no se
usan como requisito para que la comparación sea reproducible y no dependa de
descargas de pesos externos.

## Diferencias importantes

| Aspecto | Oficial | ShelfVision |
|---|---|---|
| Pesos | Un checkpoint principal | Dos checkpoints especializados |
| Productos | Una clase dentro del modelo de dos clases | Detector separado |
| Faltantes | Clase aprendida + heurística oficial | Detector separado + geometría + OpenCV |
| Etiquetas | `object` y `missing` en el brazo B | No conocemos el dataset exacto de entrenamiento |
| Arquitectura entrenada | Registrada parcialmente en `args.yaml` | No descrita en el manifiesto |
| Heurística | `gap_heuristic.py`, compartida con labeling | Geometría propia del pipeline ShelfVision |
| Oclusores | Modelo COCO opcional | No es parte del adaptador inicial |
| Auditoría | Reporte histórico `B_e35` | Manifiesto de pesos, sin métricas de entrenamiento |

La ventaja potencial de ShelfVision es que separa las responsabilidades y
añade verificaciones visuales antes de aceptar un faltante. La desventaja es
mayor complejidad, dos modelos que cargar y menor trazabilidad sobre cómo se
entrenaron los pesos entregados.

## Cómo se están comparando

La comparación visual reproducible está implementada en
`training/compare_models.py`:

```powershell
python training/compare_models.py --count 538 --seed 42
```

La corrida actual es `comparison_20261012T204356Z`. Usa las mismas 538 imágenes,
ejecuta ambos modelos y genera dos resultados anotados por imagen. La revisión
se abre en:

```text
http://localhost:8000/comparison
```

Cada caso se puede marcar como:

- gana oficial;
- gana ShelfVision;
- empate;
- no claro;
- nota manual.

Las decisiones se guardan en `reviews.jsonl`. Esto produce una tasa de
preferencia humana, no accuracy formal. Para obtener accuracy, precision,
recall o mAP de `missing` habría que crear primero labels manuales para el
conjunto revisado.

## Conclusión actual

Ya podemos comparar visualmente cuál pipeline produce mejores revisiones sobre
las 538 imágenes. Todavía no podemos afirmar que uno tenga mayor accuracy de
faltantes porque no existe ground truth manual para esa clase. La siguiente
evidencia necesaria son las decisiones de la revisión humana; después se puede
resumir cuántas imágenes gana cada modelo y seleccionar ejemplos de falsos
positivos y falsos negativos para decidir qué pipeline continuar calibrando.