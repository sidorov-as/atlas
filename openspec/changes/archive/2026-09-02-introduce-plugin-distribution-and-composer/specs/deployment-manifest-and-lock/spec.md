## ADDED Requirements

### Requirement: Manifest declares plugin selection and artifact sources
An operator SHALL declare selected plugins, their versions, and their backend/frontend artifact sources in a source-controlled deployment manifest.

#### Scenario: Manifest names an explicit plugin and version
- **WHEN** an operator adds an entry to the manifest naming a plugin id, version, and artifact sources
- **THEN** the composer resolves that exact plugin and version for the build

### Requirement: Composer resolves the manifest to a lock file
The composer SHALL resolve a manifest to a lock file recording exact artifact versions and integrity hashes for every selected plugin and Core.

#### Scenario: Lock file records exact versions and hashes
- **WHEN** the composer resolves a manifest
- **THEN** the resulting lock file records, for every selected plugin, its exact backend and frontend artifact versions and integrity hashes

### Requirement: Nothing is downloaded at container start
A built container image SHALL contain every artifact its lock file specifies; starting the container SHALL NOT fetch any plugin artifact over the network.

#### Scenario: Container starts without network access
- **WHEN** a built container starts with no outbound network access
- **THEN** it starts successfully using only artifacts already present in the image

### Requirement: A build is reproducible from manifest and lock alone
Given the same manifest and lock file, the composer SHALL produce a build with the same selected plugin versions and generated composition.

#### Scenario: Rebuilding from the same lock produces the same composition
- **WHEN** the composer runs twice against the same manifest and lock file
- **THEN** both runs select the same plugin versions and generate the same `INSTALLED_APPS` and frontend plugin list
