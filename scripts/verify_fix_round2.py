
import re

# Mock OCR Results based on user report and dump
mock_headers = [
    {'text': '2022/41', 'conf': 0.53}, # Should be H1
    {'text': '2022/09', 'conf': 0.93}, # Should represent Sep (Q3) but user wants "original date" or at least 09
    {'text': '2022/Q1', 'conf': 0.94},
]

mock_values = [
    {'text': '207', 'conf': 0.53}, # Should be 2.07
    {'text': '2 07', 'conf': 0.60}, # Should be 2.07
    {'text': '006', 'conf': 1.00}, # Should be 0.06?
    {'text': '2025/10/26', 'conf': 0.99}, # Should be found as date
    {'text': '021/05/02', 'conf': 0.96}, # Early date
]

print("=== Header Correction Logic ===")
def test_header(text):
    clean_text = text.replace(" ", "").upper()
    clean_text = re.sub(r'(\d{4})[/-](4I|41|42)(?!\d)', r'\1/H1', clean_text) # New Rule
    
    if re.search(r'(\d{4})[/-]H[12]', clean_text):
        clean_text = re.sub(r'(\d{4})[/-]H([12])', r'\1/H\2', clean_text)
    else:
        # Reduced rules
        clean_text = re.sub(r'(\d{4})[/-](O)([1-4])', r'\1/Q\3', clean_text)
        clean_text = re.sub(r'(\d{4})[/-]Q?01(?!\d)', r'\1/Q1', clean_text)
        # clean_text = re.sub(r'(\d{4})[/-](Q?09|Q9)(?!\d)', r'\1/Q3', clean_text) # REMOVED
        clean_text = re.sub(r'(\d{4})[/-](Q9)(?!\d)', r'\1/Q3', clean_text)
        clean_text = re.sub(r'(\d{4})[/-]Q?04(?!\d)', r'\1/Q4', clean_text)
    
    return clean_text

for h in mock_headers:
    print(f"{h['text']:10} -> {test_header(h['text'])}")

print("\n=== Value Cleaning Logic ===")
def test_value(text, prob):
    clean_text = text.strip()
    if "." not in clean_text:
        # Check space heuristic "2 07"
        if " " in clean_text:
            parts = clean_text.split()
            if len(parts) == 2 and len(parts[0])==1 and len(parts[1])==2 and parts[0].isdigit() and parts[1].isdigit():
                return f"{parts[0]}.{parts[1]}"
        # Check integer heuristic "207"
        elif len(clean_text) == 3 and clean_text.isdigit() and prob < 0.8:
             return f"{clean_text[0]}.{clean_text[1:]}"
    return clean_text.replace(" ", "")

for v in mock_values:
    print(f"{v['text']:10} (Conf={v['conf']}) -> {test_value(v['text'], v['conf'])}")

print("\n=== Date Extraction Logic ===")
found_dates = []
date_pattern = re.compile(r'(\d{4}[年/.-]\d{1,2}[月/.-]\d{1,2}日?|[二三四五六七八九〇]+年[一二三四五六七八九十]+月[一二三四五六七八九十]+日)')

for v in mock_values:
    match = date_pattern.search(v['text'])
    if match:
        found_dates.append(match.group(1))

print(f"Found Dates: {found_dates}")
print(f"Disclosure Date (Last): {found_dates[-1] if found_dates else 'None'}")
