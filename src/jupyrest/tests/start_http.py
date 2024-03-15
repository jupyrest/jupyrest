from pathlib import Path
import uvicorn
from jupyrest.workers.http import create_dev_app, InMemoryNotebookEventStoreRepository
from jupyrest.workers.base import Worker
from jupyrest.plugin import JupyrestPlugin, PluginManager
from jupyrest.resolvers import LocalDirectoryResolver
from jupyrest.executors import IPythonNotebookExecutor
from jupyrest.nbschema import NotebookSchemaProcessor, ModelCollection, NbSchemaBase
from datetime import datetime
from jupyrest.http.asgi import create_asgi_app
from jupyrest.dependencies import Dependencies, DependencyBag
class Incident(NbSchemaBase):
    start_time: datetime
    end_time: datetime
    title: str



notebooks_dir = Path(__file__).parent / "notebooks"
mc = ModelCollection()
mc.add_model(alias="incident", model_type=Incident)

plugin = JupyrestPlugin(
    resolver=LocalDirectoryResolver(notebooks_dir=notebooks_dir),
    nbschema=NotebookSchemaProcessor(models=mc),
    executor=IPythonNotebookExecutor(),
)
plugin_man = PluginManager()
plugin_man.register(plugin_name=PluginManager.DEFAULT_PLUGIN_NAME, plugin=plugin)

deps = Dependencies(
    notebooks_dir=notebooks_dir,
    models={"incident": Incident},
).get_dependency_bag()

worker = Worker(plugin_man=plugin_man)
asgi_app = create_asgi_app(deps=deps)
http_app = create_dev_app(worker=worker, event_store_repository=InMemoryNotebookEventStoreRepository())
uvicorn.run(app=asgi_app, port=5050)  # type: ignore