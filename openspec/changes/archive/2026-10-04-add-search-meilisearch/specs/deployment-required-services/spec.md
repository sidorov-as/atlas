## ADDED Requirements

### Requirement: A plugin can declare a required external service
A plugin's static metadata SHALL be able to declare an external service it needs, with an identifier, a purpose, a default container image reference, the port it listens on, a health check and the configuration keys by which the plugin is told where it is.

#### Scenario: Plugin without services
- **WHEN** a plugin declares no required service
- **THEN** composition, lock and generated inputs are unchanged from today

#### Scenario: Plugin with a service
- **WHEN** a selected plugin declares a required service
- **THEN** the composer includes it in its resolved view of the distribution

### Requirement: The lock records required services
The lock SHALL record each required service with its declaring plugin, identifier and pinned image reference, and SHALL NOT contain secret values.

#### Scenario: Reproducible service pin
- **WHEN** the lock is generated from the same manifest twice
- **THEN** the recorded service entries are identical

#### Scenario: Secrets absent
- **WHEN** a service needs an access key
- **THEN** the lock records the key's name or reference only

### Requirement: The composer generates deployment inputs for required services
For each required service the composer SHALL generate deployment inputs that run the service alongside the application, wire its address and secret references into the declaring plugin's configuration, and order startup so the application waits for the service's health check where the deployment target supports it.

#### Scenario: Compose topology includes the service
- **WHEN** the generated inputs are used to start the distribution
- **THEN** the service runs, is healthy, and the plugin connects to it

#### Scenario: Service omitted when plugin not selected
- **WHEN** the declaring plugin is not selected
- **THEN** no service appears in the generated inputs

### Requirement: A service can declare persistent data
A required service SHALL be able to declare a data path, and the generated deployment inputs SHALL mount a named persistent volume there.

#### Scenario: Service with data
- **WHEN** a service declares a data path
- **THEN** the generated inputs mount a named volume at that path so data survives container recreation

#### Scenario: Service without data
- **WHEN** a service declares no data path
- **THEN** no volume is generated

### Requirement: An operator can supply an existing instance
The manifest SHALL allow an operator to mark a required service as externally provided and to give its address, in which case the composer SHALL NOT generate a container for it and SHALL wire the given address into the plugin's configuration.

#### Scenario: Managed external instance
- **WHEN** the manifest marks the service as externally provided with an address
- **THEN** no container is generated and the plugin is configured with that address

#### Scenario: External instance without an address
- **WHEN** a service is marked externally provided with no address
- **THEN** composition fails identifying the service and the missing address

### Requirement: Required services are validated at composition
Composition SHALL fail when two selected plugins declare the same service identifier with conflicting definitions, or when a declared service cannot be wired to its plugin's configuration.

#### Scenario: Conflicting declarations
- **WHEN** two plugins declare the same service id with different images
- **THEN** composition fails identifying both plugins

### Requirement: Required services are documented
The documentation SHALL explain how a plugin declares a service, how an operator chooses between a generated and an external instance, and how secrets reach the plugin.

#### Scenario: Plugin author adds a service
- **WHEN** an author follows the documentation
- **THEN** they can declare a service and see it appear in generated inputs
