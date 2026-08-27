"""`IngestionIssue` bookkeeping for pipeline-stage failures.

Split out from `upsert.py`'s `ConflictRecord` helpers rather than folded into
them: these cover fetch/parse/validation/`Include` failures, which are
pipeline-stage problems keyed by `(repository, path)`, not claim-arbitration
outcomes keyed by `(kind, namespace, name)`. Kept alongside `pipeline.py`
(not inside `upsert.py`) so both `pipeline.py` and `Include` expansion can
call it without pulling in claim-arbitration machinery.
"""

from .models import IngestionIssue, RegisteredRepository


def _record_issue(repo: RegisteredRepository, path: str, message: str) -> None:
    issue = IngestionIssue.objects.filter(repository=repo, path=path).first()
    if issue is None:
        IngestionIssue.objects.create(
            repository=repo,
            repo_full_name=str(repo),
            path=path,
            message=message,
        )
    else:
        issue.repo_full_name = str(repo)
        issue.message = message
        issue.is_active = True
        issue.save(
            update_fields=["repo_full_name", "message", "is_active", "last_seen"]
        )


def _resolve_issue(repo: RegisteredRepository, path: str) -> None:
    IngestionIssue.objects.filter(repository=repo, path=path, is_active=True).update(
        is_active=False
    )
