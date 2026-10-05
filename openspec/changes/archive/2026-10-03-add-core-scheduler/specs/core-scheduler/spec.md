## ADDED Requirements

### Requirement: Core owns a single scheduler process
Core SHALL provide one `runapscheduler` management command that starts a scheduler backed by the shared persistent job store and blocks until it is signalled to stop. The command SHALL be available in every distribution regardless of which plugins are selected.

#### Scenario: Scheduler starts without any job-contributing plugin
- **WHEN** `runapscheduler` is started in a distribution where no selected plugin contributes jobs
- **THEN** the process starts, registers no jobs, and keeps running until it receives a stop signal

#### Scenario: Scheduler stops cleanly on signal
- **WHEN** the process receives SIGINT or SIGTERM
- **THEN** the scheduler shuts down and the process exits

### Requirement: Plugins contribute jobs through a declared hook
A plugin SHALL contribute scheduled jobs by exposing a job-registration hook that receives the scheduler, and SHALL declare the ids of the jobs it registers in its descriptor. Core SHALL call the hook of every selected plugin that is not disabled when the scheduler starts. Importing a plugin module SHALL NOT start or register any job.

#### Scenario: Active plugin jobs are registered
- **WHEN** the scheduler starts and an active plugin exposes the job-registration hook
- **THEN** the hook is called once with the scheduler and its jobs are registered under the ids declared in its descriptor

#### Scenario: Plugin without the hook is skipped
- **WHEN** an active plugin exposes no job-registration hook
- **THEN** the scheduler starts normally and registers nothing for that plugin

#### Scenario: Disabled plugin contributes nothing
- **WHEN** a selected plugin is disabled
- **THEN** its job-registration hook is not called

#### Scenario: Job id missing from the descriptor
- **WHEN** a plugin's hook registers a job whose id is not declared in the plugin's descriptor
- **THEN** startup fails identifying the plugin and the undeclared id

### Requirement: Job state follows plugin enablement
Jobs declared by a plugin SHALL be paused while the plugin is disabled and resumed while it is active, synchronized on process start and independent of which process performs the change.

#### Scenario: Disabling a plugin pauses its jobs
- **WHEN** a plugin that declared job ids is disabled in the manifest and the runtime starts
- **THEN** those jobs are paused and do not run

#### Scenario: Re-enabling a plugin resumes its jobs
- **WHEN** a previously disabled plugin is active again and the runtime starts
- **THEN** its declared jobs are resumed

### Requirement: Jobs are isolated from each other
A job SHALL run with its own database-connection handling and a single running instance, and a failure in one job SHALL NOT stop other jobs or the scheduler.

#### Scenario: One job raises
- **WHEN** a scheduled job raises an unhandled exception
- **THEN** the failure is logged, other jobs keep running on schedule, and the failed job runs again at its next trigger

#### Scenario: A run overlaps the next trigger
- **WHEN** a job is still running when its next trigger fires
- **THEN** the overlapping run is skipped rather than executed concurrently

### Requirement: Plugins may run their work outside the shared scheduler
A plugin SHALL be able to expose a management command that performs its scheduled work once, so a deployment can run it from a separate process instead of or in addition to the shared scheduler.

#### Scenario: One-off command runs without the scheduler
- **WHEN** an operator runs a plugin's one-off management command
- **THEN** the work executes in that process without requiring `runapscheduler` to be running

### Requirement: Ingestion jobs run on the core scheduler unchanged
The ingestion plugin's discovery and spec-refresh jobs SHALL be contributed through the job-registration hook, keep their existing ids, intervals and single-instance behaviour, and the existing service entrypoint command SHALL keep starting them.

#### Scenario: Ingestion jobs still run after the change
- **WHEN** `runapscheduler` starts in a distribution that selects ingestion
- **THEN** the discovery and spec-refresh jobs are registered under their existing ids with the configured interval

#### Scenario: Distribution without ingestion
- **WHEN** `runapscheduler` starts in a distribution that does not select ingestion, including one that does not ship the ingestion package
- **THEN** it starts without importing ingestion code and without error

### Requirement: Core schema does not depend on an optional plugin
Core's database schema and migrations SHALL NOT reference ingestion, so a distribution without ingestion can apply all migrations and start. Which repository claims an entity SHALL be recorded by ingestion itself, and entities managed through ingestion SHALL keep rejecting manual writes.

#### Scenario: Migrations apply without ingestion
- **WHEN** migrations are applied in a distribution that does not select ingestion
- **THEN** they apply without error, including the scheduler app's migrations

#### Scenario: Optional plugin does not require the ingestion package
- **WHEN** another selected plugin would register into an ingestion extension point and the ingestion package is not installed
- **THEN** startup succeeds and that registration is skipped

#### Scenario: Ingested entities stay write-protected
- **WHEN** an entity was created or claimed by ingestion and a manual write is attempted
- **THEN** the write is rejected as before
