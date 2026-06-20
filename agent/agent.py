import os
import json
from groq import Groq
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from agent.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS, handle_missing_values

console = Console()

# groq uses the same tool-use pattern as anthropic but with a slightly different
# message format -- we handle that in the loop below
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# convert our tool definitions to the format groq expects
# groq follows the OpenAI tool spec so the structure is slightly different
def _to_groq_tools(tool_definitions: list) -> list:
    groq_tools = []
    for tool in tool_definitions:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            }
        })
    return groq_tools


def run_agent(df, profile: dict):

    # initialize results first so it's available everywhere in this function
    # this was the bug -- results was being referenced before it was defined
    results = {}

    console.print(Panel.fit(
        "[bold cyan]SmartData Agent[/bold cyan] — starting analysis",
        border_style="cyan"
    ))

    # step 1: handle missing values before any analysis runs
    console.print("\n[bold yellow]handling missing values...[/bold yellow]")
    df, missing_report = handle_missing_values(df)
    results["_missing_report"] = missing_report

    if missing_report:
        _print_missing_report(missing_report)
    else:
        console.print("[green]no missing values found -- data is clean[/green]")

    # step 2: build the message for groq
    # we pass the schema so the model understands the data without seeing raw rows
    system_prompt = """you are a data analysis agent. you receive a schema profile of a dataset 
and decide which analysis tools to run based on what would be most insightful.

always run summary_stats first. then look at the schema and decide:
- if there are datetime columns, run plot_time_series
- if there are 2+ numeric columns, run plot_correlation_heatmap
- always run plot_distributions and detect_outliers for numeric data
- if there were missing values in the original data, run plot_missing_heatmap

be selective -- only call tools that make sense for this specific dataset.
after all tools have run, give a short plain-english summary of the key findings."""

    user_message = f"""here is the dataset profile:

shape: {profile['shape']['rows']} rows, {profile['shape']['columns']} columns
duplicate rows found: {profile['duplicate_rows']}
total missing values (before cleaning): {profile['total_missing']}

columns:
{json.dumps(profile['columns'], indent=2)}

based on this, decide which analysis tools to run and call them."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    groq_tools = _to_groq_tools(TOOL_DEFINITIONS)

    console.print("\n[bold yellow]agent is deciding which analyses to run...[/bold yellow]\n")

    # step 3: agentic loop -- keep calling groq until it stops using tools
    # groq returns tool calls in response.choices[0].message.tool_calls
    while True:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=groq_tools,
            tool_choice="auto",
            max_tokens=4096,
        )

        response_message = response.choices[0].message

        # add the assistant response to message history
        messages.append({
            "role": "assistant",
            "content": response_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in (response_message.tool_calls or [])
            ] or None,
        })

        # if no tool calls, the model is done -- generate written summary and break
        if not response_message.tool_calls:
            final_text = response_message.content
            if final_text:
                console.print(Panel(
                    final_text,
                    title="[bold green]agent summary[/bold green]",
                    border_style="green"
                ))
            break

        # step 4: execute each tool the model requested
        for tool_call in response_message.tool_calls:
            tool_name = tool_call.function.name
            console.print(f"[cyan]→ running:[/cyan] [bold]{tool_name}[/bold]")
            # skip if this tool already ran -- groq sometimes calls the same tool twice
            if tool_name in results:
                console.print(f"[dim]  skipping {tool_name} -- already ran[/dim]")
                output = results[tool_name]
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(output, default=str),
                })
                continue
            tool_fn = TOOL_FUNCTIONS.get(tool_name)
            if tool_fn is None:
                output = f"tool '{tool_name}' not found"
                console.print(f"[red]  tool not found: {tool_name}[/red]")
            else:
                try:
                    output = tool_fn(df)
                    results[tool_name] = output
                    console.print(f"[green]  done[/green]")
                except Exception as e:
                    # catch per-tool so one failure doesn't stop everything
                    output = f"error running {tool_name}: {str(e)}"
                    console.print(f"[red]  error: {e}[/red]")

            # feed the tool result back so the model can continue reasoning
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(output, default=str),
            })

    # step 5: generate written summary using groq
    # this is what appears in the streamlit summary card before the download button
    console.print("\n[bold yellow]generating written summary...[/bold yellow]")
    summary = _generate_summary(profile, missing_report, results)
    results["_written_summary"] = summary

    # step 6: save markdown report
    _save_markdown_report(profile, missing_report, results)

    console.print("\n[bold green]analysis complete.[/bold green] check the [cyan]output/[/cyan] folder for plots and the report.\n")

    return results


# generates a proper written paragraph summary of all findings
# called after all tools have run so it has full context to work with
def _generate_summary(profile: dict, missing_report: dict, results: dict) -> str:
    context = f"""you analyzed a dataset with {profile['shape']['rows']} rows and {profile['shape']['columns']} columns.

