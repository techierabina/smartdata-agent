import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os


# all plots get saved here -- we create it if it doesn't exist yet
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# helper to save and close plots cleanly
# calling plt.close() after every plot is important otherwise
# matplotlib stacks figures in memory and things get slow
def _save_plot(filename: str) -> str:
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"saved plot → {filepath}")
    return filepath


# ─────────────────────────────────────────────
# MISSING VALUE HANDLING
# ─────────────────────────────────────────────

# this is the brain of the cleaning step
# instead of blindly filling everything the same way,
# we look at each column individually and decide the best strategy
def handle_missing_values(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    report = {}  # we'll track what we did to each column so the agent can explain it

    for col in df.columns:
        missing_count = df[col].isnull().sum()

        # nothing to do here
        if missing_count == 0:
            continue

        missing_pct = missing_count / len(df)

        # case 1: more than 50% missing -- not worth keeping, just drop the column
        if missing_pct > 0.5:
            df.drop(columns=[col], inplace=True)
            report[col] = f"dropped (>{round(missing_pct*100)}% missing)"
            continue

        # case 2: datetime columns -- forward fill makes the most sense
        # because the previous timestamp is usually the best guess
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].ffill()
            report[col] = f"forward filled ({missing_count} values)"
            continue

        # case 3: numeric columns -- use median instead of mean
        # median is more robust when there are outliers pulling the mean around
        if pd.api.types.is_numeric_dtype(df[col]):
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            report[col] = f"filled with median ({median_val:.2f}), {missing_count} values"
            continue

        # case 4: categorical or text columns -- use mode (most frequent value)
        if hasattr(df[col], 'cat') or df[col].dtype == object:
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])
                report[col] = f"filled with mode ('{mode_val[0]}'), {missing_count} values"
            else:
                # edge case: no mode found, just flag it
                df[f"{col}_is_null"] = df[col].isnull().astype(int)
                report[col] = f"flagged with '{col}_is_null' column (no mode found)"
            continue

        # case 5: anything else with low missing % -- just flag it and move on
        # we don't want to make assumptions about columns we can't identify
        if missing_pct <= 0.05:
            df[f"{col}_is_null"] = df[col].isnull().astype(int)
            report[col] = f"flagged with '{col}_is_null' column ({missing_count} values, low %)"

    return df, report


# ─────────────────────────────────────────────
# ANALYSIS TOOLS
# these are the functions the Claude agent will call based on the data
# ─────────────────────────────────────────────

# basic descriptive stats -- always the first thing you want to know about a dataset
def summary_stats(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not numeric_cols:
        return {"message": "no numeric columns found in this dataset"}

    stats = {}
    for col in numeric_cols:
        stats[col] = {
            "mean": round(df[col].mean(), 4),
            "median": round(df[col].median(), 4),
            "std": round(df[col].std(), 4),
            "min": round(df[col].min(), 4),
            "max": round(df[col].max(), 4),
            # skewness tells us if the data leans left or right
            # anything above 1 or below -1 is worth flagging
            "skewness": round(df[col].skew(), 4),
        }

    return stats


# distribution plots help us see the shape of each numeric column
# we plot histogram + KDE overlay so both count and density are visible
def plot_distributions(df: pd.DataFrame) -> list[str]:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    saved_files = []

    if not numeric_cols:
        print("no numeric columns to plot distributions for")
        return saved_files

    for col in numeric_cols:
        fig, ax = plt.subplots(figsize=(7, 4))

        # KDE=True gives us the smooth density curve on top of the histogram
        df[col].dropna().plot(kind="hist", bins=30, edgecolor="white",
                               color="#5c8dd6", alpha=0.85, density=True, ax=ax)
        df[col].dropna().plot(kind="kde", color="#e05c5c", linewidth=2, ax=ax)

        ax.set_title(f"distribution of '{col}'", fontsize=13)
        ax.set_xlabel(col)
        ax.set_ylabel("density")
        ax.spines[["top", "right"]].set_visible(False)

        saved_files.append(_save_plot(f"dist_{col}.png"))

    return saved_files


# correlation heatmap -- great for spotting which features move together
# this is especially useful before running any ML model
def plot_correlation_heatmap(df: pd.DataFrame) -> str | None:
    numeric_df = df.select_dtypes(include=[np.number])

    if numeric_df.shape[1] < 2:
        print("need at least 2 numeric columns for a correlation heatmap")
        return None

    corr = numeric_df.corr()

    fig, ax = plt.subplots(figsize=(max(6, len(corr.columns)), max(5, len(corr.columns) - 1)))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",      # red = positive correlation, blue = negative
        center=0,
        square=True,
        linewidths=0.5,
        ax=ax,
        cbar_kws={"shrink": 0.8}
    )
    ax.set_title("correlation matrix", fontsize=13)
    plt.xticks(rotation=45, ha="right")

    return _save_plot("correlation_heatmap.png")


