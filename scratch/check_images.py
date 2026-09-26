import urllib.request
import re

photos_to_check = [
    ('photo-1551754655-cd27e38d2076', 'Hero Image'),
    ('photo-1595974482597-4b8da8879bc5', 'Card 2 / Tech center'),
    ('photo-1601648764658-cf37e8c89b70', 'Card 3 / Tech right'),
    ('photo-1523348837708-15d4a09cfac2', 'Card 1 / Tech left'),
    ('photo-1568644396922-5c3bfae12521', 'About photo'),
    ('photo-1530595467537-0b5996c41f2d', 'Potential 1'),
    ('photo-1586771107445-d3ca888129ff', 'Potential 2'),
    ('photo-1628352081506-83c43123ed6d', 'Potential 3'),
    ('photo-1500937386664-56d1dfef3854', 'Potential 4'),
    ('photo-1533240332313-0db49b459ad6', 'Potential 5'),
    ('photo-1574943320219-553eb213f72d', 'Ambient blur'),
]

for pid, label in photos_to_check:
    url = f"https://unsplash.com/photos/{pid.replace('photo-', '')}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        html = urllib.request.urlopen(req, timeout=6).read().decode('utf-8', errors='ignore')
        m_title = re.search(r'<title>(.*?)</title>', html, re.I)
        m_desc = re.search(r'content="([^"]*?)"[^>]*name="description"', html, re.I) or re.search(r'name="description"[^>]*content="([^"]*?)"', html, re.I)
        print(f"[{label}] {pid}:")
        if m_title:
            print("  Title:", m_title.group(1)[:120])
        if m_desc:
            print("  Desc:", m_desc.group(1)[:140])
    except Exception as e:
        print(f"[{label}] {pid}: Error {e}")
