#!/usr/bin/env python3
"""
综合诊断脚本：分析 tempp, tempm, tempv 的 OCR 结果
检查：
1. Q9 识别问题
2. 科目匹配问题 (EPS等)
3. 日期提取问题
"""
import os
import sys
import easyocr
import re
import difflib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config.config import FINANCIAL_METRICS

# Initialize
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

print("=" * 60)
print("综合 OCR 诊断")
print("=" * 60)

# ========== 1. 季度识别 (tempp) ==========
print("\n【1】季度识别 (tempp.png)")
print("-" * 40)
if os.path.exists("temp_p.png"):
    p_ocr = reader.readtext("temp_p.png")
    for i, (bbox, text, prob) in enumerate(p_ocr):
        print(f"  {i:02}: '{text}' (Conf={prob:.2f})")
else:
    print("  文件不存在: temp_p.png")

# ========== 2. 科目识别 (tempm) ==========
print("\n【2】科目识别 (tempm.png)")
print("-" * 40)
config_labels = [m['label'] for m in FINANCIAL_METRICS]
print(f"  Config中定义的科目 ({len(config_labels)}个): {config_labels}")

if os.path.exists("temp_m.png"):
    m_ocr = reader.readtext("temp_m.png")
    matched = []
    unmatched = []
    for i, (bbox, text, prob) in enumerate(m_ocr):
        best = difflib.get_close_matches(text, config_labels, n=1, cutoff=0.6)
        if best:
            matched.append((text, best[0]))
        else:
            unmatched.append(text)
    
    print(f"\n  成功匹配 ({len(matched)}个):")
    for ocr_text, label in matched:
        print(f"    '{ocr_text}' -> '{label}'")
    
    print(f"\n  未匹配 ({len(unmatched)}个):")
    for t in unmatched:
        print(f"    '{t}'")
else:
    print("  文件不存在: temp_m.png")

# ========== 3. 数值与日期识别 (tempv) ==========
print("\n【3】数值与日期识别 (tempv.png)")
print("-" * 40)
date_pattern = re.compile(r'(\d{4}[年/.-]\d{1,2}[月/.-]\d{1,2}日?)')

if os.path.exists("temp_v.png"):
    v_ocr = reader.readtext("temp_v.png")
    dates_found = []
    values_found = []
    
    for i, (bbox, text, prob) in enumerate(v_ocr):
        # Check for date
        date_match = date_pattern.search(text.replace(" ", ""))
        if date_match:
            dates_found.append((i, date_match.group(1), text))
        elif any(c.isdigit() for c in text):
            values_found.append((i, text, prob))
    
    print(f"\n  找到的日期 ({len(dates_found)}个):")
    for idx, date, raw in dates_found:
        print(f"    Index {idx}: '{date}' (原文: '{raw}')")
    
    print(f"\n  数值样本 (前20个):")
    for idx, text, prob in values_found[:20]:
        print(f"    Index {idx}: '{text}' (Conf={prob:.2f})")
else:
    print("  文件不存在: temp_v.png")

# ========== 4. 检查 tempm 中的日期 ==========
print("\n【4】科目截图中的日期 (tempm.png)")
print("-" * 40)
if os.path.exists("temp_m.png"):
    m_ocr = reader.readtext("temp_m.png")
    for i, (bbox, text, prob) in enumerate(m_ocr):
        date_match = date_pattern.search(text.replace(" ", ""))
        if date_match:
            print(f"  Index {i}: '{date_match.group(1)}' (原文: '{text}')")
else:
    print("  文件不存在")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
