from sqlalchemy.orm import Session
from backend.app.models.finance_model import FinancialRecordModel
from shared.schemas.finance import FinancialRecordCreate

class FinanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_update_record(self, record_in: FinancialRecordCreate):
        """
        Upsert logic: Find existing record by ticker and period, then merge its metrics.
        """
        data = record_in.model_dump() if hasattr(record_in, "model_dump") else record_in.dict()
        
        # Check for existing record
        existing = self.db.query(FinancialRecordModel).filter(
            FinancialRecordModel.ticker == data.get('ticker', 'Unknown'),
            FinancialRecordModel.period == data.get('period')
        ).first()

        if existing:
            # Update/Merge fields
            for key, value in data.items():
                # We update if value is not None. 
                # This ensures if we upload Income Statement (metrics A, B), 
                # and then Balance Sheet (metrics C, D), all A, B, C, D are present.
                if value is not None:
                    # Special case: don't overwrite report_date with default/empty if already set
                    if key == "report_date" and not value:
                        continue
                    setattr(existing, key, value)
            db_record = existing
        else:
            db_record = FinancialRecordModel(**data)
            self.db.add(db_record)
        
        self.db.commit()
        self.db.refresh(db_record)
        return db_record

    def get_all_records(self):
        return self.db.query(FinancialRecordModel).order_by(FinancialRecordModel.period.desc()).all()

    def get_record_by_id(self, record_id: int):
        return self.db.query(FinancialRecordModel).filter(FinancialRecordModel.id == record_id).first()
