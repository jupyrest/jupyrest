from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass
from nbformat.notebooknode import NotebookNode
from typing import Optional
from nbclient.client import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError
import logging

logger = logging.getLogger(__name__)


class BaseNotebookExeuctor(ABC):
    @abstractmethod
    def get_kernelspec_language(self) -> str:
        pass

    @abstractmethod
    async def execute_notebook_async(self, notebook: NotebookNode) -> Optional[str]:
        """Executes a notebook in place. Returns an exception string if any.

        Args:
            notebook (NotebookNode): notebook to execute

        Returns:
            Optional[str]: exception
        """
        pass


class IPythonNotebookExecutor(BaseNotebookExeuctor):
    def __init__(
        self, kernel_name="python3", timeout_seconds=600, language="python"
    ) -> None:
        self._kernel_name = kernel_name
        self._timeout_seconds = timeout_seconds
        self._language = language

    def get_kernelspec_language(self) -> str:
        return self._language

    async def execute_notebook_async(self, notebook: NotebookNode) -> Optional[str]:
        exception: Optional[str] = None
        try:
            await NotebookClient(
                nb=notebook,
                timeout=self._timeout_seconds,
                kernel_name=self._kernel_name,
                log=logger,
            ).async_execute()
        except CellExecutionError as cee:
            # handle cases where the notebook calls sys.exit(0),
            # which is considered successful.
            is_sys_exit_0 = cee.ename == "SystemExit" and (
                cee.evalue == "" or cee.evalue == "0"
            )
            if not is_sys_exit_0:
                exception = str(cee)
        except CellTimeoutError as cte:
            exception = str(cte)
        return exception
