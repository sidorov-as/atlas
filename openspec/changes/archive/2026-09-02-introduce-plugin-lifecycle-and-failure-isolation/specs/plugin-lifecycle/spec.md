## ADDED Requirements

### Requirement: Plugins move through a defined lifecycle
A plugin SHALL move through the states installed, active, disabled, removed, and explicitly purged; disabling SHALL suppress its contributions while preserving its code and data.

#### Scenario: Disabling suppresses contributions without deleting data
- **WHEN** an active plugin is set to disabled in the deployment manifest
- **THEN** its contributions no longer register and its permission/capability registrations are inactive, while its database tables and rows remain unchanged

### Requirement: Removal never reverses migrations or deletes data
Omitting a plugin from a distribution's manifest SHALL NOT reverse its migrations or delete its data.

#### Scenario: A removed plugin's data survives
- **WHEN** a plugin is removed from the manifest for a new build
- **THEN** its previously applied migrations remain in place and its tables and rows are untouched

### Requirement: Reinstalling a compatible version restores full functionality
Reselecting a plugin at a compatible version after removal SHALL restore its previous functionality against its preserved data.

#### Scenario: Reinstalling a removed plugin
- **WHEN** a previously removed plugin is reselected at a compatible version
- **THEN** its contributions register again and it operates against the data it left behind

### Requirement: Purge is a separate, explicit, scoped operation
Deleting a plugin's data SHALL require a separate explicit purge operation, performed while the plugin's code is still installed, that reports its deletion scope before deleting.

#### Scenario: Purge reports scope before deleting
- **WHEN** an operator initiates a purge of a plugin
- **THEN** the operation reports the tables and row counts it will delete before any deletion occurs, and requires explicit confirmation to proceed

#### Scenario: Purge requires the plugin's code to still be present
- **WHEN** an operator attempts to purge a plugin whose code has already been removed
- **THEN** the purge operation is rejected, since it cannot validate deletion scope without the plugin's models
