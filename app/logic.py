import pandas as pd
import numpy as np

def normalize_disruptions(raw: list) -> pd.DataFrame:
    if not raw: 
        return pd.DataFrame()
    rows = []
    for item in raw:
        severity = item.get("severity") or "Undefined"
        start = item.get("startTime")
        end = item.get("endTime")
        desc = item.get("description") or ""
        last = item.get("lastModified")
        lines = item.get("lines") or []
        if not lines:
            rows.append({
                "lineId": None,
                "severity": severity,
                "startTime": start, "endTime": end, "lastModified": last,
                "description": desc
            })
        else:
            for ln in lines:
                rows.append({
                    "lineId": ln.get("id"),
                    "severity": severity,
                    "startTime": start, "endTime": end, "lastModified": last,
                    "description": desc
                })
    df = pd.DataFrame(rows)
    for c in ["startTime","endTime","lastModified"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    return df

def estimate_headway_minutes(arrivals_json: list, min_hw=3, max_hw=20) -> float:
    if not arrivals_json:
        return 8.0
    df = pd.DataFrame(arrivals_json)
    if "timeToStation" not in df.columns or "naptanId" not in df.columns:
        return 8.0
    df["eta_min"] = df["timeToStation"] / 60.0
    gaps = []
    for stop_id, g in df.groupby("naptanId"):
        etas = sorted(g["eta_min"].tolist())
        if len(etas) < 2: 
            continue
        d = np.diff(etas)
        d = [x for x in d if 0.5 <= x <= (max_hw*1.5)]
        gaps.extend(d)
    if not gaps:
        return 8.0
    hw = float(np.median(gaps))
    hw = max(min_hw, min(max_hw, hw))
    return hw

def severity_delay_minutes(severity: str, severity_map: dict) -> float:
    return float(severity_map.get(severity, severity_map.get("Undefined", 5)))

def disruption_cost_per_hour(delay_per_bus_min: float, headway_min: float, cost_per_bus_min: float) -> float:
    if headway_min <= 0: headway_min = 8.0
    buses_per_hour = 60.0 / headway_min
    delay_minutes_per_hour = delay_per_bus_min * buses_per_hour
    return delay_minutes_per_hour * cost_per_bus_min

def aggregate_costs(disruptions_df: pd.DataFrame, line_id_to_headway: dict, severity_map: dict, cost_per_min: float):
    if disruptions_df.empty:
        return pd.DataFrame(columns=["lineId","severity","delay_min_per_bus","headway_min","cost_per_hour_gbp","incidents"])
    disruptions_df = disruptions_df.dropna(subset=["lineId"])
    g = disruptions_df.groupby(["lineId","severity"]).agg(
        incidents=("lineId","count"),
        last_seen=("lastModified","max")
    ).reset_index()
    out_rows = []
    for _, row in g.iterrows():
        lid = row["lineId"]
        sev = row["severity"]
        hw = float(line_id_to_headway.get(lid, 8.0))
        delay = severity_delay_minutes(sev, severity_map)
        cost_h = disruption_cost_per_hour(delay, hw, cost_per_min)
        out_rows.append({
            "lineId": lid,
            "severity": sev,
            "delay_min_per_bus": round(delay,2),
            "headway_min": round(hw,2),
            "incidents": int(row["incidents"]),
            "cost_per_hour_gbp": round(cost_h, 2),
            "last_seen": row["last_seen"]
        })
    return pd.DataFrame(out_rows).sort_values(["cost_per_hour_gbp"], ascending=False)
