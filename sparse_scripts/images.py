from pathlib import Path
from PIL import Image, ImageFile
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = False

# Usa una ruta absoluta o ajusta el directorio donde están  imágenes de SKU110K
# Si estás ejecutando el script dentro de SKU110K_fixed/images, pon "."
directorio_dataset = Path(".") 
archivo_salida = Path("revision_imagenes.txt")

extensiones_validas = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff')

print(f"📂 Buscando imágenes en: {directorio_dataset.resolve()}")

# Buscar archivos
archivos = [
    f for f in directorio_dataset.rglob("*") 
    if f.suffix.lower() in extensiones_validas
]

print(f"📊 Total de imágenes encontradas: {len(archivos)}")

if len(archivos) == 0:
    print("⚠️ Ojo: No se encontró ninguna imagen. Revisa si estás en la carpeta correcta.")
else:
    corruptas_count = 0
    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write("# Reporte de imágenes corruptas\n")
        
        for archivo in tqdm(archivos, desc="Verificando integridad"):
            try:
                with Image.open(archivo) as img:
                    img.verify()
                with Image.open(archivo) as img:
                    img.load()
            except Exception as e:
                f.write(f"{archivo.resolve()} | Error: {str(e)}\n")
                corruptas_count += 1

    print(f"\n✨ ¡Listo! Proceso terminado.")
    print(f"   - Dañadas encontradas: {corruptas_count}")
    print(f"   - Reporte guardado en: {archivo_salida.resolve()}")