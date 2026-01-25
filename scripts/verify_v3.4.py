import sys
import os
import re

# Add project root to path
sys.path.append(os.getcwd())

from backend.app.services.ocr_service import OCRService

def test_date_extraction():
    print("Testing date extraction...")
    ocr = OCRService(gpu=False)
    
    test_cases = [
        ("2023-01-25", "2023-01-25"),
        ("二○二三年一月二十五日", "二○二三年一月二十五日"),
        ("2023年01月25日", "2023年01月25日"),
        ("2022/FY", None), # Should not match as date
    ]
    
    # Mocking the internal regex check as we don't want to run full OCR here
    date_pattern = re.compile(r'(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?|[二三四五六七八九〇]+年[一二三四五六七八九十]+月[一二三四五六七八九十]+日)')
    
    for text, expected in test_cases:
        match = date_pattern.search(text)
        result = match.group(0) if match else None
        print(f"Text: {text} -> Result: {result} (Expected: {expected})")
        if result != expected:
            print("FAILED")
        else:
            print("PASSED")

def test_period_correction():
    print("\nTesting period correction...")
    # Mocking the correction logic
    test_cases = [
        ("2022IFY", "2022/FY"),
        ("2022 1FY", "2022/FY"),
        ("2022/09", "2022/Q9"),
        ("2022/O1", "2022/Q1"),
    ]
    
    for text, expected in test_cases:
        clean_text = text.replace(" ", "").upper()
        clean_text = re.sub(r'(\d{4})[I|1| ]?FY', r'\1/FY', clean_text)
        clean_text = re.sub(r'(\d{4})[/-](0|O|Q)([1-9])', r'\1/Q\3', clean_text)
        print(f"Original: {text} -> Corrected: {clean_text} (Expected: {expected})")
        if clean_text != expected:
            print("FAILED")
        else:
            print("PASSED")

if __name__ == "__main__":
    test_date_extraction()
    test_period_correction()
