# jupyrest

Jupyrest is a tool that can turn a notebook into a REST API with predefined input and output contracts.

## Usage

Suppose you have a notebook `analysis.ipynb` where you have done revenue analysis for a customer. At the end of the notebook, you determine whether the customer is eligible for a enterprise discount or not. You can quickly make your work available as a web api by including a `analysis.config.json` file alongside the notebook:

```json
// analysis.config.json
{
    "input": {
        "type": "object",
        "properties": {
            "customer_name": {
                "type": "string"
            }
        },
        "required": [
            "customer_name"
        ]
    },
    "output": {
        "type": "object",
        "properties": {
            "needs_discount": {
                "type": "boolean"
            }
        },
        "required": [
            "needs_discount"
        ]
    }
}
```

This file tells jupyrest what the schema of the input and output of the REST API should be. Your notebooks folder will now look like this:

```
notebooks/
├── analysis.config.json
└── analysis.ipynb
```

To start the web server, run:

```
python -m jupyrest worker start http --notebooks-dir=./notebooks
```

To execute this notebook:

```
POST /api/NotebookExecutions
Host: localhost:5050
Content-Type: application/json

{
    "notebook": "analysis",
    "parameters": {
        "customer_name": "microsoft"
    }
}
```

And you'll get a response:

```json
{
    "id": "fae94291-8074-475e-8d78-f9667dd33d46",
    "status": "COMPLETED",
    "notebook": "analysis",
    "parameters": {
        "customer_name": "microsoft"
    }
}
```

The `id` represnets the execution id of this notebook. Using this id you can retrieve the execution details at:

```
http://localhost:5050/api/NotebookExecutions?executionId=fae94291-8074-475e-8d78-f9667dd33d46
```

You can view the executed notebook with the `&view_html=true` parameter:

![](./docs/images/analysis_execution.png)

And you can view the output with `&output=true`

```json
{
    "id": "fae94291-8074-475e-8d78-f9667dd33d46",
    "status": "COMPLETED",
    "notebook": "analysis",
    "parameters": {
        "customer_name": "microsoft"
    },
    // if an exception was raised in the notebook,
    // we would see it here
    "exception": null,
    // this is the output we saved in the notebook
    "output": {
        "needs_discount": false
    }
}
```

See the full API at `http://localhost:5050/docs`

## Running jupyrest in production

By nature, Jupyter notebooks can be resource intensive and so it makes sense that we want to decouple the web server environment from the notebook execution environment. Jupyrest has a GRPC mode for this purpose. See `./src/jupyrest/protobufs/jupyrest.proto`.

To start the GRPC server run:

```
python -m jupyrest worker start grpc --notebooks-dir={path/to/notebooks}
```