# outlier detection using both IQR and Z-score
# IQR is better for skewed data, Z-score for roughly normal distributions
# we run both and report which rows are flagged by either
def detect_outliers(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    outlier_report = {}

    for col in numeric_cols:
        col_data = df[col].dropna()

        # IQR method
        Q1 = col_data.quantile(0.25)
        Q3 = col_data.quantile(0.75)
        IQR = Q3 - Q1
        iqr_outliers = ((df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)).sum()

        # Z-score method -- flag anything beyond 3 standard deviations
        z_scores = np.abs((df[col] - col_data.mean()) / col_data.std())
        z_outliers = (z_scores > 3).sum()

        outlier_report[col] = {
            "iqr_outliers": int(iqr_outliers),
            "zscore_outliers": int(z_outliers),
            # if both methods agree a column has outliers, it's definitely worth investigating
            "likely_has_outliers": iqr_outliers > 0 and z_outliers > 0,
        }

    return outlier_report


# time series plot -- only runs if we detect a datetime column
# we plot all numeric columns over time on the same chart
def plot_time_series(df: pd.DataFrame) -> str | None:
    date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not date_cols:
        print("no datetime column detected -- skipping time series plot")
        return None

    if not numeric_cols:
        print("no numeric columns to plot over time")
        return None

    # use the first datetime column we find as the x axis
    date_col = date_cols[0]
    df_sorted = df.sort_values(date_col)

    fig, ax = plt.subplots(figsize=(10, 5))

    for col in numeric_cols:
        ax.plot(df_sorted[date_col], df_sorted[col], label=col, linewidth=1.5)

    ax.set_title(f"time series over '{date_col}'", fontsize=13)
    ax.set_xlabel(date_col)
    ax.set_ylabel("value")
    ax.legend(loc="upper left", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    plt.xticks(rotation=30)

    return _save_plot("time_series.png")


# missing data heatmap -- visualizes where the gaps are across the whole dataset
# rows on y-axis, columns on x-axis, white = missing, colored = present
def plot_missing_heatmap(df: pd.DataFrame) -> str | None:
    if df.isnull().sum().sum() == 0:
        print("no missing values found -- skipping missing data heatmap")
        return None

    fig, ax = plt.subplots(figsize=(max(8, len(df.columns)), 5))
    sns.heatmap(
        df.isnull(),
        cbar=False,
        cmap="viridis",   # yellow = missing, purple = present
        ax=ax,
        yticklabels=False  # row labels get cluttered with large datasets
    )
    ax.set_title("missing value map (yellow = missing)", fontsize=13)
    plt.xticks(rotation=45, ha="right")

    return _save_plot("missing_heatmap.png")


# ─────────────────────────────────────────────
# TOOL DEFINITIONS FOR THE CLAUDE AGENT
# this is what gets passed to the API so Claude knows what tools exist
# and what arguments each one takes
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "summary_stats",
        "description": "computes descriptive statistics (mean, median, std, min, max, skewness) for all numeric columns",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "plot_distributions",
        "description": "plots histogram + KDE distribution for each numeric column and saves to output folder",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "plot_correlation_heatmap",
        "description": "generates a correlation heatmap for all numeric columns -- useful for feature relationship analysis",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "detect_outliers",
        "description": "detects outliers in numeric columns using both IQR and Z-score methods",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "plot_time_series",
        "description": "plots numeric columns over time -- only runs if a datetime column exists in the dataset",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "plot_missing_heatmap",
        "description": "visualizes where missing values are across the dataset as a heatmap",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]


# maps tool name strings (what the agent returns) to the actual functions above
# agent.py uses this to call the right function based on Claude's decision
TOOL_FUNCTIONS = {
    "summary_stats": summary_stats,
    "plot_distributions": plot_distributions,
    "plot_correlation_heatmap": plot_correlation_heatmap,
    "detect_outliers": detect_outliers,
    "plot_time_series": plot_time_series,
    "plot_missing_heatmap": plot_missing_heatmap,
}