import urllib.request, re

req = urllib.request.Request('https://www.wix.com/demone2/farm', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

# Search for the section enclosing "FRESH FARM PRODUCTS", "ABOUT THE FARM", "PAY US A VISIT"
pos_mid = html.find('FRESH FARM PRODUCTS')
pos_left = html.find('ABOUT')
pos_right = html.find('PAY US')

print(f"Indices: left={pos_left}, mid={pos_mid}, right={pos_right}")

# Let's inspect the HTML enclosing all three
start = min(filter(lambda x: x > 0, [pos_left, pos_mid, pos_right])) - 500
end = max([pos_left, pos_mid, pos_right]) + 1500

snippet = html[start:end]

# Extract container IDs and classes
tags = re.findall(r'<div[^>]*id="([^"]*)"[^>]*class="([^"]*)"', snippet)
for t_id, t_cls in tags[:20]:
    print(f"ID: {t_id} | Class: {t_cls[:60]}")
