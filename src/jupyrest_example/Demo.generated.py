# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Getting Started With Jupyrest
#
#
# Jupyrest is a library that converts __Jupyter Notebooks__ into __REST APIs__. It turns notebooks into *notebook functions*.
#
# This guide will demonstrate how to interact with a notebook function and other nice features that Jupyrest provides.
#
# ## Starting the Web Server
#
# See the `start_http.py` file in this directory for an example of how to configure a Jupyrest application and start the web server.
#
# ## Initializing a Jupyrest Client
#
# The `JupyrestClient` is a handy wrapper over the Jupyrest HTTP API. The HTTP API OpenAPI spec can be found at the `/docs` endpoint.

# %%
from jupyrest.client import JupyrestClient
from pprint import pprint
from IPython.display import HTML
import json

# initialize our client
base_url = "http://localhost:5051"
client = JupyrestClient(endpoint=base_url)

# Some helper functions to aid with displaying data
# in this notebook.
def print_json(data):
    print(json.dumps(data, indent=4))

def display_response(response):
    html_out = f"""
    ExecutionId: <a href="{base_url}/api/notebook_executions/{response.execution_id}" target="_blank">{response.execution_id}</a> <br>
    <a href="{base_url}{response.artifacts["html"]}" target="_blank">HTML</a> <br>
    <a href="{base_url}{response.artifacts["html_report"]}" target="_blank">HTML Report</a><br>
    <a href="{base_url}{response.artifacts["ipynb"]}" target="_blank">IPYNB</a><br>
    """
    if response.has_output:
        html_out += f'<a href="{base_url}{response.artifacts["output"]}" target="_blank">OUTPUT</a><br>'
    if response.has_exception:
        html_out += f'<a href="{base_url}{response.artifacts["exception"]}" target="_blank">EXCEPTION</a><br>'
    
    display(HTML(html_out))


# %% [markdown]
# # Getting the list of available Notebook Functions
#
# Based on what folder you have your notebooks in, Jupyrest will scan the directory and detect which notebooks in there are eligible notebook functions. This is done by looking for the `*.config.json` files.

# %%
notebooks = await client.get_notebooks()
print_json(notebooks)

# %% [markdown]
# # Get the details of a Notebook Function

# %%
hello_world_notebook = await client.get_notebook(notebook_id="hello_world")
print_json(hello_world_notebook)

# %% [markdown]
# # Executing a Notebook Function
#
# Ok, now to the fun stuff. We can use the `execute_notebook_until_complete` function to do this. 
#
# First, lets try to execute a notebook with parameters that *don't* match the expected schema:

# %%
await client.execute_notebook_until_complete(
    notebook_id="hello_world",
    parameters={
        "foo": "bar"
    }
)

# %% [markdown]
# Let's execute the notebook with the __correct__ parameters this time:

# %%
response = await client.execute_notebook_until_complete(
    notebook_id="hello_world",
    parameters={
        "name": "PyCascades"
    }
)

# %%
from fastapi.encoders import jsonable_encoder
print_json(jsonable_encoder(response))

# %%
display_response(response)

# %% [markdown]
# # Notebook Execution Artifacts
#
# Any successful execution of a notebook function will have the following artifacts:
# * `output` (if any)
#     * the data passed into the `save_output()` function in the notebook, if called
# * `html`
#     * an HTML view of the executed notebook
# * `html_report`
#     * an HTML view with the code cells removed
# * `ipynb`
#     * the .ipynb file of the executed notebook
#     
# The URLs for these artifacts are present in the response body (shown above). Of course, you can access these artifacts using the client as well:

# %%
execution_id = response.execution_id

html = await client.get_execution_html(
    execution_id=execution_id
)
html_report = await client.get_execution_html(
    execution_id=execution_id,
    report_mode=True
)
ipynb = await client.get_execution_ipynb(
    execution_id=execution_id
)
output = await client.get_execution_output(
    execution_id=execution_id
)

# %% [markdown]
# ## Notebook Execution Output
#
# The most compelling artifact of a notebook execution is the `output`. This is what makes a notebook into a notebook function.
#
# Our `"hello_world"` notebook is a notebook function because we can access its output:

# %%
print_json(output)

# %% [markdown]
# # "Erroneous" Notebook Functions
#
# What happens when the code inside a notebook fails and throws an exception? Pretty much exactly what you'd expect!
#
# We can debug any failed notebook execution by looking at its HTML. No need for any fancy logging or telemetry set ups.

# %%
from IPython.display import HTML

response = await client.execute_notebook_until_complete(notebook_id="error", parameters={})
print_json(jsonable_encoder(response))

# %%
display_response(response)

# %% [markdown]
# # Sharing Input/Output Models
#
# A good practice in API is to factor commonly used schemas as models and reference them in many API endpoints. Jupyrest lets you do this too!
#
# For this example, we will take a Portfolio Analysis notebook adapted from the [Stock Analysis For Quant](https://github.com/LastAncientOne/Stock_Analysis_For_Quant/blob/master/Python_Stock/Portfolio_Analysis.ipynb) Github repository.
#
# This notebook takes a `Portfolio` object as input. Rather than define this as raw JSON schema, we can define this as a Python class:
#
# The code below is only snippets, the full source code is in the `jupyrest_example/` folder.
#
# ```python
# from jupyrest.nbschema import NbSchemaBase
# from datetime import date
# from typing import Dict
#
# class Portfolio(NbSchemaBase):
#     start_date: date
#     end_date: date
#     holdings: Dict[str, float]
# ```
#
# Now we can give this model a name when we create our Jupyrest application:
#
# ```python
# deps = InMemoryApplicationBuilder(
#     notebooks_dir=notebooks_dir,
#     models={
#         # we name our model here
#         "portfolio": Portfolio
#     }
# ).build()
# ```
#
# With our API model created and named, we can reference it in our `config.json`:
#
# `Portfolio_Analysis.config.json`
# ```json
# {
#     "id": "portfolio_analysis",
#     "input": {
#         "type": "object",
#         "properties": {
#             "portfolio": {
#                 "$ref": "nbschema://portfolio"
#             }
#         },
#         "required": [
#             "portfolio"
#         ],
#         "additionalProperties": false
#     }
# }
# ```
#
# The cool thing is that when we use the API to get this notebook's input/output schema, we don't see the `nbschema://`, everything is fully resolved into standard JSON schema:

# %%
portfolio_notebook = await client.get_notebook(notebook_id="portfolio_analysis")
print_json(portfolio_notebook)

# %% [markdown]
# Lets now execute our portfolio analysis notebook. We can give it a set of holdings and weights:

# %%
response = await client.execute_notebook_until_complete(
    notebook_id="portfolio_analysis",
    parameters={
        "portfolio":{
            "start_date": "2022-04-26",
            "end_date": "2023-04-26",
            "holdings": {
                "AAPL": 0.5,
                "MSFT": 0.2,
                "AMD": 0.2,
                "NVDA": 0.1
            }
        }
    }
)

# %%
display_response(response)

# %% [markdown]
# Notice how the parameters have been __converted__ into a Portfolio Python object in the notebook. Isn't that just so cool!
#
# The beauty is that our notebook has *no idea* that is being used as a REST API. It is all plain-old Python through and through.

# %%
