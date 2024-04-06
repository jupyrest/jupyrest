# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: 'Python 3.7.9 64-bit (''.venv'': venv)'
#     name: pythonjvsc74a57bd0a708b0063305b1a0371e06883581be78f0942506af7d5c9c88057c24472325e0
# ---

# %% tags=["parameters"]
from jupyrest.nbschema import NbSchemaBase
import datetime
import json

class Incident(NbSchemaBase):
    start_time: datetime.datetime
    end_time: datetime.datetime
    title: str


# %%
new_incident_1 = incidents[0]
new_incident_2 = incidents[1]
bar = foo

new_incidents = {
    'new_incident_1': new_incident_1,
    'new_incident_2': new_incident_2
}

obj = {
    "new_incidents": new_incidents,
    "bar": bar
}

from jupyrest import save_output
save_output(obj)
