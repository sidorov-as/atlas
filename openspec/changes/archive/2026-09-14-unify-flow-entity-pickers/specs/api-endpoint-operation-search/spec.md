## MODIFIED Requirements

### Requirement: Cross-API Endpoint search

`atlas_plugin_apis` SHALL provide a search endpoint returning active Endpoints across every API, matching a query string against `path`, `summary`, or `operation_id`, each result carrying its owning API's reference, name, and title. The endpoint SHALL support `page` and `page_size` request parameters and SHALL return results in a paginated response (matching the pagination shape used by the plugin's other paginated list endpoints), rather than a single response capped at a fixed result count with no way to reach further matches. Results SHALL be returned in a stable, deterministic order so that successive pages for the same search term neither repeat nor skip a matching Endpoint.

#### Scenario: Search matches endpoints across multiple APIs

- **WHEN** the Endpoint search endpoint is called with a query string that matches endpoints belonging to more than one API
- **THEN** results from every matching API are returned, each annotated with its owning API's reference, name, and title

#### Scenario: Search matches on path, summary, or operation_id

- **WHEN** the Endpoint search endpoint is called with a query string that matches only one of an Endpoint's `path`, `summary`, or `operation_id`
- **THEN** that Endpoint is included in the results

#### Scenario: Removed endpoints are excluded by default

- **WHEN** the Endpoint search endpoint is called without an explicit status filter, and a matching Endpoint has `status` `removed`
- **THEN** that Endpoint is excluded from the results

#### Scenario: A page beyond the first returns the next slice of matching endpoints

- **WHEN** the Endpoint search endpoint is called with the same query string and `page=2`, after a `page=1` call for that query string returned a full page
- **THEN** the response contains the next page's worth of matching Endpoints, with no Endpoint repeated from page 1 and none skipped between the two pages

#### Scenario: The response reports whether further pages exist

- **WHEN** the Endpoint search endpoint's results for a query string span more than one page
- **THEN** the response for any given page indicates the total page count (or an equivalent has-more signal), so a caller can tell whether requesting a further page is worthwhile

### Requirement: Cross-API Operation search

`atlas_plugin_apis` SHALL provide a search endpoint returning active Operations across every API, matching a query string against `channel_address`, `summary`, or `operation_id`, each result carrying its owning API's reference, name, and title. The endpoint SHALL support `page` and `page_size` request parameters and SHALL return results in a paginated response (matching the pagination shape used by the plugin's other paginated list endpoints), rather than a single response capped at a fixed result count with no way to reach further matches. Results SHALL be returned in a stable, deterministic order so that successive pages for the same search term neither repeat nor skip a matching Operation.

#### Scenario: Search matches operations across multiple APIs

- **WHEN** the Operation search endpoint is called with a query string that matches operations belonging to more than one API
- **THEN** results from every matching API are returned, each annotated with its owning API's reference, name, and title

#### Scenario: Search matches on channel_address, summary, or operation_id

- **WHEN** the Operation search endpoint is called with a query string that matches only one of an Operation's `channel_address`, `summary`, or `operation_id`
- **THEN** that Operation is included in the results

#### Scenario: Removed operations are excluded by default

- **WHEN** the Operation search endpoint is called without an explicit status filter, and a matching Operation has `status` `removed`
- **THEN** that Operation is excluded from the results

#### Scenario: A page beyond the first returns the next slice of matching operations

- **WHEN** the Operation search endpoint is called with the same query string and `page=2`, after a `page=1` call for that query string returned a full page
- **THEN** the response contains the next page's worth of matching Operations, with no Operation repeated from page 1 and none skipped between the two pages

#### Scenario: The response reports whether further pages exist

- **WHEN** the Operation search endpoint's results for a query string span more than one page
- **THEN** the response for any given page indicates the total page count (or an equivalent has-more signal), so a caller can tell whether requesting a further page is worthwhile
