# app.py

import pytesseract
from flask import Flask, request, jsonify
from ocr_utils import extract_from_image, extract_from_text
from normalize import normalize_tokens
from classifier import classify_amounts_and_provenance
import os

# Set path to tesseract executable (Windows example)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)

# ------------------------------
# Demo route for browser testing
# ------------------------------
@app.route('/')
def demo_output():
    # Sample input text
    sample_text = "Total: INR 1200 | Paid: 1000 | Due: 200"

    # Step 1: OCR/Text extraction (text version)
    raw_tokens, currency_hint, ocr_conf = extract_from_text(sample_text)

    # Step 2: Normalize
    normalized_list, norm_conf = normalize_tokens(raw_tokens)

    # Step 3: Classify
    classification = classify_amounts_and_provenance(raw_tokens, normalized_list, sample_text)

    # Step 4: Build final JSON
    final = {
        "currency": currency_hint or "unknown",
        "amounts": [],
        "status": "ok",
        "pipeline_confidence": round((ocr_conf + norm_conf + classification.get('confidence', 0)) / 3, 3)
    }

    for a, prov in zip(classification.get('amounts', []), classification.get('provenance', [])):
        final['amounts'].append({
            "type": a['type'],
            "value": a['value'],
            "source": prov.get('source')  # context snippet
        })

    return jsonify(final)

# --------------------------------------
# API route for processing text or image
# --------------------------------------
@app.route('/api/process', methods=['POST'])
def api_process():
    """
    Full pipeline: OCR -> Normalize -> Classify
    Accepts:
    - file (image) and/or
    - JSON/form {"text": "...", "use_image": true/false}
    """
    # 1️⃣ Extract inputs safely
    body = request.get_json(silent=True) or {}
    text = body.get("text") or request.form.get("text")
    use_image = body.get("use_image") or request.form.get("use_image")
    file = request.files.get("file")

    # Normalize use_image to boolean
    if isinstance(use_image, str):
        use_image = use_image.lower() == "true"
    elif use_image is None:
        use_image = None  # Auto-detect

    raw_tokens, currency_hint, ocr_conf, provenance_text, full_text = None, None, None, None, None

    # 2️⃣ Input selection
    if use_image is True:
        if file:
            raw_tokens, currency_hint, ocr_conf, provenance_text, full_text = extract_from_image(file.stream)
        elif text:
            raw_tokens, currency_hint, ocr_conf = extract_from_text(text)
            full_text = text
        else:
            return jsonify({"error": "use_image=True but no file or text provided"}), 400

    elif use_image is False:
        if not text:
            return jsonify({"error": "use_image=False but no text provided"}), 400
        raw_tokens, currency_hint, ocr_conf = extract_from_text(text)
        full_text = text

    else:  # Auto-detect
        if file:
            raw_tokens, currency_hint, ocr_conf, provenance_text, full_text = extract_from_image(file.stream)
        elif text:
            raw_tokens, currency_hint, ocr_conf = extract_from_text(text)
            full_text = text
        else:
            return jsonify({"error": "No input provided. Send 'file' or 'text'."}), 400

    # 3️⃣ Guardrail: no amounts
    if not raw_tokens:
        return jsonify({"status": "no_amounts_found", "reason": "document too noisy or no numeric tokens detected"}), 200

    # 4️⃣ Normalize
    normalized_list, norm_conf = normalize_tokens(raw_tokens)
    if not normalized_list:
        return jsonify({"status": "no_amounts_found", "reason": "normalization failed"}), 200

    # 5️⃣ Classify
    classification = classify_amounts_and_provenance(raw_tokens, normalized_list, full_text)

    # 6️⃣ Final output
    final = {
        "currency": currency_hint or "unknown",
        "amounts": [],
        "status": "ok",
        "pipeline_confidence": round((ocr_conf + norm_conf + classification.get('confidence', 0)) / 3, 3)
    }

    for a, prov in zip(classification.get('amounts', []), classification.get('provenance', [])):
        final['amounts'].append({
            "type": a['type'],
            "value": a['value'],
            "source": prov.get('source')  # context snippet
        })

    return jsonify(final)

# ------------------------------
# Run server
# ------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
