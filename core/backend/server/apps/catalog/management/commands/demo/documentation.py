"""Purpose-specific Markdown fixtures for the booking-demo catalog."""

from collections.abc import Iterable, Mapping


def _names(values: object) -> str:
    """Format catalog references for prose while keeping empty sections
    useful."""
    if not isinstance(values, Iterable) or isinstance(values, str):
        return "None recorded"
    names = [f"`{value}`" for value in values]
    return ", ".join(names) if names else "None recorded"


def _owner(spec: Mapping[str, object]) -> str:
    return str(spec.get("owner", "the owning team")).replace("-", " ").title()


def _system_documentation(spec: Mapping[str, object]) -> str:
    """Describe a system as a business capability and decision-making
    surface."""
    context = str(spec.get("documentation", "")).strip()
    context_section = (
        f"\n## Strategic context\n\n{context}\n" if context else ""
    )
    return f"""# {spec["title"]}

## Business capability

{spec["description"]} **{spec["business_outcome"]}**

## Operating lens

| Decision area | What to evaluate |
| --- | --- |
| Primary outcome | {spec["business_outcome"]} |
| Success signal | {spec["success_signal"]} |
| Planning question | {spec["planning_question"]} |
| Material risk | {spec["material_risk"]} |

## Ownership and governance

**{_owner(spec)}** owns the capability roadmap, service boundaries, and \
changes that affect its customer or partner outcome. Use this catalog \
entry to align investment, prioritization, and cross-team dependency \
decisions—not as a deployment runbook.

{context_section}
{{% note info "Review cadence" %}}

Review the success signal and material risk at the system health review, \
and revisit the planning question before committing capacity.

{{% endnote %}}
"""


def _component_documentation(spec: Mapping[str, object]) -> str:
    """Describe a component through its implementation and operational
    contract."""
    component_type = str(spec["type"]).replace("-", " ")
    runbook_focus = {
        "service": (
            "Trace request latency, error rate, and downstream dependency "
            "failures."
        ),
        "worker": "Watch queue depth, job retries, and processing lag.",
        "website": (
            "Monitor client-side errors, page performance, and API "
            "availability."
        ),
    }.get(
        str(spec["type"]),
        "Monitor deployment health and dependency availability.",
    )
    context = str(spec.get("documentation", "")).strip()
    context_section = (
        f"\n## Implementation context\n\n{context}\n" if context else ""
    )
    return f"""# {spec["title"]}

## Technical role

This production unit is a **{component_type}** in `{spec["system"]}`. It \
is owned by **{_owner(spec)}** and currently has a \
**{spec["lifecycle"]}** lifecycle.
{context_section}
## Integration surface

| Direction | Catalog contracts |
| --- | --- |
| Provides | {_names(spec.get("provides_apis", []))} |
| Consumes | {_names(spec.get("consumes_apis", []))} |
| Stateful dependencies | {_names(spec.get("depends_on", []))} |
| Technology signals | {_names(spec.get("tags", []))} |

## Runbook focus

{runbook_focus} Preserve correlation IDs across API calls and \
asynchronous jobs when investigating an incident.
"""


def _resource_documentation(spec: Mapping[str, object]) -> str:
    """Describe an infrastructure resource in terms useful to operators and
    engineers."""
    resource_type = str(spec["type"])
    profiles = {
        "database": (
            "authoritative persistent state",
            "schema migrations, replication health, backups, and restore "
            "drills",
        ),
        "cache": (
            "low-latency derived state",
            "hit rate, eviction pressure, TTLs, and safe cache invalidation",
        ),
        "cluster": (
            "query and indexing workload",
            "index freshness, shard health, query latency, and reindex "
            "capacity",
        ),
        "queue": (
            "asynchronous hand-off",
            "consumer lag, retry/dead-letter policy, message retention, "
            "and ordering assumptions",
        ),
        "bucket": (
            "durable object storage",
            "object lifecycle rules, encryption, access policy, and "
            "retrieval failures",
        ),
    }
    role, controls = profiles.get(
        resource_type,
        (
            "platform infrastructure",
            "availability, access policy, and lifecycle controls",
        ),
    )
    context = str(spec.get("documentation", "")).strip()
    context_section = f"\n## Data context\n\n{context}\n" if context else ""
    return f"""# {spec["title"]}

## Infrastructure profile

This **{resource_type}** supplies {role} for `{spec["system"]}`. \
**{_owner(spec)}** is accountable for access and lifecycle decisions.
{context_section}
## Engineering controls

Prioritize {controls}.

| Concern | Verification |
| --- | --- |
| Access | Confirm least-privilege service and operator access. |
| Recovery | Verify the documented recovery path before a high-risk change. |
| Change safety | Record migration, retention, or topology changes with \
the owning team. |
"""


def _api_documentation(spec: Mapping[str, object]) -> str:
    context = str(spec.get("documentation", "")).strip()
    return f"""# {spec["title"]}

## Consumer contract

This `{spec["type"]}` contract is owned by **{_owner(spec)}** for the \
`{spec["system"]}` domain. The Specification tab is the source of truth \
for operations and payloads.

## Change expectations

Consumers should use explicit versioning, preserve idempotency where an \
operation changes state, and coordinate breaking changes with the owning \
team.

{
        context
        or "Review authentication, error semantics, and deprecation plans "
        "before integrating."
    }
"""


def _flow_documentation(spec: Mapping[str, object]) -> str:
    context = str(spec.get("documentation", "")).strip()
    return f"""# {spec["title"]}

## Operational narrative

{spec["description"]}

## How to use this flow

Read the steps as an execution trace: branch labels identify business \
decisions, while linked components, APIs, and resources show the \
accountable technical boundary. During an incident, locate the last \
confirmed step, then inspect its owner and observability data.

{
        context
        or "Validate failure branches whenever the associated policy, "
        "integration, or data model changes."
    }
"""


def documentation_for(kind: str, spec: Mapping[str, object]) -> str:
    """Return documentation whose focus matches the catalog entity kind."""
    renderers = {
        "system": _system_documentation,
        "component": _component_documentation,
        "resource": _resource_documentation,
        "api": _api_documentation,
        "flow": _flow_documentation,
    }
    return renderers[kind](spec)
