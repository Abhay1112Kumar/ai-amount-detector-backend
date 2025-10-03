from PIL import Image
import pytesseract
from pytesseract import Output
import re
import io

def extract_from_text(text):
    words = re.findall(r'\b[\w\.,%₹$€£¥-]+\b', text)
    raw_tokens = [w for w in words if re.search(r'\d', w)]
    currency_hint = None
    if re.search(r'\bINR\b|₹|Rs\b', text, flags=re.I):
        currency_hint = "INR"
    conf = 0.92
    return raw_tokens, currency_hint, conf

def extract_from_image(file_stream):
    image = Image.open(io.BytesIO(file_stream.read())).convert('RGB')
    data = pytesseract.image_to_data(image, output_type=Output.DICT, lang='eng')
    n = len(data.get('text', []))
    raw_tokens = []
    token_confs = []
    provenance = []
    lines = {}
    for i in range(n):
        txt = (data['text'][i] or '').strip()
        if not txt: continue
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        lines.setdefault(key, []).append((i, txt))
    full_text_parts = []
    for key, words in lines.items():
        line_text = ' '.join([w for i,w in words])
        full_text_parts.append(line_text)
        for idx, w in words:
            if re.search(r'\d', w):
                raw_tokens.append(w)
                try:
                    conf_val = float(data['conf'][idx])
                except:
                    conf_val = -1.0
                token_confs.append(conf_val)
                provenance.append({"token": w, "line_text": line_text, "conf": conf_val})
    full_text = "\n".join(full_text_parts)
    currency_hint = None
    if re.search(r'\bINR\b|₹|Rs\b', full_text, flags=re.I):
        currency_hint = "INR"
    valid = [c for c in token_confs if c >= 0]
    avg_conf = (sum(valid)/len(valid))/100.0 if valid else 0.5
    return raw_tokens, currency_hint, avg_conf, provenance, full_text
