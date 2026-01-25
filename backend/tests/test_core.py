import os
import sys
import unittest
from PIL import Image

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.ocr_service import OCRService
from backend.app.models.finance_model import init_db, SessionLocal, FinancialRecordModel
from backend.app.repositories.finance_repo import FinanceRepository
from shared.schemas.finance import FinancialRecordCreate
from backend.config.config import FINANCIAL_METRICS

class TestFinanceSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        cls.repo = FinanceRepository(cls.db)
        cls.ocr = OCRService()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_database_write_read(self):
        """Test if records can be correctly stored and retrieved in long format."""
        test_record = FinancialRecordCreate(
            metric_id="TotalRevenue",
            value="100.00",
            period="2024-Q1",
            entity_name="TestCorp",
            category="利润表"
        )
        created = self.repo.create_record(test_record)
        self.assertIsNotNone(created.id)
        
        retrieved = self.repo.get_record_by_id(created.id)
        self.assertEqual(retrieved.metric_id, "TotalRevenue")
        self.assertEqual(retrieved.value, "100.00")
        self.assertEqual(retrieved.period, "2024-Q1")

    def test_ocr_processing(self):
        """Test OCR service if a sample image exists."""
        sample_path = os.path.join(os.getcwd(), "samples", "nvda_financial.png")
        if os.path.exists(sample_path):
            results = self.ocr.extract_text_from_image(sample_path)
            self.assertTrue(len(results) > 0)
            
            parsed = self.ocr.parse_financial_data(results, FINANCIAL_METRICS)
            # Check if we at least got some items with periods and metric IDs
            self.assertTrue(len(parsed) > 0)
            for item in parsed:
                self.assertIn('metric_id', item)
                self.assertIn('period', item)
                self.assertIn('value', item)
            print(f"\n[OCR Test] Extracted {len(parsed)} grid items from sample.")
        else:
            self.skipTest("Sample image not found, skipping OCR functional test.")

if __name__ == "__main__":
    unittest.main()
