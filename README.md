
## Live Demo
https://smartdata-agent-8kffv9i6exu84v3wztzofa.streamlit.app/

# SmartData Agent

An agentic AI pipeline that autonomously cleans, analyzes, and explains any CSV or JSON dataset. Drop in your data and the agent figures out what to do with it.

Built with Python, Groq (LLaMA 3.3 70B), and Streamlit.

---

## What it does

Most data analysis tools make you tell them what to run. SmartData Agent reasons about your dataset first, then decides which analyses actually make sense for it.

1. **Ingests** your CSV or JSON file and profiles the schema
2. **Cleans** missing values column by column — drops, imputes, or flags based on data type and severity
3. **Sends the schema** to LLaMA 3.3 via Groq, which decides which analysis tools to call
4. **Runs the tools** — stats, distributions, correlation heatmap, outlier detection, time series
5. **Writes a plain-english summary** of what it found
6. **Saves** all plots and a markdown report to the `output/` folder
7. **Lets you chat with your data** after analysis — ask questions like "which column has the most outliers?" and get answers grounded in the actual analysis results

---

## Project structure

```
smartdata-agent/
├── agent/
│   ├── agent.py          # core agentic loop — calls Groq, executes tools
│   └── tools.py          # analysis functions + missing value handler
├── utils/
│   └── file_parser.py    # file loading, schema profiling, type casting
├── app.py                # terminal interface (rich UI)
├── streamlit_app.py      # web interface (localhost:8501)
├── requirements.txt
└── .env                  # your API keys (not committed)
```

---

## Quickstart

**1. Clone and set up a virtual environment**

```bash
git clone https://github.com/techierabina/smartdata-agent.git
cd smartdata-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Add your Groq API key**

Create a `.env` file in the project root:

```
GROQ_API_KEY=gsk_your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com) — you don't need credit card.

**3. Run it**

Terminal version:
```bash
python app.py data/yourfile.csv
```

Web version:
```bash
streamlit run streamlit_app.py
```

---

## How the agent works

The agent doesn't hardcode which analyses to run. It sends the dataset schema — column names, types, missing value counts, sample values — to LLaMA 3.3 and lets the model reason about what's useful.

```
schema profile → Groq (LLaMA 3.3) → tool calls → results → written summary → chat
```

For example, on the Titanic dataset the agent:
- Dropped `cabin` (77% missing)
- Filled `age` with median (177 missing values)
- Filled `embarked` with mode (2 missing values)
- Ran summary stats, distribution plots, outlier detection, and correlation heatmap
- Skipped time series (no datetime column)
- Wrote a paragraph summary of the key findings
- Answered follow-up questions like "is this dataset ready to train a model on?"

---

## Missing value strategy

Each column gets handled individually based on what makes sense for that data type:

| Condition | Strategy |
|---|---|
| More than 50% missing | Drop the column |
| Numeric column | Fill with median (robust to outliers) |
| Categorical / text column | Fill with mode (most frequent value) |
| Datetime column | Forward fill |
| Low % missing, unclear type | Add a `colname_is_null` flag column |
| All unique values (ID column) | Skip — imputing IDs makes no sense |

---

## Analysis tools

| Tool | What it does |
|---|---|
| `summary_stats` | Mean, median, std, min, max, skewness per numeric column |
| `plot_distributions` | Histogram + KDE for each numeric column |
| `plot_correlation_heatmap` | Pearson correlation matrix across all numeric columns |
| `detect_outliers` | IQR and Z-score outlier counts per column |
| `plot_time_series` | Numeric values over time (auto-detects datetime columns) |
| `plot_missing_heatmap` | Visual map of where missing values are across the dataset |
| `chat_with_data` | Ask plain-english questions and get answers grounded in the actual analysis results |

---

## Output

Every run produces:

- `output/dist_*.png` — distribution plots per column
- `output/correlation_heatmap.png` — correlation matrix
- `output/report.md` — full markdown report with stats, findings, and written summary

---

## Tech stack

- **Python 3.11+**
- **Groq API** — LLaMA 3.3 70B for agentic reasoning and chat
- **Pandas + NumPy** — Data manipulation
- **Matplotlib + Seaborn + SciPy** — Visualization
- **Rich** — Terminal UI
- **Streamlit** — Web interface

---

## Requirements

```
pandas>=2.0.0
numpy>=1.26.0
matplotlib>=3.8.0
seaborn>=0.13.0
rich>=13.0.0
python-dotenv>=1.0.0
groq
scipy>=1.11.0
streamlit
```

---

## Author

**Rabina Karki**
MS Data Science · University of Central Oklahoma
[LinkedIn](https://linkedin.com/in/rabina-karki-0a7546344) · [GitHub](https://github.com/techierabina) · [HuggingFace](https://huggingface.co/rabinaa)
