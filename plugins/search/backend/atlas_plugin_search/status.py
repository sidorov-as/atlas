"""Index and engine status for the status endpoint."""

from dataclasses import dataclass
from datetime import datetime

from django.db.models import Min
from django.utils import timezone

from . import runtime
from .models import IndexStatus, PendingChange


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
    engine_healthy: bool
    pending_count: int
    oldest_pending_age_seconds: int | None
    last_drain_at: datetime | None
    last_rebuild_at: datetime | None
    has_error: bool
    # Operational detail, shown to administrators only.
    engine_id: str
    engine_detail: str | None
    document_count: int | None
    last_error: str | None
    last_error_at: datetime | None
    last_error_job: str | None
    drain_interval_seconds: int
    rebuild_interval_seconds: int


def snapshot() -> StatusSnapshot:
    engine = runtime.get_engine()
    config = runtime.get_config()
    try:
        health = engine.health()
        healthy, detail, count = health.ok, health.detail, health.document_count
    except Exception as exc:  # noqa: BLE001 - any engine failure means unhealthy
        healthy, detail, count = False, f"{type(exc).__name__}: {exc}", None
    pending = PendingChange.objects.aggregate(oldest=Min("queued_at"))
    pending_count = PendingChange.objects.count()
    oldest = pending["oldest"]
    age = (
        max(0, int((timezone.now() - oldest).total_seconds()))
        if oldest is not None
        else None
    )
    index = IndexStatus.objects.filter(pk=1).first()
    return StatusSnapshot(
        engine_healthy=healthy,
        pending_count=pending_count,
        oldest_pending_age_seconds=age,
        last_drain_at=index.last_drain_at if index else None,
        last_rebuild_at=index.last_rebuild_at if index else None,
        has_error=bool(index and index.last_error),
        engine_id=engine.id,
        engine_detail=detail,
        document_count=count,
        last_error=(index.last_error or None) if index else None,
        last_error_at=index.last_error_at if index else None,
        last_error_job=(index.last_error_job or None) if index else None,
        drain_interval_seconds=config.drain_interval_seconds,
        rebuild_interval_seconds=config.rebuild_interval_seconds,
    )
