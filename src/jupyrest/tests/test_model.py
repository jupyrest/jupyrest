import pytest
import json
from jupyrest.model import NamedModel, NamedModelConflict, named_model_registry
from typing import Optional


class MyNamedModel(NamedModel):
    prop1: str
    prop2: int

    class Config:
        __ns__ = "models/MyNamedModel"


class MyNestedModel(NamedModel):
    prop1: MyNamedModel
    prop2: Optional[MyNamedModel] = None

    class Config:
        __ns__ = "models/MyNestedModel"


def test_parse_model():
    model = MyNamedModel(prop1="foo", prop2=5)
    model_json = json.loads(model.json())
    assert model_json == {"__ns__": "models/MyNamedModel", "prop1": "foo", "prop2": 5}

    parsed_model = NamedModel.parse_obj(model_json)
    assert isinstance(parsed_model, MyNamedModel)
    assert parsed_model.prop1 == "foo"
    assert parsed_model.prop2 == 5
    assert parsed_model.Config.__ns__ == "models/MyNamedModel"


def test_nested_model_schema():
    assert MyNestedModel.schema() == {
        "title": "MyNestedModel",
        "type": "object",
        "properties": {
            "prop1": {"$ref": "#/definitions/MyNamedModel"},
            "prop2": {"$ref": "#/definitions/MyNamedModel"},
            "__ns__": {"type": "string"},
        },
        "required": ["prop1", "__ns__"],
        "definitions": {
            "MyNamedModel": {
                "title": "MyNamedModel",
                "type": "object",
                "properties": {
                    "prop1": {"title": "Prop1", "type": "string"},
                    "prop2": {"title": "Prop2", "type": "integer"},
                    "__ns__": {"type": "string"},
                },
                "required": ["prop1", "prop2", "__ns__"],
            }
        },
    }


def test_model_cache_save():
    named = MyNamedModel(prop1="prop1", prop2=5)
    nested = MyNestedModel(prop1=named, prop2=named)

    NamedModel.parse_obj(named.dict())
    assert named_model_registry["models/MyNamedModel"] == MyNamedModel

    NamedModel.parse_obj(nested.dict())
    assert named_model_registry["models/MyNestedModel"] == MyNestedModel
    assert len(named_model_registry.keys()) == 2


def test_iter_subclasses():
    class Parent(NamedModel):

        class Config:
            __ns__ = "parent"

    class SubClass(Parent):

        class Config:
            __ns__ = "subclass"

    class InnerSubClass(SubClass):

        class Config:
            __ns__ = "inner-subclass"

    subclasses = set(Parent._iter_subclasses())

    assert len(subclasses) == 3
    assert Parent in subclasses
    assert SubClass in subclasses
    assert InnerSubClass in subclasses
