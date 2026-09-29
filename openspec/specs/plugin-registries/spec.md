# plugin-registries Specification

## Purpose
Capability, permission, and plugin-identity registries that are populated only from the deployment's operator-selected plugins during a phased startup, so that a merely-importable plugin stays inert and a composition failure (such as a duplicate registered id) prevents the backend process from accepting traffic.

## Requirements

### Requirement: Installed is not the same as selected
Merely having a plugin's Python distribution importable in the environment SHALL NOT activate it; only a plugin explicitly named in the deployment's selection SHALL be loaded.

#### Scenario: An importable but unselected plugin is inert
- **WHEN** a plugin distribution is present in the Python environment but not named in the deployment's selected-plugins list
- **THEN** its Django apps are not added to `INSTALLED_APPS` and none of its registrations run

### Requirement: Static metadata is readable before Django setup
A plugin's identity, version, compatibility ranges, and Django app list SHALL be readable without importing Django models or triggering `django.setup()`.

#### Scenario: INSTALLED_APPS is computed from static descriptors
- **WHEN** the backend starts
- **THEN** the list of Django apps to install is computed by reading each selected plugin's static descriptor, before `django.setup()` runs

### Requirement: Startup is phased
Backend startup SHALL read selected static descriptors, verify identities, generate `INSTALLED_APPS`, run `django.setup()`, then load runtime entry points and assemble the capability, permission, and Entity Kind registries, in that order.

#### Scenario: Runtime registration happens after Django setup
- **WHEN** a plugin's runtime module registers a capability or permission
- **THEN** that registration happens only after `django.setup()` has completed, never before

### Requirement: Duplicate registered ids fail composition
Two plugins registering the same capability id, permission id, or Entity Kind id SHALL cause composition validation to fail.

#### Scenario: Two plugins claim the same permission id
- **WHEN** two selected plugins each register a permission with the same id
- **THEN** composition validation fails and identifies the conflicting id and both registering plugins

### Requirement: Composition failure prevents accepting traffic
A composition validation failure SHALL prevent the backend process from starting successfully; it SHALL NOT be reported only as a warning after the process has begun serving requests.

#### Scenario: A duplicate id stops the process at startup
- **WHEN** composition validation fails during startup
- **THEN** the process exits without binding to its listening port, and no request is served
