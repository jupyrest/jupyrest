# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %% [markdown]
#
# # Usage
#
# ## Writing Notebook Functions
#
# To turn any existing notebook into a notebook function, all you need to include a `.config.json` file next to the notebook. For example a notebook named `hello_world.ipynb` should have a `hello_world.config.json` file next to it in order for Jupyrest to consider the `hello_world.ipynb` notebook to be a notebook function.
#
# If you do not intend to expose a Jupyter notebook a REST API, do not include the `.config.json` file.
#
# ### The `.config.json` file
#
# The `.config.json` file is used to set input and output schemas for the associated notebook.
#
# A `.config.json` file that looks like the one below describes a notebook function called `my-notebook` that takes an input of arbitrary schema and returns an output of arbitrary schema.
# ```json
# {
#     "id": "my-notebook",
#     "input": {},
#     "output": {}
# }
# ```
#
# The `id` property should be a URL-safe string because this value will be used in API called like:
#
# ```
# POST /api/notebooks/<notebook_id>/execute
# ```
#
# The `input` and `output` properties are [JSON-schema](https://json-schema.org/) objects.
#
# ### Setting Notebook Inputs
#
# When writing a Jupyter notebook, you might find yourself having a code cell with a set of variables that you change frequently in order to test how your notebook functions with different inputs.
#
# In order to tell Jupyrest and Papermill (the underlying library used by Jupyrest) about our notebook inputs, we need to designate this cell as the parameter cell. To do that we should set the code cell as `parameters`.
#
# How do I do that?
#
# * See these [docs](https://papermill.readthedocs.io/en/latest/usage-parameterize.html#designate-parameters-for-a-cell) from the Papermill library on how to do that in JupyterLab and Jupyter Notebook.
# * In VSCode, download the [Jupyter Cell Tags](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.vscode-jupyter-cell-tags) extension to do this.
#
# ### Setting Notebook Outputs
#
# From within a notebook, we can set the notebook's output using the `save_output` function in Jupyrest.
#
# ```python
# from jupyrest import save_output
#
# my_output_data = {
#     "title": "my output information",
#     "some_random_number": 42
# }
#
# save_output(my_output_data)
# ```
#
# The input to `save_output` should be any object that can be converted into JSON.
#
# ## Configuring a Jupyrest Application
#
# A Jupyrest application is defined by its dependencies. All parts of a Jupyrest application are configurable using a set of well defined interfaces. 
#
# These dependencies are packaged into a `DependencyBag` object:

# %%
import inspect
from IPython.display import Markdown
from jupyrest.contracts import DependencyBag
Markdown(f"""
```python
{inspect.getsource(DependencyBag)}
```
""")

# %% [markdown]
# But for practical purposes, we can't expect every developer to have to construct a DependencyBag on their own. That's why we have builders.
#
# We have the `InMemoryApplicationBuilder` and the `AzureApplicationBuilder` provided in the Jupyrest library. For this guide, we will use the `InMemoryApplicationBuilder`.
#
# We can create an `InMemoryApplicationBuilder` by providing the path to our notebooks as `notebooks_dir`:
#
# ```python
# from jupyrest.infra.in_memory.builder import InMemoryApplicationBuilder
# from pathlib import Path
#
# notebooks_dir = Path(__file__).parent / 'notebooks'
# deps = InMemoryApplicationBuilder(
#     notebooks_dir=notebooks_dir
#     ).build()
# ```
#
# The `deps` variable here is an instance of `DependencyBag` and we can use this to deploy our Jupyrest Application where we so choose.
#
# ## Starting the HTTP Server
#
# To start the HTTP Server, `jupyrest` has a `create_asgi_app` function. This functions takes a `DependencyBag` as input, and returns a [FastAPI](https://fastapi.tiangolo.com/) application instance. FastAPI is a popular web server framework for Python and supports many forms of deployment.
#
# If we wanted to run our FastAPI app locally, we could use `uvicorn`:
#
# ```python
# import uvicorn
# from jupyrest.http.asgi import create_asgi_app
# app = create_asgi_app(deps=deps)
# uvicorn.run(app, port=5051)
# ```
