import urllib.request
import json
import urllib.parse

def search_wm(query):
    url = f'https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={urllib.parse.quote(query)}&gsrlimit=10&prop=imageinfo&iiprop=url|size|extmetadata&format=json'
    req = urllib.request.Request(url, headers={'User-Agent': 'AgroJutiapaBot/1.0'})
    try:
        res = urllib.request.urlopen(req)
        data = json.loads(res.read().decode('utf-8'))
        pages = data.get('query', {}).get('pages', {})
        print(f"\n=== {query} ===")
        for pid, pinfo in pages.items():
            t = pinfo.get('title')
            if any(t.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                ii = pinfo.get('imageinfo', [{}])[0]
                url_val = ii.get('url')
                meta = ii.get('extmetadata', {})
                desc = meta.get('ImageDescription', {}).get('value', '')
                print(f"* {t}")
                print(f"  URL: {url_val}")
                print(f"  Desc: {desc[:100]}...\n")
    except Exception as e:
        print('Error:', e)

if __name__ == '__main__':
    search_wm('maizal')
    search_wm('milpa')
    search_wm('campo de maiz')
    search_wm('cultivo de maiz')
    search_wm('Zea mays field')
