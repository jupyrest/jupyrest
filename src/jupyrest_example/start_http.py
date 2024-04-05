from jupyrest_example import dependencies
from jupyrest.http.asgi import create_asgi_app
import uvicorn

app = create_asgi_app(dependencies.get_dependency_bag())

uvicorn.run(app, port=5051)
