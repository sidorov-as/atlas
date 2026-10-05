# search-documentation Specification

## Purpose
Documentation of the search architecture, index schema, indexing algorithm, authoring guides and operation.

## Requirements

### Requirement: Architecture and concepts are documented
The documentation site SHALL describe the search architecture: the three seams, what is optional and replaceable, and the flow from a data change to a visible result, with a diagram.

#### Scenario: Reader learns what to replace
- **WHEN** a reader opens the search architecture page
- **THEN** they can tell which seam to replace to change the engine, the data sources or the UI

### Requirement: The index schema is documented
The documentation SHALL specify the search document format, the rules for forming document ids, which fields each source fills, and the structure of the pending-change and status data.

#### Scenario: Reader maps source data to fields
- **WHEN** a reader looks up a source in the schema page
- **THEN** they see which of its fields feed title, body and summary

### Requirement: The indexing algorithm is documented
The documentation SHALL describe the drain and rebuild algorithms step by step, including de-duplication, batching, deletion handling, failure and retry behaviour, and the known cases signals miss.

#### Scenario: Operator diagnoses a stale index
- **WHEN** an operator reads the algorithm and status pages
- **THEN** they can identify whether the backlog, the engine or the scheduler is the cause

### Requirement: Authoring guides exist for sources and engines
The documentation SHALL include a guide for writing a source (including authorization in `resolve`) and a guide for writing an engine adapter (including capability flags and running the conformance suite).

#### Scenario: Plugin author adds a source
- **WHEN** an author follows the source guide
- **THEN** they can make a model searchable and verify authorization behaviour

### Requirement: Operating instructions are documented
The documentation SHALL cover selecting the search plugin and an engine in the manifest, the scheduler requirement, the reindex command, the status endpoint, configuration of intervals, and how to run without a scheduler by prebuilding the index.

#### Scenario: Operator enables search
- **WHEN** an operator follows the operating page
- **THEN** they can enable search and confirm the index is being built
