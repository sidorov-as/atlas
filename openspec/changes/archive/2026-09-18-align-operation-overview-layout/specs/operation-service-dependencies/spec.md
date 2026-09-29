## ADDED Requirements

### Requirement: Overview tab surfaces linked Services via the graph and a tab link, not a duplicate list
An Operation's Overview tab SHALL surface its linked Services only through the compact publishers/subscribers graph and a link to the dedicated Linked Services tab, not through a separate full or partial listing of linked Services embedded in Overview.

#### Scenario: Overview links to Linked Services instead of listing them
- **WHEN** a user views an Operation's Overview tab and it has one or more linked Services
- **THEN** Overview shows a "View all N services" link next to the publishers/subscribers graph that navigates to the Linked Services tab, rather than rendering the list of Services itself

#### Scenario: No services yet shows the graph's own empty state, not a second one
- **WHEN** an Operation has no linked Services
- **THEN** the publishers/subscribers graph's existing empty state (with its "Link service" action) is the only indication of this on Overview — no separate "no services linked" message is duplicated elsewhere on the tab
