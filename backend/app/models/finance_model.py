from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add project root to path for config import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from backend.config.config import FINANCIAL_METRICS

DATABASE_URL = "sqlite:///d:/OneDrive/Documents/Files/Code/software/Python/SketchFinance/finance.db"

Base = declarative_base()

class FinancialRecordModel(Base):
    __tablename__ = "financial_records"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, default="Unknown")
    year = Column(Integer, index=True)
    period = Column(String, index=True)  # e.g., Q1, Q2, FY
    report_date = Column(String, nullable=True)
    
    # Store category to help with UI filtering if needed
    category = Column(String, nullable=True)

    # Dynamically add columns based on FINANCIAL_METRICS
    # Note: Using Float (REAL in SQLite) for metrics
    pass

# Dynamically inject columns into the class
for metric in FINANCIAL_METRICS:
    setattr(FinancialRecordModel, metric['id'], Column(Float, default=0.0))

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # If table exists, we may need to drop it or migrate. 
    # For this refactor, we drop and recreate to ensure wide format.
    Base.metadata.create_all(bind=engine)