missing value handling:
{json.dumps(missing_report, indent=2)}

summary statistics:
{json.dumps(results.get('summary_stats', {}), indent=2, default=str)}

outlier detection:
{json.dumps(results.get('detect_outliers', {}), indent=2, default=str)}

tools that ran: {', '.join([k for k in results.keys() if not k.startswith('_')])}
"""

    try:
        summary_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = summary_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """you are a friendly data analyst writing a summary for a non-technical audience.
write 3-4 short paragraphs in plain english about what the data shows.
be specific -- mention actual numbers, column names, and real findings.
do not use bullet points. write in flowing prose like a real analyst report.
start with what the dataset contains, then talk about data quality, then key findings."""
                },
                {
                    "role": "user",
                    "content": f"write a summary of this analysis:\n\n{context}"
                }
            ],
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        # if summary generation fails, return a basic fallback so the app doesn't crash
        return f"Analysis complete. {len([k for k in results.keys() if not k.startswith('_')])} tools were run on a dataset with {profile['shape']['rows']} rows and {profile['shape']['columns']} columns."


def _print_missing_report(report: dict):
    table = Table(title="missing value handling", box=box.SIMPLE, show_header=True)
    table.add_column("column", style="cyan", no_wrap=True)
    table.add_column("action taken", style="white")

    for col, action in report.items():
        table.add_row(col, action)

    console.print(table)


def _save_markdown_report(profile: dict, missing_report: dict, results: dict):
    lines = []
    lines.append("# SmartData Agent — Analysis Report\n")
    lines.append(f"**Dataset shape:** {profile['shape']['rows']} rows × {profile['shape']['columns']} columns\n")
    lines.append(f"**Duplicate rows:** {profile['duplicate_rows']}\n")
    lines.append(f"**Missing values (before cleaning):** {profile['total_missing']}\n")

    if missing_report:
        lines.append("\n## Missing Value Handling\n")
        for col, action in missing_report.items():
            lines.append(f"- `{col}`: {action}")

    if "_written_summary" in results:
        lines.append("\n## Summary\n")
        lines.append(results["_written_summary"])

    if "summary_stats" in results and isinstance(results["summary_stats"], dict):
        lines.append("\n## Summary Statistics\n")
        for col, stats in results["summary_stats"].items():
            if isinstance(stats, dict):
                lines.append(f"### {col}")
                for stat, val in stats.items():
                    lines.append(f"- {stat}: {val}")

    if "detect_outliers" in results and isinstance(results["detect_outliers"], dict):
        lines.append("\n## Outlier Detection\n")
        for col, info in results["detect_outliers"].items():
            if isinstance(info, dict) and info.get("likely_has_outliers"):
                lines.append(f"- `{col}` likely has outliers (IQR: {info['iqr_outliers']}, Z-score: {info['zscore_outliers']})")

    lines.append("\n## Plots Generated\n")
    for tool_name, output in results.items():
        if isinstance(output, str) and output.endswith(".png"):
            lines.append(f"- {output}")
        elif isinstance(output, list):
            for item in output:
                if isinstance(item, str) and item.endswith(".png"):
                    lines.append(f"- {item}")

    report_path = "output/report.md"
    os.makedirs("output", exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    console.print(f"[dim]report saved → {report_path}[/dim]")