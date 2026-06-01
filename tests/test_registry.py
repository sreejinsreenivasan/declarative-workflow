import pytest

from workflow_core.registry import Registry


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_and_resolve(registry):
    @registry.register("http")
    class HTTPNode:
        pass

    assert registry.resolve("http") is HTTPNode


def test_register_duplicate_raises(registry):
    @registry.register("http")
    class HTTPNode:
        pass

    with pytest.raises(ValueError, match="already registered"):
        @registry.register("http")
        class AnotherNode:
            pass


def test_resolve_unknown_raises(registry):
    with pytest.raises(KeyError, match="not registered"):
        registry.resolve("unknown")


def test_contains_registered_type(registry):
    @registry.register("form")
    class FormNode:
        pass

    assert "form" in registry


def test_not_contains_unregistered_type(registry):
    assert "missing" not in registry


def test_register_returns_class_unchanged(registry):
    @registry.register("transform")
    class TransformNode:
        pass

    assert TransformNode.__name__ == "TransformNode"
