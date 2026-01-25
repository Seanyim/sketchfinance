import streamlit as st
import pandas as pd
from PIL import Image
import os
import sys
import json
import torch
import gc
from datetime import datetime

# Aggressive memory management for CUDA
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
from streamlit_paste_button import paste_image_button

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib.util
from backend.app.services.ocr_service import OCRService
from backend.app.services.ai_enhancer import AIEnhancerService
from backend.app.services.ai_local_service import AIEnhancerLocal
from backend.app.models.finance_model import init_db, SessionLocal, FinancialRecordModel
from backend.app.repositories.finance_repo import FinanceRepository
from shared.schemas.finance import FinancialRecordCreate

# Helper: Load Config
def load_financial_metrics(config_path):
    spec = importlib.util.spec_from_file_location("config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FINANCIAL_METRICS

# Initialize database
init_db()

st.set_page_config(page_title="SketchFinance - 财务数据识录", layout="wide")

# Sidebar - Settings & Config
st.sidebar.header("⚙️ 系统设置")
ollama_url = st.sidebar.text_input("Ollama URL", value="http://localhost:11434")
ollama_model = st.sidebar.text_input("Ollama Model", value="llama3")

st.sidebar.divider()
st.sidebar.header("📝 指标配置")
default_config_path = os.path.join(os.getcwd(), "backend", "config", "config.py")
uploaded_config = st.sidebar.file_uploader("上传自定义 config.py", type=['py'])

if uploaded_config:
    temp_config_path = "temp_config.py"
    with open(temp_config_path, "wb") as f:
        f.write(uploaded_config.getbuffer())
    FINANCIAL_METRICS = load_financial_metrics(temp_config_path)
    st.sidebar.success("已加载自定义配置")
else:
    FINANCIAL_METRICS = load_financial_metrics(default_config_path)

# Sidebar - Optimization Settings
st.sidebar.header("⚙️ 性能设置")
gpu_ocr_enabled = st.sidebar.toggle("⚡ OCR GPU 加速", value=False, help="如果开启本地 AI 模型，建议关闭此项以节省显存")

# Initialize Services with Safety
if 'ocr_service' not in st.session_state:
    try:
        st.session_state.ocr_service = OCRService(gpu=gpu_ocr_enabled)
    except Exception as e:
        st.sidebar.warning(f"GPU OCR 初始化失败: {e}。将回退到 CPU 模式。")
        st.session_state.ocr_service = OCRService(gpu=False)

st.sidebar.info("提示：如果显卡显存(VRAM)不足导致报错，请保持上面开关处于**关闭**状态。")

if 'ai_enhancer' not in st.session_state:
    st.session_state.ai_enhancer = AIEnhancerService(ollama_url=ollama_url, model=ollama_model)
else:
    st.session_state.ai_enhancer.ollama_url = f"{ollama_url}/api/generate"
    st.session_state.ai_enhancer.model = ollama_model

# Clean memory periodically
if torch.cuda.is_available():
    torch.cuda.empty_cache()
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
    
    use_local_ai = st.toggle("🚀 使用本地 Transformers 模型深度纠错", value=True, help="启用后将使用本地 0.5B 模型对识别结果进行语义微调")

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
                
                if torch.cuda.is_available():
                    gc.collect()
                    torch.cuda.empty_cache()
                
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
                
                # Boost with Local AI if enabled
                if use_local_ai and parsed_data:
                    if 'ai_local' not in st.session_state:
                        with st.status("🧠 正在初始化本地 AI 模型 (可能触发 GPU 内存警告)..."):
                            try:
                                gc.collect()
                                if torch.cuda.is_available(): torch.cuda.empty_cache()
                                st.session_state.ai_local = AIEnhancerLocal()
                            except Exception as e:
                                st.error(f"本地 AI 模型加载失败: {e}。将禁用 AI 增强。")
                                use_local_ai = False
                    
                    with st.spinner("🤖 本地 AI 正在深度校验识别结果..."):
                        # Convert parsed data back to text for AI to see context
                        raw_data_str = json.dumps(parsed_data, ensure_ascii=False)
                        ai_json = st.session_state.ai_local.enhance_ocr_results(raw_data_str, current_metrics)
                        try:
                            ai_parsed = json.loads(ai_json)
                            if ai_parsed:
                                parsed_data = ai_parsed
                                st.toast("✅ 本地 AI 已成功校验并优化数据结果", icon="🤖")
                        except Exception as e:
                            st.error(f"AI 校验失败: {e}")
                
                if parsed_data:
                    for item in parsed_data: item['category'] = selected_category
                    df = pd.DataFrame(parsed_data)
                    df = df.drop_duplicates(subset=['metric_id', 'period'], keep='first')
                    pivot_df = df.pivot(index='metric_id', columns='period', values='value')
                    labels_map = {m['id']: m['label'] for m in FINANCIAL_METRICS}
                    pivot_df.index = pivot_df.index.map(lambda x: labels_map.get(x, x))
                    st.session_state.parsed_df = pivot_df
                    st.session_state.raw_parsed = parsed_data
                    st.success("识别完成!")
                else:
                    st.error("识别失败，请检查截图。")

with col_res:
    st.subheader("📋 识别结果预览与编辑")
    if 'parsed_df' in st.session_state:
        edited_df = st.data_editor(st.session_state.parsed_df, use_container_width=True)
        
        target_ticker = st.text_input("公司代码 (Ticker)", value="NVDA")

        if st.button("💾 确认并同步到 Wide-Format 数据库"):
            count = 0
            # Reverse map for metric labels to IDs
            metrics_reverse_map = {m['label']: m['id'] for m in FINANCIAL_METRICS}
            
            # Group by Period (Column)
            for period_col in edited_df.columns:
                p_str = str(period_col)
                year_val = 2024
                p_val = p_str
                if "/" in p_str:
                    try:
                        parts = p_str.split("/")
                        year_val = int(parts[0])
                        p_val = parts[1]
                    except: pass
                
                # Prepare wide record dict
                record_dict = {
                    "ticker": target_ticker,
                    "year": year_val,
                    "period": p_val,
                    "category": selected_category,
                    "report_date": st.session_state.auto_disclosure_date
                }
                
                # Add metrics
                for metric_label, row in edited_df.iterrows():
                    m_id = metrics_reverse_map.get(metric_label, metric_label)
                    val = row[period_col]
                    if pd.notna(val) and str(val).strip() != "":
                        clean_val = str(val).replace("亿", "").replace("%", "").strip()
                        try: record_dict[m_id] = float(clean_val)
                        except: pass
                
                from shared.schemas.finance import FinancialRecordCreate
                record_in = FinancialRecordCreate(**record_dict)
                st.session_state.repo.create_or_update_record(record_in)
                count += 1
            
            st.success(f"已成功同步 {count} 个时间周期的 Wide-Format 数据！")
            st.rerun()
    else:
        st.info("尚未进行识别。请先上传或粘贴截图并点击“开始识别”。")

# History View (Wide Format)
st.divider()
st.header("📊 数据库已录入数据 (Wide Format)")
all_records = st.session_state.repo.get_all_records()
if all_records:
    history_data = []
    for r in all_records:
        r_dict = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        history_data.append(r_dict)
    
    hist_df = pd.DataFrame(history_data)
    core_cols = ['ticker', 'year', 'period', 'category']
    metric_cols = [c for c in hist_df.columns if c not in core_cols + ['id']]
    # Filter out all-NaN metric columns for cleaner display
    hist_df = hist_df[core_cols + metric_cols].dropna(axis=1, how='all')
    st.dataframe(hist_df, use_container_width=True)
else:
    st.info("暂无数据录入记录。")
