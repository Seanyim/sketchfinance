# backend/tests/test_ocr_income_statement.py
# 利润表数据OCR识别测试
# v2.1 - 自动化测试套件

import os
import sys
import unittest
import re

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.config.config import FINANCIAL_METRICS

# OCR服务延迟导入（需要easyocr依赖）
OCRService = None
try:
    from backend.app.services.ocr_service import OCRService as _OCRService
    OCRService = _OCRService
except ImportError:
    pass


class TestQuarterRecognition(unittest.TestCase):
    """测试季度格式精准识别"""
    
    def setUp(self):
        # 精确识别季度格式：2022/Q1, 2022FY, 2022/H1，避免误识别月份如2022/01
        self.period_pattern = re.compile(r'(\d{4}[/-]?(Q[1-4]|FY|H[12]))')
    
    def test_valid_quarter_formats(self):
        """测试有效的季度格式应被识别"""
        valid_quarters = [
            "2022/Q1", "2022/Q2", "2022/Q3", "2022/Q4",
            "2023Q1", "2023Q2", "2023Q3", "2023Q4",
            "2024/FY", "2024FY",
            "2022-Q1", "2022-FY"
        ]
        for q in valid_quarters:
            with self.subTest(quarter=q):
                match = self.period_pattern.search(q)
                self.assertIsNotNone(match, f"季度格式 {q} 应被识别")
    
    def test_invalid_month_formats_not_matched(self):
        """测试月份格式不应被误识别为季度"""
        invalid_formats = [
            "2022/01", "2022/02", "2022/03", "2022/12",
            "2022-01", "2022-12",
            "202201", "202212"
        ]
        for f in invalid_formats:
            with self.subTest(format=f):
                match = self.period_pattern.search(f)
                self.assertIsNone(match, f"月份格式 {f} 不应被识别为季度")
    
    def test_ocr_error_correction(self):
        """测试OCR错误修正：O误识别为0的情况"""
        # 根据ocr_service.py中的修正逻辑
        correction_pattern = re.compile(r'(\d{4})[/-](O)([1-4])')
        
        test_cases = [
            ("2022/O1", "2022/Q1"),
            ("2022-O2", "2022/Q2"),
        ]
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                corrected = correction_pattern.sub(r'\1/Q\3', input_val)
                self.assertEqual(corrected, expected)


class TestDisclosureDateExtraction(unittest.TestCase):
    """测试截至日期提取功能"""
    
    def setUp(self):
        # 日期模式与ocr_service.py一致
        self.date_pattern = re.compile(
            r'(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?|[二三四五六七八九〇]+年[一二三四五六七八九十]+月[一二三四五六七八九十]+日)'
        )
    
    def test_standard_date_formats(self):
        """测试标准日期格式识别"""
        valid_dates = [
            "2023-01-25",
            "2023/01/25",
            "2023年1月25日",
            "2023年12月31日",
        ]
        for d in valid_dates:
            with self.subTest(date=d):
                match = self.date_pattern.search(d)
                self.assertIsNotNone(match, f"日期格式 {d} 应被识别")
    
    def test_chinese_date_formats(self):
        """测试中文日期格式识别"""
        chinese_dates = [
            "二○二三年一月二十五日",
            "二〇二三年十二月三十一日",
        ]
        for d in chinese_dates:
            with self.subTest(date=d):
                match = self.date_pattern.search(d)
                self.assertIsNotNone(match, f"中文日期格式 {d} 应被识别")


class TestIncomeStatementMetrics(unittest.TestCase):
    """测试利润表指标识别"""
    
    def setUp(self):
        # 获取利润表类别的指标
        self.income_metrics = [m for m in FINANCIAL_METRICS if m.get('category') == '利润表']
    
    def test_income_metrics_exist(self):
        """测试利润表指标已定义"""
        self.assertGreater(len(self.income_metrics), 0, "应有利润表指标定义")
    
    def test_required_income_metrics(self):
        """测试必需的利润表指标存在"""
        required_ids = [
            "TotalRevenue", "GrossProfit", "OperatingProfit",
            "NetIncome", "NetIncomeToParent", "EPS"
        ]
        metric_ids = [m['id'] for m in self.income_metrics]
        for rid in required_ids:
            with self.subTest(metric_id=rid):
                self.assertIn(rid, metric_ids, f"利润表应包含 {rid} 指标")
    
    def test_metric_labels_for_matching(self):
        """测试指标标签可用于模糊匹配"""
        for metric in self.income_metrics:
            with self.subTest(metric_id=metric['id']):
                self.assertIn('label', metric, f"指标 {metric['id']} 应有label字段")
                self.assertIsInstance(metric['label'], str)
                self.assertGreater(len(metric['label']), 0)


class TestOCRServiceIntegration(unittest.TestCase):
    """测试OCR服务集成（需要实际图片文件）"""
    
    @classmethod
    def setUpClass(cls):
        # 检查OCR服务是否可用
        cls.ocr_available = OCRService is not None
        
        # 检查测试图片是否存在
        cls.tempp_path = os.path.join(os.getcwd(), "tempp.png")
        cls.tempm_path = os.path.join(os.getcwd(), "tempm.png")
        cls.tempv_path = os.path.join(os.getcwd(), "tempv.png")
        
        cls.images_exist = (
            os.path.exists(cls.tempp_path) and
            os.path.exists(cls.tempm_path) and
            os.path.exists(cls.tempv_path)
        )
        
        if cls.images_exist and cls.ocr_available:
            cls.ocr_service = OCRService(gpu=False)
    
    def test_multi_image_parsing(self):
        """测试多图解析功能（需要tempp/tempm/tempv图片）"""
        if not self.ocr_available:
            self.skipTest("OCR服务不可用(easyocr未安装)，跳过集成测试")
        if not self.images_exist:
            self.skipTest("测试图片(tempp.png, tempm.png, tempv.png)不存在，跳过OCR集成测试")
        
        income_metrics = [m for m in FINANCIAL_METRICS if m.get('category') == '利润表']
        
        parsed_data, disclosure_date = self.ocr_service.parse_multi_image(
            self.tempp_path, self.tempm_path, self.tempv_path, income_metrics
        )
        
        # 验证返回数据结构
        self.assertIsInstance(parsed_data, list)
        
        if parsed_data:
            # 验证每条记录包含必要字段
            for item in parsed_data:
                self.assertIn('metric_id', item)
                self.assertIn('period', item)
                self.assertIn('value', item)
            
            # 验证季度格式正确（应为Q1-Q4、FY或H1/H2，不是月份）
            period_pattern = re.compile(r'\d{4}[/-]?(Q[1-4]|FY|H[12])')
            for item in parsed_data:
                period = item.get('period', '')
                if period:
                    match = period_pattern.search(period)
                    self.assertIsNotNone(match, f"期间格式 {period} 应为季度格式(Q1-Q4/FY/H1-H2)")
            
            print(f"\n[OCR 集成测试] 成功解析 {len(parsed_data)} 条记录")
            if disclosure_date:
                print(f"[OCR 集成测试] 识别到截至日期: {disclosure_date}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
