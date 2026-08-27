# Mapping LDAP search-and-bind to `atlas.auth.providers.v1`

This is an implementation map for a future single-step LDAP credential plugin.
It is not an LDAP implementation, certification, or promise that Atlas ships a
production LDAP provider. The custom example intentionally needs no OpenLDAP
service. A maintained LDAP client library and a separately reviewed plugin can
implement this flow without changing the v1 credential contract.

The plugin implements `CredentialAuthenticationProvider` and imports its
runtime types from `atlas_plugin_api` only. In particular, the mapping below
uses `CredentialFlowContext`, `CredentialInput`, `VerifiedIdentity`,
`AssuredAttribute`, `ExternalGroupSnapshot`, and `AuthenticationFailure`; it
does not require Core models, registries, session helpers, or allauth internals.

## Typed private configuration

A plugin-owned `PluginConfigSchema` should validate and receive only its
namespaced values:

| Directory concern | Typed configuration                                                  | Required validation                                                                                                         |
|-------------------|----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| Authority         | immutable `sourceId`, for example `urn:atlas:directory:corp-prod-v1` | Non-empty, operator-declared, never inferred from a login or silently repointed                                             |
| Connection        | LDAP(S) endpoints, base DN, search scope                             | Allowlisted destinations; no caller-supplied URL; ordered failover must preserve one authority                              |
| Search            | user filter template and username attribute                          | Escape filter assertion values with the client library; never concatenate raw input                                         |
| Service bind      | bind DN plus `SecretRef` password                                    | Resolve only in backend memory; reject anonymous service bind unless the directory design explicitly and safely requires it |
| User bind         | DN returned by the unique search plus submitted password             | Escape/encode DN values with the library; never build a DN by string concatenation                                          |
| Identity          | immutable UUID/binary-id attribute                                   | Exactly one non-empty stable value; mutable DN, username, or email is not the subject                                       |
| Profile           | allowlisted username/display-name/email attributes                   | Normalize values and assign explicit assurance provenance                                                                   |
| Groups            | membership query, stable group key, page size/limit                  | Retrieve every page before returning `complete`; truncation becomes `unavailable`                                           |
| Bounds            | connect/read/overall timeout, max entries/bytes/pages                | Positive finite values constrained below Core's `CredentialFlowContext.deadline`                                            |
| Transport         | CA bundle/trust store, hostname verification, StartTLS/LDAPS choice  | Certificate and hostname verification mandatory; never retry plaintext after TLS failure                                    |

Secret-capable fields use `str | SecretRef`; production manifests use only
`{fromEnv: ...}` or an equivalent centrally supported secret reference. The
schema exposes none of these through `PUBLIC_FIELDS`, `repr`, diagnostics, the
lock, or frontend bootstrap.

## SDK input mapping

`CredentialFlowContext` supplies:

- `provider_id`: must match the provider descriptor;
- `source_id`: must equal the validated immutable directory namespace;
- `attempt_id` and `correlation_id`: safe correlation identifiers, never bind
  credentials or authorization inputs;
- `deadline`: a timezone-aware Core deadline. Every DNS, connect, TLS, bind,
  search, and pagination step uses the remaining budget and stops before it.

`CredentialInput.values` supplies standard `username` and `password` fields.
The provider treats them as ephemeral. Core rejects missing/empty fields, and
the provider still fails closed if invoked directly with incomplete data. It
must not persist, echo, trace, cache, or log either value.

## Secure verification sequence

1. Check the context provider/source and remaining deadline.
2. Normalize the login name only according to documented directory rules.
3. Escape it as an LDAP filter assertion value and search under the configured
   base with the protected service bind.
4. Require exactly one entry. Zero and multiple results both return the same
   public `INVALID_CREDENTIALS` result; neither discloses account existence.
5. Reject an empty password before any user bind. Require an authenticated user
   bind; anonymous bind success is not credential verification.
6. Read the stable directory UUID from that verified entry. Reject missing,
   ambiguous, malformed, or mutable substitutes.
7. Read only allowlisted profile attributes and attach provenance. A directory-
   managed display name can be `AUTHORITY_MANAGED`; email uses
   `VERIFIED_OWNERSHIP` only if the authority actually verifies ownership under
   the deployment's assurance policy. Otherwise use `SELF_ASSERTED` or omit it.
8. Retrieve group keys with full pagination and bounded sizes. Return
   `ExternalGroupSnapshot.complete(groups)` only after every page succeeds;
   complete-empty is authoritative. Timeout, size limit, referral ambiguity, or
   partial pagination returns unavailable/failure, never a truncated complete
   set.
9. Unbind/close connections and discard service/user bind secrets immediately.

TLS validation applies to every connection and referral. Referrals should be
disabled unless every destination and credential-forwarding rule is explicitly
validated. A certificate failure, hostname mismatch, unexpected destination,
or StartTLS failure ends verification; there is no insecure retry.

## SDK result mapping

Successful verification returns exactly one `VerifiedIdentity`:

| Public result field | LDAP value                                                                    |
|---------------------|-------------------------------------------------------------------------------|
| `provider_id`       | descriptor id                                                                 |
| `source_id`         | configured immutable directory namespace                                      |
| `subject`           | normalized stable directory UUID, never DN/email/username                     |
| `profile`           | normalized allowlisted username, display name, and email                      |
| `attributes`        | `AssuredAttribute` values with evidence-appropriate provenance                |
| `groups`            | explicit `complete`, `complete(())`, `unavailable`, or `unsupported` snapshot |

The result never contains the LDAP connection, bind DN/password, submitted
password, raw entry/attributes, Django User, Actor, Group, permission, staff or
superuser flags. Roles and groups are not permissions. Core alone applies
configured mappings and provisioning policy.

Failures use only allowlisted `AuthenticationFailure` values:

| Condition                                                          | Result                                                                             |
|--------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Empty/wrong password, no user, ambiguous user, anonymous bind      | `INVALID_CREDENTIALS`, non-retryable and indistinguishable                         |
| DNS/connect/TLS timeout, directory outage, deadline exhausted      | `UNAVAILABLE`, retryable where appropriate                                         |
| Missing UUID, source mismatch, malformed/oversized normalized data | `INVALID_RESULT`                                                                   |
| Group lookup incomplete in exact mode                              | unavailable snapshot or `UNAVAILABLE`; Core fails closed and does not renew grants |

Exception strings, directory diagnostic messages, searched DNs, raw entries,
and server response bodies do not cross the provider boundary. Health checks may
report only provider id and safe availability category, use their own bounded
operation, and never perform a user authentication.

## Ownership split

The LDAP plugin owns transport, TLS, escaping, search uniqueness, bind
verification, stable UUID extraction, profile assurance, complete group
pagination, deadlines, and sanitized failures. Authentication Core owns provider
selection, CSRF and return URLs, rate limits, attempts, source binding,
Principal/Actor provisioning, Group mapping and exact/additive grants, audit,
session creation/expiry/revocation, logout, read-only enforcement, and all
authorization decisions.

Run the public `CredentialProviderContractHooks` suite plus provider-specific
integration tests against representative directory servers, including TLS,
referrals, escaping, zero/multiple results, empty/anonymous bind, paging,
timeouts, size bounds, source/UUID stability, redaction, and outage isolation.
