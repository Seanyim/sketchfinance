# 临时脚本：检查OCR识别结果质量
import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.ocr_service import OCRService
from backend.config.config import FINANCIAL_METRICS

# 初始化OCR服务
ocr = OCRService(gpu=False)

# 获取利润表指标
income_metrics = [m for m in FINANCIAL_METRICS if m.get('category') == '利润表']

# 解析图片
tempp = "tempp.png"
tempm = "tempm.png"
tempv = "tempv.png"

print("=" * 60)
print("开始OCR识别质量检查...")
print("=" * 60)

parsed_data, disclosure_date = ocr.parse_multi_image(tempp, tempm, tempv, income_metrics)

print(f"\n📅 识别到的截至日期: {disclosure_date if disclosure_date else '未识别'}")
print(f"📊 总记录数: {len(parsed_data)}")

# 分析季度格式
period_pattern = re.compile(r'(\d{4}[/-]?(Q[1-4]|FY|H[12]))')
valid_periods = []
invalid_periods = []

for item in parsed_data:
    period = item.get('period', '')
    if period_pattern.search(period):
        valid_periods.append(period)
    else:
        invalid_periods.append(period)

unique_valid = set(valid_periods)
unique_invalid = set(invalid_periods)

print(f"\n✅ 有效季度格式 (匹配 Q1-Q4/FY): {len(unique_valid)} 种")
for p in sorted(unique_valid):
    print(f"   - {p}")

print(f"\n⚠️ 无效/异常格式: {len(unique_invalid)} 种")
for p in sorted(unique_invalid):
    print(f"   - {p}")

# 分析指标分布
metric_counts = {}
for item in parsed_data:
    mid = item.get('metric_id', 'Unknown')
    metric_counts[mid] = metric_counts.get(mid, 0) + 1

print(f"\n📈 指标分布:")
for mid, count in sorted(metric_counts.items(), key=lambda x: -x[1])[:10]:
    print(f"   - {mid}: {count} 条")

print("\n" + "=" * 60)
print("OCR识别质量检查完成")
print("=" * 60)
