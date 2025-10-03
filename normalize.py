# normalize.py
import re
import statistics

# Map of common OCR-confusions -> digit likely intended
CHAR_MAP = {
    'O':'0','o':'0','Q':'0',
    'l':'1','I':'1','i':'1','|':'1',
    'S':'5','s':'5',
    'B':'8','b':'6',  # be careful but helpful
    ',': '',  # thousand separators
    ' ': '',
    '\u2014':'-', '\u2013':'-'
}

def _apply_char_map(token):
    res = []
    replacements = 0
    for ch in token:
        if ch in CHAR_MAP:
            res.append(CHAR_MAP[ch])
            replacements += 1
        else:
            res.append(ch)
    return ''.join(res), replacements

def normalize_single(token):
    """
    Attempts to clean token -> numeric value (int or float).
    Returns (value or None, confidence 0..1)
    """
    orig = token
    # remove common currency symbols
    token = re.sub(r'[₹$€£,]', '', token)
    token = token.strip()
    # If token contains percent, treat specially (we won't include percent in numeric amounts list)
    if '%' in token:
        return None, 0.6  # we detect percent but don't return numeric amount (design choice)
    mapped, replacements = _apply_char_map(token)
    # Remove any stray non-digit/period/minus
    cleaned = re.sub(r'[^\d\.\-]', '', mapped)
    if cleaned == '':
        return None, 0.0
    try:
        if '.' in cleaned:
            val = float(cleaned)
        else:
            val = int(cleaned)
        # confidence drops with more heuristic replacements
        conf = max(0.25, 1.0 - (replacements * 0.06))
        return val, conf
    except Exception:
        return None, 0.0

def normalize_tokens(raw_tokens):
    """
    Input: list of token strings
    Output:
      normalized_list: list of numeric values (preserving order),
      normalization_confidence: average confidence
    We drop tokens that are percent strings or fail to parse.
    Also returns list of tuples (value, original_token, conf) for internal use.
    """
    results = []
    confs = []
    final_values = []
    for tok in raw_tokens:
        v, c = normalize_single(tok)
        if v is not None:
            results.append({"orig":tok, "value":v, "conf":c})
            final_values.append(v)
            confs.append(c)
    norm_conf = (sum(confs)/len(confs)) if confs else 0.0
    # return list of [values] (keeps order) and norm_conf
    return final_values, norm_conf
