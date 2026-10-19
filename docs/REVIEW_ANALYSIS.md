# Analisis de la revision humana

Corrida: `comparison_20261012T204356Z`  
Archivo: `app/data/comparisons/comparison_20261012T204356Z/reviews.jsonl`

## Resultado actual

Se recibieron 103 registros sobre 100 imagenes unicas. Los indices `13`, `72`
y `90` fueron revisados dos veces; para el resumen se considera el ultimo
registro de cada indice.

| Veredicto | Casos | Porcentaje de las 100 imagenes |
|---|---:|---:|
| Oficial | 76 | 76% |
| ShelfVision | 17 | 17% |
| Empate | 2 | 2% |
| No claro | 5 | 5% |

Entre los casos con ganador claro o empate, el oficial obtiene 76 de 95 casos
no ambiguos, aproximadamente 80%.

## Patrones observados

- ShelfVision a veces detecta mas objetos o espacios grandes, pero algunas cajas
  quedan fuera de los margenes o no quedan exactamente sobre la posicion real.
- El oficial fue percibido como mejor en varias escenas con perspectiva y en
  estanterias de bebidas.
- Ambos modelos tienen problemas con bebidas lejanas y producen falsos
  positivos en algunas escenas.
- La muestra actual mide preferencia visual, no accuracy formal: no hay labels
  manuales de `missing` para calcular precision, recall o mAP de esa clase.

## Prioridad recomendada

1. **No sustituir el oficial por ShelfVision todavia.** El resultado humano
   actual favorece al oficial.
2. **Crear un conjunto de hard examples** con las imagenes donde aparecieron
   perspectiva, bebidas lejanas, productos pequenos y faltantes fuera de
   margen.
3. **Etiquetar manualmente cajas reales**, especialmente `missing`. Las notas y
   veredictos no son labels de entrenamiento.
4. **Mejorar primero recall de `object`** con el brazo A o un fine-tuning
   controlado del checkpoint oficial. Si no se ven los productos, la geometria
   y el detector de faltantes tampoco pueden corregirlos.
5. **Entrenar despues el brazo B** con las cajas `missing` revisadas y ejemplos
   negativos de espacios que no son faltantes.
6. **Evaluar en un holdout nuevo**, separado de las imagenes usadas para
   fine-tuning. Repetir la revision visual y comparar latencia y falsos
   positivos.

## Experimento siguiente

El notebook `training/pipeline_completo.ipynb` esta preparado para:

```python
import os
os.environ["EXPERIMENT_NAME"] = "B_hard_examples_v1"
os.environ["INIT_WEIGHTS"] = "modelos/best.pt"
os.environ["TRAIN_ARM"] = "B"
os.environ["TRAIN_EPOCHS"] = "50"
```

En Colab se debe subir la version actualizada del notebook o clonar una rama
que contenga estos cambios. Las celdas generan un paquete con `best.pt`,
`metrics.json`, `train_config.json` y `MODEL_MANIFEST.json` para copiarlo al
proyecto oficial y repetir la comparacion.