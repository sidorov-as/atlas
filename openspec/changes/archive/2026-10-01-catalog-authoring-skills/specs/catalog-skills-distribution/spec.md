## ADDED Requirements

### Requirement: Skills are published as a top-level installable collection
The repository SHALL provide a top-level `skills/` directory containing one folder per skill, named `atlas-scout`, `atlas-flow`, and `atlas-curator`. Each folder SHALL contain a `SKILL.md` whose frontmatter has a `name` equal to the folder name and a non-empty `description` stating when the skill applies, and MAY contain a `references/` folder of files loaded on demand.

#### Scenario: Every skill has valid frontmatter
- **WHEN** the skills collection is checked
- **THEN** each `SKILL.md` has a `name` matching its folder and a non-empty `description`

#### Scenario: References resolve
- **WHEN** a `SKILL.md` or reference file points at another file by relative path
- **THEN** that file exists, including paths into another skill's `references/`

### Requirement: Skills are documented as a set installed together
The documentation SHALL describe how to install the skills, SHALL state that they are installed together because `atlas-scout` and `atlas-flow` rely on `atlas-curator`, and SHALL describe the MCP connection and token scopes the skills need.

#### Scenario: Install instructions exist
- **WHEN** a user opens the skills documentation
- **THEN** it explains installation, the required MCP server connection, and the `catalog:write` and `flows:write` scopes

#### Scenario: Missing sibling skill is reported
- **WHEN** `atlas-scout` or `atlas-flow` runs without `atlas-curator` available
- **THEN** it stops and tells the user to install the full set instead of continuing without it

### Requirement: Every skill checks the MCP server before acting
Each skill SHALL, before any catalog read or write, establish which Atlas MCP tools are available. If no Atlas catalog tools are available, the skill SHALL stop and explain how to connect the server. If a tool the skill prefers is missing, the skill SHALL state what it cannot do and SHALL continue with reduced behavior only after the user agrees.

#### Scenario: No MCP connection
- **WHEN** a skill starts and no Atlas catalog tools are available
- **THEN** it explains how to connect the Atlas MCP server and does not attempt any write

#### Scenario: Relationship tools missing
- **WHEN** the connected server has no relationship tools
- **THEN** the skill tells the user relationships cannot be created and asks whether to proceed with entities only

#### Scenario: Permission error is not retried
- **WHEN** a write is rejected for a missing token scope or permission
- **THEN** the skill reports which scope or permission is needed and does not retry the same request

### Requirement: Skills follow the user's language
Each skill SHALL instruct the assistant that, when the user asks for a specific language, all later discussion, plans, and summaries are conducted in that language. Each skill that writes catalog content SHALL ask once which language to use for entity titles and descriptions and apply the answer to everything it writes, keeping entity name identifiers, field names, and enum values in English.

#### Scenario: User requests another language
- **WHEN** the user asks the assistant to respond in a given language
- **THEN** the skill's questions, plan, and summaries are in that language for the rest of the conversation

#### Scenario: Content language is asked once
- **WHEN** a skill is about to draft titles and descriptions
- **THEN** it asks which language to write them in, and uses that language for every entity it writes in the session

### Requirement: Skills never write without confirmation and never remove entities or flows
Each skill SHALL present, in the conversation, a summary of what will be created or changed and SHALL wait for explicit user confirmation before the first write. No skill SHALL remove, purge, or restore a catalog entity, and no skill SHALL delete a flow, even when the user asks; in that case the skill SHALL explain that removal is performed in the Atlas web UI. A skill MAY delete a manual relationship only when the user explicitly asks for that specific relationship to be deleted and has confirmed a summary of the deletion.

#### Scenario: Writes wait for confirmation
- **WHEN** a skill has assembled the changes it intends to make
- **THEN** it shows a summary and makes no write until the user confirms

#### Scenario: Catalog items missing from the source are left alone
- **WHEN** a catalog entity has no counterpart in the code or conversation
- **THEN** the skill reports it as needing investigation and does not remove it

#### Scenario: Request to remove an entity is redirected
- **WHEN** the user asks a skill to remove or delete an entity or a flow
- **THEN** the skill makes no removal call, explains that removal is done in the Atlas web UI, and offers to list the related entities it can find

#### Scenario: Relationship deletion needs an explicit request and confirmation
- **WHEN** the user explicitly asks to delete one manual relationship
- **THEN** the skill shows what will be deleted and deletes it only after the user confirms

### Requirement: Skills are checked in CI
CI SHALL fail when a `SKILL.md` lacks valid frontmatter or when a relative reference inside the skills collection does not resolve.

#### Scenario: Broken reference fails the check
- **WHEN** a skill references a file that does not exist
- **THEN** the check fails and names the skill and the missing path
