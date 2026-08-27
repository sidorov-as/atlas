"""sqlglot-based SQL parser for the `DatabaseSchema` Facet (sqlglot rather than
ANTLR grammars-v4 or sqlfluff, for parsing).

Produces the tbls-compatible `parsed_schema` shape (the tbls-*json* shape,
not the tbls-*Go-struct* shape) — the documented JSON-input subset, not tbls'
runtime-computed Go structs::

    {
        "tables": [
            {"name": str, "type": "BASE TABLE", "columns": [...],
             "indexes": [...], "constraints": [...]},
            ...
        ],
        "relations": [
            {"table": str, "columns": [str], "parent_table": str,
             "parent_columns": [str],
             "cardinality": "many_to_one" | "one_to_one"},
            ...
        ],
        "enums": [{"name": str, "values": [str]}, ...],
    }

Indexes and constraints are captured even though the ER Diagram view doesn't
render them yet — the old regex parser deferred locking the shape until a
second consumer existed, so the shape is set once, not twice.

Table/relation names are unqualified (schema/db prefixes like `dbo.` are
dropped) so a table's `name` always matches how it's referenced elsewhere in
`parsed_schema` — bounded parsing scope, matching the
old parser's behavior.
"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError as SqlglotParseError

from .dialects import SQLGLOT_DIALECTS

_TABLE_TYPE = "BASE TABLE"


class SqlParseError(Exception):
    """Raised when `source_sql` cannot be parsed under the facet's selected
    dialect.

    Callers (the facet CRUD endpoint) catch this and set `parse_status`
    to `failed` while still saving `source_sql` verbatim (a failed parse
    preserves the saved SQL).
    """


def parse_schema(sql: str, dialect: str) -> dict:
    """Parse `sql` under the catalog `dialect` (a
    `DatabaseSchema.DIALECT_CHOICES` value) into the tbls-compatible
    `parsed_schema` shape."""
    sqlglot_dialect = SQLGLOT_DIALECTS[dialect]
    try:
        statements = [
            statement
            for statement in sqlglot.parse(sql, read=sqlglot_dialect)
            if statement is not None
        ]
    except SqlglotParseError as exc:
        raise SqlParseError(str(exc)) from exc

    create_tables = [
        statement
        for statement in statements
        if isinstance(statement, exp.Create) and statement.kind == "TABLE"
    ]
    if not create_tables:
        raise SqlParseError("No CREATE TABLE statement found")

    enums = _collect_enum_types(statements)

    tables: dict[str, dict] = {}
    table_order: list[str] = []
    relations: list[dict] = []
    for statement in create_tables:
        table, fk_specs = _parse_create_table(
            statement,
            sqlglot_dialect,
            enums,
        )
        # Table/relation names are unqualified (module docstring) — two
        # schema-qualified tables sharing a base name (e.g. `public.settings`
        # and `audit.settings`) would otherwise silently overwrite one
        # another instead of raising, since `parsed_schema` has no field to
        # tell them apart.
        if table["name"] in tables:
            raise SqlParseError(
                f"Multiple tables named {table['name']!r} (schema-qualified "
                "names collide once qualifiers are dropped)",
            )
        tables[table["name"]] = table
        table_order.append(table["name"])
        relations.extend(_resolve_relations(table, fk_specs))

    for other_statement in statements:
        if isinstance(other_statement, exp.Alter):
            relations.extend(_apply_alter_table(other_statement, tables))
        elif (
            isinstance(other_statement, exp.Create) and other_statement.kind == "INDEX"
        ):
            _apply_create_index(other_statement, tables, sqlglot_dialect)

    _resolve_implicit_parent_columns(relations, tables)

    return {
        "tables": [tables[name] for name in table_order],
        "relations": relations,
        "enums": enums,
    }


def _qualified_name(table_exp: exp.Table) -> str:
    return table_exp.name


def _identifier_names(expressions) -> list[str]:
    return [expression.name for expression in expressions]


def _ordered_column_names(expressions) -> list[str]:
    names = []
    for expression in expressions:
        is_ordered = isinstance(expression, exp.Ordered)
        column = expression.this if is_ordered else expression
        names.append(column.name)
    return names


def _collect_enum_types(statements: list[exp.Expr]) -> list[dict]:
    enums = []
    for statement in statements:
        if not (isinstance(statement, exp.Create) and statement.kind == "TYPE"):
            continue
        data_type = statement.args.get("expression")
        if not isinstance(data_type, exp.DataType):
            continue
        if data_type.this != exp.DataType.Type.ENUM:
            continue
        enums.append(
            {
                "name": statement.this.name,
                "values": [value.this for value in data_type.expressions],
            }
        )
    return enums


def _unwrap_named_constraint(
    item: exp.Expression,
) -> tuple[str | None, exp.Expression | None]:
    if isinstance(item, exp.Constraint):
        name = item.this.name if item.this else None
        inner = item.expressions[0] if item.expressions else None
        return name, inner
    return None, item


def _reference_target(
    reference_this: exp.Expression | None,
) -> tuple[str, list[str]]:
    if isinstance(reference_this, exp.Schema):
        return (
            _qualified_name(reference_this.this),
            _identifier_names(reference_this.expressions),
        )
    if isinstance(reference_this, exp.Table):
        return _qualified_name(reference_this), []
    return "", []


def _foreign_key_spec(
    inner: exp.ForeignKey,
    name: str | None,
    child_table: str,
) -> dict:
    child_columns = _identifier_names(inner.expressions)
    reference = inner.args.get("reference")
    parent_table, parent_columns = _reference_target(
        reference.this if reference else None,
    )
    return {
        "name": name or f"{child_table}_{'_'.join(child_columns)}_fkey",
        "columns": child_columns,
        "parent_table": parent_table,
        "parent_columns": parent_columns,
    }


def _fk_constraint_entry(fk: dict, table_name: str) -> dict:
    parent_columns = ", ".join(fk["parent_columns"])
    child_columns = ", ".join(fk["columns"])
    return {
        "name": fk["name"],
        "type": "FOREIGN KEY",
        "def": (
            f"FOREIGN KEY ({child_columns}) "
            f"REFERENCES {fk['parent_table']}({parent_columns})"
        ),
        "table": table_name,
        "columns": fk["columns"],
        "referenced_table": fk["parent_table"],
        "referenced_columns": fk["parent_columns"] or None,
    }


def _reference_spec(
    kind: exp.Reference,
    child_column: str,
    child_table: str,
) -> dict:
    parent_table, parent_columns = _reference_target(kind.this)
    return {
        "name": f"{child_table}_{child_column}_fkey",
        "columns": [child_column],
        "parent_table": parent_table,
        "parent_columns": parent_columns,
    }


def _parse_column(
    item: exp.ColumnDef,
    sqlglot_dialect: str,
    table_name: str,
    enums: list[dict],
) -> tuple[dict, bool, dict | None, bool]:
    name = item.name
    data_type = item.args.get("kind")
    type_str = data_type.sql(dialect=sqlglot_dialect) if data_type is not None else ""

    if (
        isinstance(data_type, exp.DataType)
        and data_type.this == exp.DataType.Type.ENUM
        and data_type.expressions
    ):
        enums.append(
            {
                "name": f"{table_name}.{name}",
                "values": [value.this for value in data_type.expressions],
            }
        )

    nullable = True
    default = None
    is_primary_key = False
    is_unique = False
    fk_spec = None

    for column_constraint in item.constraints:
        kind = column_constraint.kind
        if isinstance(kind, exp.PrimaryKeyColumnConstraint):
            is_primary_key = True
            nullable = False
        elif isinstance(kind, exp.NotNullColumnConstraint):
            nullable = False
        elif isinstance(kind, exp.DefaultColumnConstraint) and kind.this:
            default = kind.this.sql(dialect=sqlglot_dialect)
        elif isinstance(kind, exp.Reference):
            fk_spec = _reference_spec(kind, name, table_name)
        elif isinstance(kind, exp.UniqueColumnConstraint):
            is_unique = True

    column = {
        "name": name,
        "type": type_str,
        "nullable": nullable,
        "default": default,
    }
    return column, is_primary_key, fk_spec, is_unique


def _apply_table_level_item(
    item: exp.Expression,
    table_name: str,
    sqlglot_dialect: str,
    constraints: list[dict],
    indexes: list[dict],
    fk_specs: list[dict],
    pk_columns: list[str],
) -> None:
    name, inner = _unwrap_named_constraint(item)
    if inner is None:
        return

    if isinstance(inner, exp.PrimaryKey):
        for column_name in _identifier_names(inner.expressions):
            if column_name not in pk_columns:
                pk_columns.append(column_name)
        return

    if isinstance(inner, exp.ForeignKey):
        fk_spec = _foreign_key_spec(inner, name, table_name)
        fk_specs.append(fk_spec)
        constraints.append(_fk_constraint_entry(fk_spec, table_name))
        return

    if isinstance(inner, exp.UniqueColumnConstraint):
        schema = inner.this
        columns = (
            _identifier_names(schema.expressions)
            if isinstance(schema, exp.Schema)
            else []
        )
        schema_name = (
            schema.this.name if isinstance(schema, exp.Schema) and schema.this else None
        )
        constraint_name = name or schema_name or f"{table_name}_{'_'.join(columns)}_key"
        constraints.append(
            {
                "name": constraint_name,
                "type": "UNIQUE",
                "def": item.sql(dialect=sqlglot_dialect),
                "table": table_name,
                "columns": columns,
                "referenced_table": None,
                "referenced_columns": None,
            }
        )
        return

    if isinstance(inner, exp.CheckColumnConstraint):
        constraints.append(
            {
                "name": name or f"{table_name}_check",
                "type": "CHECK",
                "def": item.sql(dialect=sqlglot_dialect),
                "table": table_name,
                "columns": [],
                "referenced_table": None,
                "referenced_columns": None,
            }
        )
        return

    if isinstance(inner, exp.IndexColumnConstraint):
        indexes.append(
            {
                "name": inner.this.name if inner.this else f"{table_name}_idx",
                "def": item.sql(dialect=sqlglot_dialect),
                "table": table_name,
                "columns": _ordered_column_names(inner.expressions),
            }
        )
        return
    # Other table-level items (dialect-specific storage/table options, etc.)
    # aren't represented in `parsed_schema` — bounded parsing scope.


def _parse_create_table(
    statement: exp.Create,
    sqlglot_dialect: str,
    enums: list[dict],
) -> tuple[dict, list[dict]]:
    schema_exp = statement.this
    is_schema = isinstance(schema_exp, exp.Schema)
    table_exp = schema_exp.this if is_schema else schema_exp
    table_name = _qualified_name(table_exp)
    items = schema_exp.expressions if is_schema else []

    columns: dict[str, dict] = {}
    column_order: list[str] = []
    indexes: list[dict] = []
    constraints: list[dict] = []
    pk_columns: list[str] = []
    fk_specs: list[dict] = []

    for item in items:
        if isinstance(item, exp.ColumnDef):
            column, is_pk, fk_spec, is_unique = _parse_column(
                item,
                sqlglot_dialect,
                table_name,
                enums,
            )
            columns[column["name"]] = column
            column_order.append(column["name"])
            if is_pk and column["name"] not in pk_columns:
                pk_columns.append(column["name"])
            if fk_spec is not None:
                fk_specs.append(fk_spec)
                constraints.append(_fk_constraint_entry(fk_spec, table_name))
            if is_unique:
                constraints.append(
                    {
                        "name": f"{table_name}_{column['name']}_key",
                        "type": "UNIQUE",
                        "def": f"UNIQUE ({column['name']})",
                        "table": table_name,
                        "columns": [column["name"]],
                        "referenced_table": None,
                        "referenced_columns": None,
                    }
                )
        else:
            _apply_table_level_item(
                item,
                table_name,
                sqlglot_dialect,
                constraints,
                indexes,
                fk_specs,
                pk_columns,
            )

    if pk_columns:
        constraints.insert(
            0,
            {
                "name": f"{table_name}_pkey",
                "type": "PRIMARY KEY",
                "def": f"PRIMARY KEY ({', '.join(pk_columns)})",
                "table": table_name,
                "columns": pk_columns,
                "referenced_table": None,
                "referenced_columns": None,
            },
        )
        for column_name in pk_columns:
            if column_name in columns:
                columns[column_name]["nullable"] = False

    table = {
        "name": table_name,
        "type": _TABLE_TYPE,
        "columns": [columns[name] for name in column_order],
        "indexes": indexes,
        "constraints": constraints,
    }
    return table, fk_specs


def _unique_column_sets(table: dict) -> set:
    return {
        frozenset(constraint["columns"])
        for constraint in table["constraints"]
        if constraint["type"] in ("PRIMARY KEY", "UNIQUE") and constraint["columns"]
    }


def _resolve_relations(table: dict, fk_specs: list[dict]) -> list[dict]:
    unique_sets = _unique_column_sets(table)
    relations = []
    for fk in fk_specs:
        cardinality = (
            "one_to_one" if frozenset(fk["columns"]) in unique_sets else "many_to_one"
        )
        relations.append(
            {
                "table": table["name"],
                "columns": fk["columns"],
                "parent_table": fk["parent_table"],
                "parent_columns": fk["parent_columns"],
                "cardinality": cardinality,
            }
        )
    return relations


def _primary_key_columns(table: dict) -> list[str]:
    for constraint in table["constraints"]:
        if constraint["type"] == "PRIMARY KEY":
            return constraint["columns"]
    return []


def _resolve_implicit_parent_columns(
    relations: list[dict],
    tables: dict[str, dict],
) -> None:
    # `REFERENCES parent_table` without an explicit column list implicitly
    # references the parent's primary key (SQL standard) — without this,
    # `parent_columns` stays `[]` and the frontend's per-column edge lookup
    # (`parent_columns[columnIndex] ?? parent_columns[0]`) finds nothing,
    # silently dropping the relation from the diagram.
    for relation in relations:
        if relation["parent_columns"]:
            continue
        parent = tables.get(relation["parent_table"])
        if parent is not None:
            relation["parent_columns"] = _primary_key_columns(parent)


def _apply_alter_table(
    statement: exp.Alter,
    tables: dict[str, dict],
) -> list[dict]:
    table_exp = statement.this
    if not isinstance(table_exp, exp.Table):
        return []
    table = tables.get(_qualified_name(table_exp))
    if table is None:
        return []

    new_fk_specs = []
    for action in statement.args.get("actions") or []:
        if not isinstance(action, exp.AddConstraint):
            continue
        for expression in action.expressions:
            name, inner = _unwrap_named_constraint(expression)
            if not isinstance(inner, exp.ForeignKey):
                continue
            fk_spec = _foreign_key_spec(inner, name, table["name"])
            table["constraints"].append(
                _fk_constraint_entry(fk_spec, table["name"]),
            )
            new_fk_specs.append(fk_spec)

    return _resolve_relations(table, new_fk_specs)


def _apply_create_index(
    statement: exp.Create,
    tables: dict[str, dict],
    sqlglot_dialect: str,
) -> None:
    index_exp = statement.this
    if not isinstance(index_exp, exp.Index):
        return
    table_exp = index_exp.args.get("table")
    if table_exp is None:
        return
    table = tables.get(_qualified_name(table_exp))
    if table is None:
        return

    params = index_exp.args.get("params")
    columns = (
        _ordered_column_names(params.args.get("columns") or [])
        if params is not None
        else []
    )
    table["indexes"].append(
        {
            "name": index_exp.name,
            "def": statement.sql(dialect=sqlglot_dialect),
            "table": table["name"],
            "columns": columns,
        }
    )
