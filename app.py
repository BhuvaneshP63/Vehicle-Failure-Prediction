import json
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st

from src.data_preprocessing import FEATURES
from src.operations import FIELDS, MODEL, assets, change_case, ingest, snapshot
from src.replay import replay
from src.interface import heading

st.set_page_config(page_title="FleetScope | Maintenance", page_icon=":material/monitor_heart:", layout="wide")
st.sidebar.markdown("## :material/precision_manufacturing: FleetScope")
page = st.sidebar.radio("Workspace", ["Fleet overview", "Sensor console", "Review queue", "Model details"], key="workspace")
st.sidebar.divider()
st.sidebar.caption("AI4I equipment maintenance demo")
if not MODEL.exists():
    st.error("Train the model with python src/model_training.py")
    st.stop()

artifact, version = assets()


def visit_case(case_id):
    st.session_state.workspace = "Review queue"
    st.session_state.target_case = int(case_id)


def result_panel(result, asset_id):
    st.subheader(f"{asset_id} · {result['label']}")
    failure = result["probabilities"]["Failure"]
    cutoff = result["threshold"]
    if result["alert"]:
        st.warning(f"Case #{result['case_id']} · Failure score {failure:.2%} meets the review threshold of {cutoff:.2%}.")
    else:
        st.info(f"Failure score {failure:.2%} is below the review threshold of {cutoff:.2%}.")
    cols = st.columns(3)
    for col, (name, value) in zip(cols, result["probabilities"].items()):
        col.metric(name, f"{value:.1%}", border=True)
    with st.expander("Explore sensor contributions"):
        show_contributions(result)


def show_contributions(result):
    impact = pd.Series(result["impacts"]).mul(100).sort_values()
    st.bar_chart(impact.rename("Percentage points"), horizontal=True, color="#158778")
    st.caption(f"Change from the reference score of {result['baseline']:.1%} for the predicted class. "
               f"Model {result['version']}.")


if page == "Sensor console":
    heading("Sensor console", "Score a reading and record it in the asset history.")
    entry, saved = st.columns([3, 2])
    with entry.form("reading"):
        st.subheader("Equipment", anchor=False)
        a, b = st.columns(2)
        asset = a.text_input("Asset ID", "UNIT-01")
        kind = b.selectbox("Equipment type", ["L", "M", "H"])
        st.divider()
        st.subheader("Sensor readings", anchor=False)
        thermal, mechanical = st.tabs(["Temperature", "Speed, torque & wear"])
        temperatures = thermal.columns(2)
        mechanical = mechanical.columns(3)
        values = []
        for col, name, default, step in zip(
            [*temperatures, *mechanical], FEATURES[1:],
            [298., 308., 1500., 40., 50.], [.1, .1, 1., .1, 1.]
        ):
            low, high = artifact["bounds"][name].loc[["min", "max"]]
            values.append(col.number_input(
                f"{name} · {low:g}–{high:g}", min_value=float(low), max_value=float(high),
                value=default, step=step, format="%.0f" if step == 1 else "%.1f"
            ))
        submit = st.form_submit_button("Record and score", type="primary", icon=":material/monitor_heart:", width="stretch")
    if submit:
        try:
            observed = datetime.now(timezone.utc).isoformat()
            st.session_state.last = ingest(dict(asset=asset, type=kind, observed=observed,
                                                **dict(zip(FIELDS, values))))
            st.session_state.last_asset = asset
            st.session_state.last_observed = observed
        except ValueError as exc:
            entry.error(str(exc))
    with saved.container(border=True):
        st.subheader("Last saved reading", anchor=False)
        if "last" in st.session_state:
            last = st.session_state.last
            if "last_observed" in st.session_state:
                st.caption(pd.Timestamp(st.session_state.last_observed).strftime("%d %b %Y, %H:%M:%S UTC"))
            result_panel(last, st.session_state.last_asset)
            if last["case_id"]:
                st.button(f"View case #{last['case_id']}", on_click=visit_case, args=(last["case_id"],))
        else:
            st.caption("Record a reading to see its score and review decision here.")

elif page == "Model details":
    heading("Model details", "Inspect training coverage and the threshold used for maintenance review.")
    threshold, identity = st.columns(2)
    threshold.metric("Review threshold", f"{artifact['threshold']:.2%}", border=True)
    identity.metric("Scoring model", "XGBoost", border=True)
    st.subheader("Supported sensor ranges", anchor=False)
    st.dataframe(artifact["bounds"].T.rename(columns={"min":"Minimum", "max":"Maximum"}), width="stretch")
    st.caption(f"Model fingerprint · {version}")
    st.write("XGBoost scores individual AI4I machine readings using the six inputs plus temperature rise, "
             "shaft power and a wear–torque interaction. The warning class uses wear, torque and speed rules. "
             "Vehicle fault lead time requires separate field validation.")

