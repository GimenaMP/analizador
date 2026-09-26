import os
import urllib.request
import json
import time

out_dir = r"c:\Users\gimen\Downloads\analizador\front\img"
headers = {'User-Agent': 'AgroJutiapaEducationBot/2.0 (contact@agro-jutiapa.gt)'}

candidates = [
    # Golden corn ear close-up / elote
    ("corn_golden_cob.jpg", "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Maize_%28corn.jpg/1280px-Maize_%28corn.jpg"),
    # Sweet corn / mazorcas frescas
    ("sweet_corn_ears.jpg", "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Maka_%28Sweet_Corn%29.jpg/1280px-Maka_%28Sweet_Corn%29.jpg"),
    # Central America milpa / maize field
    ("central_america_milpa.jpg", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Milpa_2011.jpg/1280px-Milpa_2011.jpg"),
    # Green cornfield
    ("green_cornfield_landscape.jpg", "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/CULTIVO_DE_MAIZ_%2CTENJO_-_panoramio.jpg/1280px-CULTIVO_DE_MAIZ_%2CTENJO_-_panoramio.jpg"),
]

for filename, url in candidates:
    target = os.path.join(out_dir, filename)
    print(f"Fetching {filename}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res, open(target, 'wb') as f:
            f.write(res.read())
        print(f" -> SUCCESS: {filename} ({os.path.getsize(target)/1024:.1f} KB)")
    except Exception as e:
        print(f" -> FAILED {filename}: {e}")
    time.sleep(3.0)
