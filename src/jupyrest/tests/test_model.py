import pytest
import json
from jupyrest.model import NamedModel, NamedModelConflict
from typing import Optional


class MyNamedModel(NamedModel):
    __ns__ = "models/MyNamedModel"

    prop1: str
    prop2: int


class MyNestedModel(NamedModel):
    __ns__ = "models/MyNestedModel"

    prop1: MyNamedModel
    prop2: Optional[MyNamedModel] = None


def test_parse_model():
    model = MyNamedModel(prop1="foo", prop2=5)
    model_json = json.loads(model.json())
    assert model_json == {"__ns__": "models/MyNamedModel", "prop1": "foo", "prop2": 5}

    parsed_model = NamedModel.parse_obj(model_json)
    assert isinstance(parsed_model, MyNamedModel)
    assert parsed_model.prop1 == "foo"
    assert parsed_model.prop2 == 5
    assert parsed_model.__ns__ == "models/MyNamedModel"


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
    assert NamedModel.__nsmap__["models/MyNamedModel"] == MyNamedModel
    assert len(NamedModel.__nsmap__.keys()) == 1

    NamedModel.parse_obj(nested.dict())
    assert NamedModel.__nsmap__["models/MyNestedModel"] == MyNestedModel
    assert len(NamedModel.__nsmap__.keys()) == 2


def test_model_cache_conflict():
    """
    We have 2 models with the same name (__ns__).
    When we try to parse these models, we except
    to see an exception telling us that we have
    a conflict.
    """

    class ConflictingModel1(NamedModel):
        __ns__ = "models/conflict"

    class ConflictingModel2(NamedModel):
        __ns__ = "models/conflict"

    cm1 = ConflictingModel1()
    cm2 = ConflictingModel2()

    # we expect to see an exception when
    # parsing either model
    with pytest.raises(NamedModelConflict):
        NamedModel.parse_obj(cm1.dict())

    with pytest.raises(NamedModelConflict):
        NamedModel.parse_obj(cm2.dict())


def test_iter_subclasses():
    class Parent(NamedModel):
        __ns__ = "parent"

    class SubClass(Parent):
        __ns__ = "subclass"

    class InnerSubClass(SubClass):
        __ns__ = "inner-subclass"

    subclasses = set(Parent._iter_subclasses())

    assert len(subclasses) == 3
    assert Parent in subclasses
    assert SubClass in subclasses
    assert InnerSubClass in subclasses