elif page == "Fleet overview":
    heading("Fleet overview", "Inspect recorded equipment telemetry and follow readings into maintenance review.")
    history, cases = snapshot()
    with st.expander("Replay sample telemetry", expanded=history.empty):
        st.caption("24 selected dataset readings across three simulated assets. IDs and times are simulated. "
                   "Replaying the same batch preserves existing records.")
        if st.button("Run demo replay", type="primary"):
            summary = replay()
            history, cases = snapshot()
            st.success(" · ".join(f"{key}: {value}" for key, value in summary.items()))
    cols = st.columns(3)
    for col, title, number in zip(cols, ["Monitored assets", "Recorded readings", "Active cases"],
                                 [history.asset.nunique(), len(history), (cases.state != "Closed").sum()]):
        col.metric(title, number, border=True)
    if history.empty:
        st.info("Run the sample replay or record your first reading in Sensor console.")
    else:
        active = cases[cases.state != "Closed"].set_index("asset")
        status_rows = []
        for row in history.drop_duplicates("asset").itertuples():
            result = json.loads(row.result)
            state = active.at[row.asset, "state"] if row.asset in active.index else "No active case"
            status_rows.append({"Asset": row.asset, "Latest reading (UTC)": pd.Timestamp(row.observed),
                                "Class": result["label"], "Failure score (%)": result["probabilities"]["Failure"] * 100,
                                "Case status": state})
        status = pd.DataFrame(status_rows).sort_values(
            ["Case status", "Failure score (%)"], ascending=[True, False],
            key=lambda col: col.map({"Open": 0, "Acknowledged": 1, "No active case": 2})
            if col.name == "Case status" else col).reset_index(drop=True)
        st.subheader("Asset status", anchor=False)
        st.caption("Select a row to inspect its readings. Open cases appear first.")
        selection = st.dataframe(status, hide_index=True, width="stretch", on_select="rerun",
                                 selection_mode="single-row", column_config={
                                     "Failure score (%)": st.column_config.NumberColumn(format="%.2f")})
        rows = selection.selection.rows
        asset = status.iloc[rows[0] if rows and rows[0] < len(status) else 0]["Asset"]
        st.subheader(f"{asset} telemetry", anchor=False)
        if asset in active.index:
            case_id = int(active.at[asset, "id"])
            st.button(f"View case #{case_id}", on_click=visit_case, args=(case_id,))
        history = history[history.asset == asset]
        records = []
        for row in history.itertuples():
            payload, result = json.loads(row.payload), json.loads(row.result)
            records.append({"Observed (UTC)": pd.Timestamp(row.observed), "Class": result["label"],
                            "Failure score (%)": round(100 * result["probabilities"]["Failure"], 3),
                            "Threshold (%)": 100 * result["threshold"], "Review triggered": result["alert"],
                            **{key: payload[key] for key in FIELDS}, "Model": result["version"]})
        table = pd.DataFrame(records).set_index("Observed (UTC)")
        table = table.rename(columns=dict(zip(FIELDS, FEATURES[1:])))
        series = st.selectbox("Measurement", ["Failure score (%)", *FEATURES[1:]])
        chart, readings = st.tabs(["Trend", "Reading history"])
        base = alt.Chart(table.sort_index().reset_index()).encode(
            x=alt.X("Observed (UTC):T", scale=alt.Scale(type="utc")),
            y=alt.Y(series, type="quantitative"), tooltip=["Observed (UTC):T", series, "Class"])
        plot = base.mark_line(point=True, color="#087F71")
        if series == "Failure score (%)":
            threshold = base.mark_line(point=True, strokeDash=[6, 4], color="#805322",
                                       interpolate="step-after").encode(y="Threshold (%):Q")
            flagged = base.transform_filter(alt.datum["Review triggered"]).mark_point(
                filled=True, size=95, color="#b04423", shape="diamond")
            plot = plot + threshold + flagged
            chart.caption("Dashed line: review threshold · Orange diamond: reading triggered review")
        chart.altair_chart(plot.properties(height=280), width="stretch")
        chart.caption(f"{len(table)} readings · Latest observation {table.index.max():%d %b %Y, %H:%M UTC}")
        readings.dataframe(table, width="stretch")
        readings.download_button("Export asset history", table.to_csv(), f"{asset}-history.csv", "text/csv")

else:
    heading("Maintenance review queue", "Review flagged readings and record inspection outcomes.")
    history, cases = snapshot()
    target = st.session_state.pop("target_case", None)
    if target in cases.id.values:
        st.session_state.case_status = cases.set_index("id").at[target, "state"]
        st.session_state.case_choice = target
    state = st.radio("Case status", ["Open", "Acknowledged", "Closed"], horizontal=True, key="case_status",
                     format_func=lambda status: f"{status} ({int((cases.state == status).sum())})")
    selected = cases[cases.state == state]
    if selected.empty:
        st.info(f"No {state.lower()} cases.")
    else:
        row_id = st.selectbox("Case", selected.id.tolist(), key="case_choice", format_func=lambda i:
            f"#{i} · {selected.loc[selected.id == i, 'asset'].iloc[0]}")
        case = selected[selected.id == row_id].iloc[0]
        st.write(f"{case.asset} · {case.alerts} flagged reading(s)")
        latest = history[history.case_id == row_id].iloc[0]
        st.caption(f"Latest flagged reading · {latest.observed}")
        result_panel(dict(case_id=row_id, **json.loads(latest.result)), case.asset)
        if state == "Closed":
            st.success(f"Inspection outcome · {case.outcome}")
        else:
            outcome = st.selectbox("Inspection outcome", ["Confirmed fault", "False alarm", "Inconclusive"]) if state == "Acknowledged" else None
            next_state = "Closed" if outcome else "Acknowledged"
            if st.button("Close case" if outcome else "Acknowledge case", type="primary"):
                try:
                    change_case(int(row_id), state, next_state, outcome)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
