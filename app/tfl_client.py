import os, time, requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.tfl.gov.uk"
APP_ID = os.getenv("TFL_APP_ID", "")
APP_KEY = os.getenv("TFL_APP_KEY", "")

def _auth_params():
    return {"app_id": APP_ID, "app_key": APP_KEY} if APP_ID and APP_KEY else {}

def _get(path, params=None, retries=2, timeout=15):
    params = params or {}
    params.update(_auth_params())
    url = f"{BASE}{path}"
    for i in range(retries+1):
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        # polite backoff
        time.sleep(0.8 * (i+1))
    r.raise_for_status()

def get_bus_disruptions():
    """
    Disruptions that affect bus lines.
    Endpoint: /Line/Mode/bus/Disruption
    """
    return _get("/Line/Mode/bus/Disruption")

def get_line_arrivals(line_id: str):
    """
    Live arrivals for a given line across stops.
    Endpoint: /Line/{lineId}/Arrivals
    """
    return _get(f"/Line/{line_id}/Arrivals")

def get_line_stop_points(line_id: str):
    """
    Stop points for mapping/nearest joins.
    Endpoint: /Line/{lineId}/StopPoints
    """
    return _get(f"/Line/{line_id}/StopPoints")

def get_route_sequence(line_id: str, direction="inbound"):
    """
    Route geometry/sequence of stops.
    Endpoint: /Line/{lineId}/Route/Sequence/{direction}
    """
    return _get(f"/Line/{line_id}/Route/Sequence/{direction}", params={"serviceTypes":"Regular"})