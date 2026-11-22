from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["Type", "Air temperature [K]", "Process temperature [K]",
            "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]


def load_sensor_data(csv_path=ROOT / "dataset.csv"):
    path = Path(csv_path)
    if not path.exists():
        from ucimlrepo import fetch_ucirepo
        fetch_ucirepo(id=601).data.original.to_csv(path, index=False)
    data = pd.read_csv(path)
    aliases = {name.split(" [")[0]: name for name in FEATURES if name not in data}
    data = data.rename(columns=aliases)
    sensors = data[FEATURES].copy()
    warning = ((sensors["Tool wear [min]"] > 200) | (sensors["Torque [Nm]"] > 60)
               | ~sensors["Rotational speed [rpm]"].between(1300, 2000))
    risk = warning.astype(int).mask(data["Machine failure"].eq(1), 2)
    return sensors, risk
