#!/usr/bin/env python3
with open('web/static/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace common problematic characters
content = content.replace('—', '-')
content = content.replace('─', '-')
content = content.replace('“', '"')
content = content.replace('”', '"')
content = content.replace('‘', "'")
content = content.replace('’', "'")

with open('web/static/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed non-ASCII characters')