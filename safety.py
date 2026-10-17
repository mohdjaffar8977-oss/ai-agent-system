SENSITIVE_WORDS = [
    "discount", "diskount", "chhoot", "refund", "paise wapas",
    "payment", "advance", "emi", "udhaar", "upi",
    "dawai", "dawa", "medicine", "tablet", "injection", "dose",
    "emergency", "court", "police", "vakil", "legal",
]


def is_sensitive_message(text):
    t = text.lower()
    return any(word in t for word in SENSITIVE_WORDS)
