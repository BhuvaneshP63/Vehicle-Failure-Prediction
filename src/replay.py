from datetime import datetime, timedelta, timezone
from src.data_preprocessing import load_sensor_data
from src.operations import FIELDS, ingest


def replay(submit=ingest):
    sensors, labels = load_sensor_data()
    counts = {"Added": 0, "Already recorded": 0, "Outside coverage": 0}
    rows = sensors.loc[sorted(index for level in range(3) for index in labels[labels == level].index[:8])]
    for step, (_, row) in enumerate(rows.iterrows()):
        event = dict(asset=f"DEMO-{1 + step % 3:02}", type=row.iloc[0],
                     observed=(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=step)).isoformat(),
                     **dict(zip(FIELDS, map(float, row.iloc[1:]))))
        try:
            result = submit(event)
        except ValueError as exc:
            if "training coverage" not in str(exc):
                raise
            counts["Outside coverage"] += 1
        else:
            counts["Already recorded" if result["duplicate"] else "Added"] += 1
    return counts

if __name__ == "__main__":
    import json
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    def post(event):
        request = Request("http://127.0.0.1:8765/v1/readings", data=json.dumps(event).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as exc:
            raise ValueError(json.load(exc)["error"]) from exc

    print(replay(post))
