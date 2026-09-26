import urllib.request
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.wix.com/demone2/lawn-care'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

print("Page length:", len(html))

# Extract fonts from stylesheets or inline styles
font_families = set(re.findall(r'font-family:\s*([^;\"}]+)', html))
cleaned_fonts = {f.strip() for f in font_families if len(f.strip()) < 50}
print("Fonts found:")
for f in sorted(cleaned_fonts):
    print(" -", f)

# Extract font urls
font_links = re.findall(r'https?://[^\s"\'<>]+\.woff2[^\s"\'<>]*', html)
print("\nFont links:")
for fl in set(font_links):
    print(" -", fl)

# Look for site theme / colors in JSON
theme_colors = re.findall(r'\"--color_[0-9]+\":\"([^\"]+)\"', html)
print("\nTheme colors count:", len(theme_colors))
for c in set(theme_colors):
    print(" -", c)

# Let's extract the main textual content and headlines
h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)

def clean_tag(txt):
    return re.sub(r'<[^>]+>', '', txt).strip()

print("\nH1s:")
for h in h1s:
    print("  *", clean_tag(h))

print("\nH2s:")
for h in h2s:
    print("  *", clean_tag(h))

print("\nH3s:")
for h in h3s[:15]:
    print("  *", clean_tag(h))
