from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class FinancialRecordBase(BaseModel):
    ticker: str = "Unknown"
    year: int
    period: str
    report_date: Optional[str] = None
    category: Optional[str] = None
    
    # Allow extra fields for dynamic metrics
    model_config = ConfigDict(extra="allow", from_attributes=True)

class FinancialRecordCreate(FinancialRecordBase):
    pass

class FinancialRecord(FinancialRecordBase):
    id: int
