## 1. Required services in the composer

- [x] 1.1 Add a required-service declaration to plugin static metadata (id, purpose, image, port, health check, configuration keys)
- [x] 1.2 Validate declarations at composition: identical ids with conflicting definitions fail naming both plugins
- [x] 1.3 Record required services in the lock with a pinned image reference and no secret values
- [x] 1.4 Support marking a service as externally provided with an address in the manifest, and fail when the address is missing
- [x] 1.5 Add an optional data path to the service declaration and mount a named volume for it in generated inputs
- [x] 1.6 Generate deployment inputs for each required service and wire its address and secret references into the plugin's configuration; omit when the plugin is not selected
- [x] 1.7 Tests for no services, one service, external instance, conflicts and lock reproducibility

## 2. Adapter plugin

- [x] 2.1 Scaffold the plugin package, descriptor, configuration schema and declared service
- [x] 2.2 Implement the HTTP client with configured endpoint, key and timeouts, without logging the key
- [x] 2.3 Implement reversible id encoding and storing the original id
- [x] 2.4 Implement index creation with ranked searchable attributes and kind as a filterable attribute
- [x] 2.5 Implement upsert and delete that wait for task completion within the timeout and surface failures
- [x] 2.6 Implement query with kind filter, pagination and scores
- [x] 2.7 Implement atomic replace-all through a temporary index and swap, discarding on failure
- [x] 2.8 Convert native highlights to the neutral safe marker form and declare capabilities
- [x] 2.9 Implement health reporting
- [x] 2.10 Register the engine in the runtime hook

## 3. Tests

- [x] 3.1 Run the shared conformance suite against a real instance in CI
- [x] 3.2 Test awkward ids, markup in content, typo tolerance and filter behaviour
- [x] 3.3 Test write failure, timeout and instance-down behaviour through the drain job

## 4. Distribution and deployment

- [x] 4.1 Add an example manifest selecting the adapter and verify composition fails with both engines
- [x] 4.2 Verify generated compose inputs start the service and the plugin connects
- [x] 4.3 Verify the default distribution and the demo are unchanged

## 5. Documentation

- [x] 5.1 Write the engine selection and operating page including volume, keys and rebuild after switching
- [x] 5.2 Document declaring required services for plugin authors
- [x] 5.3 Update the engine authoring guide with the second adapter as a reference

## 6. Verification

- [x] 6.1 End-to-end test: switch engines, rebuild, and search through the same UI and endpoint
- [x] 6.2 Run the full local CI target and fix regressions
