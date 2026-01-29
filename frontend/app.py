import streamlit as st
import pandas as pd
from PIL import Image
import os
import sys
import json
import gc
from datetime import datetime

# Aggressive memory management for CUDA
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
from streamlit_paste_button import paste_image_button

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib.util
from backend.app.services.ocr_service import OCRService
from backend.app.models.finance_model import init_db, SessionLocal
from backend.app.repositories.finance_repo import FinanceRepository

# Helper: Load Config
def load_financial_metrics(config_path):
    spec = importlib.util.spec_from_file_location("config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FINANCIAL_METRICS

# Initialize database
init_db()

st.set_page_config(page_title="SketchFinance - 财务数据识录", layout="wide")

# Sidebar - Config Only
st.sidebar.header("📝 指标配置")
default_config_path = os.path.join(os.getcwd(), "backend", "config", "config.py")
uploaded_config = st.sidebar.file_uploader("上传自定义 config.py (仅影响数据录入)", type=['py'])

if uploaded_config:
    temp_config_path = "temp_config.py"
    with open(temp_config_path, "wb") as f:
        f.write(uploaded_config.getbuffer())
    FINANCIAL_METRICS = load_financial_metrics(temp_config_path)
    st.sidebar.success("已加载自定义配置")
else:
    FINANCIAL_METRICS = load_financial_metrics(default_config_path)

# Initialize OCR Service (CPU mode for stability)
if 'ocr_service' not in st.session_state:
    st.session_state.ocr_service = OCRService(gpu=False)

# Clean memory periodically
gc.collect()

if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()
    st.session_state.repo = FinanceRepository(st.session_state.db)

if 'auto_disclosure_date' not in st.session_state:
    st.session_state.auto_disclosure_date = ""

# Sidebar - Samples and History
st.sidebar.header("📁 参考与历史")
sample_dir = os.path.join(os.getcwd(), "samples")
if not os.path.exists(sample_dir):
    os.makedirs(sample_dir)

samples = [f for f in os.listdir(sample_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.db'))]
selected_sample = st.sidebar.selectbox("选择参考文件", ["无"] + samples)

if selected_sample != "无":
    st.sidebar.info(f"正在查看: {selected_sample}")

# Helper: Filter metrics by category
def get_metrics_by_category(category):
    return [m for m in FINANCIAL_METRICS if m.get('category') == category]

# Main Layout: Two columns
col_up, col_res = st.columns([1, 1])

with col_up:
    # Category & Disclosure Date
    st.header("1. 配置基础信息")
    cats = globals().get('CATEGORY_ORDER', ["关键指标", "利润表", "资产负债表", "现金流量表"])
    selected_category = st.selectbox("请选择要识别的报表类型", cats)
    current_metrics = get_metrics_by_category(selected_category)
    
    # Disclosure date will be extracted automatically
    if st.session_state.auto_disclosure_date:
        st.success(f"📅 识别到报表截止日: {st.session_state.auto_disclosure_date}")

    # Multi-Image Upload
    st.header("2. 上传/粘贴截图模块")
    st.info("提示：您可以直接点击按钮并使用 Ctrl+V 粘贴截图")
    
    col_p, col_m, col_v = st.columns(3)
    with col_p:
        st.subheader("📅 季度")
        upload_p = st.file_uploader("文件", type=["png", "jpg", "jpeg"], key="up_p")
        paste_p = paste_image_button("📋 粘贴季度", key="p_p")
        img_p = upload_p if upload_p else (paste_p.image_data if paste_p.image_data else None)
        if img_p: st.image(img_p)
    with col_m:
        st.subheader("📊 科目")
        upload_m = st.file_uploader("文件", type=["png", "jpg", "jpeg"], key="up_m")
        paste_m = paste_image_button("📋 粘贴科目", key="p_m")
        img_m = upload_m if upload_m else (paste_m.image_data if paste_m.image_data else None)
        if img_m: st.image(img_m)
    with col_v:
        st.subheader("💰 数据")
        upload_v = st.file_uploader("文件", type=["png", "jpg", "jpeg"], key="up_v")
        paste_v = paste_image_button("📋 粘贴数据", key="p_v")
        img_v = upload_v if upload_v else (paste_v.image_data if paste_v.image_data else None)
        if img_v: st.image(img_v)

    if st.button("🚀 开始多图智能识别", use_container_width=True):
        if not (img_p and img_m and img_v):
            st.warning("请上传完整的三个部分截图。")
        else:
            with st.spinner(f"正在深度解析 {selected_category}..."):
                # Save temp
                paths = []
                for img, n in [(img_p, "p"), (img_m, "m"), (img_v, "v")]:
                    path = f"temp_{n}.png"
                    if hasattr(img, 'save'): # PIL Image from paste
                        img.save(path)
                    else: # Bytes/UploadedFile
                        with Image.open(img) as o_img:
                            o_img.save(path)
                    paths.append(path)
                
                gc.collect()
                
                # Perform Multi-Image OCR
                try:
                    parsed_data, extracted_date = st.session_state.ocr_service.parse_multi_image(
                        paths[0], paths[1], paths[2], current_metrics
                    )
                except Exception as e:
                    st.error(f"OCR 识别失败: {e}. 建议关闭侧边栏 'OCR GPU 加速' 后重试。")
                    parsed_data, extracted_date = None, None

                if extracted_date:
                    st.session_state.auto_disclosure_date = extracted_date
                
                
                if parsed_data:
                    for item in parsed_data: item['category'] = selected_category
                    df = pd.DataFrame(parsed_data)
                    df = df.drop_duplicates(subset=['metric_id', 'period'], keep='first')
                    
                    # 创建主数据透视表
                    pivot_df = df.pivot(index='metric_id', columns='period', values='value')
                    labels_map = {m['id']: m['label'] for m in FINANCIAL_METRICS}
                    pivot_df.index = pivot_df.index.map(lambda x: labels_map.get(x, x))
                    
                    # 提取每季度的截止日期
                    if 'report_date' in df.columns:
                        date_df = df.drop_duplicates(subset=['period'])[['period', 'report_date']]
                        date_dict = dict(zip(date_df['period'], date_df['report_date']))
                        st.session_state.period_dates = date_dict
                        
                        # 创建日期行并添加到透视表
                        date_row = pd.DataFrame([date_dict], index=['截止日期'])
                        date_row = date_row.reindex(columns=pivot_df.columns)
                        pivot_df = pd.concat([date_row, pivot_df])
                    
                    st.session_state.parsed_df = pivot_df
                    st.session_state.raw_parsed = parsed_data
                    st.success("识别完成!")
                else:
                    st.error("识别失败，请检查截图。")


with col_res:
    st.subheader("📋 识别结果预览与编辑")
    if 'parsed_df' in st.session_state:
        # 显示披露日期
        if st.session_state.auto_disclosure_date:
            st.info(f"📅 识别到的披露日期：**{st.session_state.auto_disclosure_date}**")
        
        edited_df = st.data_editor(st.session_state.parsed_df, use_container_width=True)
        
        target_ticker = st.text_input("公司代码 (Ticker)", value="NVDA")
        
        # 数据库管理选项
        db_col1, db_col2 = st.columns(2)
        with db_col1:
            overwrite_existing = st.checkbox("🔄 覆盖相同日期数据", value=True, 
                help="勾选后，相同Ticker、年份、期间、类别的数据会被覆盖；否则跳过已存在的记录")
        with db_col2:
            if st.button("🗑️ 清空该类别数据"):
                # 获取将被删除的记录数
                deleted = st.session_state.repo.delete_by_category(selected_category)
                st.warning(f"已清空 {deleted} 条{selected_category}数据")
                st.rerun()

        if st.button("💾 保存到数据库 (Pivot Format)"):
            try:
                # 获取每季度截止日期
                period_dates = st.session_state.get('period_dates', {})
                
                # 调用新的 Pivot 格式保存方法
                st.session_state.repo.save_pivot_data(
                    category=selected_category,
                    ticker=target_ticker,
                    pivot_df=edited_df,
                    period_dates=period_dates
                )
                
                st.success(f"已成功保存 {selected_category} 数据到数据库！")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
    else:
        st.info('尚未进行识别。请先上传或粘贴截图并点击开始识别。')

# History View (Pivot Format - Per Category)
st.divider()
st.header("📊 数据库已录入数据")

# 按类别显示数据
from backend.app.models.finance_model import CATEGORY_MODEL_MAP
db_categories = list(CATEGORY_MODEL_MAP.keys())
selected_db_category = st.selectbox("选择要查看的类别", db_categories, key="db_view_category")

db_df = st.session_state.repo.get_pivot_data(selected_db_category)
if not db_df.empty:
    st.dataframe(db_df, use_container_width=True)
else:
    st.info(f"暂无 {selected_db_category} 数据录入记录。")

