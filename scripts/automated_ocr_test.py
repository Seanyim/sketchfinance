#!/usr/bin/env python3
"""
自动化测试: 验证新OCR逻辑
1. Q9/09 保留验证
2. EPS 匹配验证
3. 每季度截止日期验证
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.ocr_service import OCRService
from backend.config.config import FINANCIAL_METRICS

# 过滤利润表指标
income_metrics = [m for m in FINANCIAL_METRICS if m.get('category') == '利润表']

print("=" * 60)
print("自动化OCR测试")
print("=" * 60)

# 检查文件
for f in ["temp_p.png", "temp_m.png", "temp_v.png"]:
    if not os.path.exists(f):
        print(f"❌ 缺少文件: {f}")
        sys.exit(1)

# 执行OCR
ocr = OCRService(gpu=False)
parsed_data, disclosure_date = ocr.parse_multi_image("temp_p.png", "temp_m.png", "temp_v.png", income_metrics)

print(f"\n解析记录数: {len(parsed_data)}")
print(f"全局披露日期: {disclosure_date}")

# ========== 测试1: Q9/09 保留 ==========
print("\n【测试1】Q9/09 保留验证:")
periods = set(d['period'] for d in parsed_data)
has_09 = any('/09' in p for p in periods)
has_Q3 = any('/Q3' in p for p in periods)
print(f"  包含 /09 格式: {'✓' if has_09 else '✗'}")
print(f"  包含 /Q3 格式: {'✓' if has_Q3 else '✗'}")
if has_09 and not has_Q3:
    print("  ✅ 测试通过: 09 已保留，未转换为 Q3")
else:
    print("  ⚠️ 测试待确认")

# ========== 测试2: EPS 匹配 ==========
print("\n【测试2】EPS 匹配验证:")
metrics = set(d['metric_id'] for d in parsed_data)
has_eps = 'EPS' in metrics
eps_records = [d for d in parsed_data if d['metric_id'] == 'EPS']
print(f"  EPS 记录数: {len(eps_records)}")
if len(eps_records) > 0:
    print(f"  ✅ 测试通过: EPS 已匹配 ({len(eps_records)} 条)")
    print(f"  示例值: {eps_records[0]['value'] if eps_records else 'N/A'}")
else:
    print("  ❌ 测试失败: EPS 未匹配")

# ========== 测试3: 每季度截止日期 ==========
print("\n【测试3】每季度截止日期验证:")
# 检查每个季度是否有对应的report_date
periods_with_dates = {}
for d in parsed_data:
    period = d['period']
    report_date = d.get('report_date', '')
    if period not in periods_with_dates:
        periods_with_dates[period] = report_date

print(f"  季度数: {len(periods_with_dates)}")
dates_found = sum(1 for v in periods_with_dates.values() if v)
print(f"  有日期的季度: {dates_found}")

if dates_found == len(periods_with_dates):
    print("  ✅ 测试通过: 所有季度都有对应日期")
elif dates_found > 0:
    print("  ⚠️ 部分季度有日期")
else:
    print("  ❌ 测试失败: 无季度有日期")

# 打印季度-日期对应
print("\n  季度-日期对应:")
for period in sorted(periods_with_dates.keys()):
    date = periods_with_dates[period]
    print(f"    {period}: {date if date else '(无)'}")

# ========== 测试4: 全指标覆盖 ==========
print("\n【测试4】指标覆盖验证:")
for m in income_metrics:
    status = "✓" if m['id'] in metrics else "✗"
    count = sum(1 for d in parsed_data if d['metric_id'] == m['id'])
    print(f"  {status} {m['id']}: {count} 条")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
