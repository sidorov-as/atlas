## ADDED Requirements

### Requirement: Schema editor shows SQL syntax highlighting
The Database Schema facet's `source_sql` editor SHALL render its content with SQL syntax highlighting, using generic SQL tokenization regardless of the selected dialect (PostgreSQL, MySQL, or MS SQL). Selecting a dialect SHALL continue to affect only save and parse behavior, not highlighting.

#### Scenario: SQL editor highlights syntax
- **WHEN** a user opens the Schema tab for a Resource and types `source_sql`
- **THEN** the editor renders the SQL with syntax highlighting

#### Scenario: Highlighting is unaffected by dialect selection
- **WHEN** a user switches the selected dialect between PostgreSQL, MySQL, and MS SQL
- **THEN** the SQL editor's highlighting is unchanged, and only save/parse behavior reflects the selected dialect
