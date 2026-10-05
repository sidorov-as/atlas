"""Scheduler job bodies. Failures are logged and recorded, never raised, so a
broken engine does not turn into a scheduler error loop."""

import logging

from . import indexer

logger = logging.getLogger(__name__)


def drain_job() -> None:
    try:
        result = indexer.drain_pending()
    except Exception:
        logger.exception("Search drain job crashed")
        return
    if result.skipped:
        logger.debug("Search drain skipped: another indexing run is in progress")


def rebuild_job() -> None:
    try:
        indexer.rebuild_index()
    except indexer.IndexingBusyError:
        logger.info("Search rebuild skipped: another indexing run is in progress")
    except Exception:
        logger.exception("Search rebuild job failed")


def initial_rebuild_job() -> None:
    try:
        if indexer.rebuild_if_index_empty():
            logger.info("Search index was empty; rebuilt it at scheduler start")
    except Exception:
        logger.exception("Initial search rebuild failed")
