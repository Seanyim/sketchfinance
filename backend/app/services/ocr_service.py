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
                "box": bbox,  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                "confidence": prob
            })
        return extracted

    def parse_multi_image(self, periods_path: str, metrics_path: str, values_path: str, metric_config: List[Dict]) -> Tuple[List[Dict], str]:
        try:
            return self._do_parse_multi_image(periods_path, metrics_path, values_path, metric_config)
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and self.gpu:
                print("CUDA OOM detected! Falling back to CPU for OCR...")
                # Temporarily switch to CPU reader
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
        Coordinate OCR across three images:
        ...
        """
        # 0. Initialize return values
        disclosure_date = ""
        # Support both YYYY-MM-DD and Chinese numbers like 二○二三...
        date_pattern = re.compile(r'(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?|[二三四五六七八九〇]+年[一二三四五六七八九十]+月[一二三四五六七八九十]+日)')
        # 1. Periods (X-axis)
        p_ocr = self.reader.readtext(periods_path)
        # Expanded Period pattern: handles 2023/Q1, 2023/01, 2023FY, etc.
        period_pattern = re.compile(r'(\d{4}[/-]?\w+|20\d{2})')
        headers = []
        for (bbox, text, prob) in p_ocr:
            clean_text = text.replace(" ", "").upper()
            
            # --- Advanced OCR Correction ---
            # 1. Fix Year/FY (e.g., 2022IFY -> 2022/FY, 2022 1FY -> 2022/FY)
            clean_text = re.sub(r'(\d{4})[I|1| ]?FY', r'\1/FY', clean_text)
            
            # 2. Fix Year/QX (e.g., 2022/09 -> 2022/Q9, 2022/O1 -> 2022/Q1)
            # Match 202X followed by separator and something that looks like Q then number
            clean_text = re.sub(r'(\d{4})[/-](0|O|Q)([1-9])', r'\1/Q\3', clean_text)
            
            # 3. Detect Disclosure Date (e.g., 2023-01-25)
            date_match = date_pattern.search(clean_text)
            if date_match and not disclosure_date:
                disclosure_date = date_match.group(1)
                continue

            # 4. Handle standalone Quarter if year is implied
            if period_pattern.search(clean_text):
                x_center = sum([p[0] for p in bbox]) / 4
                headers.append({"text": clean_text, "x": x_center})
        
        headers.sort(key=lambda x: x['x'])
        # Post-process: If multiple headers are very close, they might be fragments
        # (Usually EasyOCR handles this, but sorted list is safer)

        # 2. Metrics (Y-axis)
        m_ocr = self.reader.readtext(metrics_path)
        indices = []
        config_labels = [m['label'] for m in metric_config]
        label_to_id = {m['label']: m['id'] for m in metric_config}

        for (bbox, text, prob) in m_ocr:
            clean_text = text.replace(" ", "")
            y_center = sum([p[1] for p in bbox]) / 4
            
            # Use difflib for fuzzy matching
            matches = difflib.get_close_matches(clean_text, config_labels, n=1, cutoff=0.3)
            if matches:
                matched_label = matches[0]
                indices.append({
                    "metric_id": label_to_id[matched_label],
                    "label": matched_label,
                    "y": y_center
                })
            else:
                # Fallback to simple containment for long strings
                for m in metric_config:
                    label = m['label']
                    if len(clean_text) > 3 and (label in clean_text or clean_text in label):
                        indices.append({
                            "metric_id": m['id'],
                            "label": label,
                            "y": y_center
                        })
                        break
        indices.sort(key=lambda x: x['y'])

        # 3. Values (Main Grid)
        v_ocr = self.reader.readtext(values_path)
        values = []
        for (bbox, text, prob) in v_ocr:
            clean_text = text.replace(" ", "")
            if any(char.isdigit() for char in clean_text) or "亿" in clean_text or "%" in clean_text or "." in clean_text:
                x_center = sum([p[0] for p in bbox]) / 4
                y_center = sum([p[1] for p in bbox]) / 4
                values.append({"text": clean_text, "x": x_center, "y": y_center})

        if not headers or not indices:
            return []

        # 4. Mapping (Anchor-based + Proportion)
        # Even if Image 3 has different scale, we can map using relative order
        parsed_data = []
        
        # Determine Value Grid bounds in Image 3
        # We assume values are laid out in a grid corresponding to sorted headers and indices
        for v in values:
            # Match to closest Period by X
            # We use normalized relative position of x in values compared to spans of headers
            # Simpler: find the header whose relative X rank matches the value's relative X rank
            # Or just find the physically closest if scales are somewhat consistent
            
            closest_hdr = min(headers, key=lambda h: abs(h['x'] - v['x']), default=None)
            closest_idx = min(indices, key=lambda i: abs(i['y'] - v['y']), default=None)

            # Verification: If the distance is too large, it might be a false positive
            # But with separate images, scale might differ. 
            # A more robust way is to use relative rank:
            # 1. Get rank of v['x'] among all value's x
            # 2. Map rank to a header
            # But let's try physical distance first as user likely crops consistently.
            
            if closest_hdr and closest_idx:
                parsed_data.append({
                    "metric_id": closest_idx['metric_id'],
                    "period": closest_hdr['text'],
                    "value": v['text']
                })

        return parsed_data, disclosure_date

    def parse_financial_data(self, ocr_results: List[Dict], metric_config: List[Dict]) -> List[Dict]:
        """
        Advanced grid recognition logic.
        1. Identify Period Headers (e.g., 2022/Q1, 2023/FY).
        2. Identify Metric Indices (match labels from config).
        3. Map values to intersections.
        """
        headers = [] # List of (text, x_center, y_center)
        indices = [] # List of (metric_id, label, x_center, y_center)
        values = []  # List of (text, x_center, y_center)

        # Regex for years/periods: 202X or 202X/XX or XX/XX (simplified)
        period_pattern = re.compile(r'(\d{4}[/-]?\w+|20\d{2})')

        for item in ocr_results:
            text = item['text'].replace(" ", "")
            box = item['box']
            x_center = sum([p[0] for p in box]) / 4
            y_center = sum([p[1] for p in box]) / 4

            # 1. Identify Headers
            if period_pattern.search(text):
                headers.append({"text": text, "x": x_center, "y": y_center})
                continue
            
            # 2. Identify Indices (Fuzzy match with config labels)
            matched_metric = None
            for m in metric_config:
                label = m['label'].replace(" ", "")
                # Simple exact or partial match for now; could use fuzzywuzzy
                if label in text or text in label:
                    matched_metric = m
                    break
            
            if matched_metric:
                indices.append({
                    "metric_id": matched_metric['id'],
                    "label": matched_metric['label'],
                    "category": matched_metric['category'],
                    "x": x_center,
                    "y": y_center
                })
                continue

            # 3. Everything else is a potential value
            # Filter for numbers/billions/etc.
            if any(char.isdigit() for char in text) or "亿" in text or "%" in text:
                values.append({"text": text, "x": x_center, "y": y_center})

        # Mapping Values to Grid
        parsed_data = []
        for v in values:
            # Find closest index (row) - sharing similar Y
            closest_idx = None
            min_y_dist = 20 # Pixel threshold
            for idx in indices:
                dist = abs(idx['y'] - v['y'])
                if dist < min_y_dist:
                    min_y_dist = dist
                    closest_idx = idx
            
            if not closest_idx: continue

            # Find closest header (column) - sharing similar X
            closest_hdr = None
            min_x_dist = 100 # X distance can be larger between columns
            for hdr in headers:
                dist = abs(hdr['x'] - v['x'])
                if dist < min_x_dist:
                    min_x_dist = dist
                    closest_hdr = hdr
            
            if closest_hdr:
                parsed_data.append({
                    "metric_id": closest_idx['metric_id'],
                    "category": closest_idx['category'],
                    "period": closest_hdr['text'],
                    "value": v['text']
                })
        
        return parsed_data
