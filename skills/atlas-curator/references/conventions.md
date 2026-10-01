# Conventions

## Names (identifiers)

- Lowercase kebab-case, ASCII, taken from the thing's real name: `billing-service`, `orders-db`, `payments`.
- No `/` or `:` (the server rejects them) and no spaces.
- Always English, even when the conversation and descriptions are in another language. Transliterate if needed.
- Unique per kind. Reuse a repository or package name for the Component it builds when that is its natural name.
- Do not put the kind in the name unless it is how the team says it (`billing-db` is fine for a database).

## Titles and descriptions

- Ask once which language to use for titles and descriptions; apply it to every entity written in the session.
- Draft them yourself; do not interview the user about wording. Show them in the summary so they can correct them.
- Title: the human name, short. Description: one or two sentences saying what it does and for whom, based on
  evidence (README, code, config). Do not invent business facts; leave the description empty or say what the
  code shows.
- Relationship labels follow the content language too.

## Tags

- A few lowercase tags that help search: the main language or framework (`python`, `django`), the domain
  (`payments`), a notable protocol. At most a handful per entity.
- Reuse tags already present in the catalog when a similar one exists (check with `search_catalog`).

## Owners

- Owners are existing Groups. Look them up with `search_catalog` (`kind: group`, `q` for a name) and show titles
  with refs so the user can choose.
- One owner for the whole batch is the usual answer; offer it first.
- Never create, rename, or substitute a group. If the right one is missing, stop and tell the user to create it
  in Atlas.

## Refs

Write refs with the kind prefix: `group:platform-team`, `system:payments`, `api:billing-api`,
`resource:billing-db`, `component:billing-service`. Use the `ref` returned by search when you have it.
