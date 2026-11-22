"""Evaluate the shipped artifact on the training script's held-out split."""
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score
from sklearn.model_selection import train_test_split

from src.data_preprocessing import FEATURES, load_sensor_data
from src.operations import assets


def main():
    sensors, risk = load_sensor_data()
    _, test, _, labels = train_test_split(
        sensors, risk, stratify=risk, test_size=0.2, random_state=42)
    artifact, version = assets()
    bounds = artifact["bounds"]
    numeric = test[FEATURES[1:]]
    covered = (numeric.ge(bounds.loc["min"]) & numeric.le(bounds.loc["max"])).all(axis=1)
    samples = test.loc[covered].copy()
    samples["Type"] = artifact["encoder"].transform(samples["Type"])
    truth = labels.loc[covered]
    scores = artifact["model"].predict_proba(samples.to_numpy(dtype=float))
    alerts = scores[:, 2] >= artifact["threshold"]
    failures = truth == 2
    print(f"Model {version} | stratified 20% holdout, seed 42 | covered {len(samples)}/{len(test)}")
    print(f"Three-class accuracy {accuracy_score(truth, scores.argmax(axis=1)):.2%}")
    print("Confusion matrix (rows actual, columns predicted: Normal, Warning, Failure)")
    print(confusion_matrix(truth, scores.argmax(axis=1), labels=[0, 1, 2]))
    print(f"Review threshold {artifact['threshold']:.2%}")
    print("TN FP FN TP:", *confusion_matrix(failures, alerts, labels=[False, True]).ravel())
    print(f"Failure precision {precision_score(failures, alerts):.2%}; recall {recall_score(failures, alerts):.2%}")


if __name__ == "__main__":
    main()
