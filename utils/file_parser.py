import pandas as pd
import json
import os


# this function is the entry point for loading any file the user passes in
# right now we support CSV and JSON -- can add Excel later if needed
def load_file(filepath: str) -> pd.DataFrame:
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"couldn't find the file at: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        df = _load_csv(filepath)
    elif ext == ".json":
        df = _load_json(filepath)
    else:
        raise ValueError(f"unsupported file type '{ext}' -- please use CSV or JSON")

    print(f"loaded {len(df)} rows and {len(df.columns)} columns from '{os.path.basename(filepath)}'")
    return df


# CSV loading is straightforward but we try a different encodings
# because files exported from Excel or Google Sheets sometimes break with utf-8
def _load_csv(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(filepath, encoding="utf-8")
    except UnicodeDecodeError:
        # fall back to latin-1 which handles most special characters from Excel exports
        print("utf-8 failed, retrying with latin-1 encoding...")
        df = pd.read_csv(filepath, encoding="latin-1")
    
    return df


# JSON can come in two shapes -- a list of records or a nested dict
# we handle both so the user doesn't have to worry about format
def _load_json(filepath: str) -> pd.DataFrame:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        # most common case -- list of dicts like [{"col": val}, ...]
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        # sometimes APIs return {"data": [...]} or similar wrapper
        # we try to find the first key that holds a list
        list_key = next((k for k, v in data.items() if isinstance(v, list)), None)
        if list_key:
            print(f"found records under key '{list_key}', using that")
            df = pd.DataFrame(data[list_key])
        else:
            # last resort -- just normalize the whole thing
            df = pd.json_normalize(data)
    else:
        raise ValueError("JSON structure not recognized -- expected a list or dict at the top level")

    return df


# after loading we want a quick snapshot of the data before anything else runs
# this gets passed to the agent so it knows what it's working with
def get_schema_profile(df: pd.DataFrame) -> dict:
    
    profile = {
        "shape": {"rows": df.shape[0], "columns": df.shape[1]},
        "columns": {},
        "total_missing": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }

    for col in df.columns:
        missing_count = int(df[col].isnull().sum())
        missing_pct = round((missing_count / len(df)) * 100, 2)

        profile["columns"][col] = {
            "dtype": str(df[col].dtype),
            "missing_count": missing_count,
            "missing_pct": missing_pct,
            "unique_values": int(df[col].nunique()),
            # sample helps the agent understand what kind of data is in this column
            "sample": df[col].dropna().head(3).tolist(),
        }

    return profile


# cleans up column names so they're consistent and easy to work with
# things like "First Name" become "first_name", "  AGE  " becomes "age"
def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace(r"[^\w]", "_", regex=True)  # replace anything that's not alphanumeric or underscore
    )
    return df


# pandas reads almost everything as strings by default
# this goes through each column and fixes that where it can
def cast_column_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in df.columns:
        # skip columns that are already numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            continue

        # try parsing as number first
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() > 0.8 * len(df):
            # more than 80% converted successfully, treat it as numeric
            df[col] = converted
            continue

        # try parsing as datetime -- useful for time series detection later
        try:
            converted_dates = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            if converted_dates.notna().sum() > 0.8 * len(df):
                df[col] = converted_dates
                continue
        except Exception:
            pass

        # if a column has very few unique values relative to total rows, it's probably categorical
        if df[col].nunique() / len(df) < 0.05:
            df[col] = df[col].astype("category")

    return df


# this is the main function that runs the full ingestion pipeline
# load → clean names → cast types → profile
# returns both the cleaned dataframe and the schema so the agent has full context
def ingest(filepath: str) -> tuple[pd.DataFrame, dict]:
    df = load_file(filepath)
    df = clean_column_names(df)
    df = cast_column_types(df)
    profile = get_schema_profile(df)
    return df, profile