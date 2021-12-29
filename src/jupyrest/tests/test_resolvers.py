from azure.storage.blob import (
    StorageStreamDownloader,
    BlobClient,
    ContainerClient,
    BlobServiceClient,
)
from pathlib import Path
from typing import Container, Optional, Any
import json
from nbformat.notebooknode import NotebookNode
import pytest
from jupyrest.resolvers import AzureStorageResolver


@pytest.fixture(autouse=True)
def container_client():
    emulator_conn_str = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
    container_name = "notebook-storage"
    container_client = BlobServiceClient.from_connection_string(
        emulator_conn_str
    ).get_container_client(container_name)
    # create the container is not exists
    if container_client.exists():
        container_client.delete_container()
    container_client.create_container()
    return container_client


@pytest.fixture(autouse=True)
def abs_resolver(
    notebooks_dir: Path, container_client: ContainerClient
) -> AzureStorageResolver:
    # upload files in notebooks_dir to the container
    files = ["io_contract_example.ipynb", "io_contract_example.config.json"]
    for f in files:
        name = f
        data = (notebooks_dir / f).read_text()
        container_client.upload_blob(name=name, data=data)
    return AzureStorageResolver(container_client=container_client)


def test_azure_storage_resolver_loads_notebook(abs_resolver: AzureStorageResolver):
    notebook_name = "io_contract_example"

    notebook = abs_resolver.resolve_notebook(notebook_name)

    assert notebook is not None
    assert isinstance(notebook, NotebookNode)
    assert len(notebook.cells) == 7


def test_azure_storage_resolver_missing_notebook(abs_resolver: AzureStorageResolver):
    notebook_name = "does_not_exist"
    notebook = abs_resolver.resolve_notebook(notebook_name)

    assert notebook == None


def test_azure_storage_resolver_loads_config(
    notebooks_dir: Path, abs_resolver: AzureStorageResolver
):
    notebook_name = "io_contract_example"
    config_file_name = f"{notebook_name}.config.json"
    config_file_path = notebooks_dir / config_file_name

    config = abs_resolver.resolve_config(notebook_name)
    config_expectation = json.loads(config_file_path.read_text())

    assert config == config_expectation


def test_azure_storage_resolver_missing_config(abs_resolver: AzureStorageResolver):
    notebook_name = "does_not_exist"

    config = abs_resolver.resolve_config(notebook_name)

    assert config == None
