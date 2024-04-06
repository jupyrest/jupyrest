import aiohttp
import pytest
from jupyrest.client import JupyrestClient

@pytest.mark.anyio
async def test_execute_delay_notebook(jupyrest_client: JupyrestClient):
    notebook_id = "delay"
    parameters = {
        "delay_seconds": 3
    }
    result = await jupyrest_client.execute_notebook_until_complete(notebook_id, parameters)
    assert result is not None
    assert result.status == "COMPLETED"
    assert result.execution_end_ts is not None
    assert result.execution_start_ts is not None
    assert result.execution_id is not None
    assert result.notebook_id == notebook_id
    assert result.parameters == parameters
    assert result.execution_accepted_ts is not None
    assert result.execution_end_ts > result.execution_start_ts
    assert result.execution_completion_status is not None
    assert result.execution_completion_status == "SUCCEEDED"
    assert result.has_exception == False
    assert result.has_output == False
    assert result.artifacts is not None
    assert result.artifacts.keys() == set(["html", "ipynb", "html_report"])
    assert result.artifacts["html"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html"
    assert result.artifacts["ipynb"] == f"/api/notebook_executions/{result.execution_id}/artifacts/ipynb"
    assert result.artifacts["html_report"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html_report"

@pytest.mark.anyio
async def test_error_notebook(jupyrest_client: JupyrestClient):
    notebook_id = "error"
    parameters = {}
    result = await jupyrest_client.execute_notebook_until_complete(notebook_id, parameters)
    assert result is not None
    assert result.status == "COMPLETED"
    assert result.execution_end_ts is not None
    assert result.execution_start_ts is not None
    assert result.execution_id is not None
    assert result.notebook_id == notebook_id
    assert result.parameters == parameters
    assert result.execution_accepted_ts is not None
    assert result.execution_end_ts > result.execution_start_ts
    assert result.execution_completion_status == "FAILED"
    assert result.has_exception == True
    assert result.has_output == False
    assert result.artifacts is not None
    assert result.artifacts.keys() == set(["html", "ipynb", "html_report", "exception"])
    assert result.artifacts["html"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html"
    assert result.artifacts["ipynb"] == f"/api/notebook_executions/{result.execution_id}/artifacts/ipynb"
    assert result.artifacts["html_report"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html_report"
    assert result.artifacts["exception"] == f"/api/notebook_executions/{result.execution_id}/artifacts/exception"

@pytest.mark.anyio
async def test_valid_input(jupyrest_client: JupyrestClient):
    notebook_id = "io_contract_example"
    parameters = {
        "foo": "foo string",
        "bar": 500
    }
    result = await jupyrest_client.execute_notebook_until_complete(notebook_id, parameters)
    assert result is not None
    assert result.status == "COMPLETED"
    assert result.has_output == True
    assert result.has_exception == False
    assert result.execution_completion_status == "SUCCEEDED"
    assert result.artifacts is not None
    assert result.artifacts.keys() == set(["html", "ipynb", "html_report", "output"])
    assert result.artifacts["output"] == f"/api/notebook_executions/{result.execution_id}/artifacts/output"
    assert result.artifacts["html"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html"
    assert result.artifacts["ipynb"] == f"/api/notebook_executions/{result.execution_id}/artifacts/ipynb"
    assert result.artifacts["html_report"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html_report"
    output = await jupyrest_client.get_execution_output(result.execution_id)
    assert isinstance(output, list)
    assert len(output) == 2
    assert output[0] == {
        "red": parameters["foo"],
        "green": parameters["bar"],
        "blue": "baz"
    }
    assert output[1] == {
        "red": "baz",
        "green": parameters["bar"],
        "blue": parameters["foo"]
    }

@pytest.mark.anyio
async def test_invalid_input(jupyrest_client: JupyrestClient):
    notebook_id = "io_contract_example"
    parameters = {
        "foo": "foo string",
        "bar": "500"
    }
    with pytest.raises(aiohttp.ClientResponseError) as exc_info:
        await jupyrest_client.execute_notebook_until_complete(notebook_id, parameters)
        assert exc_info.value.status == 400
        assert exc_info.value.message == "Bad Request"

@pytest.mark.anyio
async def test_model_input_output(jupyrest_client: JupyrestClient):
    notebook_id = "model_io"
    parameters = {
        "incidents": [
            {
                "title": "Incident 1",
                "start_time": "2021-01-01T00:00:00",
                "end_time": "2021-02-01T01:00:00",
            },
            {
                "title": "Incident 2",
                "start_time": "2022-01-01T00:00:00",
                "end_time": "2022-02-01T01:00:00",
            }
        ],
        "foo": "FOO"
    }
    result = await jupyrest_client.execute_notebook_until_complete(notebook_id, parameters)
    assert result is not None
    assert result.status == "COMPLETED"
    assert result.has_output == True
    assert result.has_exception == False
    assert result.execution_completion_status == "SUCCEEDED"
    assert result.artifacts is not None
    assert result.artifacts.keys() == set(["html", "ipynb", "html_report", "output"])
    assert result.artifacts["output"] == f"/api/notebook_executions/{result.execution_id}/artifacts/output"
    assert result.artifacts["html"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html"
    assert result.artifacts["ipynb"] == f"/api/notebook_executions/{result.execution_id}/artifacts/ipynb"
    assert result.artifacts["html_report"] == f"/api/notebook_executions/{result.execution_id}/artifacts/html_report"
    output = await jupyrest_client.get_execution_output(result.execution_id)
    assert isinstance(output, dict)
    assert len(output["new_incidents"]) == 2
    assert output["new_incidents"]["new_incident_1"] == {
        "title": "Incident 1",
        "start_time": "2021-01-01T00:00:00",
        "end_time": "2021-02-01T01:00:00",
    }
    assert output["new_incidents"]["new_incident_2"] == {
        "title": "Incident 2",
        "start_time": "2022-01-01T00:00:00",
        "end_time": "2022-02-01T01:00:00",
    }
    assert output["bar"] == "FOO"

@pytest.mark.anyio
async def test_get_execution_html(jupyrest_client: JupyrestClient):
    notebook_id = "io_contract_example"
    parameters = {
        "foo": "foo string",
        "bar": 500
    }
    result = await jupyrest_client.execute_notebook_until_complete(notebook_id, parameters)
    assert result is not None
    html = await jupyrest_client.get_execution_html(result.execution_id)
    assert html is not None
    assert "foo string" in html
    assert "500" in html
    assert "baz" in html


@pytest.mark.anyio
async def test_get_notebook(jupyrest_client: JupyrestClient):
    notebook_id = "io_contract_example"
    result = await jupyrest_client.get_notebook(notebook_id)
    assert result is not None
    assert result["notebook_id"] == notebook_id
    assert result["input_schema"] == {
        "type": "object",
        "properties": {
            "foo": {
                "type": "string"
            },
            "bar": {
                "type": "number"
            },
            "baz": {
                "type": "string"
            }
        },
        "required": [
            "foo",
            "bar"
        ]
    }
    assert result["output_schema"] == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "red": {
                    "type": "string"
                },
                "green": {
                    "type": "string"
                },
                "blue": {
                    "type": "string"
                }
            },
            "required": [
                "red",
                "green",
                "blue"
            ]
        }
    }