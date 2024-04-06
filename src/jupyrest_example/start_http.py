from jupyrest.http.asgi import create_asgi_app
import uvicorn
from jupyrest.infra.in_memory.builder import InMemoryApplicationBuilder
from jupyrest_example import Portfolio, notebooks_dir

# Build our Jupyrest Application, here we are using the in-memory configuration
deps = InMemoryApplicationBuilder(
    notebooks_dir=notebooks_dir, models={"portfolio": Portfolio}
).build()

# Generate a FastAPI application
app = create_asgi_app(deps=deps)

# start the server
if __name__ == "__main__":
    uvicorn.run(app, port=5051)
