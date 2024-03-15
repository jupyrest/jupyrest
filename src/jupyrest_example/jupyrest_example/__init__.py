from pathlib import Path
from datetime import date
from typing import Union, Dict, List
import pandas as pd
from jupyrest.nbschema import NotebookSchemaProcessor, ModelCollection, NbSchemaBase
from jupyrest.plugin import JupyrestPlugin
from jupyrest.resolvers import LocalDirectoryResolver
from jupyrest.executors import IPythonNotebookExecutor

from pydantic import BaseModel, Extra


notebooks_dir = Path(__file__).parent / "notebooks"

class Portfolio(NbSchemaBase):
    start_date: date
    end_date: date
    holdings: Dict[str, float]

    class Config:
        extra = Extra.forbid

class GCloudServer(NbSchemaBase):
    project_id: str
    zone: str
    instance_name: str

    def run_ssh_command(self, command: str):
        print(f"Running ssh command {command} on server {repr(self)}")

class SSHCommand(NbSchemaBase):
    command: str

    @classmethod
    def from_gloud_instance(self, gcloud_instance: GCloudServer, command: str):
        return SSHCommand(
            command=f"gcloud compute ssh {gcloud_instance.instance_name} --project {gcloud_instance.project_id} --zone {gcloud_instance.zone} --command '{command}'"
        )

mc = ModelCollection()
mc.add_model(alias="portfolio", model_type=Portfolio)
mc.add_model(alias="ssh_command", model_type=SSHCommand)
mc.add_model(alias="gcloud_server", model_type=GCloudServer)
def load_data(portfolio: Dict[str, float], start_date: date, end_date: date):
    fp = str(notebooks_dir / "portfolio_analysis" / "stock_data" / "stock_data.csv")
    df = pd.read_csv(fp)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(by="Date").set_index("Date")
    return df[list(portfolio.keys())][start_date:end_date], list(portfolio.values())


def load_data_from_object(portfolio: Portfolio):
    return load_data(portfolio.holdings, portfolio.start_date, portfolio.end_date)

def analyze_cpu_on_node(gcloud_server: GCloudServer):
    import random
    import matplotlib.pyplot as plt

    # Simulate CPU consumption data for processes
    processes = ["Apache", "MySQL", "Nginx", "Node.js", "Tomcat"]
    cpu_usage = {"Apache": [], "MySQL": [], "Nginx": [], "Node.js": [], "Tomcat": []}

    # Simulate CPU usage for 24 hours (in 5-minute intervals)
    for hour in range(24):
        for minute in range(12):
            for process in processes:
                if process == "Apache":
                    # Simulate higher CPU usage for Apache process
                    cpu_percent = random.uniform(20, 90)
                else:
                    cpu_percent = random.uniform(1, 20)
                cpu_usage[process].append(cpu_percent)

    # Plotting the simulated CPU usage data
    time_intervals = [f"{hour:02d}:{minute*5:02d}" for hour in range(24) for minute in range(12)]

    plt.figure(figsize=(12, 6))
    for process in processes:
        plt.plot(time_intervals, cpu_usage[process], label=process)

    plt.xlabel("Time (HH:MM)")
    plt.ylabel("CPU Usage (%)")
    plt.title(f"Process CPU Consumption")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()

def find_process_hogging_cpu(gcloud_server: GCloudServer):
    return 821, "apache2"

plugin = JupyrestPlugin(
    resolver=LocalDirectoryResolver(notebooks_dir=notebooks_dir),
    nbschema=NotebookSchemaProcessor(models=mc),
    executor=IPythonNotebookExecutor(),
)