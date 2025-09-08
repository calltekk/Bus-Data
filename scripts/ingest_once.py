import json, os
import pandas as pd
from app import tfl_client as tfl
from app.logic import normalize_disruptions
from app.storage import upsert_df
from datetime import datetime, timezone

RAW_DIR = "app/data"

os.makedirs(RAW_DIR, exist_ok=True)

def run():
    # disruptions
    disr = tfl.get_bus_disruptions()
    with open(os.path.join(RAW_DIR, "latest_disruptions.json"), "w") as f:
        json.dump(disr, f)

    df_disr = normalize_disruptions(disr)
    df_disr["snapshot_utc"] = datetime.now(timezone.utc)
    upsert_df(df_disr, "disruptions", ["lineId","lastModified","description"])

    # optional: sample arrivals for a few lines (for offline)
    for lid in ["55","25","149","29"]:
        arr = tfl.get_line_arrivals(lid)
        with open(os.path.join(RAW_DIR, f"sample_arrivals_line{lid}.json"), "w") as f:
            json.dump(arr, f)
    print("Ingestion done.")

if __name__ == "__main__":
    run()
