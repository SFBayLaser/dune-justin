#
# Plot the dataframe from the jobStatistics.py module
#
import subprocess
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from pathlib import Path


HIST_COLOR = "#1f77b4"   # Plotly default blue
CDF_COLOR  = "#d62728"   # Plotly default red

def get_git_commit_hash(short=True, repo_dir=None) -> str:
    """
    Return current git commit hash (short by default).
    If not in a git repo, returns 'unknown' without printing git errors.
    If repo_dir is provided, runs git from that directory.
    """
    try:
        args = ["git", "rev-parse"]
        args += ["--short", "HEAD"] if short else ["HEAD"]
        cwd = str(repo_dir) if repo_dir else None

        return subprocess.check_output(
            args,
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,  # suppress the fatal message
        ).strip()
    except Exception:
        return "unknown"

def make_summary_table_df(df_sel: pd.DataFrame) -> pd.DataFrame:
    # only include numeric cols you care about
    cols = ["cpu_s", "wall_s", "cpu_frac", "maxrss_bytes"]
    d = df_sel[cols].copy()

    # RSS in MiB is easier to read
    if "maxrss_bytes" in d.columns:
        d["maxrss_mib"] = d["maxrss_bytes"] / (1024**2)
        cols = ["cpu_s", "wall_s", "cpu_frac", "maxrss_mib"]

    # stats
    summary = pd.DataFrame({
        "N": [len(df_sel)],
        "CPU mean (s)": [d["cpu_s"].mean()],
        "CPU p50 (s)": [d["cpu_s"].median()],
        "CPU p95 (s)": [d["cpu_s"].quantile(0.95)],
        "Wall mean (s)": [d["wall_s"].mean()],
        "CPU frac mean": [d["cpu_frac"].mean()],
        "RSS p95 (MiB)": [d["maxrss_mib"].quantile(0.95)] if "maxrss_mib" in d else [np.nan],
    })

    # pretty formatting
    for c in summary.columns:
        if c != "N":
            summary[c] = summary[c].map(lambda v: "" if pd.isna(v) else f"{v:.3g}")
    summary["N"] = summary["N"].astype(int).astype(str)
    return summary

def plot_hist_with_cdf(fig, row, col, x, nbins, name="Time", xlabel="CPU time (s)"):
    counts, edges = np.histogram(x, bins=nbins)

    # guard against empty selection
    if counts.sum() == 0:
        return

    cdf = np.cumsum(counts) / counts.sum()

    # Histogram on primary y-axis
    fig.add_trace(
        go.Scatter(
            x=edges[:-1],
            y=counts,
            mode="lines",
            line=dict(color=HIST_COLOR, width=2),
            line_shape="hvh",
            name=name,
            showlegend=(row == 1 and col == 1),  # avoid duplicate legend entries
        ),
        row=row, col=col, secondary_y=False
    )

    # CDF on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=edges[1:],     # right edges so it reaches 1.0 at end
            y=cdf,
            mode="lines+markers",
            #line_shape="hvh",
            line=dict(color=CDF_COLOR, width=2, dash="solid"),
            marker=dict(
                symbol="circle",
                size=6,
                color=CDF_COLOR,
            ),
            opacity=0.4,
            name="CDF",
            showlegend=(row == 1 and col == 1),
        ),
        row=row, col=col, secondary_y=True
    )

    fig.update_xaxes(title_text=xlabel, row=row, col=col)
    fig.update_yaxes(title_text="Count", row=row, col=col, secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title_text="CDF",   row=row, col=col, secondary_y=True, range=[0, 1])

    return
    
def make_cpu_figure_with_table(df_sel, workflow_id, stage, commit):
    x = df_sel["cpu_s"].dropna().astype(float).to_numpy()
    nbins = max(10, int(np.sqrt(len(x))))  # reasonable default

    summary_df = make_summary_table_df(df_sel)

    fig = make_subplots(
        rows=2, cols=1,
        specs=[[{"secondary_y": True}], [{"type": "table"}]],
        row_heights=[0.75, 0.25],
        vertical_spacing=0.08,
    )

    plot_hist_with_cdf(fig, 1, 1, x, nbins)

    # Add the table (under plot)
    fig.add_trace(
        go.Table(
            header=dict(values=list(summary_df.columns)),
            cells=dict(values=[summary_df[c].tolist() for c in summary_df.columns]),
        ),
        row=2, col=1
    )

    title_text = (
        f"<b>Workflow {workflow_id} — Stage {stage} CPU time</b><br>"
        f"<span style='font-size:16px'>"
        f"{len(df_sel)} jobs (exit = 0, CPU>0, finished) • commit {commit}"
        f"</span>"
    )

    fig.update_layout(
        title=dict(text=title_text, x=0.5, xanchor="center", font=dict(size=24)),
        width=1200, height=800,
        margin=dict(t=120, l=70, r=70, b=50),
    )
    fig.update_xaxes(title_text="CPU time (s)", row=1, col=1)

    return fig

