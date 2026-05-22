import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000"

@st.cache_data(ttl=30)
def get_compliance_score() -> dict:
    """Returns {"score": float, "total_rules": int, "active_violations": int}"""
    try:
        response = requests.get(f"{BASE_URL}/api/score")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}

@st.cache_data(ttl=30)
def get_device_count() -> dict:
    """Returns {"count": int}"""
    try:
        response = requests.get(f"{BASE_URL}/api/devices/count")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}

@st.cache_data(ttl=30)
def get_rules(limit=200, skip=0) -> list | dict:
    """Paginated rules from /api/rules"""
    try:
        response = requests.get(f"{BASE_URL}/api/rules", params={"limit": limit, "skip": skip})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}

@st.cache_data(ttl=15)
def get_violations(limit=100, skip=0, status="all") -> list | dict:
    """Paginated violations from /api/violations"""
    try:
        response = requests.get(f"{BASE_URL}/api/violations", params={"limit": limit, "skip": skip, "status": status})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}

def execute_remediation(violation_id: str) -> dict:
    """POST to /api/remediate/{violation_id}. NOT cached (mutation)."""
    try:
        response = requests.post(f"{BASE_URL}/api/remediate/{violation_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if response is not None and response.status_code == 400:
            return {"status": "error", "detail": response.json().get("detail", "Bad Request")}
        return {"status": "error", "detail": str(e)}

def simulate_drift() -> dict:
    """POST to /api/simulate-drift. NOT cached (mutation)."""
    try:
        response = requests.post(f"{BASE_URL}/api/simulate-drift")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if response is not None and response.status_code == 400:
            return {"status": "error", "detail": response.json().get("detail", "Bad Request")}
        return {"status": "error", "detail": str(e)}

@st.cache_data(ttl=5)
def get_metrics() -> dict:
    """GET to /metrics and parse simple prometheus output into a dict."""
    try:
        response = requests.get(f"{BASE_URL}/metrics")
        response.raise_for_status()
        metrics = {}
        for line in response.text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(" ")
            if len(parts) >= 2:
                key = parts[0]
                try:
                    val = float(parts[1])
                    metrics[key] = val
                except ValueError:
                    pass
        return metrics
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}
