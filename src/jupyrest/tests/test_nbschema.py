from tests.conftest import Notebooks
from jupyrest.plugin import BasePlugin
import pytest
import json
from jupyrest.nbschema import NbSchemaBase, NbSchemaEncoder, OutputResult
from datetime import datetime
from itertools import chain


class Incident(NbSchemaBase):
    start_time: datetime
    end_time: datetime
    title: str


@pytest.fixture
def default_plugin(default_plugin: BasePlugin) -> BasePlugin:
    default_plugin.get_nbschema().models.add_model(
        alias="incident", model_type=Incident
    )
    return default_plugin


@pytest.fixture
def sample_incident():
    return Incident(
        title="Sample", start_time=datetime(2020, 1, 1), end_time=datetime(2020, 1, 2)
    )


@pytest.fixture
def sample_incident_json(sample_incident):
    return json.loads(json.dumps(sample_incident, cls=NbSchemaEncoder))


def test_correct_input_schema(default_plugin: BasePlugin):
    parameters = {"foo": "foo", "bar": 5, "baz": "baz"}
    result = default_plugin.validate_input(
        notebook_id=Notebooks.io_contract_example, parameters=parameters
    )
    assert result.is_valid


def test_incorrect_input_schema(default_plugin: BasePlugin):
    bad_input = {"foo": 60}
    result = default_plugin.validate_input(
        notebook_id=Notebooks.io_contract_example, parameters=bad_input
    )
    assert not result.is_valid


def test_none_input_parameters(default_plugin: BasePlugin):
    bad_input = None
    result = default_plugin.validate_input(
        notebook_id=Notebooks.io_contract_example, parameters=bad_input
    )
    assert not result.is_valid


def test_inject_model_refs_object(
    default_plugin: BasePlugin, sample_incident: Incident, sample_incident_json
):
    schema = {
        "type": "object",
        "properties": {
            "incident": {"$ref": "nbschema://incident"},
            "foo": {"type": "string"},
        },
        "required": ["incident"],
    }
    payload = {"incident": sample_incident_json, "foo": "foo"}
    new_payload = default_plugin.get_nbschema().inject_model_refs(
        schema=schema, payload=payload
    )

    assert isinstance(new_payload, dict)
    assert isinstance(new_payload["incident"], Incident)
    assert new_payload["incident"] == sample_incident
    assert new_payload["foo"] == "foo"


def test_inject_model_refs_array(
    default_plugin: BasePlugin, sample_incident: Incident, sample_incident_json
):
    schema = {"type": "array", "items": {"$ref": "nbschema://incident"}}
    payload = [sample_incident.dict(), sample_incident, sample_incident_json]
    new_payload = default_plugin.get_nbschema().inject_model_refs(
        schema=schema, payload=payload  # type: ignore
    )

    assert isinstance(new_payload, list)
    assert len(new_payload) == len(payload)
    assert all(map(lambda p: isinstance(p, Incident), new_payload))
    assert all(map(lambda p: p == sample_incident, new_payload))


def test_inject_model_refs_nested_objects(
    default_plugin: BasePlugin, sample_incident: Incident, sample_incident_json
):
    schema = {
        "type": "object",
        "properties": {
            "incident_array": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"incident": {"$ref": "nbschema://incident"}},
                    "required": ["incident"],
                },
            }
        },
        "required": ["incident_array"],
    }
    payload = {
        "incident_array": [
            {"incident": sample_incident},
            {"incident": sample_incident.dict()},
            {"incident": sample_incident_json},
        ]
    }
    new_payload = default_plugin.get_nbschema().inject_model_refs(
        schema=schema, payload=payload
    )

    assert isinstance(new_payload, dict)
    assert all(
        map(
            lambda p: isinstance(p["incident"], Incident), new_payload["incident_array"]
        )
    )
    assert all(
        map(lambda p: p["incident"] == sample_incident, new_payload["incident_array"])
    )


def test_inject_model_refs_nested_arrays(
    default_plugin: BasePlugin, sample_incident: Incident, sample_incident_json
):
    schema = {
        "type": "array",
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"incident": {"$ref": "nbschema://incident"}},
                "required": ["incident"],
            },
        },
    }
    payload = [
        [{"incident": sample_incident}, {"incident": sample_incident.dict()},],
        [{"incident": sample_incident.dict()},],
        [{"incident": sample_incident_json},],
    ]
    new_payload = default_plugin.get_nbschema().inject_model_refs(
        schema=schema, payload=payload  # type: ignore
    )

    assert isinstance(new_payload, list)
    assert len(new_payload) == len(payload)
    assert all(map(lambda p: isinstance(p["incident"], Incident), chain(*new_payload)))
    assert all(map(lambda p: p["incident"] == sample_incident, chain(*new_payload)))


def test_inject_model_refs_invalid_model_ref(
    default_plugin: BasePlugin, sample_incident: Incident
):
    schema = {
        "type": "object",
        "properties": {"incident": {"$ref": "nbschema://invalid"}},
    }
    payload = {"incident": sample_incident}
    with pytest.raises(KeyError, match="Model for alias invalid not found"):
        default_plugin.get_nbschema().inject_model_refs(schema=schema, payload=payload)


def test_inject_model_refs_bad_input(default_plugin: BasePlugin):
    schema = None
    payload = None
    new_payload = default_plugin.get_nbschema().inject_model_refs(
        schema=dict(), payload=payload  # type: ignore
    )
    assert new_payload is None
    new_payload = default_plugin.get_nbschema().inject_model_refs(
        schema=schema, payload=dict()  # type: ignore
    )
    assert new_payload == dict()


@pytest.mark.asyncio
async def test_execute_notebook_model_io(
    default_plugin: BasePlugin, sample_incident_json
):
    parameters = {
        "incidents": [sample_incident_json, sample_incident_json],
        "foo": "FOO",
    }
    notebook_id = Notebooks.model_io
    notebook = default_plugin.get_resolver().resolve_notebook(notebook_id=notebook_id)
    assert notebook is not None
    notebook = default_plugin.parameterize_notebook(
        notebook_id=Notebooks.model_io, parameters=parameters, notebook=notebook
    )
    exception = await default_plugin.get_notebook_executor().execute_notebook_async(
        notebook=notebook
    )
    assert exception is None
    # get output
    output_result = default_plugin.get_nbschema().get_notebook_output(notebook=notebook)
    assert isinstance(output_result, OutputResult)
    assert output_result.present
    output = json.loads(output_result.json_str)
    assert isinstance(output, dict)
    assert output["bar"] == parameters["foo"]
    assert output["new_incidents"]["new_incident_1"] == sample_incident_json
    assert output["new_incidents"]["new_incident_2"] == sample_incident_json
