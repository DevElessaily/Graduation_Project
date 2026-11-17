"""Inference helper for the SMS models.

Usage:
    from ml.infer import SMSClassifier
    clf = SMSClassifier(models_dir="models")
    print(clf.predict("Purchase of EGP 100 at Carrefour on 01/01/2025"))
"""
import json
import os
import re
import unicodedata

import joblib

# Mirror of generate_sms_dataset.normalize (keep in sync for mobile porting).
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ـ": None})
_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PUNCT = str.maketrans({"٫": ".", "٬": ",", "،": ",", "\u200f": None, "\u200e": None, "\u00a0": " "})
_DIAC = re.compile(r"[\u064B-\u065F\u0670]")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DIG).translate(_PUNCT).translate(_FOLD)
    text = _DIAC.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()


class SMSClassifier:
    def __init__(self, models_dir="models"):
        self.bin_model = joblib.load(os.path.join(models_dir, "is_transaction.joblib"))
        self.cat_model = joblib.load(os.path.join(models_dir, "category.joblib"))

    def predict(self, text: str):
        n = normalize(text)
        is_tx = bool(self.bin_model.predict([n])[0])
        result = {"is_transaction": is_tx, "normalized": n}
        if is_tx:
            cat = self.cat_model.predict([n])[0]
            result["category"] = cat
            try:
                result["category_score"] = float(self.cat_model.decision_function([n]).max())
            except Exception:
                result["category_score"] = None
        else:
            result["category"] = None
        try:
            result["is_transaction_score"] = float(self.bin_model.decision_function([n])[0])
        except Exception:
            pass
        return result

    def predict_batch(self, texts):
        return [self.predict(t) for t in texts]


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?")
    ap.add_argument("--models", default="models")
    a = ap.parse_args()
    clf = SMSClassifier(models_dir=a.models)
    if a.text:
        print(json.dumps(clf.predict(a.text), ensure_ascii=False, indent=2))
    else:
        demos = [
            "Purchase of EGP 1437.02 at CAIRO SCHOOL on 23-May-2025 8:55 PM",
            "Your OTP is 123456 - do not share it with anyone",
            "تم تنفيذ تحويل لحظي من حسابكم 5124 بمبلغ 200.00 جم في 11:44 يوم 11/6/26 رقم المعاملة b2df3ead للمزيد أتصل ب 16990",
        ]
        for d in demos:
            print(d, "->", clf.predict(d))
