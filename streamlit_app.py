import streamlit as st
import pandas as pd
import os
import json
import tempfile
from dotenv import load_dotenv

load_dotenv()

# create output folder on startup so terminal version never crashes
os.makedirs("output", exist_ok=True)

st.set_page_config(
    page_title="SmartData Agent",
    page_icon="✦",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
.stApp { background-color: #ffffff; }

[data-testid="stSidebar"] {
    background-color: #fafafa;
    border-right: 1px solid #f0e6ff;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown li {
    font-size: 13px; color: #555; line-height: 1.8;
}

.app-header {
    padding: 2.5rem 0 1.5rem 0;
    border-bottom: 1px solid #f0e6ff;
    margin-bottom: 2rem;
}
.app-title { font-size: 28px; font-weight: 600; color: #1a1a1a; letter-spacing: -0.5px; margin: 0; }
.app-subtitle { font-size: 14px; color: #888; font-weight: 400; margin: 4px 0 0 0; }
.app-tag {
    display: inline-block; font-size: 11px; font-weight: 500;
    color: #7c3aed; background: #f3e8ff; padding: 3px 10px;
    border-radius: 20px; margin-top: 10px; letter-spacing: 0.3px;
}

.section-label {
    font-size: 11px; font-weight: 600; letter-spacing: 1.2px;
    text-transform: uppercase; color: #aaa; margin: 2rem 0 0.75rem 0;
}

.metric-card { background: #fafafa; border: 1px solid #f0e6ff; border-radius: 10px; padding: 1.1rem 1.25rem; }
.metric-label { font-size: 11px; font-weight: 500; letter-spacing: 0.8px; text-transform: uppercase; color: #aaa; margin: 0 0 6px 0; }
.metric-value { font-size: 26px; font-weight: 600; color: #7c3aed; margin: 0; line-height: 1; }
.metric-value.neutral { color: #1a1a1a; }
.metric-value.good    { color: #16a34a; }
.metric-value.warn    { color: #d97706; }

.clean-row { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f5f0ff; }
.clean-col-name { font-size: 13px; font-weight: 500; color: #1a1a1a; min-width: 140px; }
.clean-action { font-size: 13px; color: #555; line-height: 1.5; }
.tag { display: inline-block; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 4px; margin-right: 6px; }
.tag-dropped { background: #fef2f2; color: #dc2626; }
.tag-filled  { background: #f0fdf4; color: #16a34a; }
.tag-forward { background: #eff6ff; color: #2563eb; }
.tag-flagged { background: #fefce8; color: #b45309; }

.stButton > button {
    background: #7c3aed; color: white; border: none; border-radius: 8px;
    padding: 0.65rem 2rem; font-family: 'Poppins', sans-serif;
    font-size: 14px; font-weight: 500; transition: background 0.2s; width: 100%;
}
.stButton > button:hover { background: #6d28d9; color: white; border: none; }

[data-testid="stFileUploader"] { background: #fafafa; border: 1.5px dashed #d8b4fe; border-radius: 10px; }

.step-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; font-size: 13px; color: #555; border-bottom: 1px solid #f5f0ff; }
.step-done { width: 20px; height: 20px; border-radius: 50%; background: #7c3aed; color: white; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.step-name { font-weight: 500; color: #1a1a1a; }

.summary-card {
    background: #faf5ff; border-left: 3px solid #c084fc;
    border-radius: 0 10px 10px 0; padding: 1.5rem 1.75rem;
    font-size: 14px; line-height: 1.9; color: #333;
}

.stDownloadButton > button {
    background: transparent; color: #7c3aed; border: 1.5px solid #d8b4fe;
    border-radius: 8px; padding: 0.6rem 1.5rem;
    font-family: 'Poppins', sans-serif; font-size: 13px; font-weight: 500;
}
.stDownloadButton > button:hover { background: #f3e8ff; border-color: #a855f7; color: #6d28d9; }

[data-testid="stDataFrame"] { border: 1px solid #f0e6ff; border-radius: 10px; overflow: hidden; }
hr { border: none; border-top: 1px solid #f5f0ff; margin: 2rem 0; }
h2, h3 { font-family: 'Poppins', sans-serif; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

from utils.file_parser import ingest
from agent.tools import handle_missing_values, TOOL_FUNCTIONS


# ── header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <p class="app-title">SmartData Agent</p>
    <p class="app-subtitle">Upload a dataset. The agent cleans it, analyzes it, and explains what it found.</p>
    <span class="app-tag">Powered by Groq · LLaMA 3.3 · 70B</span>
</div>
""", unsafe_allow_html=True)


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**How it works**")
    st.markdown("""
1. Upload your CSV or JSON file
2. The agent detects and handles missing values
3. Groq reasons about your data and picks the right analyses
4. Plots, statistics, and a written summary appear below
    """)
    st.markdown("---")
    st.markdown("**Settings**")

    auto_mode = st.toggle("Let the agent decide", value=True,
                          help="When on, Groq picks which tools to run based on your data")

    if not auto_mode:
        st.markdown("Select tools to run:")
        run_stats    = st.checkbox("Summary statistics", value=True)
        run_dist     = st.checkbox("Distributions", value=True)
        run_corr     = st.checkbox("Correlation heatmap", value=True)
        run_outliers = st.checkbox("Outlier detection", value=True)
        run_ts       = st.checkbox("Time series", value=False)
        run_missing  = st.checkbox("Missing value map", value=True)

    st.markdown("---")
    st.caption("SmartData Agent · built with Python, Groq, Streamlit")


# ── file upload ───────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Dataset</p>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload a CSV or JSON file to get started",
    type=["csv", "json"],
    label_visibility="collapsed",
)

if uploaded_file is None:
    st.markdown("""
    <div style="text-align:center; padding: 3rem 0; color: #bbb; font-size:14px;">
        No file uploaded yet. Drop a CSV or JSON above.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# clear results and chat when a new file is uploaded
if "last_file" not in st.session_state or st.session_state["last_file"] != uploaded_file.name:
    st.session_state.pop("results", None)
    st.session_state["chat_history"] = []
    st.session_state["last_file"] = uploaded_file.name


# ── load data ─────────────────────────────────────────────────────────────────
with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
    tmp.write(uploaded_file.read())
    tmp_path = tmp.name

try:
    df, profile = ingest(tmp_path)
except Exception as e:
    st.error(f"Could not load file: {e}")
    st.stop()
finally:
    os.unlink(tmp_path)


# ── dataset overview ──────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Overview</p>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><p class="metric-label">Rows</p><p class="metric-value neutral">{profile["shape"]["rows"]:,}</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><p class="metric-label">Columns</p><p class="metric-value neutral">{profile["shape"]["columns"]}</p></div>', unsafe_allow_html=True)
with c3:
    wc = "warn" if profile["total_missing"] > 0 else "good"
    st.markdown(f'<div class="metric-card"><p class="metric-label">Missing Values</p><p class="metric-value {wc}">{profile["total_missing"]:,}</p></div>', unsafe_allow_html=True)
with c4:
    dc = "warn" if profile["duplicate_rows"] > 0 else "good"
    st.markdown(f'<div class="metric-card"><p class="metric-label">Duplicate Rows</p><p class="metric-value {dc}">{profile["duplicate_rows"]}</p></div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

with st.expander("View column details"):
    cols_df = pd.DataFrame([
        {"Column": col, "Type": info["dtype"], "Missing": f"{info['missing_count']} ({info['missing_pct']}%)",
         "Unique values": info["unique_values"], "Sample": str(info["sample"])}
        for col, info in profile["columns"].items()
    ])
    st.dataframe(cols_df, use_container_width=True, hide_index=True)

st.markdown("---")


# ── missing value handling ────────────────────────────────────────────────────
st.markdown('<p class="section-label">Data Cleaning</p>', unsafe_allow_html=True)

with st.spinner("Handling missing values..."):
    df_clean, missing_report = handle_missing_values(df)

if missing_report:
    rows_html = ""
    for col, action in missing_report.items():
        if "dropped" in action:        tag = '<span class="tag tag-dropped">dropped</span>'
        elif "median" in action or "mode" in action: tag = '<span class="tag tag-filled">imputed</span>'
        elif "forward filled" in action: tag = '<span class="tag tag-forward">forward filled</span>'
        else:                          tag = '<span class="tag tag-flagged">flagged</span>'
        rows_html += f'<div class="clean-row"><span class="clean-col-name">{col}</span><span class="clean-action">{tag}{action}</span></div>'
    st.markdown(rows_html, unsafe_allow_html=True)
else:
    st.success("No missing values detected. Data is clean.")

st.markdown("---")


# ── run analysis ──────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Analysis</p>', unsafe_allow_html=True)

if auto_mode:
    run_button = st.button("Run Agent Analysis")

    if run_button:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            st.error("GROQ_API_KEY not found in your .env file.")
            st.stop()

        from agent.agent import run_agent
        import io
        from contextlib import redirect_stdout

        with st.spinner("Agent is analyzing your dataset..."):
            try:
                f = io.StringIO()
                with redirect_stdout(f):
                    st.session_state["results"] = run_agent(df_clean, profile)
            except Exception as e:
                st.error(f"Agent error: {e}")
                st.stop()

else:
    if st.button("Run Selected Tools"):
        tools_to_run = []
        if run_stats:    tools_to_run.append("summary_stats")
        if run_dist:     tools_to_run.append("plot_distributions")
        if run_corr:     tools_to_run.append("plot_correlation_heatmap")
        if run_outliers: tools_to_run.append("detect_outliers")
        if run_ts:       tools_to_run.append("plot_time_series")
        if run_missing:  tools_to_run.append("plot_missing_heatmap")

        tool_results = {}
        progress = st.progress(0)
        for i, tool_name in enumerate(tools_to_run):
            with st.spinner(f"Running {tool_name}..."):
                try:
                    output = TOOL_FUNCTIONS[tool_name](df_clean)
                    tool_results[tool_name] = output
                except Exception as e:
                    st.warning(f"{tool_name} — {e}")
            progress.progress((i + 1) / len(tools_to_run))

        st.session_state["results"] = tool_results


# ── display results ───────────────────────────────────────────────────────────
if "results" in st.session_state:
    results = st.session_state["results"]

    # steps completed
    st.markdown('<p class="section-label">Steps Completed</p>', unsafe_allow_html=True)
    steps_html = ""
    for i, tool_name in enumerate([k for k in results.keys() if not k.startswith("_")], 1):
        steps_html += f'<div class="step-row"><span class="step-done">{i}</span><span class="step-name">{tool_name.replace("_", " ")}</span></div>'
    st.markdown(steps_html, unsafe_allow_html=True)
    st.markdown("---")

    # summary statistics table
    if "summary_stats" in results and isinstance(results["summary_stats"], dict):
        st.markdown('<p class="section-label">Summary Statistics</p>', unsafe_allow_html=True)
        stats_data = [{"column": col, **stats} for col, stats in results["summary_stats"].items() if isinstance(stats, dict)]
        if stats_data:
            st.dataframe(pd.DataFrame(stats_data).set_index("column"), use_container_width=True)
        st.markdown("---")

    # outlier table
    if "detect_outliers" in results and isinstance(results["detect_outliers"], dict):
        st.markdown('<p class="section-label">Outlier Detection</p>', unsafe_allow_html=True)
        outlier_data = [
            {"column": col, "IQR outliers": info["iqr_outliers"], "Z-score outliers": info["zscore_outliers"],
             "status": "flagged" if info["likely_has_outliers"] else "clean"}
            for col, info in results["detect_outliers"].items() if isinstance(info, dict)
        ]
        if outlier_data:
            st.dataframe(pd.DataFrame(outlier_data).set_index("column"), use_container_width=True)
        st.markdown("---")

    # plots -- displayed in memory using st.pyplot() -- no disk needed
    st.markdown('<p class="section-label">Plots</p>', unsafe_allow_html=True)
    plot_cols = st.columns(2)
    plot_index = 0

    # distribution figures -- list of (col_name, fig) tuples
    if "plot_distributions" in results and isinstance(results["plot_distributions"], list):
        for col_name, fig in results["plot_distributions"]:
            if fig is not None:
                with plot_cols[plot_index % 2]:
                    st.pyplot(fig, use_container_width=True)
                    st.caption(f"distribution of {col_name}")
                plot_index += 1

    # single figure tools
    for tool_name in ["plot_correlation_heatmap", "plot_time_series", "plot_missing_heatmap"]:
        if tool_name in results and results[tool_name] is not None:
            fig = results[tool_name]
            if hasattr(fig, "get_axes"):  # check it's actually a matplotlib figure
                with plot_cols[plot_index % 2]:
                    st.pyplot(fig, use_container_width=True)
                    st.caption(tool_name.replace("_", " "))
                plot_index += 1

    if plot_index == 0:
        st.info("No plots generated yet — run the agent to create them.")

    st.markdown("---")

    # written summary
    if "_written_summary" in results:
        st.markdown('<p class="section-label">Summary</p>', unsafe_allow_html=True)
        summary_text = results["_written_summary"].replace("\n", "<br>")
        st.markdown(f'<div class="summary-card">{summary_text}</div>', unsafe_allow_html=True)
        st.markdown("---")

    # download report
    report_path = "output/report.md"
    if os.path.exists(report_path):
        st.markdown('<p class="section-label">Export</p>', unsafe_allow_html=True)
        with open(report_path, "r") as f:
            report_content = f.read()
        st.download_button(
            label="Download analysis report",
            data=report_content,
            file_name="smartdata_report.md",
            mime="text/markdown",
        )


# ── chat with your data ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-label">Ask a question about your data</p>', unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for message in st.session_state["chat_history"]:
    if message["role"] == "user":
        st.markdown(f"""
        <div style="text-align:right; margin: 8px 0;">
            <span style="background:#7c3aed; color:white; padding:8px 14px;
            border-radius:12px 12px 2px 12px; font-size:13px; display:inline-block;
            max-width:75%; text-align:left;">{message["content"]}</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align:left; margin: 8px 0;">
            <span style="background:#f3e8ff; color:#3b0764; padding:8px 14px;
            border-radius:12px 12px 12px 2px; font-size:13px; display:inline-block;
            max-width:75%; text-align:left; line-height:1.6;">{message["content"]}</span>
        </div>""", unsafe_allow_html=True)

question = st.chat_input("Ask anything about your dataset...")

if question and "results" in st.session_state:
    from agent.agent import chat_with_data
    st.session_state["chat_history"].append({"role": "user", "content": question})
    with st.spinner("Thinking..."):
        answer = chat_with_data(question, profile, st.session_state["results"])
    st.session_state["chat_history"].append({"role": "assistant", "content": answer})
    st.rerun()

elif question and "results" not in st.session_state:
    st.warning("Run the agent analysis first before asking questions.")

