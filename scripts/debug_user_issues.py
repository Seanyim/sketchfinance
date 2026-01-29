# 诊断脚本：模拟用户报告的问题
import os
import sys
import re

# 模拟OCR识别结果（基于用户描述）
mock_ocr_results = [
    # 模拟 H1 误识别为 Q4 的情况（实际上应该是Q2被识别错了，或者H1被错误替换）
    {'text': '2024/H1', 'confidence': 0.9},
    {'text': '2024/41', 'confidence': 0.6},  # 之前修复的case
    
    # 模拟 Q9 误识别
    {'text': '2025/Q9', 'confidence': 0.8},
    {'text': '2025/09', 'confidence': 0.8},

    # 模拟 2.07 误识别为 207（丢失小数点）
    {'text': '2.07', 'confidence': 0.9},
    {'text': '2 07', 'confidence': 0.7},  # 可能被去空格变成207
    {'text': '207', 'confidence': 0.6},
]

# 模拟 tempv 倒数第三行有日期
mock_tempv_results = [
    {'text': '100.5', 'confidence': 0.9},
    {'text': '截止2025年6月30日', 'confidence': 0.9}, # 倒数第三行
    {'text': '单位：亿元', 'confidence': 0.8},
    {'text': '来源：财报', 'confidence': 0.8},
]

# ----------------------------------------------------------------
# 测试逻辑复现
# ----------------------------------------------------------------

print("=== 测试1: 季度纠错逻辑 ===")

def clean_period(text):
    clean_text = text.replace(" ", "").upper()
    # 1. Fix Year/FY
    clean_text = re.sub(r'(\d{4})[I|1| ]?FY', r'\1/FY', clean_text)
    
    # Pre-process H1/H2 (Prevent them from being modified by Q logic)
    if re.search(r'(\d{4})[/-]H[12]', clean_text):
        clean_text = re.sub(r'(\d{4})[/-]H([12])', r'\1/H\2', clean_text)
    else:
        # Standard correction
        clean_text = re.sub(r'(\d{4})[/-](O)([1-4])', r'\1/Q\3', clean_text)
        clean_text = re.sub(r'(\d{4})[/-]Q?01(?!\d)', r'\1/Q1', clean_text)
        clean_text = re.sub(r'(\d{4})[/-](4I|41|42)(?!\d)', r'\1/Q2', clean_text) # 修正41->Q2
        clean_text = re.sub(r'(\d{4})[/-](Q?09|Q9)(?!\d)', r'\1/Q3', clean_text)
        clean_text = re.sub(r'(\d{4})[/-]Q?04(?!\d)', r'\1/Q4', clean_text)
        
    return clean_text

for item in mock_ocr_results:
    original = item['text']
    cleaned = clean_period(original)
    print(f"原始: {original:10} -> 清洗后: {cleaned}")


print("\n=== 测试2: 数值点丢失逻辑 (Updated) ===")
def clean_value(text):
    # 模拟 ocr_service.py 中的新逻辑
    clean_text = text.strip()
    
    if " " in clean_text and "." not in clean_text:
        parts = clean_text.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            # Case 1: "2 07" -> 2.07 (Heuristic: integer part len 1, decimal part len 2)
            if len(parts[0]) == 1 and len(parts[1]) == 2:
                return f"{parts[0]}.{parts[1]}"
            else:
                return clean_text.replace(" ", "")
        else:
            return clean_text.replace(" ", "")
    else:
        return clean_text.replace(" ", "")

for item in mock_ocr_results:
    if '2' in item['text']:
        print(f"原始: {item['text']:10} -> 清洗后: {clean_value(item['text'])}")

print("\n=== 测试3: 日期提取逻辑 (Updated) ===")
# Updated date pattern from ocr_service.py
date_pattern = re.compile(r'(\d{4}[年/.-]\d{1,2}[月/.-]\d{1,2}日?|[二三四五六七八九〇]+年[一二三四五六七八九十]+月[一二三四五六七八九十]+日)')

for item in mock_tempv_results:
    match = date_pattern.search(item['text'])
    print(f"文本: {item['text']:20} -> 提取日期: {match.group(1) if match else 'None'}")
