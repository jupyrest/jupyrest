from pathlib import Path
import uvicorn
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

asgi_app = create_asgi_app(deps=deps)
import sys
import asyncio
if sys.platform == 'win32':
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
uvicorn.run(app=asgi_app, port=5050)  # type: ignore