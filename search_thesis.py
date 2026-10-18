import os
path = os.path.join(os.environ['TEMP'], 'thesis_extract', 'thesis_text.txt')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

def find_section(keyword, limit=5000):
    idx = c.find(keyword)
    if idx < 0:
        print(f'NOT FOUND: {keyword}')
        return
    print(f'=== FOUND "{keyword}" at char {idx} ===')
    print(c[idx:idx+limit])
    print()

find_section('Summary Of Findings', 6000)
find_section('Standard Operating Procedure', 4000)
find_section('Conclusions', 5000)
find_section('Recommendations', 6000)
find_section('SOP', 3000)
