#!/usr/bin/env python3
"""
测试新的OCR逻辑是否正确处理:
1. 季度转换 (09 -> Q3)
2. EPS别名匹配
3. 日期提取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.ocr_service import OCRService
from backend.config.config import FINANCIAL_METRICS

# 过滤利润表指标
income_metrics = [m for m in FINANCIAL_METRICS if m.get('category') == '利润表']

print("=" * 60)
print("OCR逻辑验证测试")
print("=" * 60)

# 初始化OCR服务
ocr = OCRService(gpu=False)

# 检查图片是否存在
for f in ["temp_p.png", "temp_m.png", "temp_v.png"]:
    if not os.path.exists(f):
        print(f"缺少文件: {f}")
        sys.exit(1)

print("\n执行多图OCR解析...")
parsed_data, disclosure_date = ocr.parse_multi_image("temp_p.png", "temp_m.png", "temp_v.png", income_metrics)

print(f"\n【结果】")
print(f"  披露日期: {disclosure_date}")
print(f"  解析记录数: {len(parsed_data)}")

# 检查季度格式
periods = set(d['period'] for d in parsed_data)
print(f"\n【季度分布】:")
for p in sorted(periods):
    count = sum(1 for d in parsed_data if d['period'] == p)
    print(f"  {p}: {count} 条")

# 检查指标覆盖
metrics = set(d['metric_id'] for d in parsed_data)
print(f"\n【指标覆盖】:")
for m in income_metrics:
    status = "✓" if m['id'] in metrics else "✗"
    print(f"  {status} {m['id']} ({m['label']})")

# 检查是否有09格式残留
has_09 = any('/09' in d['period'] for d in parsed_data)
print(f"\n【09格式检查】: {'有残留 ✗' if has_09 else '无残留 ✓'}")

# 检查EPS
has_eps = 'EPS' in metrics
print(f"【EPS检查】: {'已匹配 ✓' if has_eps else '未匹配 ✗'}")

# 检查日期
print(f"【披露日期】: {disclosure_date if disclosure_date else '未提取 ✗'}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
