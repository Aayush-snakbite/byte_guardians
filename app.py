"""Snakbite: Monitor. Detect. Protect. A local educational monitoring dashboard."""
from datetime import datetime
import io, json, time
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from modules import storage
from modules.password_security import build_password_checker_html
from modules.system_monitor import collect_metrics, get_processes, get_interfaces, get_connections
from modules.security_checks import run_health_check
from modules.charts import metric_chart

st.set_page_config(page_title="Snakbite | Cybersecurity Monitor", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
storage.initialize()
st.markdown("""
<style>
html,body,[class*="css"]{font-family:Segoe UI,Arial,sans-serif} .stApp{background:radial-gradient(ellipse at 70% 0%,#102d31 0%,#08131c 42%,#071019 100%);color:#e3edf2}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0c1b25,#08121a);border-right:1px solid #1b303b}
[data-testid="stMetric"]{background:linear-gradient(145deg,#11222c,#0d1b24);padding:18px 20px;border:1px solid #20343d;border-radius:15px;box-shadow:0 8px 28px #03080d55}
[data-testid="stMetricLabel"]{color:#91a7b2!important} [data-testid="stMetricValue"]{color:#f1f7f8!important}
.eyebrow{letter-spacing:.16em;text-transform:uppercase;color:#42d3a2;font-size:.72rem;font-weight:800}.muted{color:#90a5af}.panel{background:linear-gradient(145deg,#10212a,#0b1821);border:1px solid #20343d;border-radius:15px;padding:18px 20px;margin:.35rem 0 1rem}
.demo{border:1px solid #9e712c;background:#342614;color:#ffd780;border-radius:10px;padding:12px 15px;font-weight:800}
div.stButton>button{border-radius:9px;border:1px solid #28424b;background:#122630;color:#e7f4f2;font-weight:700;min-height:2.5rem} div.stButton>button:hover{border-color:#3bd09e;color:#53e4b2}
h1,h2,h3{letter-spacing:-.035em} [data-testid="stDataFrame"]{border:1px solid #20343d;border-radius:12px;overflow:hidden}
</style>""", unsafe_allow_html=True)

PAGES=["Dashboard","System Monitor","Network Monitor","Security Alerts","Password Security","Activity Logs","Settings","About"]
if "page" not in st.session_state: st.session_state.page="Dashboard"
if "history" not in st.session_state: st.session_state.history=[]
if "latest" not in st.session_state: st.session_state.latest=collect_metrics()

def go(page): st.session_state.page=page
def get_live():
    st.session_state.latest=collect_metrics()
    m=st.session_state.latest
    st.session_state.history.append({"time":m["collected_at"],"time_label":datetime.fromtimestamp(m["collected_at"]).strftime("%H:%M:%S"),"cpu_percent":m["cpu_percent"],"ram_percent":m["ram_percent"],"bytes_recv":m["bytes_recv"],"bytes_sent":m["bytes_sent"]})
    st.session_state.history=st.session_state.history[-120:]
    st.session_state.refreshed=datetime.now().strftime("%H:%M:%S")
    return m

def pct(v): return f"{v:.1f}%" if isinstance(v,(int,float)) else "Unavailable"
def fmt_bytes(v):
    if v is None:return "Unavailable"
    units=["B","KB","MB","GB","TB"]; value=float(v)
    for unit in units:
        if value<1024 or unit==units[-1]:return f"{value:.1f} {unit}"
        value/=1024
def fmt_duration(seconds):
    if seconds is None:return "Unavailable"
    d,rem=divmod(seconds,86400); h,rem=divmod(rem,3600); m=rem//60
    return f"{d}d {h}h {m}m"
def run_check():
    m=get_live(); results=run_health_check(m,storage.get_settings())
    st.session_state.check_results=results
    st.session_state.flash="Basic health check completed. Results were saved to Activity Logs."

with st.sidebar:
    st.markdown("<div style='padding:8px 0 18px'><div style='font-size:1.45rem;font-weight:800;color:#f2f8f7'>⬡ SNAKBITE</div><div style='color:#41d2a0;font-size:.75rem;letter-spacing:.13em'>MONITOR. DETECT. PROTECT.</div></div>",unsafe_allow_html=True)
    st.markdown("<div class='eyebrow'>Workspace</div>",unsafe_allow_html=True)
    for p in PAGES:
        if st.button(("▣  " if p=="Dashboard" else "◈  ")+p,key="nav_"+p,width="stretch"): go(p)
    st.divider(); st.markdown("<div class='muted'>LOCAL MONITORING<br>Data stays on this device</div>",unsafe_allow_html=True)

m=st.session_state.latest
page=st.session_state.page
top1,top2=st.columns([5,1.2])
with top1:
    st.markdown("<div class='eyebrow'>SNK / LOCAL TELEMETRY</div>",unsafe_allow_html=True)
    st.title("Snakbite — Basic Cybersecurity Monitor" if page=="Dashboard" else page)
with top2:
    st.markdown("<div style='height:18px'></div>",unsafe_allow_html=True)
    if st.button("↻  Refresh metrics",key="refresh",width="stretch"): m=get_live(); st.success("Metrics refreshed from this device.")
st.caption(f"● Monitoring active · {m.get('hostname') or 'Device name unavailable'} · Last refresh {st.session_state.get('refreshed','just now')} · Metrics come from the host running Snakbite (cloud deployments show cloud-host metrics)")
if st.session_state.get("flash"):
    st.success(st.session_state.pop("flash"))

def metric_cards():
    cols=st.columns(4)
    data=[("CPU Usage",pct(m["cpu_percent"]),"processor utilization"),("RAM Usage",pct(m["ram_percent"]),f"{fmt_bytes(m['ram_available'])} available"),("Disk Usage",pct(m["disk_percent"]),f"{fmt_bytes(m['disk_free'])} free"),("Network Traffic",f"↓ {fmt_bytes(m['bytes_recv'])}",f"↑ {fmt_bytes(m['bytes_sent'])} sent")]
    for c,(label,val,helptext) in zip(cols,data): c.metric(label,val,helptext)

def health_label(value,warning,critical):
    if value is None:return "Unavailable"
    return "Critical" if value>=critical else "Warning" if value>=warning else "Healthy"

if page=="Dashboard":
    metric_cards(); st.write("")
    health=st.columns([1.1,1.9])
    with health[0]:
        settings=storage.get_settings(); vals=[("CPU",m["cpu_percent"],settings["cpu_warning"],settings["cpu_critical"]),("RAM",m["ram_percent"],settings["ram_warning"],settings["ram_critical"]),("Disk",m["disk_percent"],settings["disk_warning"],settings["disk_critical"])];
        statuses=[health_label(v,w,c) for _,v,w,c in vals]
        overall="Critical" if "Critical" in statuses else "Warning" if "Warning" in statuses else "Healthy" if "Unavailable" not in statuses else "Partial data"
        st.markdown("<div class='panel'><div class='eyebrow'>SYSTEM HEALTH OVERVIEW</div>",unsafe_allow_html=True)
        st.subheader("●  "+overall)
        for label,v,w,c in vals: st.write(f"**{label}** · {pct(v)} · {health_label(v,w,c)}")
        st.markdown("High resource use indicates load, not proof of an attack.</div>",unsafe_allow_html=True)
    with health[1]:
        st.markdown("<div class='panel'><div class='eyebrow'>LIVE RESOURCE HISTORY</div>",unsafe_allow_html=True)
        fig=metric_chart(st.session_state.history,["cpu_percent","ram_percent"],["CPU","RAM"],"CPU & RAM usage")
        if fig: st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
        else: st.info("Collecting metric history. Use Refresh Metrics to add a point.")
        st.markdown("</div>",unsafe_allow_html=True)
    cols=st.columns([1.05,1.4]);
    with cols[0]:
        st.markdown("<div class='panel'><div class='eyebrow'>QUICK ACTIONS</div>",unsafe_allow_html=True)
        if st.button("Run Basic Health Check",key="dashcheck",width="stretch"): run_check(); st.rerun()
        a,b=st.columns(2)
        with a:
            if st.button("View Security Alerts",key="dashalerts",width="stretch"): go("Security Alerts"); st.rerun()
            if st.button("Export Report",key="dashexport",width="stretch"):
                report={"generated_at":storage.now(),"metrics":m,"recent_events":storage.get_events(50)}
                st.download_button("Download report JSON",json.dumps(report,indent=2),"snakbite_report.json","application/json",key="reportdownload")
        with b:
            if st.button("Open Activity Logs",key="dashlogs",width="stretch"): go("Activity Logs"); st.rerun()
            if st.button("Open Settings",key="dashsettings",width="stretch"): go("Settings"); st.rerun()
        st.markdown("</div>",unsafe_allow_html=True)
    with cols[1]:
        st.markdown("<div class='panel'><div class='eyebrow'>RECENT ACTIVITY</div>",unsafe_allow_html=True)
        events=storage.get_events(5)
        if events: st.dataframe(pd.DataFrame(events)[["timestamp","source","event_type","severity","description"]],hide_index=True,width="stretch")
        else: st.caption("No activity yet. Run a health check to record your first result.")
        st.markdown("</div>",unsafe_allow_html=True)
    if st.session_state.get("check_results"):
        st.subheader("Latest health-check findings")
        st.dataframe(pd.DataFrame(st.session_state.check_results),hide_index=True,width="stretch")
elif page=="System Monitor":
    metric_cards(); st.subheader("Device information")
    a,b,c=st.columns(3); a.write(f"**Operating system**\n\n{m['os']}"); b.write(f"**Device name**\n\n{m['hostname'] or 'Unavailable'}"); c.write(f"**System uptime**\n\n{fmt_duration(m['uptime_seconds'])}")
    st.subheader("Running processes (read-only)")
    procs=get_processes(); st.dataframe(pd.DataFrame(procs) if procs else pd.DataFrame(columns=["PID","Process","Memory (MB)"]),hide_index=True,width="stretch")
    st.caption("Some process details may be hidden by operating-system permissions. Snakbite never stops processes.")
elif page=="Network Monitor":
    st.subheader("Network activity")
    fig=metric_chart(st.session_state.history,["bytes_recv","bytes_sent"],["Received","Sent"],"Network totals since collection (bytes)"," B")
    if fig: st.plotly_chart(fig,width="stretch")
    else: st.info("No network history yet. Refresh metrics to collect a point.")
    st.subheader("Network interfaces")
    interfaces=get_interfaces(); st.dataframe(pd.DataFrame(interfaces) if interfaces else pd.DataFrame(columns=["Interface","Status","IP addresses"]),hide_index=True,width="stretch")
    st.subheader("Visible connection metadata")
    conns=get_connections()
    if conns is None: st.info("Connection details are unavailable with the current operating-system permissions.")
    elif conns: st.dataframe(pd.DataFrame(conns),hide_index=True,width="stretch")
    else: st.caption("No visible active network connections.")
    st.caption("Unknown addresses are not classified as malicious. No packet contents are collected.")
elif page=="Security Alerts":
    st.markdown("<div class='demo'>DEMO DATA · SIMULATED SCENARIO · Not evidence of an actual attack</div>",unsafe_allow_html=True)
    alert=storage.get_demo_alert(); st.subheader("Simulated alert")
    st.write("**DEMO: Repeated login failures detected in a simulated scenario.**")
    st.caption(f"Status: {alert['status']} · Updated {alert['updated_at']}")
    with st.expander("View Details",expanded=True):
        st.write("This fictional alert is included for a college demonstration. Snakbite has no login-event source and has not observed real login failures.")
        st.write("**Recommended demo response:** discuss account lockout and multifactor authentication as general defensive practices.")
        hist=json.loads(alert["history"])
        if hist: st.write("**Status history**"); st.dataframe(pd.DataFrame(hist),hide_index=True,width="stretch")
    a,b,c=st.columns(3)
    with a:
        if alert["status"]=="Open" and st.button("Resolve demo alert",key="resolve"): storage.update_demo_alert("Resolved"); st.rerun()
        if alert["status"]=="Resolved" and st.button("Reopen demo alert",key="reopen"): storage.update_demo_alert("Open"); st.rerun()
    with c:
        if st.button("Reset demo data",key="resetdemo"): storage.reset_demo_alert(); st.success("Demo alert reset to Open."); st.rerun()
    st.subheader("Real health-check findings")
    ev=[e for e in storage.get_events() if e["event_type"]=="Health check"]
    if ev:
        evdf=pd.DataFrame(ev)
        search=st.text_input("Search security findings",key="alert_search",placeholder="Search findings…")
        severities=st.multiselect("Finding severity",["Info","Warning","Critical","Healthy"],default=["Info","Warning","Critical","Healthy"],key="alert_severity")
        evdf=evdf[evdf["severity"].isin(severities)]
        if search: evdf=evdf[evdf["description"].str.contains(search,case=False,na=False)]
        if not evdf.empty: st.dataframe(evdf[["timestamp","severity","description","result"]],hide_index=True,width="stretch")
        else: st.caption("No findings match the selected filters.")
        chart_col1,chart_col2=st.columns(2)
        with chart_col1:
            counts=evdf["severity"].value_counts().rename_axis("Severity").reset_index(name="Checks")
            if not counts.empty:
                fig=px.bar(counts,x="Severity",y="Checks",color="Severity",title="Health-check results")
                fig.update_layout(height=260,margin={"l":5,"r":5,"t":40,"b":5},paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font={"color":"#d8e4ec"})
                st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
        with chart_col2:
            all_events=pd.DataFrame(storage.get_events())
            if not all_events.empty:
                severity_counts=all_events[all_events["severity"].isin(["Info","Warning","Critical"])]["severity"].value_counts().rename_axis("Severity").reset_index(name="Events")
                if not severity_counts.empty:
                    fig=px.pie(severity_counts,names="Severity",values="Events",title="Logged event severity distribution")
                    fig.update_layout(height=260,margin={"l":5,"r":5,"t":40,"b":5},paper_bgcolor="rgba(0,0,0,0)",font={"color":"#d8e4ec"})
                    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
    else: st.info("No health-check findings recorded. Run Basic Health Check from Dashboard. Resource warnings are not attack detections.")
elif page=="Password Security":
    st.markdown("<div class='eyebrow'>LOCAL BROWSER ANALYSIS · NO PASSWORD LOGGING</div>",unsafe_allow_html=True)
    st.write("Analyze password length, character diversity, and predictable patterns. This is an educational estimate and does not check breach databases.")
    components.html(build_password_checker_html(),height=1050,scrolling=True)
elif page=="Activity Logs":
    events=storage.get_events(5000); df=pd.DataFrame(events)
    q=st.text_input("Search logs",placeholder="Search descriptions, severity, event type…")
    if not df.empty:
        sev=st.multiselect("Severity",sorted(df["severity"].dropna().unique()),default=sorted(df["severity"].dropna().unique()))
        source=st.multiselect("Data source",sorted(df["source"].dropna().unique()),default=sorted(df["source"].dropna().unique()))
        df=df[df["severity"].isin(sev)&df["source"].isin(source)]
        if q: df=df[df.astype(str).apply(lambda col:col.str.contains(q,case=False,na=False)).any(axis=1)]
        st.dataframe(df[["timestamp","event_type","severity","description","metrics","result","alert_status","source"]],hide_index=True,width="stretch")
        st.download_button("Export logs as CSV",df.to_csv(index=False).encode("utf-8-sig"),"snakbite_activity_logs.csv","text/csv")
    else: st.info("No activity recorded yet. Health checks and demo actions create persistent records here.")
    if st.button("Clear activity logs",key="clearlogs"): st.session_state.confirm_clear=True
    if st.session_state.get("confirm_clear"):
        st.warning("Clear all locally stored activity events? This cannot be undone.")
        yes,no=st.columns(2)
        with yes:
            if st.button("Confirm clear",key="confirmclear"): storage.clear_events(); st.session_state.confirm_clear=False; st.success("Activity logs cleared."); st.rerun()
        with no:
            if st.button("Cancel",key="cancelclear"): st.session_state.confirm_clear=False; st.rerun()
elif page=="Settings":
    st.write("Thresholds apply to basic resource checks. Values at or above critical are Critical; values at or above warning are Warning. They do not indicate cyberattacks.")
    current=storage.get_settings()
    with st.form("settings_form"):
        st.subheader("Resource thresholds (%)")
        heads=st.columns(3); [heads[i].markdown(f"**{x}**") for i,x in enumerate(("CPU","RAM","Disk"))]
        cols=[st.columns(3) for _ in range(2)]
        values={}
        for idx,name in enumerate(("cpu","ram","disk")):
            values[name+"_warning"]=cols[0][idx].number_input("Warning",0,100,int(current[name+"_warning"]),key=name+"warn")
            values[name+"_critical"]=cols[1][idx].number_input("Critical",0,100,int(current[name+"_critical"]),key=name+"crit")
        st.subheader("Refresh preference")
        values["refresh_seconds"]=st.selectbox("Preferred interval",[10,15,30,60,120],index=[10,15,30,60,120].index(current["refresh_seconds"]),format_func=lambda x:f"{x} seconds")
        if st.form_submit_button("Save settings"):
            invalid=[n.upper() for n in ("cpu","ram","disk") if values[n+"_warning"]>=values[n+"_critical"]]
            if invalid: st.error("Critical thresholds must be greater than warning thresholds: "+", ".join(invalid))
            else: storage.save_settings(values); storage.add_event("Settings updated","Info","Resource thresholds or refresh preference changed.",values,result="Saved"); st.success("Settings saved locally.")
    st.caption("Preferred refresh interval is saved for reference. Refresh is user-triggered to avoid collecting data in the background without your action.")
elif page=="About":
    st.markdown("<div class='eyebrow'>MONITOR. DETECT. PROTECT.</div>",unsafe_allow_html=True)
    st.title("Snakbite")
    st.write("**Problem:** beginners need a clear way to see basic computer resource health and understand how simple rules create actionable findings.")
    st.write("**Objectives:** collect local system metrics, compare CPU/RAM/disk with configurable thresholds, and persist understandable activity records.")
    st.write("**Proposed solution:** a local Streamlit dashboard using psutil and SQLite, with charts and a clearly separated simulated alert for demonstrations.")
    st.write("**Technology:** Python 3.10+, Streamlit (web UI), psutil (system metrics), pandas (tables), Plotly (interactive charts), SQLite (local persistent records).")
    st.write("**Workflow:** collect metrics → evaluate threshold rules → display health findings → store event locally → review/export the log. Password analysis runs separately inside a local browser component and has no connection to the log store.")
    st.write("**Password Security:** an offline browser-side checker scores length, character diversity, common examples, sequences, repeats, keyboard paths, predictable words/substitutions, dates, and optional comparison fragments. Password input is not returned to Python or written to app storage.")
    st.warning("Snakbite is an educational cybersecurity-monitoring prototype. It is not antivirus software or professional security monitoring, and it cannot detect every attack.")
    st.subheader("Current limitations")
    st.write("Resource checks only; network metadata access varies by OS permissions; no packet inspection or login event source; in-memory charts reset when the app restarts; a refresh is user-triggered. Hosted deployment metrics describe the cloud container, not a visitor's device, and Community Cloud does not guarantee persistence of generated local files. Password quality is an educational heuristic with a small local example list, not a breached-password check; theoretical entropy is not a crack-time guarantee.")
    st.subheader("Future scope")
    st.write("Optional OS-native event-log integration, persistent metric history, configurable notification rules, stronger cross-platform packaging, and measured usability/security testing.")
    st.subheader("Presentation guide")
    with st.expander("30-second introduction"):
        st.write("Snakbite is a local educational cybersecurity-monitoring dashboard. It reads real CPU, memory, disk, and network counters from the computer using psutil. A basic rule-based health check compares resource usage with adjustable thresholds and stores findings in a local SQLite database. A separate simulated alert supports demonstration, and is clearly labelled so it cannot be confused with a real detection. It is a learning prototype, not antivirus software.")
    with st.expander("Two-minute live demo and viva preparation"):
        st.markdown("""**Demo sequence:** 1. Open Dashboard and point out local monitoring status. 2. Show CPU, RAM, disk and network values from this device. 3. Click **Run Basic Health Check**. 4. Explain measured values and thresholds, then open **Activity Logs** to show saved rows. 5. Open **Security Alerts**, point to the DEMO DATA label and View Details. 6. Resolve the simulated alert. 7. Open **Password Security** and explain local-only analysis, pattern warnings, and entropy limits. 8. Explain limitations and future scope. Do not cause an actual resource problem for the demo.

**Likely viva questions**
- **What is psutil?** A Python library that reads operating-system and process information.
- **Why Streamlit?** It lets Python create an interactive local web interface with little frontend code.
- **How are warnings decided?** A simple comparison of a measured percentage against user-configured warning and critical thresholds.
- **Where do logs go?** To a SQLite database in the project's `data` folder; SQLite is a small database stored in a file.
- **Does high CPU mean an attack?** No. It may be normal workload; this project reports resource health only.
- **How does Password Security protect the input?** The JavaScript analyzer runs in a local browser iframe. The password is never submitted to Python, saved, or logged; Reset clears its fields.
- **Does its entropy estimate predict crack time?** No. It assumes uniform randomness and is only a theoretical upper bound. Real attacks depend on password choice, hashing, attacker resources, and leaked context.

**Workflow:** psutil collection → threshold evaluation → Streamlit presentation → SQLite activity log. CSV is a portable text table for exporting log rows.

**Password strength:** longer unique passwords and passphrases are generally harder to guess. Predictable sequences, repeated chunks, common words, dates, and personal fragments lower the educational score. The browser-only checker does not send or save entered values. The theoretical entropy estimate is not a crack-time guarantee.
""")

st.markdown("<div style='color:#6e8792;font-size:.76rem;margin-top:2rem;border-top:1px solid #20343d;padding-top:1rem'>SNAKBITE · LOCAL EDUCATIONAL PROTOTYPE · NO CLOUD UPLOADS</div>",unsafe_allow_html=True)

