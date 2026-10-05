## MODIFIED Requirements

### Requirement: API detail page lists its endpoints
An API's detail page SHALL show a list of its Endpoints, searchable by path/summary/operationId and filterable by HTTP method and deprecated status. This list SHALL show only `active` Endpoints by default. The list SHALL be paginated, showing 15 Endpoints per page by default with a choice of 15, 30, 50 or 100 per page and a page number input; the pagination control SHALL be shown whenever the list is not empty.

#### Scenario: Endpoint list search
- **WHEN** a user searches the endpoint list for text matching an endpoint's path, summary, or operationId
- **THEN** only matching endpoints are shown

#### Scenario: Removed endpoints are excluded from the default list
- **WHEN** an API's endpoint list is viewed with no removed-endpoints filter applied
- **THEN** Endpoints with `status=removed` are not shown

#### Scenario: Long list is split into pages
- **WHEN** an API has 20 active Endpoints and its endpoint list is opened
- **THEN** the first 15 are shown and the pagination control offers a second page with the remaining 5

#### Scenario: Page size can be changed
- **WHEN** a user selects 50 per page on an API with 20 active Endpoints
- **THEN** all 20 are shown on one page and the page resets to the first

#### Scenario: Filtering returns to the first page
- **WHEN** a user is on the second page and changes the search text, method or deprecated filter
- **THEN** the list shows the first page of the filtered results

#### Scenario: Pagination reflects the filtered total
- **WHEN** a filter leaves 7 Endpoints
- **THEN** the pagination control counts 7 items and offers a single page
