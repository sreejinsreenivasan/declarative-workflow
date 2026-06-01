import pytest
from pydantic import ValidationError

from workflow_core.result import NodeError, Result


def test_result_defaults():
    result = Result()
    assert result.output == {}
    assert result.transition == "success"


def test_result_with_output():
    result = Result(output={"user_id": 42}, transition="success")
    assert result.output["user_id"] == 42


def test_result_custom_transition():
    result = Result(output={}, transition="needs_review")
    assert result.transition == "needs_review"


def test_result_is_immutable():
    result = Result()
    with pytest.raises(ValidationError):
        result.transition = "failure"


def test_node_error_defaults():
    error = NodeError(code="VALIDATION_FAILED", message="Age must be positive")
    assert error.details == {}
    assert error.transition == "failure"


def test_node_error_with_details():
    error = NodeError(
        code="VALIDATION_FAILED",
        message="Invalid fields",
        details={"field": "age", "value": -1},
    )
    assert error.details["field"] == "age"


def test_node_error_custom_transition():
    error = NodeError(code="KYC_FAILED", message="Identity check failed", transition="kyc_error")
    assert error.transition == "kyc_error"


def test_node_error_is_immutable():
    error = NodeError(code="ERR", message="fail")
    with pytest.raises(ValidationError):
        error.code = "OTHER"
