import os, time, requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.tfl.gov.uk"
APP_KEY = os.getenv("TFL_APP_KEY", "")

def _auth_params():
    return {"app_key": APP_KEY} if APP_KEY else {}

def _get(path, params=None, retries=2, timeout=15):
    params = params or {}
    params.update(_auth_params())
    url = f"{BASE}{path}"
    for i in range(retries+1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except requests.exceptions.RequestException:
            time.sleep(0.8 * (i+1))
    return []

def get_bus_disruptions():
    return _get("/Line/Mode/bus/Disruption")

def get_line_arrivals(line_id: str):
    return _get(f"/Line/{line_id}/Arrivals")

def get_line_stop_points(line_id: str):
    return _get(f"/Line/{line_id}/StopPoints")

def get_route_sequence(line_id: str, direction="inbound"):
    return _get(f"/Line/{line_id}/Route/Sequence/{direction}", params={"serviceTypes":"Regular"})
