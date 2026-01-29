"""
财务数据模型 - Pivot Format
按类别分表存储，格式与预览表一致
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# 数据库路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'finance.db')}"

Base = declarative_base()

# =============================================================================
# 通用 Pivot 格式表模型
# 每行代表一个指标，每列代表一个季度
# =============================================================================

class IncomeStatementModel(Base):
    """利润表"""
    __tablename__ = "income_statement"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, default="Unknown")
    metric_id = Column(String, index=True)      # e.g., "EPS"
    metric_label = Column(String)                # e.g., "每股收益 (EPS)"
    # 季度数据存储为 JSON 字符串: {"2024/Q1": "0.6", "2024/H1": "1.2", ...}
    period_data = Column(Text, default="{}")
    # 每季度截止日期也存储为 JSON: {"2024/Q1": "2024/04/27", ...}
    period_dates = Column(Text, default="{}")


class BalanceSheetModel(Base):
    """资产负债表"""
    __tablename__ = "balance_sheet"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, default="Unknown")
    metric_id = Column(String, index=True)
    metric_label = Column(String)
    period_data = Column(Text, default="{}")
    period_dates = Column(Text, default="{}")


class CashFlowModel(Base):
    """现金流量表"""
    __tablename__ = "cash_flow"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, default="Unknown")
    metric_id = Column(String, index=True)
    metric_label = Column(String)
    period_data = Column(Text, default="{}")
    period_dates = Column(Text, default="{}")


class KeyRatiosModel(Base):
    """关键指标"""
    __tablename__ = "key_ratios"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, default="Unknown")
    metric_id = Column(String, index=True)
    metric_label = Column(String)
    period_data = Column(Text, default="{}")
    period_dates = Column(Text, default="{}")


# 类别到模型的映射
CATEGORY_MODEL_MAP = {
    "利润表": IncomeStatementModel,
    "资产负债表": BalanceSheetModel,
    "现金流量表": CashFlowModel,
    "关键指标": KeyRatiosModel,
}

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(bind=engine)

def reset_db():
    """重置数据库（删除并重新创建所有表）"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
