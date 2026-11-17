# SMS ML Models

Two scikit-learn models trained on `sms_dataset.json` (13,600 synthetic Egyptian bank SMS):

1. **is_transaction** — binary classifier (transaction vs. OTP/promo/declined/balance/etc.).
2. **category** — 16-class spending category, run only when `is_transaction == true`.

Both are `TfidfVectorizer(word 1-2 grams) + LinearSVC`, trained on normalized text (`text_norm`).

## Files

- `ml/train.py` — trains both models, evaluates, saves artifacts.
- `ml/infer.py` — Python inference helper with `normalize()`.
- `ml/onnx_test.py` — smoke test for ONNX Runtime.
- `models/is_transaction.{joblib,onnx}`, `models/category.{joblib,onnx}`.
- `reports/metrics.json`, `reports/*_report.txt`.

## Training

```bash
.venv/bin/python ml/train.py
```

## Evaluation (accuracy)

| split | is_transaction | category |
|---|---|---|
| validation | 1.000 | 0.978 |
| test_unseen_template | 0.892 | 0.855 |
| test_unseen_merchant | 1.000 | 0.560 |
| real_test | 1.000 | 1.000 |

`test_unseen_merchant` is intentionally hard: the model cannot memorize merchant names, so category accuracy drops. The dataset was designed to expose this overfitting.

## Python inference

```python
from ml.infer import SMSClassifier
clf = SMSClassifier(models_dir="models")
print(clf.predict("Purchase of EGP 100 at Carrefour on 01/01/2025"))
```

## Mobile deployment (ONNX)

1. Add `onnxruntime` (mobile build) to the app.
2. Load `models/is_transaction.onnx` and `models/category.onnx`.
3. Input: a 1-D string tensor named `text_input` (shape `[N]`).
4. Output: `label` (string/int class) and `probabilities` (float array).
5. **Normalize the raw SMS before inference** using the same steps as `normalize()` in `ml/infer.py`:
   - `unicodedata.normalize("NFKC", text)`
   - fold Arabic-Indic digits (٠-٩, ۰-۹) to ASCII
   - replace Arabic punctuation (٫→., ٬→,, ،→,) and remove bidi marks / non-breaking spaces
   - fold alef variants (أإآ→ا), ى→ي, remove tatweel (ـ)
   - strip diacritics (U+064B–U+065F, U+0670)
   - collapse whitespace, trim, lowercase
6. Cascade: run `is_transaction`; only run `category` if true.

## Notes

- Models are text-only for mobile portability; char n-grams were dropped because skl2onnx cannot convert them.
- `normalize()` must be kept in sync between training and inference (and the mobile port).
- Real SMS should be collected and added to `real_sms_test.json` to validate on actual device messages.
