# New HTTP API

## Root:
```
/api/v0/plugins/<plugin_name>/
```

## Notebooks API

Get a list of notebook functions:
```
GET /notebooks
```

Get a specific notebook:
```
GET /notebooks/<notebook_id>
```

Execute a notebook:

```
POST /notebooks/<notebook_id>/execute
```

## Execution API

```
GET /executions
```

```
GET /executions/<execution_id>
```

```
POST /executions/<execution_id>/cancel
```


# v2

Notebooks API

```
GET /notebooks/<notebook_id>

GET /notebooks/<notebook_id>/html

GET /notebooks/<notebook_id>/ipynb

POST /notebooks/<notebook_id>/execute
```

Notebook Executions API

```
GET /notebook_executions/<execution_id>

GET /notebook_executions/<execution_id>/output

GET /notebook_executions/<execution_id>/html

GET /notebook_executions/<execution_id>/ipynb
```

FileObjects API

```
GET /file_objects/<file_id>

```

```python

class HTTPResource():


    async def get():
        pass

    async def post():
        pass

```

# Dependencies

```

Jupyrest Service

    - notebooks_dir
    - model_collection
    - Notebook Execution Location
        - Local Executor
            - run on the machine serving the request
        - Remote Executor
            - Submit on a task queue
                - Azure Storage Queue
    - Execution Metadata
        - InMemory
        - Azure Blob
    - Execution Artifact Storage
        - InMemory
        - Azure Blob

```
