
import os
import sys
import easyocr
import re

# Initialize Reader
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

def analyze_image(path, name):
    print(f"\n{'='*20} Analyzing {name} ({path}) {'='*20}")
    if not os.path.exists(path):
        print("File not found.")
        return

    results = reader.readtext(path)
    for i, (bbox, text, prob) in enumerate(results):
        print(f"Index {i:03}: Text='{text}' (Conf={prob:.2f})")

    return results

# Analyze headers (tempp) to see H1 and Q9/09 issues
analyze_image("tempp.png", "Quarter Headers (tempp)")

# Analyze values (tempv) to find date and 2.07 issue
analyze_image("tempv.png", "Values (tempv)")
