import requests
import json
from typing import List, Dict

class AIEnhancerService:
    def __init__(self, ollama_url="http://localhost:11434", model="llama3"):
        self.ollama_url = f"{ollama_url}/api/generate"
        self.model = model

    def enhance_data(self, raw_ocr_text: str, metric_config: List[Dict]) -> str:
        """
        Send raw OCR text to local Ollama to structure it.
        Now includes metric config for context.
        """
        metrics_list = ", ".join([m['label'] for m in metric_config])
        prompt = f"""
        Task: Extract financial data from OCR text.
        Allowed Metrics: {metrics_list}
        Output Format: JSON list of objects: [{{"metric_id": "id", "period": "YYYY/QX", "value": "num"}}]
        
        Raw OCR Text:
        {raw_ocr_text}
        
        Important: Match the metric labels exactly to the metric_id provided in config.
        """
        
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=10
            )
            if response.status_code == 200:
                result = response.json().get('response', "")
                # Basic JSON extraction if AI wraps it in backticks
                if "```json" in result:
                    result = result.split("```json")[-1].split("```")[0]
                return result
        except Exception as e:
            return f"AI Enhancement Error: {str(e)}"
        
        return ""

    def validate_row(self, category: str, value: str) -> bool:
        """
        Basic heuristic validation for financial data.
        """
        # Example: check if value contains numerical digits or units
        has_digit = any(char.isdigit() for char in value)
        is_financial = any(unit in value for unit in ["亿", "%", ".", ","])
        return has_digit or is_financial
