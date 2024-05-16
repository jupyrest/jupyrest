from jupyrest.http.asgi import create_asgi_app
import uvicorn
from jupyrest.infra.in_memory.builder import InMemoryApplicationBuilder
from jupyrest_example import Portfolio, notebooks_dir
import sys

# Build our Jupyrest Application, here we are using the in-memory configuration
deps = InMemoryApplicationBuilder(
    notebooks_dir=notebooks_dir, models={"portfolio": Portfolio}
).build()

# Generate a FastAPI application
app = create_asgi_app(deps=deps)
default_port = 5051
# start the server
if __name__ == "__main__":
    if len(sys.argv) < 2:
        port = default_port
    else:
        try:
            port = int(sys.argv[1])
        except:
            print("Unable to parse port number, using default port: ", default_port)
            port = default_port
    uvicorn.run(app, port=port)
