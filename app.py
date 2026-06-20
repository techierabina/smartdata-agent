import os
import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich import box
from rich.rule import Rule

# load the .env file so ANTHROPIC_API_KEY is available before anything else runs
load_dotenv()

from utils.file_parser import ingest
from agent.agent import run_agent

console = Console()


# ── little helpers for the lilac / fun color theme ──────────────────────────

LILAC       = "bold #c084fc"
SOFT_PINK   = "bold #f0abfc"
LAVENDER    = "#e9d5ff"
MINT        = "bold #86efac"
PEACH       = "bold #fdba74"
WHITE       = "bold #f5f3ff"
DIM         = "#a78bfa"


def banner():
    # big welcome banner -- sets the vibe right away
    console.print()
    console.print(Panel.fit(
        Text.assemble(
            ("✦  ", SOFT_PINK),
            ("Smart", LILAC),
            ("Data", SOFT_PINK),
            (" Agent", LILAC),
            ("  ✦\n", SOFT_PINK),
            ("  your data, analyzed automagically  ", LAVENDER),
        ),
        border_style="#c084fc",
        box=box.DOUBLE,
        padding=(1, 4),
    ))
    console.print()


def divider(label: str = ""):
    console.print(Rule(f"[{DIM}]{label}[/{DIM}]", style="#c084fc"))


def step(icon: str, message: str):
    console.print(f"  [{SOFT_PINK}]{icon}[/{SOFT_PINK}]  [{LAVENDER}]{message}[/{LAVENDER}]")


def success(message: str):
    console.print(f"\n  [{MINT}]✔  {message}[/{MINT}]")


def error(message: str):
    console.print(f"\n  [bold red]✘  {message}[/bold red]")


def info(label: str, value: str):
    console.print(f"  [{DIM}]{label}:[/{DIM}]  [{WHITE}]{value}[/{WHITE}]")


# ────────────────────────────────────────────────────────────────────────────


def check_api_key():
    # make sure the key exists before we go any further
    # nothing worse than running the whole pipeline and failing at the API call
    key = os.getenv("GROQ_API_KEY")
    if not key:
        error("ANTHROPIC_API_KEY not found!")
        console.print(f"  [{LAVENDER}]add it to your .env file like this:[/{LAVENDER}]")
        console.print(f"  [{DIM}]ANTHROPIC_API_KEY=sk-ant-...[/{DIM}]\n")
        sys.exit(1)
    success("API key found")


def parse_args():
    parser = argparse.ArgumentParser(
        description="SmartData Agent -- drop in a CSV or JSON and let the agent do the rest",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "filepath",
        type=str,
        help="path to your CSV or JSON file\nexample: python app.py data/sales.csv",
    )
    return parser.parse_args()


def main():
    banner()

    # ── step 1: check setup ──────────────────────────────────────────────────
    divider("setting up")
    check_api_key()

    args = parse_args()
    filepath = args.filepath

    if not os.path.exists(filepath):
        error(f"file not found: {filepath}")
        sys.exit(1)

    info("file", filepath)

    # ── step 2: load and profile the data ───────────────────────────────────
    console.print()
    divider("loading your data")

    try:
        step("📂", "reading file and profiling schema...")
        df, profile = ingest(filepath)
    except Exception as e:
        error(f"failed to load file: {e}")
        sys.exit(1)

    console.print()
    info("rows", str(profile["shape"]["rows"]))
    info("columns", str(profile["shape"]["columns"]))
    info("missing values", str(profile["total_missing"]))
    info("duplicate rows", str(profile["duplicate_rows"]))

    # show column names so the user can see what was loaded
    col_names = ", ".join(profile["columns"].keys())
    console.print(f"\n  [{DIM}]columns:[/{DIM}]  [{LAVENDER}]{col_names}[/{LAVENDER}]")

    success("data loaded and profiled!")

    # ── step 3: run the agent ────────────────────────────────────────────────
    console.print()
    divider("running agent")
    step("🤖", "sending schema to Claude and letting it decide what to analyze...")
    console.print()

    try:
        results = run_agent(df, profile)
    except Exception as e:
        error(f"agent crashed: {e}")
        sys.exit(1)

    # ── step 4: wrap up ──────────────────────────────────────────────────────
    console.print()
    divider("all done!")

    tools_run = list(results.keys())
    console.print(f"\n  [{DIM}]tools run:[/{DIM}]  [{LAVENDER}]{', '.join(tools_run)}[/{LAVENDER}]")

    console.print()
    console.print(Panel.fit(
        Text.assemble(
            ("✦  ", SOFT_PINK),
            ("check the ", LAVENDER),
            ("output/", LILAC),
            (" folder for your plots + report  ", LAVENDER),
            ("✦", SOFT_PINK),
        ),
        border_style="#c084fc",
        box=box.ROUNDED,
        padding=(0, 3),
    ))
    console.print()


if __name__ == "__main__":
    main()