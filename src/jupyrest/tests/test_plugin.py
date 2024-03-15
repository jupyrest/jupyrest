from jupyrest.nbschema import OutputResult
import pytest
import json
from tests.conftest import Notebooks
from jupyrest.plugin import BasePlugin


@pytest.mark.asyncio
async def test_execute_notebook_basic(default_plugin: BasePlugin):
    parameters = {"foo": "foo", "bar": 50, "baz": "baz"}
    notebook_id = Notebooks.io_contract_example
    notebook = default_plugin.get_resolver().resolve_notebook(notebook_id=notebook_id)
    assert notebook is not None
    notebook = default_plugin.parameterize_notebook(
        notebook_id=Notebooks.io_contract_example,
        parameters=parameters,
        notebook=notebook,
    )
    exception = await default_plugin.get_notebook_executor().execute_notebook_async(
        notebook=notebook
    )
    assert exception is None
    # get output
    output_result = default_plugin.get_nbschema().get_notebook_output(notebook)
    assert isinstance(output_result, OutputResult)
    assert output_result.present
    output = json.loads(output_result.json_str)
    for i, row in enumerate(output):
        for color in ["red", "green", "blue"]:
            assert row[color] == f"{color}{i+1}"


@pytest.mark.asyncio
async def test_execute_notebook_error(default_plugin: BasePlugin):
    notebook_id = Notebooks.error
    parameters = {}
    notebook = default_plugin.get_resolver().resolve_notebook(notebook_id=notebook_id)
    assert notebook is not None
    notebook = default_plugin.parameterize_notebook(
        notebook_id=notebook_id, parameters=parameters, notebook=notebook
    )
    exception = await default_plugin.get_notebook_executor().execute_notebook_async(
        notebook=notebook
    )
    assert exception is not None and isinstance(exception, str)
    assert "here is an exception" in exception
