# API specs

Endpoints and operations are never written directly. They are parsed from the document attached to an API
entity, so attaching the spec is how they appear.

## Choosing how to attach

| Situation                                                                | Do                                                                           |
|--------------------------------------------------------------------------|------------------------------------------------------------------------------|
| An OpenAPI or AsyncAPI file is in the repository or provided by the user | `specSource: "inline"`, `specContent`: the file text, unchanged              |
| The user gives a public HTTPS address of the document                    | `specSource: "url"`, `specUrl`: that address                                 |
| No document exists                                                       | `specSource: "none"`; tell the user endpoints appear once a spec is attached |
| `grpc` or `graphql` type                                                 | Stored, but not parsed into endpoints or operations; tell the user           |

Use the document text as is; never transcribe or rewrite a spec by hand, and never invent endpoints.

## Size limit

Inline `specContent` is limited to 2 MiB. If the file is larger, warn the user and do not send it inline. Offer
`specSource: "url"` if the document is available at a public HTTPS address.

## URL fetching

The server fetches the URL itself, with safety limits: a 10 second timeout, a 20 MiB response cap, and
rejection of unsafe targets (SSRF protection: private or internal addresses are refused, and plain HTTP is
refused unless the host is allowlisted). So the address must be public HTTPS. For a spec on a private or
internal host, use `inline` instead.

## Verify after the write

1. Read the API back with `get_entity`.
2. Check the flags in `spec`: `specResolveFailed` (the URL could not be fetched or the body was unusable),
   `endpointsSyncFailed`, `operationsSyncFailed`. Report any that are true.
3. Confirm the expected content appeared: `search_api_endpoints` (OpenAPI) or `search_api_operations`
   (AsyncAPI) with the API's id. Report how many were found. If zero when the document defines some, say so
   instead of reporting success.

If the tools for endpoints or operations are not available, say that you could not verify the count and report
only the flags.

## Updating

Re-attaching changes `specSource`, `specUrl`, or `specContent` through `update_entity`. Read the API back afterwards
and verify as above.
