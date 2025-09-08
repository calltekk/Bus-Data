import os
import pandas as pd
from sqlalchemy import create_engine

DB_PATH = os.getenv("DB_PATH", "bus_demo.sqlite")

_engine = None
def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
    return _engine

def upsert_df(df: pd.DataFrame, table: str, key_cols: list):
    """
    Simple upsert: replace on conflict by dropping duplicates on key_cols.
    """
    if df.empty: 
        return
    df = df.drop_duplicates(subset=key_cols)
    df.to_sql(table, engine(), if_exists="append", index=False)

def read_table(table: str) -> pd.DataFrame:
    try:
        return pd.read_sql_table(table, engine())
    except Exception:
        return pd.DataFrame()
