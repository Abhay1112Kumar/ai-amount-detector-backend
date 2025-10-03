import re

KEYWORDS = {
    "total_bill": ["total", "grand total", "net total", "amount payable", "bill amount"],
    "paid": ["paid", "received", "amount paid", "settled", "cash received"],
    "due": ["due", "balance", "amount due", "outstanding"],
    "discount": ["discount", "%", "off"]
}

def _find_context_snippet(full_text, raw_token, window=12):
    if not full_text:
        return raw_token
    idx = full_text.find(raw_token)
    if idx == -1:
        digits = re.sub(r"[^\d]", "", raw_token)
        idx = full_text.find(digits) if digits else 0
    start = max(0, idx - window)
    end = min(len(full_text), idx + len(raw_token) + window)
    return full_text[start:end].strip()

def classify_amounts_and_provenance(raw_tokens, normalized_vals, full_text):
    if not normalized_vals:
        return {"amounts": [], "confidence": 0.0, "provenance": []}

    classified = []
    provenance = []

    for rt, val in zip(raw_tokens, normalized_vals):
        snippet = _find_context_snippet(full_text, rt)
        snippet_lower = snippet.lower()
        assigned_type = "unknown"
        conf = 0.6

        for label, kws in KEYWORDS.items():
            for kw in kws:
                if kw in snippet_lower:
                    assigned_type = label
                    conf = 0.9
                    break
            if assigned_type != "unknown":
                break

        if '%' in rt:
            assigned_type = "discount"
            val = float(re.sub(r'[^\d.]', '', rt))
            conf = 0.9

        if assigned_type == "unknown":
            if val == max(normalized_vals):
                assigned_type = "total_bill"
                conf = 0.85
            elif val == min(normalized_vals):
                assigned_type = "discount"
                conf = 0.75
            else:
                assigned_type = "due"
                conf = 0.7

        classified.append({
            "type": assigned_type,
            "value": val,
            "context_snippet": f"text: '{snippet}'",
            "confidence": conf
        })
        provenance.append({
            "token": rt,
            "value": val,
            "source": f"text: '{snippet}'"
        })

    overall_conf = sum(c['confidence'] for c in classified) / len(classified)

    return {
        "amounts": [{"type": c['type'], "value": c['value']} for c in classified],
        "confidence": round(overall_conf, 3),
        "provenance": provenance
    }
