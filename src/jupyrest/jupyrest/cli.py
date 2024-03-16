import typer
from typing import Optional
from pathlib import Path
import uvicorn
from jupyrest.dependencies import Dependencies
from jupyrest.http.asgi import create_asgi_app

HTTP_PORT = 5050

cli_app = typer.Typer(name="jupyrest cli")
http_app = typer.Typer()

cli_app.add_typer(http_app, name="http")

use_new = True
@http_app.command("start")
def start(
    notebooks_dir: Optional[Path] = typer.Option(None),
    port: Optional[int] = typer.Option(None, help="Port to serve worker on."),
):
    # if not use_new:
    #     plugin_man = PluginManager()
    #     if notebooks_dir is not None:
    #         plugin_man.register(
    #             plugin_name=PluginManager.DEFAULT_PLUGIN_NAME,
    #             plugin=JupyrestPlugin(
    #                 resolver=LocalDirectoryResolver(notebooks_dir=notebooks_dir),
    #                 nbschema=NotebookSchemaProcessor(),
    #                 executor=IPythonNotebookExecutor(),
    #             ),
    #         )
    #     worker = Worker(plugin_man=plugin_man)

    #     if port is None:
    #         port = HTTP_PORT
    #     http_app = create_dev_app(
    #         worker=worker, event_store_repository=InMemoryNotebookEventStoreRepository()
    #     )
    #     typer.echo(f"Starting http worker server on {port}")
    #     uvicorn.run(app=http_app, port=port)  # type: ignore
    # else:
    if notebooks_dir is None:
        raise ValueError("Notebooks directory must be specified")
    deps = Dependencies(
        notebooks_dir=notebooks_dir,
        models={},
    )
    app = create_asgi_app(deps=deps.get_dependency_bag())
    typer.echo(f"Starting http worker server on {port}")
    uvicorn.run(app=app, port=5050) # type: ignore
