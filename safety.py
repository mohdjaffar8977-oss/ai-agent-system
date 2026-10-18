SENSITIVE_WORDS = [
    "discount", "diskount", "chhoot", "refund", "paise wapas",
    "payment", "advance", "emi", "udhaar", "upi",
    "dawai", "dawa", "medicine", "tablet", "injection", "dose",
    "emergency", "court", "police", "vakil", "legal",
]


def is_sensitive_message(text):
    t = text.lower()
    return any(word in t for word in SENSITIVE_WORDS)


import re

PRICE_PATTERNS = [
    r"(?:\brs\.?|₹|\brupees?\b|\brupaye\b|\brupay\b)\s*([0-9][0-9,]*)",
    r"([0-9][0-9,]*)\s*(?:\brs\b|₹|\brupees?\b|\brupaye\b|\brupay\b)",
]
MEDICINE_WORDS = ["tablet", "capsule", "syrup", "injection", "dose", " mg"]


def reply_problem(reply, system_prompt):
    r = reply.lower()
    p = system_prompt.lower().replace(",", "")
    for pattern in PRICE_PATTERNS:
        for num in re.findall(pattern, r):
            if num.replace(",", "") not in p:
                return "price_not_in_prompt"
    if any(w in r for w in MEDICINE_WORDS):
        return "medicine_word"
    return None
