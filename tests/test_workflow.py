import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application
from streamlit.testing.v1 import AppTest

from api import Reading
from src.operations import change_case, ingest, snapshot
from src.replay import replay


class WorkflowTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application([(r"/v1/readings", Reading)])

    def setUp(self):
        super().setUp()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, VFP_DATABASE=str(Path(temp.name) / "test.sqlite3"))
        env.start()
        self.addCleanup(env.stop)

    def test_http(self):
        event = dict(asset="A", observed="2026-01-01T00:00:00Z", type="L",
                     air_k=298, process_k=308, rpm=1500, torque_nm=40, wear_min=50)
        def send(item):
            return self.fetch("/v1/readings", method="POST", body=json.dumps(item)).code
        self.assertEqual(send(event), 201)
        self.assertEqual(send(event), 200)
        self.assertEqual(send(dict(event, rpm=1550)), 409)
        self.assertEqual(send(dict(event, observed="yesterday")), 400)
        self.assertEqual(send(dict(event, asset="B", rpm=99999)), 400)
        self.assertEqual(send({}), 400)
        self.assertEqual(len(snapshot()[0]), 1)
        for rpm in (1168, 2874):
            self.assertEqual(send(dict(event, asset=str(rpm), rpm=rpm)), 201)
        self.assertEqual(send(dict(event, asset="outside", rpm=3000)), 400)
        self.assertEqual(len(snapshot()[0]), 3)

    def test_new_alert_after_closure(self):
        replay()
        history, cases = snapshot()
        previous = int(cases.iloc[0].id)
        event = json.loads(history.loc[history.case_id == previous, "payload"].iloc[0])
        change_case(previous, "Open", "Acknowledged")
        change_case(previous, "Acknowledged", "Closed", "Confirmed fault")
        result = ingest(dict(event, observed="2026-02-01T00:00:00Z"))
        self.assertTrue(result["alert"])
        self.assertNotEqual(result["case_id"], previous)
        self.assertEqual(snapshot()[1].set_index("id").at[result["case_id"], "state"], "Open")

    def test_dashboard_workflow(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        history, cases = snapshot()
        self.assertEqual(len(history), 24)
        self.assertGreater(cases.alerts.max(), 1)
        app.button[0].click().run()
        self.assertEqual(len(snapshot()[0]), 24)
        app.sidebar.radio[0].set_value("Review queue").run()
        app.button[0].click().run()
        app.main.radio[0].set_value("Acknowledged").run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("Confirmed fault", snapshot()[1].outcome.tolist())
        app = AppTest.from_file("app.py", default_timeout=60).run()
        app.sidebar.radio[0].set_value("Sensor console").run()
        app.button[0].click().run()
        self.assertEqual(len(app.metric), 3)
        app.sidebar.radio[0].set_value("Model details").run()
        self.assertFalse(app.exception)

