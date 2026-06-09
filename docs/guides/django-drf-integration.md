# Django REST Framework Integration

Use workflow-core for orchestration in Django REST Framework applications. While DRF handles REST conventions (serialization, authentication, permissions), workflow-core handles complex business logic and multi-step processes.

## Installation

```bash
pip install 'workflow-core[django]' djangorestframework
```

## Core Concepts

**DRF handles:** REST concerns (serialization, auth, permissions, status codes)

**workflow-core handles:** Business logic orchestration (validation chains, state machines, suspend/resume)

```python
# Good separation:
# - DRF ViewSet: HTTP layer, authentication, response formatting
# - workflow-core Runtime: business logic, data flow, persistence
```

## Basic ViewSet Integration

Create a ViewSet that executes workflows:

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from workflow_core import Runtime, Workflow, Registry

class UserViewSet(viewsets.ViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.runtime = Runtime(CREATE_USER_WORKFLOW, self.get_registry())

    def create(self, request):
        """POST /users/ - Create user"""
        context = self.runtime.execute(
            f"user-{uuid4()}",
            input_data={"input": request.data},
        )
        response = context.data.get("response", {})
        return Response(
            response.get("data", {}),
            status=response.get("status", 200),
        )

    @staticmethod
    def get_registry():
        registry = Registry()
        registry.register("form")(FormNode)
        registry.register("response")(ResponseNode)
        return registry

urlpatterns = [
    path("api/users/", UserViewSet.as_view({"post": "create"})),
]
```

## Suspend/Resume with DRF

For multi-step workflows (e.g., form submission, confirmation, processing):

```python
from workflow_core import InMemoryStore

class SignupViewSet(viewsets.ViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = InMemoryStore()  # Use RedisStore in production
        self.runtime = Runtime(SIGNUP_WORKFLOW, self.get_registry(), store=self.store)

    def list(self, request):
        """GET /signup/ - Start new signup"""
        execution_id = str(uuid4())
        context = self.runtime.execute(execution_id, input_data={})
        # Client stores execution_id for next step
        return Response({
            "execution_id": execution_id,
            "html": context.data.get("html", ""),
        })

    def create(self, request):
        """POST /signup/ - Submit signup form"""
        execution_id = request.data.get("execution_id")
        if not execution_id:
            return Response(
                {"error": "execution_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            context = self.runtime.resume(
                execution_id,
                input_data={"input": request.data},
            )
        except RuntimeError:
            return Response(
                {"error": "Signup session expired"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if "response" in context.data:
            # Workflow completed
            return Response(context.data["response"]["data"])
        else:
            # Workflow suspended (re-render form)
            return Response({"html": context.data.get("html", "")})

urlpatterns = [
    path("api/signup/", SignupViewSet.as_view({
        "get": "list",
        "post": "create",
    })),
]
```

## Combining Serializers + Workflows

Use DRF serializers for REST concerns, workflows for orchestration:

```python
from rest_framework import serializers
from workflow_core.nodes import FormNode

class UserSerializer(serializers.Serializer):
    """REST serialization for API docs, pagination, etc."""
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    age = serializers.IntegerField(min_value=0)

class UserViewSet(viewsets.ViewSet):
    def create(self, request):
        """POST /users/ - Create user"""
        # Validate request with DRF serializer
        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Pass validated data to workflow
        context = self.runtime.execute(
            f"user-{uuid4()}",
            input_data={"input": serializer.validated_data},
        )
        response = context.data.get("response", {})
        return Response(
            response.get("data", {}),
            status=response.get("status", 201),
        )
```

**When to use each:**

| Task | Use |
|------|-----|
| Validate request structure | DRF Serializer |
| Validate business rules | workflow FormNode |
| Multi-step process | workflow Nodes |
| Authentication/permissions | DRF Permissions |
| Pagination, filtering | DRF Pagination |
| Complex orchestration | workflow Runtime |

## Authentication & Permissions

Workflows run **after** DRF's authentication/permission layer:

```python
from rest_framework.permissions import IsAuthenticated

class SecureWorkflowViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        """Only authenticated users can start workflows"""
        # request.user is available here
        context = self.runtime.execute(
            f"user-{request.user.id}-{uuid4()}",
            input_data={
                "input": request.data,
                "user_id": request.user.id,  # Pass to workflow
            },
        )
        return Response(...)
```

Workflows can access user context:

```python
class CheckOwnershipNode:
    async def run(self, context, params):
        user_id = context.data.get("user_id")
        resource_id = context.data.get("resource_id")
        
        if not user_owns_resource(user_id, resource_id):
            return NodeError(code="FORBIDDEN", message="Not resource owner")
        
        return Result(transition="allowed")
```

## Error Handling

Workflows return structured errors:

```python
class CreateResourceViewSet(viewsets.ViewSet):
    def create(self, request):
        context = self.runtime.execute(
            f"resource-{uuid4()}",
            input_data={"input": request.data},
        )

        response = context.data.get("response")
        if not response:
            # Workflow suspended (e.g., needs confirmation)
            return Response(context.data.get("html", ""))

        if response.get("status") >= 400:
            # Workflow returned error
            return Response(
                response.get("data", {}),
                status=response.get("status"),
            )

        # Success
        return Response(response.get("data", {}), status=response.get("status"))
```

## Real-World Example: KYC Verification

Multi-step workflow: form → validation → API call → decision → result

**Workflow definition:**

```python
KYC_WORKFLOW = Workflow(
    id="kyc_verify",
    start="collect",
    nodes={
        "collect": Node(
            type="form",
            params={
                "fields": {
                    "full_name": {"type": "str", "required": True},
                    "ssn": {"type": "str", "required": True, "max_length": 11},
                    "dob": {"type": "str", "required": True},  # ISO date
                }
            },
            transitions={"success": "verify", "failure": "error"},
        ),
        "verify": Node(
            type="http",
            params={
                "method": "POST",
                "url": "https://kyc-api.example.com/verify",
                "body_key": "validated",
                "response_key": "kyc_result",
            },
            transitions={"success": "check_risk", "failure": "error"},
        ),
        "check_risk": Node(
            type="decision",
            params={
                "key": "kyc_result.risk_score",
                "operator": "lt",
                "value": 50,
            },
            transitions={"true": "approved", "false": "manual_review"},
        ),
        "approved": Node(
            type="response",
            params={"status": 200, "include": ["kyc_result"]},
            transitions={"success": None},
        ),
        "manual_review": Node(
            type="response",
            params={"status": 202, "include": ["kyc_result"]},  # 202 Accepted
            transitions={"success": None},
        ),
        "error": Node(
            type="response",
            params={"status": 400},
            transitions={"success": None},
        ),
    },
)
```

**DRF ViewSet:**

```python
from rest_framework import viewsets, status
from rest_framework.response import Response
from uuid import uuid4

class KYCViewSet(viewsets.ViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        registry = Registry()
        registry.register("form")(FormNode)
        registry.register("http")(HTTPNode)
        registry.register("decision")(DecisionNode)
        registry.register("response")(ResponseNode)
        self.runtime = Runtime(KYC_WORKFLOW, registry)

    def create(self, request):
        """POST /kyc/ - Start KYC verification"""
        execution_id = f"kyc-{request.user.id}-{uuid4()}"

        context = self.runtime.execute(
            execution_id,
            input_data={"input": request.data},
        )

        response_data = context.data.get("response", {})
        return Response(
            response_data.get("data", {}),
            status=response_data.get("status", 200),
        )

urlpatterns = [
    path("api/kyc/", KYCViewSet.as_view({"post": "create"})),
]
```

**Usage:**

```bash
# Start KYC verification
curl -X POST http://localhost:8000/api/kyc/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Alice Smith",
    "ssn": "123-45-6789",
    "dob": "1990-01-15"
  }'

# Response:
# {
#   "kyc_result": {
#     "status": "verified",
#     "risk_score": 35,
#     "country": "US"
#   }
# }
```

## Pagination & Filtering

Workflows don't handle pagination. For listing, use DRF's pagination:

```python
from rest_framework.pagination import PageNumberPagination

class ExecutionListViewSet(viewsets.ViewSet):
    pagination_class = PageNumberPagination

    def list(self, request):
        """GET /executions/ - List executions"""
        # Fetch from store or database
        executions = Execution.objects.filter(user=request.user)
        
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(executions, request)
        
        return paginator.get_paginated_response([
            {
                "id": ex.execution_id,
                "workflow": ex.workflow_id,
                "status": ex.status,
                "created_at": ex.created_at,
            }
            for ex in result_page
        ])
```

## Testing

Test workflows and DRF views together:

```python
from rest_framework.test import APITestCase

class KYCTestCase(APITestCase):
    def test_kyc_approved(self):
        """Test KYC with low-risk user"""
        response = self.client.post("/api/kyc/", {
            "full_name": "Alice Smith",
            "ssn": "123-45-6789",
            "dob": "1990-01-15",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("kyc_result", response.data)

    def test_kyc_manual_review(self):
        """Test KYC with high-risk user"""
        # Mock HTTP response with high risk score
        with patch("httpx.AsyncClient.request") as mock_req:
            mock_req.return_value.json.return_value = {
                "risk_score": 75,
            }
            response = self.client.post("/api/kyc/", {...})
            self.assertEqual(response.status_code, 202)  # Accepted
```

## Production Setup

**1. Use production store (Redis):**

```python
from workflow_core.adapters.redis_store import RedisStore
import redis.asyncio

redis_client = redis.asyncio.from_url("redis://localhost")
store = RedisStore(redis_client)
runtime = Runtime(WORKFLOW, registry, store=store)
```

**2. Async views (Django 3.1+):**

```python
from asgiref.sync import sync_to_async

class AsyncWorkflowViewSet(viewsets.ViewSet):
    async def create(self, request):
        """DRF auto-wraps sync views; make async for await"""
        context = await self.runtime.execute(
            f"exec-{uuid4()}",
            input_data={"input": request.data},
        )
        return Response(...)
```

**3. Logging & monitoring:**

```python
class MonitoredViewSet(viewsets.ViewSet):
    def create(self, request):
        execution_id = f"exec-{uuid4()}"
        
        # Log workflow start
        logger.info(f"Starting workflow {execution_id}", extra={
            "user_id": request.user.id,
            "workflow": "create_user",
        })
        
        context = self.runtime.execute(execution_id, {...})
        
        # Log completion
        logger.info(f"Completed workflow {execution_id}", extra={
            "status": context.data.get("response", {}).get("status"),
        })
        
        return Response(...)
```

## Summary

**workflow-core + DRF:**

| Aspect | DRF | workflow-core |
|--------|-----|---------------|
| Request parsing | ✅ Serializers | — |
| Response formatting | ✅ Response class | — |
| Authentication | ✅ Permissions | — |
| Business logic | — | ✅ Nodes |
| Multi-step processes | — | ✅ Workflows |
| State persistence | — | ✅ ExecutionStore |
| Complex validation chains | — | ✅ FormNode + Processors |

Use both: DRF for REST conventions, workflow-core for orchestration.
