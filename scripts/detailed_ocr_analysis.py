#!/usr/bin/env python3
"""
详细分析OCR输出：
1. Q9 vs Q3 问题
2. EPS 行位置
3. 每个季度对应的截止日期
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import easyocr

reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

print("=" * 60)
print("详细OCR分析")
print("=" * 60)

# 分析季度
print("\n【1】季度原始OCR (tempp):")
p_ocr = reader.readtext("temp_p.png")
for i, (bbox, text, prob) in enumerate(p_ocr):
    # 检查是否包含Q9
    if 'Q9' in text.upper() or '09' in text or 'Q3' in text.upper():
        print(f"  {i:02}: '{text}' (Conf={prob:.2f}) <-- 关注")
    else:
        print(f"  {i:02}: '{text}' (Conf={prob:.2f})")

# 分析EPS行
print("\n【2】科目原始OCR (tempm) - 查找EPS相关:")
m_ocr = reader.readtext("temp_m.png")
eps_found = []
for i, (bbox, text, prob) in enumerate(m_ocr):
    if '每股' in text or 'EPS' in text.upper() or '收益' in text:
        y_center = sum([p[1] for p in bbox]) / 4
        eps_found.append((i, text, prob, y_center))
        print(f"  {i:02}: '{text}' (Conf={prob:.2f}, Y={y_center:.0f})")

# 分析日期和它们的位置
print("\n【3】日期原始OCR (tempv) - 查找截止日期行:")
v_ocr = reader.readtext("temp_v.png")
dates_found = []
import re
date_pattern = re.compile(r'(\d{4}[/.-]\d{1,2}[/.-]\d{1,2})')
for i, (bbox, text, prob) in enumerate(v_ocr):
    match = date_pattern.search(text)
    if match:
        x_center = sum([p[0] for p in bbox]) / 4
        y_center = sum([p[1] for p in bbox]) / 4
        dates_found.append((i, match.group(1), x_center, y_center))

print(f"  找到 {len(dates_found)} 个日期:")
for i, date, x, y in dates_found:
    print(f"    Index {i:03}: '{date}' (X={x:.0f}, Y={y:.0f})")

# 分析季度和日期的X位置对应关系
print("\n【4】季度-日期X位置对应分析:")
headers = [(i, text, sum([p[0] for p in bbox])/4) for i, (bbox, text, prob) in enumerate(p_ocr)]
headers.sort(key=lambda x: x[2])
print("  季度X位置:")
for i, text, x in headers[:10]:
    print(f"    '{text}': X={x:.0f}")

print("=" * 60)
