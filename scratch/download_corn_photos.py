import os
import urllib.request
import json
import time

out_dir = r"c:\Users\gimen\Downloads\analizador\front\img"
os.makedirs(out_dir, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# 1. Authentic Jutiapa & Guatemala Corn Fields from Wikimedia Commons
wm_sources = [
    ("jutiapa_corn_field.jpg", "https://upload.wikimedia.org/wikipedia/commons/7/7a/Cultivo_de_maiz_de_El_Progreso.JPG"),
    ("guatemala_milpa_field.jpg", "https://upload.wikimedia.org/wikipedia/commons/4/4e/Milpa_in_Quiche_Guatemala.JPG"),
    ("central_america_milpa.jpg", "https://upload.wikimedia.org/wikipedia/commons/2/2a/Milpa_2011.jpg"),
    ("campo_maiz_parcela.jpg", "https://upload.wikimedia.org/wikipedia/commons/d/d6/Campo_de_ma%C3%ADz.jpg"),
    ("corn_zea_mays_rows.jpg", "https://upload.wikimedia.org/wikipedia/commons/e/ed/Corn_Zea_mays_Plant_Row_2000px.jpg"),
]

for filename, url in wm_sources:
    target = os.path.join(out_dir, filename)
    print(f"Downloading {filename} from {url}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res, open(target, 'wb') as f:
            f.write(res.read())
        sz = os.path.getsize(target)
        print(f" -> SUCCESS: {filename} ({sz / 1024:.1f} KB)")
    except Exception as e:
        print(f" -> ERROR downloading {filename}: {e}")
    time.sleep(1.0)
