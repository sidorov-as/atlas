## ADDED Requirements

### Requirement: Outbound fetch targets are resolved and verified before connecting
The `atlas_plugin_api.safe_http` helper SHALL resolve a target hostname's DNS
once, reject the request if any resolved address falls in a private,
loopback, link-local, multicast, unique-local, or otherwise IANA-reserved
range, and connect only to a verified address — never re-resolving the
hostname at connect time.

#### Scenario: Request to a private-range address is rejected
- **WHEN** a caller requests a URL whose hostname resolves to an RFC1918
  address (e.g. `10.0.0.5`)
- **THEN** the helper raises before any network connection to that address is
  attempted

#### Scenario: Request to a loopback address is rejected
- **WHEN** a caller requests a URL whose hostname resolves to `127.0.0.1` or
  `::1`
- **THEN** the helper raises before any network connection is attempted

#### Scenario: Request to a link-local address is rejected
- **WHEN** a caller requests a URL whose hostname resolves to a link-local
  address (e.g. `169.254.169.254`, a common cloud metadata endpoint)
- **THEN** the helper raises before any network connection is attempted

#### Scenario: Verified address is used for the actual connection
- **WHEN** a caller requests a URL whose hostname resolves to one or more
  publicly-routable addresses
- **THEN** the helper connects to one of the resolved and verified addresses
  directly, while presenting the original hostname as the `Host` header and
  TLS SNI value

### Requirement: Redirects are re-validated before being followed
The helper SHALL NOT follow an HTTP redirect to a new address without
independently resolving and verifying that address against the same
rejection rules applied to the original request, up to a caller-configurable
maximum number of hops.

#### Scenario: Redirect to a disallowed address is not followed
- **WHEN** a fetched response redirects to a URL whose hostname resolves to a
  private, loopback, or link-local address
- **THEN** the helper does not follow the redirect and raises instead

#### Scenario: Redirect to a verified public address is followed
- **WHEN** a fetched response redirects to a URL whose hostname resolves only
  to publicly-routable addresses, within the configured hop limit
- **THEN** the helper follows the redirect after re-validating it

#### Scenario: Caller can disable redirects entirely
- **WHEN** a caller sets the maximum redirect hops to zero
- **THEN** the helper does not follow any redirect and instead returns or
  raises on the redirect response

### Requirement: Response reads are bounded regardless of declared size
The helper SHALL support a caller-supplied maximum response size, enforced by
reading the response body incrementally and aborting once the cap is
exceeded, independent of any `Content-Length` header the response declares.

#### Scenario: Oversized response is aborted mid-stream
- **WHEN** a response body exceeds the caller-supplied byte cap while being
  read, whether or not `Content-Length` was present or accurate
- **THEN** the helper stops reading and raises, without buffering the entire
  body first

### Requirement: Request URLs are constrained by scheme and structure
The helper SHALL reject request URLs that contain embedded credentials or a
fragment, and SHALL only allow the HTTPS scheme unless the caller explicitly
opts into HTTP for that request.

#### Scenario: URL with embedded credentials is rejected
- **WHEN** a caller requests a URL containing a `user:password@host`
  authority component
- **THEN** the helper raises before making any request

#### Scenario: Non-HTTPS URL is rejected by default
- **WHEN** a caller requests an `http://` URL without explicitly opting into
  HTTP for that request
- **THEN** the helper raises before making any request

#### Scenario: Caller can opt into HTTP explicitly
- **WHEN** a caller requests an `http://` URL and has explicitly opted into
  allowing HTTP for that request
- **THEN** the helper proceeds, subject to all other verification rules
