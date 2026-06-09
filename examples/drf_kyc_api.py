"""
Django REST Framework + workflow-core example: KYC verification API.

Demonstrates:
- Multi-step workflow orchestration via DRF ViewSet
- Form validation → API call → decision logic
- Error handling and response formatting
- Real-world use case

Usage:
    # Install dependencies
    pip install djangorestframework workflow-core

    # Configure Django settings (settings.py)
    INSTALLED_APPS = [
        'rest_framework',
        # ... others
    ]

    # Wire up URLs (urls.py)
    from rest_framework.routers import DefaultRouter
    from .views import KYCViewSet

    router = DefaultRouter()
    router.register(r'kyc', KYCViewSet, basename='kyc')

    urlpatterns = router.urls

    # Test
    curl -X POST http://localhost:8000/api/kyc/ \
      -H "Content-Type: application/json" \
      -d '{
        "full_name": "Alice Smith",
        "ssn": "123-45-6789",
        "dob": "1990-01-15"
      }'
"""

from __future__ import annotations

import asyncio
from uuid import uuid4
from typing import Any

from workflow_core import (
    Node, Registry, Runtime, Workflow,
)
from workflow_core.context import Context
from workflow_core.nodes import FormNode, HTTPNode, DecisionNode, ResponseNode
from workflow_core.result import NodeError, Result


# ---------------------------------------------------------------------------
# Workflow Definition
# ---------------------------------------------------------------------------

KYC_WORKFLOW = Workflow(
    id="kyc_verify",
    start="collect",
    nodes={
        # Step 1: Collect and validate input
        "collect": Node(
            type="form",
            params={
                "fields": {
                    "full_name": {
                        "type": "str",
                        "required": True,
                        "max_length": 100,
                    },
                    "ssn": {
                        "type": "str",
                        "required": True,
                        "max_length": 11,
                    },
                    "dob": {
                        "type": "str",
                        "required": True,
                        "min_length": 10,
                    },
                }
            },
            transitions={
                "success": "verify",
                "failure": "validation_error",
            },
        ),

        # Step 2: Call external KYC API
        "verify": Node(
            type="http",
            params={
                "method": "POST",
                "url": "https://kyc-api.example.com/verify",
                "body_key": "validated",
                "response_key": "kyc_result",
                "headers": {"Authorization": "Bearer test-token"},
            },
            transitions={
                "success": "check_risk",
                "failure": "api_error",
            },
        ),

        # Step 3: Decide based on risk score
        "check_risk": Node(
            type="decision",
            params={
                "key": "kyc_result.risk_score",
                "operator": "lt",
                "value": 50,
            },
            transitions={
                "true": "approved",
                "false": "manual_review",
            },
        ),

        # Terminals
        "approved": Node(
            type="response",
            params={
                "status": 200,
                "include": ["kyc_result", "validated"],
            },
            transitions={"success": None},
        ),
        "manual_review": Node(
            type="response",
            params={
                "status": 202,  # 202 Accepted
                "include": ["kyc_result"],
            },
            transitions={"success": None},
        ),
        "validation_error": Node(
            type="response",
            params={"status": 400},
            transitions={"success": None},
        ),
        "api_error": Node(
            type="response",
            params={"status": 502, "include": ["kyc_result"]},
            transitions={"success": None},
        ),
    },
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def get_registry() -> Registry:
    registry = Registry()
    registry.register("form")(FormNode)
    registry.register("http")(HTTPNode)
    registry.register("decision")(DecisionNode)
    registry.register("response")(ResponseNode)
    return registry


# ---------------------------------------------------------------------------
# DRF ViewSet (pseudo-code, requires Django setup)
# ---------------------------------------------------------------------------

# from rest_framework import viewsets, status
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
#
# class KYCViewSet(viewsets.ViewSet):
#     permission_classes = [IsAuthenticated]
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.runtime = Runtime(KYC_WORKFLOW, get_registry())
#
#     def create(self, request):
#         """POST /api/kyc/ - Start KYC verification"""
#         execution_id = f"kyc-{request.user.id}-{uuid4()}"
#
#         context = self.runtime.execute(
#             execution_id,
#             input_data={"input": request.data},
#         )
#
#         response_data = context.data.get("response", {})
#         return Response(
#             response_data.get("data", {}),
#             status=response_data.get("status", 200),
#         )


# ---------------------------------------------------------------------------
# Standalone Simulation (for testing without Django)
# ---------------------------------------------------------------------------

async def simulate_kyc_api_call(scenario: str) -> dict[str, Any]:
    """Simulate KYC API call without Django."""

    runtime = Runtime(KYC_WORKFLOW, get_registry())

    # Test scenarios
    scenarios = {
        "approved": {
            "full_name": "Alice Smith",
            "ssn": "123-45-6789",
            "dob": "1990-01-15",
        },
        "invalid": {
            "full_name": "Bob",
            "ssn": "invalid",
            # Missing dob
        },
    }

    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario}")

    execution_id = f"kyc-{scenario}-{uuid4()}"
    input_data = scenarios[scenario]

    print(f"\n── Scenario: {scenario}")
    print(f"   Input: {input_data}")

    context = await runtime.execute(
        execution_id,
        input_data={"input": input_data},
    )

    response = context.data.get("response", {})
    status_code = response.get("status", 200)
    data = response.get("data", {})

    print(f"   Status: {status_code}")
    print(f"   Response: {data}")

    return {
        "execution_id": execution_id,
        "status": status_code,
        "data": data,
    }


async def main():
    """Run all scenarios."""
    print("=" * 70)
    print("KYC Verification API - Workflow Simulation")
    print("=" * 70)

    # Scenario 1: Valid input
    await simulate_kyc_api_call("approved")

    # Scenario 2: Invalid input
    await simulate_kyc_api_call("invalid")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
