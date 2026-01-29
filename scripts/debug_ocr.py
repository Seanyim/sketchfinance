# 诊断脚本：检查tempv数值和日期OCR结果
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.ocr_service import OCRService

ocr = OCRService(gpu=False)

print("=" * 60)
print("检查tempv.png (数据图片) OCR原始结果 - 最后20项")
print("=" * 60)
results = ocr.extract_text_from_image("tempv.png")

# 显示最后20个识别结果（包含倒数第三行的日期）
print(f"\n总识别项数: {len(results)}")
print("\n最后20项:")
for i, r in enumerate(results[-20:]):
    print(f"{len(results)-20+i+1}. 文本: {r['text']!r}  置信度: {r['confidence']:.2f}")

# 查找包含小数点的数值
print("\n" + "=" * 60)
print("查找包含小数点或日期的项:")
print("=" * 60)
for i, r in enumerate(results):
    text = r['text']
    if '.' in text or '年' in text or '-' in text or '月' in text:
        print(f"{i+1}. 文本: {text!r}  置信度: {r['confidence']:.2f}")
