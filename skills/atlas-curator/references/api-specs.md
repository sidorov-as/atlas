# API specs

Endpoints and operations are never written directly. They are parsed from the document attached to an API
entity, so attaching the spec is how they appear.

## Choosing how to attach

| Situation                                                                | Do                                                                           |
|--------------------------------------------------------------------------|------------------------------------------------------------------------------|
| A small OpenAPI or AsyncAPI file (under about 100 KB) is in the repository or provided by the user | `specSource: "inline"`, `specContent`: the file text, unchanged |
| A large file, or any file on disk, and you can run shell commands        | Upload link (see below): `request_attach`, then `curl -T`; the text stays out of the conversation |
| The user gives a public HTTPS address of the document                    | `specSource: "url"`, `specUrl`: that address                                 |
| No document exists                                                       | `specSource: "none"`; tell the user endpoints appear once a spec is attached |
| `grpc` or `graphql` type                                                 | Stored, but not parsed into endpoints or operations; tell the user           |

Use the document text as is; never transcribe or rewrite a spec by hand, and never invent endpoints.

## Size limit

Inline `specContent` is limited to 2 MiB, and every byte of it passes through the conversation, so keep it for
small files. A larger file goes through the upload link (up to 20 MiB). If you cannot run shell commands and
the file is over 2 MiB, warn the user and do not send it inline. Offer `specSource: "url"` if the document is
available at a public HTTPS address, or ask the user to upload it.

## Upload link for large files

Only when the `request_attach` tool is present and you can run shell commands:

1. Create the API first with `specSource: "none"` (an API without a spec is valid).
2. Call `request_attach` with `entity` (`api:<name>`) and `field` `spec`. It needs the `apis:write` scope.
3. Run the returned `exampleCommand`, replacing `<file>` with the path of the spec file. Do not read the file
   into the conversation to do this.
4. Read the JSON reply. `ok: true` means the spec was saved; `summary` gives the spec kind and the number of
   endpoints or operations. `ok: false` carries the reason (not parseable, over the limits, wrong kind of
   document for the API's `type`): fix the file and run the same command again, the link stays valid until it
   expires. A 404 means the link expired or was already used; request a new one.
5. If the URL's host does not connect (for example `host.docker.internal` when the MCP server runs in a
   container), replace the host with one your shell can reach and keep the path.

The URL is a secret. Do not print it for the user, put it in a file, or commit it. A successful upload sets the
spec source to inline, replacing a `url` source. Then verify as below.

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

Re-attaching changes `specSource`, `specUrl`, or `specContent` through `update_entity`, or uploads a new file
through a new link. Read the API back afterwards
and verify as above.
