"""Catalog dialect -> sqlglot dialect registry (a registry, not branches):
one lookup feeds
the parser, so adding a future dialect sqlglot already supports (e.g.
`oracle`) is a `DatabaseSchema.DIALECT_CHOICES` entry, a migration, and a
registry entry here — not a parser code change.
"""

SQLGLOT_DIALECTS = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "mssql": "tsql",
}
