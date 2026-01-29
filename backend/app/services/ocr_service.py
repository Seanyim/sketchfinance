import easyocr
import re
import numpy as np
import difflib
from PIL import Image
from typing import List, Dict, Tuple

class OCRService:
    def __init__(self, languages=['ch_sim', 'en'], gpu=True):
        self.languages = languages
        self.gpu = gpu
        self.reader = easyocr.Reader(languages, gpu=gpu)

    def extract_text_from_image(self, image_path: str) -> List[Dict]:
        """
        Extract text and coordinates from an image.
        Returns a list of dicts with 'text', 'box', and 'confidence'.
        """
        results = self.reader.readtext(image_path)
        extracted = []
        for (bbox, text, prob) in results:
            extracted.append({
                "text": text,
                "box": bbox,
                "confidence": prob
            })
        return extracted

    def parse_multi_image(self, periods_path: str, metrics_path: str, values_path: str, metric_config: List[Dict]) -> Tuple[List[Dict], str]:
        try:
            return self._do_parse_multi_image(periods_path, metrics_path, values_path, metric_config)
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and self.gpu:
                print("CUDA OOM detected! Falling back to CPU for OCR...")
                temp_reader = easyocr.Reader(self.languages, gpu=False)
                original_reader = self.reader
                self.reader = temp_reader
                try:
                    return self._do_parse_multi_image(periods_path, metrics_path, values_path, metric_config)
                finally:
                    self.reader = original_reader
            raise e

    def _do_parse_multi_image(self, periods_path: str, metrics_path: str, values_path: str, metric_config: List[Dict]) -> Tuple[List[Dict], str]:
        """
        Coordinate OCR across three images.
        Returns (parsed_data, disclosure_date)
        Each item in parsed_data includes: metric_id, period, value, report_date (per-period)
        """
        # Date pattern
        date_pattern = re.compile(r'(\d{4}[年/.-]\d{1,2}[月/.-]\d{1,2}日?)')
        
        # ========== 1. Periods (X-axis) ==========
        p_ocr = self.reader.readtext(periods_path)
        headers = []
        for (bbox, text, prob) in p_ocr:
            clean_text = text.replace(" ", "").upper()
            
            # Fix Year/FY
            clean_text = re.sub(r'(\d{4})[I|1| ]?FY', r'\1/FY', clean_text)
            
            # H1 映射: 41 -> H1
            clean_text = re.sub(r'(\d{4})[/-](4I|41|42)(?!\d)', r'\1/H1', clean_text)
            
            # 标准化H1/H2
            if re.search(r'(\d{4})[/-]H[12]', clean_text):
                clean_text = re.sub(r'(\d{4})[/-]H([12])', r'\1/H\2', clean_text)
            else:
                # 季度修正 - 用户要求保留09（不转为Q3）
                clean_text = re.sub(r'(\d{4})[/-](O)([1-4])', r'\1/Q\3', clean_text)  # O -> Q
                clean_text = re.sub(r'(\d{4})[/-]Q?01(?!\d)', r'\1/Q1', clean_text)  # 01 -> Q1
                # 不再转换09 -> Q3，保留原始值
                clean_text = re.sub(r'(\d{4})[/-]Q?04(?!\d)', r'\1/Q4', clean_text)  # 04 -> Q4
            
            # 允许多种格式通过
            if re.search(r'(\d{4}[/-]?(Q[1-4]|FY|H[12]|\d{2}))', clean_text):
                x_center = sum([p[0] for p in bbox]) / 4
                headers.append({"text": clean_text, "x": x_center})
        
        headers.sort(key=lambda x: x['x'])

        # ========== 2. Metrics (Y-axis) with Enhanced Matching ==========
        m_ocr = self.reader.readtext(metrics_path)
        indices = []
        config_labels = [m['label'] for m in metric_config]
        
        # 扩展别名映射（针对低置信度OCR结果）
        alias_map = {
            # EPS 别名（包括所有可能的OCR错误变体）
            "其本每股收益": "每股收益 (EPS)",
            "基本每股收益": "每股收益 (EPS)",
            "稀释每股收益": "每股收益 (EPS)",
            "每股收益": "每股收益 (EPS)",
            "EPS": "每股收益 (EPS)",
            "每股盈利": "每股收益 (EPS)",
            # 营业相关（OCR常将"营"识别为"菅"）
            "菅业总收入": "营业总收入",
            "菅业费用": "营业费用",
            "其他菅业费用": "营业费用",
            "菅业利润": "营业利润",
            # 归母净利润
            "归屑于母公司股东净利润": "归属母公司净利润",
            "归属于普通股股东净利润": "归属母公司净利润",
            "归属母公司股东净利润": "归属母公司净利润",
            # 其他
            "毛利润": "毛利",
        }
        
        for (bbox, text, prob) in m_ocr:
            current_y = sum([p[1] for p in bbox]) / 4
            clean_text = text.replace(" ", "")
            
            # 跳过非科目文本
            if '截止' in clean_text or '会计' in clean_text or '审计' in clean_text:
                continue
            
            # 1. 首先尝试别名匹配（优先级最高）
            matched_label = None
            for alias, label in alias_map.items():
                if alias in clean_text or clean_text in alias:
                    matched_label = label
                    break
            
            # 2. 如果别名匹配失败，尝试模糊匹配（降低cutoff到0.4）
            if not matched_label:
                best_match = difflib.get_close_matches(clean_text, config_labels, n=1, cutoff=0.4)
                if best_match:
                    matched_label = best_match[0]
            
            # 3. 最后尝试简单包含匹配
            if not matched_label:
                for m in metric_config:
                    if m['label'] in clean_text or clean_text in m['label']:
                        matched_label = m['label']
                        break
            
            if matched_label:
                metric_obj = next((m for m in metric_config if m['label'] == matched_label), None)
                if metric_obj:
                    # 避免重复添加相同指标
                    if not any(idx['metric_id'] == metric_obj['id'] for idx in indices):
                        indices.append({
                            "metric_id": metric_obj['id'],
                            "label": metric_obj['label'],
                            "y": current_y,
                            "x": sum([p[0] for p in bbox]) / 4
                        })
        
        indices.sort(key=lambda x: x['y'])

        # ========== 3. Values (Main Grid) + Per-Period Dates ==========
        v_ocr = self.reader.readtext(values_path)
        values = []
        period_dates = []  # 存储(x_center, date)用于后续匹配
        
        for (bbox, text, prob) in v_ocr:
            x_center = sum([p[0] for p in bbox]) / 4
            y_center = sum([p[1] for p in bbox]) / 4
            
            # 检测日期
            date_match = date_pattern.search(text.replace(" ", ""))
            if date_match:
                period_dates.append({"x": x_center, "date": date_match.group(1)})
                continue
            
            clean_text = text.strip()
            
            # 修复丢失小数点
            if "." not in clean_text:
                if " " in clean_text:
                    parts = clean_text.split()
                    if len(parts) == 2 and len(parts[0]) == 1 and len(parts[1]) == 2:
                        if parts[0].isdigit() and parts[1].isdigit():
                            clean_text = f"{parts[0]}.{parts[1]}"
                elif len(clean_text) == 3 and clean_text.isdigit() and prob < 0.8:
                    clean_text = f"{clean_text[0]}.{clean_text[1:]}"
            
            clean_text = clean_text.replace(" ", "")
            
            if any(c.isdigit() for c in clean_text) or "亿" in clean_text or "%" in clean_text or "." in clean_text:
                values.append({"text": clean_text, "x": x_center, "y": y_center})
        
        # 为每个季度匹配对应的截止日期
        def find_closest_date(header_x):
            """根据header的X位置找到最接近的日期"""
            if not period_dates:
                return ""
            closest = min(period_dates, key=lambda d: abs(d['x'] - header_x))
            # 如果距离太远（超过100像素），不匹配
            if abs(closest['x'] - header_x) > 100:
                return ""
            return closest['date']
        
        # 创建header到日期的映射
        header_to_date = {}
        for h in headers:
            header_to_date[h['text']] = find_closest_date(h['x'])

        if not headers or not indices:
            return [], ""

        # ========== 4. Mapping Values to Headers and Indices ==========
        parsed_data = []
        
        for v in values:
            closest_hdr = min(headers, key=lambda h: abs(h['x'] - v['x']), default=None)
            closest_idx = min(indices, key=lambda i: abs(i['y'] - v['y']), default=None)
            
            if closest_hdr and closest_idx:
                parsed_data.append({
                    "metric_id": closest_idx['metric_id'],
                    "period": closest_hdr['text'],
                    "value": v['text'],
                    "report_date": header_to_date.get(closest_hdr['text'], "")
                })

        # 返回最后一个日期作为全局披露日期（向后兼容）
        disclosure_date = period_dates[-1]['date'] if period_dates else ""
        
        return parsed_data, disclosure_date

    def parse_financial_data(self, ocr_results: List[Dict], metric_config: List[Dict]) -> List[Dict]:
        """
        Parse OCR results into structured financial data using metric config.
        """
        parsed = []
        config_labels = [m['label'] for m in metric_config]
        
        for item in ocr_results:
            text = item.get('text', '')
            matches = difflib.get_close_matches(text, config_labels, n=1, cutoff=0.6)
            if matches:
                parsed.append({
                    "label": matches[0],
                    "raw_text": text
                })
        return parsed
