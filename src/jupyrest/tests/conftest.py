import pytest
from xprocess import ProcessStarter
from pathlib import Path
import aiohttp
import sys

cwd = Path(__file__).parent


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
@pytest.mark.anyio
async def http_server(xprocess):
    class Starter(ProcessStarter):
        pattern = "Uvicorn running"  # type: ignore
        args = [sys.executable, str(cwd / "start_http.py")]  # type: ignore

        def check(self, stdout, stderr):
            return self.pattern in stdout + stderr

    xprocess.ensure("http_server", Starter)

    # This provides the process name to the test function
    yield aiohttp.ClientSession(base_url="http://localhost:5050")

    # Clean up after the test
    xprocess.getinfo("http_server").terminate()
