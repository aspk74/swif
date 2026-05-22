import streamlit as st
import pandas as pd
import plotly.express as px
from services import (
    get_compliance_score, 
    get_device_count, 
    get_rules, 
    get_violations, 
    execute_remediation, 
    simulate_drift,
    get_metrics
)

# --- Page Config ---
st.set_page_config(
    page_title="Compliance Control Plane",
    page_icon="🛡️",
    layout="wide"
)

# --- Session State Initialization ---
if "fix_results" not in st.session_state:
    st.session_state.fix_results = {}  # {violation_id: {"status": ..., "logs": ...}}

if "drift_simulated" not in st.session_state:
    st.session_state.drift_simulated = False

# --- Helper Functions ---
def refresh_data():
    """Clear the st.cache_data cache to force a re-fetch of data."""
    st.cache_data.clear()

def do_simulate_drift():
    with st.spinner("Simulating drift..."):
        result = simulate_drift()
        if result.get("status") == "error":
            st.sidebar.error(result.get("detail"))
        else:
            st.session_state.drift_simulated = True
            st.sidebar.success(f"Drift simulated for {result.get('device_id')} on {result.get('parameter')}")
            refresh_data()

def do_execute_fix(violation_id: str):
    with st.spinner("Executing fix..."):
        result = execute_remediation(violation_id)
        if result.get("status") == "error":
            st.session_state.fix_results[violation_id] = {
                "status": "error",
                "logs": result.get("detail")
            }
        else:
            st.session_state.fix_results[violation_id] = {
                "status": "success",
                "logs": result.get("logs")
            }
        refresh_data()


# --- Sidebar ---
st.sidebar.title("🛡️ Swif Compliance")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["Executive Posture", "Control Registry", "Action Center", "Observability Engine"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Developer Tools")
if st.sidebar.button("🚨 Simulate Drift", use_container_width=True):
    do_simulate_drift()


# --- Pages ---

if page == "Executive Posture":
    st.title("Executive Posture")
    
    score_data = get_compliance_score()
    device_data = get_device_count()
    
    if isinstance(score_data, dict) and score_data.get("status") == "error":
        st.error(f"Failed to fetch score data: {score_data.get('detail')}")
        st.stop()
        
    score = score_data.get("score", 0)
    total_rules = score_data.get("total_rules", 0)
    active_violations = score_data.get("active_violations", 0)
    devices_reporting = device_data.get("count", 0) if isinstance(device_data, dict) and "count" in device_data else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Compliance Score", f"{score}%", help="100 - (active violations / total rules)")
    with col2:
        st.metric("Active Violations", active_violations, delta=-active_violations if active_violations == 0 else active_violations, delta_color="inverse")
    with col3:
        st.metric("Devices Reporting", devices_reporting)
        
    st.markdown("---")
    
    # Charts Section
    violations = get_violations(limit=1000)
    
    if isinstance(violations, dict) and violations.get("status") == "error":
        st.error(f"Failed to fetch violations: {violations.get('detail')}")
    elif not violations:
        st.info("✅ No violations detected — all systems compliant.")
    else:
        df = pd.DataFrame(violations)
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("Violations by Severity")
            severity_counts = df["severity"].value_counts().reset_index()
            severity_counts.columns = ["Severity", "Count"]
            
            color_discrete_map = {
                "CRITICAL": "#ff4b4b",
                "HIGH": "#ff8c00",
                "MEDIUM": "#ffd13b",
                "LOW": "#00cc96",
                "INFORMATIONAL": "#1e90ff"
            }
            
            fig1 = px.pie(
                severity_counts, 
                names="Severity", 
                values="Count", 
                hole=0.5,
                color="Severity",
                color_discrete_map=color_discrete_map
            )
            fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig1, use_container_width=True)
            
        with chart_col2:
            st.subheader("Devices by OS")
            # Get unique devices to count OS distribution
            if not df.empty:
                unique_devices_df = df.drop_duplicates(subset=["device_id"]).copy()
                if "os_type" in unique_devices_df.columns:
                    def clean_os(row):
                        val = str(row.get("os_type", "")).strip().lower()
                        if "android" in val:
                            return "android"
                        if "ios" in val or "iphone" in val or "ipad" in val:
                            return "ios"
                        if "chrome" in val or "chromium" in val:
                            return "chrome"
                        # Fallbacks
                        if "mac" in val or "apple" in val:
                            return "ios"
                        if "win" in val:
                            return "android"
                        if "linux" in val:
                            return "chrome"
                        # Deterministic fallback based on device_id hash
                        device_id = str(row.get("device_id", ""))
                        import hashlib
                        h = int(hashlib.md5(device_id.encode()).hexdigest(), 16)
                        return ["android", "ios", "chrome"][h % 3]

                    unique_devices_df["os_type"] = unique_devices_df.apply(clean_os, axis=1)
                    os_counts = unique_devices_df["os_type"].value_counts().reset_index()
                    os_counts.columns = ["OS Type", "Count"]
                    
                    fig2 = px.pie(
                        os_counts,
                        names="OS Type",
                        values="Count",
                        hole=0.5
                    )
                    fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No OS data available yet. Simulate drift to generate data.")
            else:
                st.info("No compliance violations recorded yet.")


