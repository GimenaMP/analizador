import urllib.request
import re
import json

url = 'https://es.wix.com/website-template/view/html/2220?originUrl=https%3A%2F%2Fes.wix.com%2Fwebsite%2Ftemplates%2Fhtml%2Findustrial%2Fagriculture-farming&esi=168b0a36-3022-4b79-a378-ae8dd8c618de'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

# Search for the demo iframe or live site URL
matches = re.findall(r'(https://[a-zA-Z0-9_\-\.]+\.wixsite\.com/[^\s"\'<>]+)', html)
print("Wixsite matches:", set(matches))

demones = re.findall(r'(https://www\.wix\.com/demone[0-9]*/[^\s"\'<>]+)', html)
print("Demone matches:", set(demones))

# Look for viewerUrl or similar json data
m = re.findall(r'\"viewerUrl\":\"([^\"]+)\"', html)
if m:
    print("viewerUrl:", m[0])

# Search for template name or title
title = re.findall(r'<title>([^<]+)</title>', html)
print("Title:", title)
