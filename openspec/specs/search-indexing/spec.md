# search-indexing Specification

## Purpose
Pending-change tracking, incremental indexing, periodic full rebuild, failure handling and index status.

## Requirements

### Requirement: Changes are recorded in the same transaction as the write
When a watched model instance of a registered source is saved or deleted, the system SHALL record the affected document ids with the operation in a pending table within the same database transaction, de-duplicated by document id.

#### Scenario: Rolled-back write leaves no pending change
- **WHEN** a watched instance is saved inside a transaction that is rolled back
- **THEN** no pending change remains

#### Scenario: Repeated writes coalesce
- **WHEN** the same document is changed several times before indexing runs
- **THEN** one pending entry for that document exists

#### Scenario: Delete is recorded
- **WHEN** a watched instance is deleted
- **THEN** a delete (or reindex-to-detect-absence) pending entry exists for the affected document id

### Requirement: Pending changes are indexed by a short-interval job
A scheduled job SHALL take pending changes in batches, load documents from the owning source, upsert present documents and delete absent ones through the engine, and remove the processed pending rows only after the engine accepted the change.

#### Scenario: Engine accepts a batch
- **WHEN** the job processes a batch and the engine succeeds
- **THEN** the documents are queryable and the pending rows are removed

#### Scenario: Engine is unavailable
- **WHEN** the engine rejects or cannot be reached
- **THEN** pending rows remain, the failure is recorded in status, and the next run retries them

#### Scenario: Document no longer exists
- **WHEN** a pending document id is no longer produced by its source
- **THEN** it is deleted from the index

### Requirement: A periodic full rebuild repairs the index
A scheduled job SHALL rebuild the entire index from all registered sources and replace the engine's content atomically, at a configurable interval, and SHALL also be runnable on demand through a management command.

#### Scenario: Bulk update missed by signals
- **WHEN** rows changed through a bulk operation that emitted no signal
- **THEN** the next rebuild brings the index in line with the data

#### Scenario: Stale document removed
- **WHEN** a document exists in the index but no source produces it
- **THEN** it is absent after the rebuild

#### Scenario: Manual rebuild
- **WHEN** an operator runs the reindex command
- **THEN** the same rebuild runs to completion without needing the scheduler

### Requirement: Job intervals are configurable
The drain and rebuild intervals SHALL be configurable in the search plugin's configuration, with defaults of 10 seconds and 6 hours.

#### Scenario: Default intervals
- **WHEN** no interval is configured
- **THEN** pending changes are drained every 10 seconds and the index is rebuilt every 6 hours

#### Scenario: Configured intervals
- **WHEN** an operator sets different intervals
- **THEN** the jobs run at the configured intervals

### Requirement: An empty index is built at start
When the scheduler starts and the engine holds no documents while sources do, a rebuild SHALL run once immediately.

#### Scenario: First enablement
- **WHEN** search is enabled on a catalog with existing content
- **THEN** the index is built at scheduler start without waiting for the rebuild interval

#### Scenario: Engine switched
- **WHEN** the engine plugin is replaced and the new engine is empty
- **THEN** a rebuild runs at scheduler start

### Requirement: Indexing state is observable
The system SHALL record the time of the last successful drain, the last successful rebuild, the number of pending changes, the age of the oldest pending change, and the last error, and make them available through the status endpoint.

#### Scenario: Status reflects backlog
- **WHEN** pending changes exist
- **THEN** status reports their count and the age of the oldest

#### Scenario: Status reflects the last failure
- **WHEN** the last drain failed
- **THEN** status reports the failure message and time

### Requirement: An index can be prebuilt without a scheduler
The reindex command SHALL build the complete index without requiring the scheduler or any other long-running process, so an image or deployment can ship with a ready index.

#### Scenario: Index built at image build time
- **WHEN** the reindex command runs after the catalog is seeded and no scheduler exists
- **THEN** the first search request after startup returns indexed results

#### Scenario: Edit in a deployment without a scheduler
- **WHEN** content is edited and no scheduler is running
- **THEN** the change stays pending and status reports the backlog and its age instead of failing silently

### Requirement: Indexing is inert when search is not selected
When the search plugin is not selected or is disabled, the system SHALL NOT connect signals, write pending changes or schedule indexing jobs.

#### Scenario: Search disabled
- **WHEN** the search plugin is disabled
- **THEN** writes to watched models record no pending changes and its jobs are paused
