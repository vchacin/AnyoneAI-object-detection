"""Test de latencia de inferencia en CPU con el modelo entrenado en el dataset SKU110K."""
import time
from pathlib import Path

from ultralytics import YOLO

model_path = "training/weights/B_e35/weights/best.pt"
print(f"Cargando modelo desde: {model_path}")

model = YOLO(model_path)

test_image = "data_pipeline/dataset_sku110k/images/test_0.jpg"

print("Iniciando warm-up del modelo...")
model.predict(test_image, device="cpu", verbose=False)

print("Midiendo latencia de inferencia...")
start_time = time.time()
results = model.predict(test_image, device="cpu", verbose=False)
end_time = time.time()
latency_ms = (end_time - start_time) * 1000

print("--- RESULTADOS CPU ---")
print(f"Tiempo de inferencia: {latency_ms:.2f} milisegundos")

if latency_ms < 200:
    verdict = "Excelente para CPU. No necesitamos cuantizar por ahora."
elif latency_ms < 500:
    verdict = "Aceptable, pero podriamos evaluar exportar a ONNX para mejorar."
else:
    verdict = "Lento. Hay que hablar con Ivan sobre cuantizacion (ONNX/OpenVINO)."
print(f"Veredicto: {verdict}")

for box in results[0].boxes:
    clase_id = int(box.cls[0].item())
    nombre_clase = model.names[clase_id]
    confianza = box.conf[0].item()
    print(f"Detectado: {nombre_clase} con confianza {confianza:.2f}")
