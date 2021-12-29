"""
These tests require a running GrpcWorkerServer on port 5050.
"""

from typing import AsyncGenerator
import pytest

from datetime import datetime
from jupyrest.nbschema import SchemaValidationResponse
import pytest
import json
from tests.conftest import Notebooks
from jupyrest.errors import BaseError
from jupyrest.domain import (
    NotebookEventStore,
    NotebookExecutionCreated,
    NotebookExecuted,
)
from jupyrest.plugin import PluginManager
from jupyrest.workers.grpc import GrpcWorkerClient
from grpc.aio import insecure_channel, Channel
from jupyrest.cli import MAX_MESSAGE_LENGTH


@pytest.fixture
def grpc_channel() -> Channel:
    options = [
        ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
        ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
    ]
    GRPC_ADDRESS = "localhost:50051"
    return insecure_channel(GRPC_ADDRESS, options=options)


@pytest.fixture
@pytest.mark.asyncio
async def grpc_worker_client(
    grpc_channel: Channel,
) -> AsyncGenerator[GrpcWorkerClient, None]:
    async with grpc_channel:
        yield GrpcWorkerClient(channel=grpc_channel)


@pytest.mark.asyncio
async def test_grpc_execute_notebook_basic(grpc_worker_client: GrpcWorkerClient):
    parameters = {"foo": "foo", "bar": 50, "baz": "baz"}
    notebook_id = Notebooks.io_contract_example
    plugin_name = PluginManager.DEFAULT_PLUGIN_NAME
    response = await grpc_worker_client.execute_notebook_async(
        plugin_name=plugin_name, notebook_id=notebook_id, parameters=parameters,
    )
    assert not isinstance(response, BaseError)
    event_store = NotebookEventStore(notebook=response)
    execution_created = event_store.get_event(NotebookExecutionCreated)
    assert isinstance(execution_created, NotebookExecutionCreated)
    assert execution_created.plugin_name == plugin_name
    assert execution_created.notebook_id == notebook_id
    assert execution_created.parameters == parameters

    # assert the execution completion
    notebook_executed = event_store.get_event(NotebookExecuted)
    assert isinstance(notebook_executed, NotebookExecuted)
    assert isinstance(notebook_executed.start_time, datetime)
    assert isinstance(notebook_executed.end_time, datetime)
    assert notebook_executed.end_time > notebook_executed.start_time
    assert notebook_executed.exception is None
    # get output
    output_json_str = notebook_executed.output_json_str
    assert output_json_str is not None
    assert isinstance(output_json_str, str)
    output = json.loads(output_json_str)
    assert output is not None
    output_validation = notebook_executed.output_validation
    assert isinstance(output_validation, SchemaValidationResponse)
    assert output_validation.is_valid
    assert isinstance(output, list)
    for i, row in enumerate(output):
        for color in ["red", "green", "blue"]:
            assert row[color] == f"{color}{i+1}"
