## MODIFIED Requirements

### Requirement: API detail page lists its operations grouped by channel
An API's detail page SHALL show its Operations grouped into sections by `channel_address`, each section showing a summary of how many publisher and how many subscriber roles exist for that channel across its Operations' linked Services, with Operations nested under their channel's section. This list SHALL show only `active` Operations by default. The list SHALL be paginated by Operation, showing 15 Operations per page by default with a choice of 15, 30, 50 or 100 per page and a page number input; the pagination control SHALL be shown whenever the list is not empty. Grouping SHALL be applied to the Operations of the current page, so a channel whose Operations span a page boundary appears in a section on each of those pages.

#### Scenario: Two operations on the same channel appear in one group
- **WHEN** an API has two Operations sharing the same `channel_address` (e.g. one `send`, one `receive`) and both are on the same page
- **THEN** both appear nested under one channel section, not as two unrelated top-level rows

#### Scenario: Channel group shows a publisher/subscriber summary
- **WHEN** a channel section is rendered
- **THEN** it shows a count of publisher roles and a count of subscriber roles derived from its Operations' linked Services (including each Operation's document-owner role implied by its `direction`)

#### Scenario: Removed operations are excluded from the default list
- **WHEN** an API's operation list is viewed with no removed-operations filter applied
- **THEN** Operations with `status=removed` are not shown

#### Scenario: Long list is split into pages
- **WHEN** an API has 20 active Operations and its operation list is opened
- **THEN** the first 15 Operations are shown, grouped by channel, and the pagination control offers a second page with the remaining 5

#### Scenario: Channel spanning a page boundary
- **WHEN** two Operations of one channel fall on different pages
- **THEN** each page shows that channel's section with the Operations that are on that page

#### Scenario: Filtering returns to the first page
- **WHEN** a user is on the second page and changes the search text, direction or status filter
- **THEN** the list shows the first page of the filtered results
