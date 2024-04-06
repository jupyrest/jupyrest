from ..contracts import NotebookExecutionFileNamer
from ..notebook_execution.entity import NotebookExecution

class DefaultNotebookExecutionFileNamer(NotebookExecutionFileNamer):

    def get_ipynb_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.ipynb"
    
    def get_html_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.html"
    
    def get_html_report_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.report.html"
    
    def get_output_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.output.json"
    
    def get_exception_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.exception.txt"