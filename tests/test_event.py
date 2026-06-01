import pytest
from pydantic import ValidationError

from workflow_core.event import Event, EventType


def test_event_construction():
    event = Event(type=EventType.NODE_STARTED, execution_id="exec_001", node_id="step_a")
    assert event.type == EventType.NODE_STARTED
    assert event.node_id == "step_a"
    assert event.data == {}


def test_event_timestamp_set_automatically():
    event = Event(type=EventType.WORKFLOW_COMPLETED, execution_id="exec_001")
    assert event.timestamp is not None


def test_event_node_id_is_optional():
    event = Event(type=EventType.WORKFLOW_COMPLETED, execution_id="exec_001")
    assert event.node_id is None


def test_event_with_data():
    event = Event(
        type=EventType.CONTEXT_UPDATED,
        execution_id="exec_001",
        node_id="step_a",
        data={"key": "name", "value": "Alice"},
    )
    assert event.data["key"] == "name"


def test_event_is_immutable():
    event = Event(type=EventType.NODE_STARTED, execution_id="exec_001")
    with pytest.raises(ValidationError):
        event.execution_id = "other"


def test_all_event_types_are_strings():
    for event_type in EventType:
        assert isinstance(event_type.value, str)
        assert "." in event_type.value
