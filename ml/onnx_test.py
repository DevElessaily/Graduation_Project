import os
import numpy as np
import onnxruntime as ort
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_json(f"{ROOT}/data/sms_dataset.json")
tut = df[df.split == "test_unseen_template"]


def run(model_name, texts):
    sess = ort.InferenceSession(f"{ROOT}/models/{model_name}.onnx")
    inp_name = sess.get_inputs()[0].name
    arr = np.array(texts, dtype=str)
    out = sess.run(None, {inp_name: arr})
    return out, sess.get_outputs()


sample = tut.text_norm.iloc[:5].tolist()
out, outs = run("is_transaction", sample)
print("binary outputs:", [o.name for o in outs])
print("binary pred:", out[0].tolist())

sample2 = tut[tut.is_transaction].text_norm.iloc[:5].tolist()
out2, outs2 = run("category", sample2)
print("category outputs:", [o.name for o in outs2])
print("category pred:", out2[0].tolist())
print("OK")
