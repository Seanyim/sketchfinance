import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import re

class AIEnhancerLocal:
    def __init__(self, model_id="Qwen/Qwen2.5-0.5B-Instruct"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cuda":
            torch.cuda.empty_cache()
            
        print(f"Initializing local AI on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        
        try:
            # Force float16 for CUDA to save 50% VRAM
            load_params = {
                "pretrained_model_name_or_path": model_id,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
            }
            
            # Accelerate device_map="auto" is great but sometimes OOMs if it overestimates capacity
            # We try it first; if fails, we go manual.
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    **load_params,
                    device_map="auto"
                )
            except:
                self.model = AutoModelForCausalLM.from_pretrained(**load_params)
                self.model.to(self.device)
                
        except Exception as e:
            print(f"Total failure loading model: {e}")
            raise e
            
        self.model_id = model_id

    @torch.no_grad()
    def enhance_ocr_results(self, raw_ocr_text: str, metric_config: list) -> str:
        """
        Use local LLM to clean up OCR text and map to metrics.
        Returns a JSON string of records.
        """
        metrics_desc = "\n".join([f"- {m['label']} (ID: {m['id']})" for m in metric_config])
        
        prompt = f"""你是一个专业的财务数据提取助手。
给定以下 OCR 识别出的杂乱文本，请将其整理并提取为结构化的财务数据。
只输出 JSON 格式，不要包含任何解释。

要求：
1. 识别文本中的年份和季度（如 2023/Q1, 2022/FY）。
2. 将结果对应到以下预定义的指标 ID 中：
{metrics_desc}

输出格式示例：
[
  {{"metric_id": "TotalRevenue", "period": "2023/Q1", "value": "123.45"}},
  {{"metric_id": "NetIncome", "period": "2023/Q1", "value": "50.0"}}
]

待处理 OCR 文本：
{raw_ocr_text}
"""
        messages = [
            {"role": "system", "content": "你是一个专业的财务数据助手，擅长从 OCR 文本中提取 JSON 数据。"},
            {"role": "user", "content": prompt}
        ]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        try:
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=1024,
                temperature=0.1
            )
            # Remove input tokens from result
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        finally:
            # Aggressive cleanup
            del model_inputs
            if self.device == "cuda":
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        
        # Clean up JSON from response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return "[]"
