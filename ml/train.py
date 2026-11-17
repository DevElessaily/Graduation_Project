"""Train and export the SMS models (binary is_transaction + category).

Text-only, TF-IDF (word n-grams) + Logistic Regression, trained on normalized text.
Exports joblib + ONNX for mobile deployment.
"""
import json
import os

import numpy as np
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, classification_report
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "sms_dataset.json")
MODEL_DIR = os.path.join(ROOT, "models")
REPORT_DIR = os.path.join(ROOT, "reports")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

df = pd.read_json(DATA)
train = df[df.split == "train"]
val = df[df.split == "validation"]
tut = df[df.split == "test_unseen_template"]
tum = df[df.split == "test_unseen_merchant"]
real_path = os.path.join(ROOT, "data", "real_sms_test.json")
real = pd.read_json(real_path) if os.path.exists(real_path) else pd.DataFrame()

tr_tx = train[train.is_transaction]
va_tx = val[val.is_transaction]
tut_tx = tut[tut.is_transaction]
tum_tx = tum[tum.is_transaction]


def make_vectorizer():
    return TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        max_features=40000,
        sublinear_tf=True,
    )


def train_model(X_train, y_train):
    pipe = Pipeline([
        ("tfidf", make_vectorizer()),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            C=1.0,
            solver="lbfgs",
            n_jobs=-1,
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def eval_model(pipe, X, y):
    pred = pipe.predict(X)
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "f1_macro": float(f1_score(y, pred, average="macro")),
        "f1_weighted": float(f1_score(y, pred, average="weighted")),
    }


# --- Binary model (all rows) ---
bin_model = train_model(train.text_norm, train.is_transaction.astype(int))

# --- Category model (transactions only) ---
cat_model = train_model(tr_tx.text_norm, tr_tx.category)

# --- Evaluation ---
metrics = {"binary": {}, "category": {}, "cascade": {}}

for name, d, y in [
    ("validation", val, val.is_transaction.astype(int)),
    ("test_unseen_template", tut, tut.is_transaction.astype(int)),
    ("test_unseen_merchant", tum, tum.is_transaction.astype(int)),
    ("real_test", real, real.is_transaction.astype(int) if len(real) else []),
]:
    if len(y) == 0:
        continue
    metrics["binary"][name] = eval_model(bin_model, d.text_norm, y)

for name, d, y in [
    ("validation", va_tx, va_tx.category),
    ("test_unseen_template", tut_tx, tut_tx.category),
    ("test_unseen_merchant", tum_tx, tum_tx.category),
]:
    metrics["category"][name] = eval_model(cat_model, d.text_norm, y)

if len(real) > 0:
    real_tx = real[real.is_transaction]
    metrics["category"]["real_test"] = eval_model(cat_model, real_tx.text_norm, real_tx.category)


def cascade_eval(split_df):
    is_tx_pred = bin_model.predict(split_df.text_norm)
    cat_pred = [None] * len(split_df)
    mask = is_tx_pred == 1
    if mask.any():
        preds = cat_model.predict(split_df.loc[mask, "text_norm"])
        idx = 0
        for i in range(len(split_df)):
            if mask[i]:
                cat_pred[i] = preds[idx]
                idx += 1
    correct = total = 0
    for i, (_, r) in enumerate(split_df.iterrows()):
        if r.is_transaction:
            total += 1
            if is_tx_pred[i] == 1 and cat_pred[i] == r.category:
                correct += 1
    return {
        "category_cascade_acc_on_actual_tx": (correct / total if total else 0.0),
        "n_actual_tx": int(total),
    }


for name, d in [
    ("validation", val),
    ("test_unseen_template", tut),
    ("test_unseen_merchant", tum),
    ("real_test", real),
]:
    if len(d) > 0:
        metrics["cascade"][name] = cascade_eval(d)

# --- Save joblib ---
joblib.dump(bin_model, os.path.join(MODEL_DIR, "is_transaction.joblib"))
joblib.dump(cat_model, os.path.join(MODEL_DIR, "category.joblib"))

# --- ONNX export ---
initial_type = [("text_input", StringTensorType([None]))]

for name, model in [("is_transaction", bin_model), ("category", cat_model)]:
    onx = convert_sklearn(model, initial_types=initial_type, target_opset=12)
    with open(os.path.join(MODEL_DIR, name + ".onnx"), "wb") as f:
        f.write(onx.SerializeToString())

# --- Reports ---
pred_tut = cat_model.predict(tut_tx.text_norm)
with open(os.path.join(REPORT_DIR, "category_unseen_template_report.txt"), "w") as f:
    f.write(classification_report(tut_tx.category, pred_tut, digits=3))

pred_bin_tut = bin_model.predict(tut.text_norm)
with open(os.path.join(REPORT_DIR, "binary_unseen_template_report.txt"), "w") as f:
    f.write(classification_report(tut.is_transaction.astype(int), pred_bin_tut, digits=3))

with open(os.path.join(REPORT_DIR, "metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)

print(json.dumps(metrics, indent=2, ensure_ascii=False))
print("\nModels saved to", MODEL_DIR)