def make_time_figure_with_table(df_sel, workflow_id, stage, commit,
                                value_col="cpu_s",
                                title_metric="CPU time",
                                x_label="CPU time (s)"):
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    x = df_sel[value_col].dropna().astype(float).to_numpy()
    nbins = max(10, int(np.sqrt(len(x))))

    summary_df = make_summary_table_df(df_sel)

    fig = make_subplots(
        rows=2, cols=1,
        specs=[[{"secondary_y": True}], [{"type": "table"}]],
        row_heights=[0.75, 0.25],
        vertical_spacing=0.08,
    )

    plot_hist_with_cdf(fig, 1, 1, x, nbins)

    fig.add_trace(
        go.Table(
            header=dict(values=list(summary_df.columns)),
            cells=dict(values=[summary_df[c].tolist() for c in summary_df.columns]),
        ),
        row=2, col=1
    )

    title_text = (
        f"<b>Workflow {workflow_id} — Stage {stage} {title_metric}</b><br>"
        f"<span style='font-size:16px'>"
        f"{len(df_sel)} jobs (exit = 0, cpu>0, finished) • commit {commit}"
        f"</span>"
    )

    fig.update_layout(
        title=dict(text=title_text, x=0.5, xanchor="center", font=dict(size=24)),
        width=1200, height=800,
        margin=dict(t=120, l=70, r=70, b=50),
    )
    fig.update_xaxes(title_text=x_label, row=1, col=1)

    return fig

def write_html_report(figs, outfile="report.html", title="justIN job performance report"):
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>{title}</title>",
        "<style>",
        "body { font-family: sans-serif; }",
        "h1 { text-align: center; margin-bottom: 30px; font-size: 32px;  }",
        "</style>",
        "</head><body>",
        f"<h1>{title}</h1>",
    ]
    # include plotly.js only once
    first = True
    for fig in figs:
        parts.append(pio.to_html(fig, full_html=False, include_plotlyjs="cdn" if first else False))
        first = False

    parts.append("</body></html>")
    Path(outfile).write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {outfile}")

workflow_id = 12080
stage = 3
commit = get_git_commit_hash()

mask = (
    df["jobState"].str.contains("finished", case=False, na=False)
    & (df["exit"] == 0)
    & (df["stageID"] == stage)
    & (df["cpu_s"] > 0)
)
df_sel = df.loc[mask].copy()

fig_cpu  = make_time_figure_with_table(df_sel, workflow_id, stage, commit,
                                       value_col="cpu_s", title_metric="CPU time", x_label="CPU time (s)")
fig_wall = make_time_figure_with_table(df_sel, workflow_id, stage, commit,
                                       value_col="wall_s", title_metric="Wall time", x_label="Wall time (s)")
write_html_report(
    [fig_cpu, fig_wall],
    outfile=f"workflow{workflow_id}_stage{stage}_report.html",
    title=f"Workflow {workflow_id} — Stage {stage} performance report"
)
## Which stage?
#workflow_id = 12080
#stage = 3
#n_jobs = len(df_sel)
#
## Selection mask
#mask = (
#    df["jobState"].str.contains("finished", case=False, na=False)
#    & (df["exit"] == 0)
#    & (df["stageID"] == stage)
#    & (df["cpu_s"] > 0)
#)
#
#df_sel = df.loc[mask].copy()
#
#fig = make_subplots(
#    rows=2,
#    cols=2,
#    subplot_titles=("CPU time per job", "Wall-clock time per job","Max RSS bytes",""),
#    specs=[[{"secondary_y": True}, {"secondary_y": True}], [{"secondary_y": True}, {"secondary_y": True}]],
#)
#
#x = df_sel["cpu_s"].dropna().astype(float).to_numpy()
#plot_hist_with_cdf(fig, 1, 1, x, int(np.sqrt(len(x))), name="Time", xlabel="CPU time (s)")
#
#x = df_sel["wall_s"].dropna().astype(float).to_numpy()
#plot_hist_with_cdf(fig, 1, 2, x, int(np.sqrt(len(x))), name="Time", xlabel="Wall time (s)")
#
#x = df_sel["maxrss_bytes"].dropna().astype(float).to_numpy()
#plot_hist_with_cdf(fig, 2, 1, x, int(np.sqrt(len(x))), name="Bytes", xlabel="Max RSS (bytes)")
#
#title_text = (
#    f"Workflow {workflow_id} — Stage {stage} CPU time<br>"
#    f"<span style='font-size:16px'>"
#    f"{n_jobs} jobs, 50 events/job (exit = 0, CPU>0, finished)</span>"
#)
#fig.update_layout(
#    title=dict(
#        text=title_text,
#        x=0.5,               # center horizontally
#        xanchor="center",
#        yanchor="top",
#        font=dict(
#            size=24,         # main title size
#        ),
#    ),
#    margin=dict(t=130),
#    width=1200,
#    height=800,
#)
#fig.show()
#