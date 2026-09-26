import os
import urllib.request
import time

out_dir = r"c:\Users\gimen\Downloads\analizador\front\img"
headers = {'User-Agent': 'AgroJutiapaEducationBot/2.0 (contact@agro-jutiapa.gt; research project)'}

# High quality Wikimedia Commons corn photos
candidates = [
    # 1. Corn seedling / young corn plant in fertile soil
    ("corn_young_sprout.jpg", "https://upload.wikimedia.org/wikipedia/commons/e/eb/Corn_field_-_panoramio.jpg"),
    # 2. Corn plants with ears on the stalk
    ("corn_ear_plant.jpg", "https://upload.wikimedia.org/wikipedia/commons/e/ed/Corn_Zea_mays_Plant_Row_2000px.jpg"),
    # 3. Panorama of cornfield parcels
    ("corn_parcel_panorama.jpg", "https://upload.wikimedia.org/wikipedia/commons/0/0e/Panoramica_de_los_Campos_de_Maiz_%E2%80%93_Campos_de_Ribadeo.jpg"),
    # 4. Maize field in fertile valley
    ("maize_valley_field.jpg", "https://upload.wikimedia.org/wikipedia/commons/d/d6/Campo_de_ma%C3%ADz.jpg"),
    # 5. Corn crop rows
    ("corn_crop_rows.jpg", "https://upload.wikimedia.org/wikipedia/commons/8/80/Cultivo_de_maiz.JPG"),
    # 6. Single maize cob on plant
    ("maize_cob_stalk.jpg", "https://upload.wikimedia.org/wikipedia/commons/e/e6/Cultivo_de_Ma%C3%ADz.jpg"),
]

for filename, url in candidates:
    target = os.path.join(out_dir, filename)
    if os.path.exists(target) and os.path.getsize(target) > 50000:
        print(f"Already exists: {filename}")
        continue
    print(f"Fetching {filename}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res, open(target, 'wb') as f:
            f.write(res.read())
        print(f" -> SUCCESS: {filename} ({os.path.getsize(target)/1024:.1f} KB)")
    except Exception as e:
        print(f" -> FAILED {filename}: {e}")
    time.sleep(3.0)
