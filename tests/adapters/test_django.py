"""
Django adapter unit tests.

These tests verify the Django adapter functions without requiring Django installation.
They mock Django components and test the adapter logic directly.
"""
import pytest

from workflow_core.adapters.django import add_execution_id_to_form


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

def test_add_execution_id_to_form_with_placeholder():
    """Test that execution_id is injected into form placeholders."""
    html = "<form><!-- execution_id --><input name='x' /></form>"
    result = add_execution_id_to_form(html, "exec-123")

    assert 'value="exec-123"' in result
    assert 'type="hidden"' in result
    assert 'name="execution_id"' in result
    assert "<!-- execution_id -->" not in result


def test_add_execution_id_no_placeholder():
    """Test that HTML without placeholder is unchanged."""
    html = "<form><input name='x' /></form>"
    result = add_execution_id_to_form(html, "exec-123")

    assert result == html


def test_add_execution_id_multiple_placeholders():
    """Test that all placeholders are replaced."""
    html = """
    <form>
      <!-- execution_id -->
      <input name='x' />
      <!-- execution_id -->
    </form>
    """
    result = add_execution_id_to_form(html, "exec-456")

    # Both should be replaced
    assert result.count('value="exec-456"') == 2
    assert "<!-- execution_id -->" not in result


# ---------------------------------------------------------------------------
# Integration notes
# ---------------------------------------------------------------------------
# Full integration tests with Django views require Django to be installed.
# For those tests, see the Django documentation on testing async views:
#
#   from django.test import AsyncClient
#   from django.urls import path
#   from workflow_core.adapters.django import json_api_view, form_view
#
#   # Set up Django settings
#   # Create views with decorators
#   # Use AsyncClient to test GET/POST
#
# The adapter itself is framework-agnostic and delegates workflow execution
# to the Runtime. The integration tests verify:
#   - Request metadata extraction (method, HTMX flag)
#   - Form data parsing
#   - Response routing (HTML vs JSON)
#   - Error handling (missing execution_id, not found)