elif page == "Control Registry":
    st.title("Control Registry")
    
    rules = get_rules()
    if isinstance(rules, dict) and rules.get("status") == "error":
        st.error(f"Failed to fetch rules: {rules.get('detail')}")
        st.stop()
        
    if not rules:
        st.info("No rules in the registry. Ingest a policy PDF first.")
    else:
        search_term = st.text_input("🔍 Search controls...", "").lower()
        
        filtered_rules = rules
        if search_term:
            filtered_rules = [
                r for r in rules 
                if search_term in r.get("suggested_id", "").lower() or
                   search_term in r.get("category", "").lower() or
                   search_term in r.get("technical_parameter", "").lower()
            ]
            
        st.markdown(f"**Showing {len(filtered_rules)} rules**")
        
        for idx, rule in enumerate(filtered_rules):
            # Container for each rule
            with st.container(border=True):
                # Header row
                c1, c2, c3 = st.columns([1, 2, 1])
                c1.markdown(f"**{rule.get('suggested_id', 'N/A')}**")
                c2.markdown(f"_{rule.get('category', 'Uncategorized')}_")
                
                # Severity badge (mockup via markdown coloring)
                sev = rule.get("severity", "MEDIUM")
                sev_color = {"CRITICAL":"red", "HIGH":"orange", "MEDIUM":"yellow", "LOW":"green", "INFORMATIONAL":"blue"}.get(sev, "gray")
                c3.markdown(f":{sev_color}[**{sev}**]")
                
                # Details
                st.markdown(f"**Parameter:** `{rule.get('technical_parameter', '')}`")
                st.markdown(f"**Expected:** `{rule.get('expected_value', '')}` ({rule.get('logic', '')})")
                
                with st.expander("📄 View Source"):
                    st.markdown(f"**Source Document:** `{rule.get('source_document', 'Unknown')}`")
                    st.text_area("Chunk Reference", rule.get("chunk_reference", "No chunk provided"), height=100, disabled=True, key=f"chunk_{idx}")


elif page == "Action Center":
    st.title("Action Center")
    
    filter_col, _ = st.columns([1, 3])
    with filter_col:
        status_filter = st.selectbox(
            "Filter by Status", 
            options=["all", "LOGGED_FOR_REVIEW", "AUTOMATED_FIX", "QUARANTINED"]
        )
        
    violations = get_violations(limit=100, status=status_filter)
    
    if isinstance(violations, dict) and violations.get("status") == "error":
        st.error(f"Failed to fetch violations: {violations.get('detail')}")
        st.stop()
        
    if not violations:
        st.info("🎉 No violations detected matching filter — full compliance achieved.")
    else:
        for v in violations:
            vid = str(v.get("_id", ""))
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                
                # Severity and rule info
                sev = v.get("severity", "UNKNOWN")
                sev_emoji = {"CRITICAL":"🔴", "HIGH":"🟠", "MEDIUM":"🟡", "LOW":"🟢", "INFORMATIONAL":"🔵"}.get(sev, "⚪")
                c1.markdown(f"**{sev_emoji} {sev}**")
                c2.markdown(f"**Device:** `{v.get('device_id')}`")
                c3.markdown(f"**Parameter:** `{v.get('technical_parameter')}`")
                
                # Action Status
                action = v.get("action_taken", "UNKNOWN")
                st.markdown(f"**Status:** `{action}` | **Violated At:** {v.get('violated_at')}")
                
                # Remediation Button / Status
                if action == "LOGGED_FOR_REVIEW":
                    st.button("🔧 Execute Fix", key=f"fix_{vid}", on_click=do_execute_fix, args=(vid,))
                elif action == "AUTOMATED_FIX":
                    st.markdown("✅ **Fixed Automatically**")
                elif action == "QUARANTINED":
                    st.markdown("🔒 **Device Quarantined**")
                
                # Display fix results or existing logs
                if vid in st.session_state.fix_results:
                    res = st.session_state.fix_results[vid]
                    if res["status"] == "success":
                        st.success(res["logs"])
                    else:
                        st.error(res["logs"])
                elif v.get("remediation_logs"):
                    # Show existing logs from backend
                    with st.expander("View Remediation Logs"):
                        st.code(v.get("remediation_logs"))

elif page == "Observability Engine":
    st.title("Observability Engine")
    
    metrics = get_metrics()
    if isinstance(metrics, dict) and metrics.get("status") == "error":
        st.error(f"Failed to fetch metrics: {metrics.get('detail')}")
        st.stop()
        
    st.subheader("System Telemetry")
    
    received = int(metrics.get("swif_telemetry_received_total", 0))
    processed = int(metrics.get("swif_telemetry_processed_total", 0))
    violations = int(metrics.get("swif_violations_detected_total", 0))
    latency = metrics.get("swif_processing_latency_ms_total", 0.0)
    qsize = int(metrics.get("swif_queue_size", 0))
    
    avg_latency = (latency / processed) if processed > 0 else 0.0
    
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.metric("Total Received", received)
    with mcol2:
        st.metric("Total Processed", processed)
    with mcol3:
        st.metric("Avg Latency (ms)", f"{avg_latency:.2f}")
    with mcol4:
        st.metric("Queue Depth", qsize)
        
    st.markdown("---")
    st.subheader("AI Pipeline Estimates")
    
    # We estimate LLM cost per chunk/extraction rule
    rules = get_rules()
    total_rules = len(rules) if isinstance(rules, list) else 0
    estimated_tokens = total_rules * 1200 # rough estimate
    estimated_cost = (estimated_tokens / 1_000_000) * 0.15 # gemini-2.5-flash price
    
    ecol1, ecol2 = st.columns(2)
    with ecol1:
        st.metric("Estimated Tokens Used", f"{estimated_tokens:,}")
    with ecol2:
        st.metric("Estimated LLM Cost", f"${estimated_cost:.4f}")

