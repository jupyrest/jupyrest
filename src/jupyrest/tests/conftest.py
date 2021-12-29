import pytest
from pathlib import Path
from jupyrest.workers.base import Worker
from jupyrest.plugin import BasePlugin, JupyrestPlugin, PluginManager
from jupyrest.nbschema import NotebookSchemaProcessor
from jupyrest.executors import IPythonNotebookExecutor
from jupyrest.resolvers import LocalDirectoryResolver


class Notebooks:
    io_contract_example = "io_contract_example"
    model_io = "model_io"
    error = "error"


@pytest.fixture
def notebooks_dir() -> Path:
    return Path(__file__).parent / "notebooks"


@pytest.fixture
def default_plugin(notebooks_dir) -> BasePlugin:
    return JupyrestPlugin(
        resolver=LocalDirectoryResolver(notebooks_dir=notebooks_dir),
        nbschema=NotebookSchemaProcessor(),
        executor=IPythonNotebookExecutor(),
    )


@pytest.fixture
def plugin_name() -> str:
    return PluginManager.DEFAULT_PLUGIN_NAME


@pytest.fixture
def plugin_man(default_plugin: BasePlugin, plugin_name: str) -> PluginManager:
    pm = PluginManager()
    pm.register(plugin_name=plugin_name, plugin=default_plugin)
    return pm


@pytest.fixture
def worker(plugin_man: PluginManager):
    return Worker(plugin_man=plugin_man)
