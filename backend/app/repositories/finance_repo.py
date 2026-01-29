"""
财务数据仓库 - Pivot Format
支持按类别分表存储和读取
"""
from sqlalchemy.orm import Session
from backend.app.models.finance_model import (
    CATEGORY_MODEL_MAP, 
    IncomeStatementModel, 
    BalanceSheetModel, 
    CashFlowModel, 
    KeyRatiosModel
)
import json
import pandas as pd
from typing import Dict, Optional

class FinanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def _get_model_for_category(self, category: str):
        """获取类别对应的模型类"""
        return CATEGORY_MODEL_MAP.get(category)

    def save_pivot_data(self, category: str, ticker: str, pivot_df: pd.DataFrame, period_dates: Dict[str, str] = None):
        """
        保存 Pivot 格式数据到数据库
        
        Args:
            category: 类别名称 (利润表/资产负债表/现金流量表/关键指标)
            ticker: 股票代码
            pivot_df: 透视表 DataFrame (index=metric_label, columns=periods)
            period_dates: 每季度截止日期字典 {"2024/Q1": "2024/04/27", ...}
        """
        Model = self._get_model_for_category(category)
        if not Model:
            raise ValueError(f"未知类别: {category}")
        
        period_dates = period_dates or {}
        
        # 遍历每个指标行
        for metric_label in pivot_df.index:
            # 跳过"截止日期"行
            if metric_label == "截止日期":
                continue
            
            # 构建季度数据字典
            period_data = {}
            for period in pivot_df.columns:
                val = pivot_df.loc[metric_label, period]
                if pd.notna(val) and str(val).strip():
                    period_data[period] = str(val)
            
            if not period_data:
                continue  # 跳过空行
            
            # 查找现有记录
            existing = self.db.query(Model).filter(
                Model.ticker == ticker,
                Model.metric_label == metric_label
            ).first()
            
            if existing:
                # 合并现有数据和新数据
                old_data = json.loads(existing.period_data or "{}")
                old_dates = json.loads(existing.period_dates or "{}")
                old_data.update(period_data)
                old_dates.update(period_dates)
                existing.period_data = json.dumps(old_data, ensure_ascii=False)
                existing.period_dates = json.dumps(old_dates, ensure_ascii=False)
            else:
                # 创建新记录
                # 尝试从 label 推断 metric_id
                metric_id = metric_label  # 默认使用 label 作为 id
                new_record = Model(
                    ticker=ticker,
                    metric_id=metric_id,
                    metric_label=metric_label,
                    period_data=json.dumps(period_data, ensure_ascii=False),
                    period_dates=json.dumps(period_dates, ensure_ascii=False)
                )
                self.db.add(new_record)
        
        self.db.commit()

    def get_pivot_data(self, category: str, ticker: str = None) -> pd.DataFrame:
        """
        获取指定类别的 Pivot 格式数据
        
        Args:
            category: 类别名称
            ticker: 可选，过滤特定股票
            
        Returns:
            DataFrame with index=metric_label, columns=periods
        """
        Model = self._get_model_for_category(category)
        if not Model:
            return pd.DataFrame()
        
        query = self.db.query(Model)
        if ticker:
            query = query.filter(Model.ticker == ticker)
        
        records = query.all()
        if not records:
            return pd.DataFrame()
        
        # 收集所有季度
        all_periods = set()
        data_rows = []
        
        for r in records:
            period_data = json.loads(r.period_data or "{}")
            all_periods.update(period_data.keys())
            row = {"metric_label": r.metric_label, "ticker": r.ticker}
            row.update(period_data)
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        if df.empty:
            return df
        
        df = df.set_index("metric_label")
        
        # 按季度排序列
        period_cols = sorted([c for c in df.columns if c not in ['ticker']])
        return df[['ticker'] + period_cols] if 'ticker' in df.columns else df[period_cols]

    def get_all_data_by_category(self, category: str):
        """获取某类别的所有原始记录"""
        Model = self._get_model_for_category(category)
        if not Model:
            return []
        return self.db.query(Model).all()

    def delete_by_category(self, category: str) -> int:
        """删除指定类别的所有记录"""
        Model = self._get_model_for_category(category)
        if not Model:
            return 0
        deleted = self.db.query(Model).delete(synchronize_session=False)
        self.db.commit()
        return deleted

    def delete_all(self) -> int:
        """清空所有表"""
        total = 0
        for category in CATEGORY_MODEL_MAP.keys():
            total += self.delete_by_category(category)
        return total
