"""Turn bank / wallet SMS into structured transactions.

The messages in this project come from a small set of senders (BDC bank,
Vodafone, Vodafone Cash), so a rule-based parser is both accurate and free:
it runs offline, needs no API key and is easy to unit-test.


Examples handled
----------------
BDC (outgoing):
    تم تنفيذ تحويل لحظي من حسابكم 5124 بمبلغ 4,000.00 جم في 14:51 يوم 10/30/26
BDC (incoming):
    تم إستقبال تحويل لحظي إلى حسابكم 5124 بمبلغ 16,000.00 جم من HASSAN ... في 21:44
Vodafone Cash (incoming):
    تم استلام مبلغ 30.00 جنيه من 01027033233؛ المسجل بإسم MOAZ ... بتاريخ 10:44
Vodafone / Vodafone Cash (airtime):
    تم شحن30.0 ج و رصيدك0.0 ج. رقم العملية V7MTP...
    تم شحن رصيد موبايلك ب 30 بنجاح وخصم 30 من محفظتك ...
Generic English:
    Your card was charged EGP 250
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Arabic-Indic and Persian digits -> ASCII.
_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)

# Outgoing money movements, checked before incoming ones.
_OUTGOING_PATTERNS = (
    r"تم تنفيذ تحويل",
    r"تم شحن رصيد موبايلك",
    r"تم شحن\s*[0-9]",
    r"شحنت\s+(?:كارت|باقة|رصيد)",
    r"تم خصم",
    r"خصم مبلغ",
    r"تم دفع",
    r"دفع مبلغ",
    r"تم سداد",
    r"سداد مبلغ",
    r"تم شراء",
    r"شراء بمبلغ",
    r"\bcharged\b",
    r"\bdebited\b",
    r"\bwithdrawn\b",
    r"\bpaid\b",
    r"\bpurchase\b",
    r"\bspent\b",
)

_INCOMING_PATTERNS = (
    r"تم (?:إستقبال|استقبال) تحويل",
    r"تم استلام مبلغ",
    r"تم إيداع",
    r"تم ايداع",
    r"أضيف(?:ت)? (?:مبلغ|رصيد)",
    r"تم إضافة",
    r"\bcredited\b",
    r"\breceived\b",
    r"\bdeposited\b",
    r"\brefund(?:ed)?\b",
    r"\bsalary\b",
)

# Messages that look like transactions but are not (OTP, failed payment...).
_SKIP_PATTERNS = (
    r"\botp\b",
    r"one[ -]time password",
    r"كود التفعيل",
    r"رمز التحقق",
    r"لا تشارك",
    r"حاول ال[أا]تصال",
    r"متاح الآن يمكن الاتصال",
    r"لا يمكن إتمام العملية",
    r"لم يتم (?:خصم|تنفيذ|استلام)",
    r"\bfailed\b",
    r"\bdeclined\b",
    r"\binsufficient\b",
    r"your current .*balance is",
)

# Ordered amount patterns. The first group is the amount.
_AMOUNT_PATTERNS = (
    r"بمبلغ\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"(?:استلام|إيداع|ايداع|خصم|دفع|سداد|شراء)\s*مبلغ\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"تم شحن رصيد موبايلك ب\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"تم شحن\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"شحنت\s+(?:كارت فكة|باقة[^0-9]*|رصيد[^0-9]*)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:جنيه|جم|ج\.م|EGP|LE)\b",
    r"(?:EGP|LE)\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
)

_CATEGORY_KEYWORDS = (
    (
        "Bills",
        (
            "vodafone",
            "vf-cash",
            "etisalat",
            "orange",
            "recharge",
            "باقة",
            "فكة",
            "فاتورة",
            "كهرباء",
            "غاز",
        ),
    ),
    (
        "Food",
        (
            "restaurant",
            "cafe",
            "coffee",
            "food",
            "مطعم",
            "كافيه",
            "بازوكا",
            "دشكا",
        ),
    ),
    (
        "Transport",
        (
            "uber",
            "careem",
            "taxi",
            "fuel",
            "petrol",
            "بنزين",
            "مترو",
        ),
    ),
    (
        "Shopping",
        (
            "amazon",
            "noon",
            "shop",
            "store",
            "مول",
        ),
    ),
    (
        "Health",
        (
            "pharmacy",
            "hospital",
            "clinic",
            "صيدلية",
            "مستشفى",
        ),
    ),
    (
        "Entertainment",
        (
            "netflix",
            "cinema",
            "spotify",
            "ترفيه",
        ),
    ),
    (
        "Salary",
        (
            "salary",
            "payroll",
            "راتب",
            "مرتب",
        ),
    ),
)

_KNOWN_SENDERS = ("bdc", "vodafone", "vf-cash", "vf-store", "bank")


@dataclass(frozen=True)
class ParsedTransaction:
    """A transaction detected inside an SMS."""

    amount: Decimal
    currency: str
    db_type: str  # withdrawal / deposit
    category: str
    description: str
    merchant: str | None = None
    reference: str | None = None
    confidence: float = 0.0


def normalize(text: str) -> str:
    """Convert Arabic digits and collapse whitespace."""

    return re.sub(r"\s+", " ", text.translate(_DIGITS)).strip()


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _find_amount(text: str) -> Decimal | None:
    for pattern in _AMOUNT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(1).replace(",", "")
            try:
                amount = Decimal(raw)
            except InvalidOperation:
                continue
            if amount > 0:
                return amount
    return None


def _find_currency(text: str) -> str:
    lower = text.lower()

    if "$" in text or "usd" in lower or "دولار" in text:
        return "USD"
    if "ريال" in text or re.search(r"\bsar\b", lower):
        return "SAR"
    if "درهم" in text or re.search(r"\baed\b", lower):
        return "AED"
    if "€" in text or re.search(r"\beur\b", lower):
        return "EUR"

    return "EGP"


def _clean_name(value: str) -> str | None:
    name = re.sub(r"\s+", " ", value).strip(" .،,;-")
    return name or None


def _find_merchant(sender: str, text: str) -> str | None:
    # BDC incoming: "... بمبلغ 16,000.00 جم من HASSAN ALAAELDEEN في 21:44 ..."
    match = re.search(r"من\s+(.+?)\s+في\s+\d{1,2}:\d{2}", text)
    if match:
        return _clean_name(match.group(1))

    # Vodafone Cash incoming: "... من 010...؛ المسجل بإسم MOAZ ... على رقم ..."
    match = re.search(r"المسجل بإسم\s+(.+?)\s+على رقم", text)
    if match:
        return _clean_name(match.group(1))

    # Wallet / bank transfer from a phone number.
    match = re.search(r"من\s+(\+?\d{6,15})", text)
    if match:
        return match.group(1)

    lower = sender.lower()
    if "vodafone" in lower or "vf-cash" in lower:
        return "Vodafone"

    return None


def _find_reference(text: str) -> str | None:
    match = re.search(
        r"(?:رقم المعاملة|رقم العملية|Trx ID)\s*:?\s*([A-Za-z0-9]+)",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _category(sender: str, text: str, outgoing: bool) -> str:
    lower = text.lower()

    if "bdc" in sender.lower():
        return "Transfer"

    if (
        "كارت فكة" in text
        or "رصيد موبايلك" in text
        or re.search(r"تم شحن\s*[0-9]", text)
    ):
        return "Bills"

    if not outgoing and ("تحويل" in text or "استلام مبلغ" in text):
        return "Transfer"

    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in lower for keyword in keywords):
            return category

    return "Other"


def _description(
    sender: str,
    outgoing: bool,
    merchant: str | None,
    category: str,
) -> str:
    if category == "Bills":
        return "Mobile recharge"

    if outgoing:
        if merchant and "bdc" not in sender.lower():
            return f"Transfer to {merchant}"
        if "bdc" in sender.lower():
            return "Bank transfer"
        return "Payment"

    if merchant:
        return f"Transfer from {merchant}"
    return "Incoming transfer"


def parse_transaction_sms(sender: str, message: str) -> ParsedTransaction | None:
    """Return the transaction described by an SMS, or ``None``.

    ``None`` means the message is not a completed money movement: marketing,
    OTPs, balance notifications, missed calls and failed payments all end up
    here, so they are never turned into transactions.
    """

    text = normalize(message)

    if not text or _matches(_SKIP_PATTERNS, text):
        return None

    outgoing = _matches(_OUTGOING_PATTERNS, text)
    incoming = _matches(_INCOMING_PATTERNS, text)

    if not outgoing and not incoming:
        return None

    # "تم شحن رصيد موبايلك ... وخصم" is a purchase, not a deposit.
    if outgoing and incoming:
        incoming = False

    amount = _find_amount(text)
    if amount is None:
        return None

    currency = _find_currency(text)
    merchant = _find_merchant(sender, text)
    category = _category(sender, text, outgoing)

    # ML override: use the trained model's fine-grained category when available.
    try:
        from app.services.ml_classifier import get_classifier
        ml = get_classifier()
        ml_cat = ml.category(message)
        if ml_cat is not None:
            category = ml_cat[0]
    except Exception:
        pass

    reference = _find_reference(text)

    known = any(name in sender.lower() for name in _KNOWN_SENDERS)

    return ParsedTransaction(
        amount=amount,
        currency=currency,
        db_type="withdrawal" if outgoing else "deposit",
        category=category,
        description=_description(sender, outgoing, merchant, category)[:255],
        merchant=merchant[:255] if merchant else None,
        reference=reference[:100] if reference else None,
        confidence=0.9 if known else 0.55,
    )