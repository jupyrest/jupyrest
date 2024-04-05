from pathlib import Path
from datetime import date
from typing import Union, Dict, List
from fastapi import dependencies
import pandas as pd
from jupyrest.nbschema import NotebookSchemaProcessor, ModelCollection, NbSchemaBase
from jupyrest.dependencies import Dependencies
from pydantic import Extra


notebooks_dir = Path(__file__).parent / "notebooks"

class Portfolio(NbSchemaBase):
    start_date: date
    end_date: date
    holdings: Dict[str, float]

    class Config:
        extra = Extra.forbid

def load_data(portfolio: Dict[str, float], start_date: date, end_date: date):
    fp = str(notebooks_dir / "portfolio_analysis" / "stock_data" / "stock_data.csv")
    df = pd.read_csv(fp)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(by="Date").set_index("Date")
    return df[list(portfolio.keys())][start_date:end_date], list(portfolio.values())


def load_data_from_object(portfolio: Portfolio):
    return load_data(portfolio.holdings, portfolio.start_date, portfolio.end_date)

dependencies = Dependencies(notebooks_dir=notebooks_dir, models={
    "portfolio": Portfolio,
})