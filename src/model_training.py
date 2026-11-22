import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import joblib
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, LabelEncoder
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_preprocessing import ROOT, FEATURES, load_sensor_data
from src.operating_features import operating_features


def train_and_evaluate_models():
    sensors, risk = load_sensor_data()
    development, test, labels, test_labels = train_test_split(
        sensors, risk, stratify=risk, test_size=0.2, random_state=42)
    train, validation, train_labels, validation_labels = train_test_split(
        development, labels, stratify=labels, test_size=0.25, random_state=42)
    encoder = LabelEncoder().fit(train["Type"])

    def encode(frame):
        return frame.assign(Type=encoder.transform(frame["Type"])).to_numpy(dtype=float)

    model = make_pipeline(FunctionTransformer(operating_features),
                          XGBClassifier(eval_metric="mlogloss", random_state=42, n_jobs=2))
    model.fit(encode(train), train_labels)
    scores = model.predict_proba(encode(validation))[:, 2]
    precision, recall, thresholds = precision_recall_curve(validation_labels == 2, scores)
    # F2 weights recall more heavily for the maintenance review queue.
    f2 = 5 * precision[:-1] * recall[:-1] / np.maximum(4 * precision[:-1] + recall[:-1], 1e-12)
    threshold = float(thresholds[np.argmax(f2)])
    test_scores = model.predict_proba(encode(test))
    print(classification_report(test_labels, test_scores.argmax(axis=1), digits=3))
    for name, alerts in [("Class decision", test_scores.argmax(axis=1) == 2),
                         ("Review threshold", test_scores[:, 2] >= threshold)]:
        print(name, "TN FP FN TP", confusion_matrix(test_labels == 2, alerts).ravel())
    print("Review threshold", threshold)
    assets = dict(model=model, encoder=encoder, features=FEATURES, reference=encode(train)[0],
                  bounds=train[FEATURES[1:]].agg(["min", "max"]), threshold=threshold)
    folder = ROOT / "models"
    folder.mkdir(exist_ok=True)
    with NamedTemporaryFile(dir=folder, delete=False) as temp:
        joblib.dump(assets, temp, compress=3)
    os.replace(temp.name, folder / "predictor.joblib")


if __name__ == "__main__":
    train_and_evaluate_models()
