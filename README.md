# FleetScope — Equipment Failure Prediction and Maintenance Review

A local maintenance review workspace for the AI4I equipment dataset. The dashboard and ingestion API share a SQLite database. The sample replay assigns simulated asset IDs and timestamps to 24 selected records. Its class mix and trends do not represent a real fleet.

## Windows quick start

Install Python 3.13, then run these commands in PowerShell. The repository includes the trained model.

```powershell
git clone https://github.com/BhuvaneshP63/Vehicle-Failure-Prediction.git
cd Vehicle-Failure-Prediction
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

1. Open Fleet overview and select **Run demo replay**. A fresh database shows 24 readings across three simulated assets.
2. Select an asset with an open case. In its failure-score trend, diamonds identify readings that triggered review. The dashed line shows the review threshold.
3. Select **View case**, acknowledge it, then choose **Acknowledged** in the queue. Record an inspection outcome and close the case.
4. In Sensor console, submit a reading within the displayed ranges. The last saved reading panel shows its score and UTC timestamp.

## Model performance

The shipped XGBoost model classifies individual equipment readings as Normal, Warning, or Failure. Warning labels come from speed, wear and torque rules. Vehicle performance and advance warning time remain unverified.

| Held-out AI4I evaluation | Result |
|---|---:|
| Readings within training coverage | 1,998 of 2,000 |
| Three-class accuracy on covered readings | 98.95% |
| Failure precision at the review threshold | 74.65% |
| Failure recall at the review threshold | 80.30% |
| Detected failures / missed failures / false alerts | 53 / 13 / 18 |

Run `python -m src.evaluate` with the project environment to reproduce these numbers. Review opens when the failure score meets the validation-selected threshold of 5.38%.

## API and replay

Start the loopback API in a separate terminal.

```powershell
.\.venv\Scripts\python.exe api.py
```

Run the same replay through HTTP from another terminal.

```powershell
.\.venv\Scripts\python.exe -m src.replay
```

POST JSON to /v1/readings with an asset ID and timezone-aware observation time.

```json
{"asset":"UNIT-01","observed":"2026-01-01T10:00:00Z","type":"L","air_k":298,"process_k":308,"rpm":1500,"torque_nm":40,"wear_min":50}
```

A new reading returns 201. An identical retry returns the original result with 200. Conflicting readings at the same asset and instant return 409. Invalid or unsupported readings return 400. Alerts join the current active case for the asset. A later ingestion after case closure can open another case.

## Reproduce

Use Python 3.13 and install requirements.txt in a virtual environment. Train with python src/model_training.py and run tests with python -m unittest discover -s tests -v. VFP_DATABASE overrides the local database path. Docker Compose packages the dashboard and API with a shared persistent volume. Run docker compose up --build with Docker Desktop running. Published ports 8501 and 8765 bind to localhost. This local demo has no user authentication.
