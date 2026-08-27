"""Tests for the sqlglot-based, multi-dialect SQL parser."""

import pytest

from atlas_plugin_database_schema.parser import SqlParseError, parse_schema


def _table(parsed, name):
    return next(table for table in parsed["tables"] if table["name"] == name)


def _column(table, name):
    return next(column for column in table["columns"] if column["name"] == name)


def _constraint(table, name):
    return next(
        constraint for constraint in table["constraints"] if constraint["name"] == name
    )


class TestPostgreSql:
    def test_parses_a_single_table_with_a_primary_key(self):
        parsed = parse_schema(
            "CREATE TABLE users (id uuid PRIMARY KEY, email varchar(255) NOT NULL);",
            "postgresql",
        )
        table = _table(parsed, "users")
        assert table["type"] == "BASE TABLE"
        column_names = [column["name"] for column in table["columns"]]
        assert column_names == ["id", "email"]
        assert _column(table, "id")["nullable"] is False
        assert _column(table, "email")["nullable"] is False
        assert _constraint(table, "users_pkey") == {
            "name": "users_pkey",
            "type": "PRIMARY KEY",
            "def": "PRIMARY KEY (id)",
            "table": "users",
            "columns": ["id"],
            "referenced_table": None,
            "referenced_columns": None,
        }

    def test_parses_a_column_level_foreign_key_and_a_many_to_one_relation(self):
        parsed = parse_schema(
            "CREATE TABLE users (id uuid PRIMARY KEY); "
            "CREATE TABLE orders "
            "(id uuid PRIMARY KEY, user_id uuid REFERENCES users(id));",
            "postgresql",
        )
        orders = _table(parsed, "orders")
        fk = _constraint(orders, "orders_user_id_fkey")
        assert fk["type"] == "FOREIGN KEY"
        assert fk["referenced_table"] == "users"
        assert fk["referenced_columns"] == ["id"]
        assert parsed["relations"] == [
            {
                "table": "orders",
                "columns": ["user_id"],
                "parent_table": "users",
                "parent_columns": ["id"],
                "cardinality": "many_to_one",
            }
        ]

    def test_a_foreign_key_without_an_explicit_column_list_uses_the_parent_pk(self):
        parsed = parse_schema(
            "CREATE TABLE users (id uuid PRIMARY KEY); "
            "CREATE TABLE orders "
            "(id uuid PRIMARY KEY, user_id uuid REFERENCES users);",
            "postgresql",
        )
        assert parsed["relations"] == [
            {
                "table": "orders",
                "columns": ["user_id"],
                "parent_table": "users",
                "parent_columns": ["id"],
                "cardinality": "many_to_one",
            }
        ]

    def test_a_foreign_key_on_a_unique_column_is_a_one_to_one_relation(self):
        parsed = parse_schema(
            "CREATE TABLE users (id uuid PRIMARY KEY); "
            "CREATE TABLE profiles "
            "(user_id uuid UNIQUE REFERENCES users(id));",
            "postgresql",
        )
        assert parsed["relations"][0]["cardinality"] == "one_to_one"

    def test_parses_a_table_level_primary_key_and_named_foreign_key(self):
        parsed = parse_schema(
            "CREATE TABLE products (id uuid PRIMARY KEY); "
            "CREATE TABLE order_items ("
            "order_id uuid, product_id uuid, "
            "PRIMARY KEY (order_id, product_id), "
            "CONSTRAINT fk_product FOREIGN KEY (product_id) "
            "REFERENCES products (id)"
            ");",
            "postgresql",
        )
        table = _table(parsed, "order_items")
        pk_columns = _constraint(table, "order_items_pkey")["columns"]
        assert pk_columns == ["order_id", "product_id"]
        fk = _constraint(table, "fk_product")
        assert fk["columns"] == ["product_id"]
        assert fk["referenced_table"] == "products"

    def test_parses_a_named_unique_constraint(self):
        parsed = parse_schema(
            "CREATE TABLE order_items (order_id uuid, product_id uuid, "
            "CONSTRAINT uq_order_product UNIQUE (order_id, product_id));",
            "postgresql",
        )
        table = _table(parsed, "order_items")
        unique = _constraint(table, "uq_order_product")
        assert unique["type"] == "UNIQUE"
        assert unique["columns"] == ["order_id", "product_id"]

    def test_alter_table_add_constraint_foreign_key_produces_a_relation(self):
        parsed = parse_schema(
            "CREATE TABLE users (id uuid PRIMARY KEY); "
            "CREATE TABLE orders "
            "(id uuid PRIMARY KEY, user_id uuid NOT NULL); "
            "ALTER TABLE orders ADD CONSTRAINT fk_orders_user "
            "FOREIGN KEY (user_id) REFERENCES users(id);",
            "postgresql",
        )
        orders = _table(parsed, "orders")
        fk = _constraint(orders, "fk_orders_user")
        assert fk["referenced_table"] == "users"
        assert {
            "table": "orders",
            "columns": ["user_id"],
            "parent_table": "users",
            "parent_columns": ["id"],
            "cardinality": "many_to_one",
        } in parsed["relations"]

    def test_parses_a_partial_index(self):
        parsed = parse_schema(
            "CREATE TABLE orders (id uuid PRIMARY KEY, status text); "
            "CREATE INDEX idx_orders_status ON orders (status) "
            "WHERE status <> 'cancelled';",
            "postgresql",
        )
        table = _table(parsed, "orders")
        assert len(table["indexes"]) == 1
        index = table["indexes"][0]
        assert index["name"] == "idx_orders_status"
        assert index["columns"] == ["status"]
        assert "WHERE" in index["def"]

    def test_parses_an_enum_type_and_uses_it_as_a_column_type(self):
        parsed = parse_schema(
            "CREATE TYPE order_status AS ENUM "
            "('pending', 'shipped', 'delivered'); "
            "CREATE TABLE orders "
            "(id uuid PRIMARY KEY, status order_status NOT NULL);",
            "postgresql",
        )
        assert parsed["enums"] == [
            {
                "name": "order_status",
                "values": ["pending", "shipped", "delivered"],
            },
        ]
        status_column = _column(_table(parsed, "orders"), "status")
        assert status_column["type"] == "order_status"

    def test_a_generated_column_is_still_captured(self):
        parsed = parse_schema(
            "CREATE TABLE order_items (qty integer NOT NULL, "
            "total numeric(10,2) GENERATED ALWAYS AS (qty * 1.0) STORED);",
            "postgresql",
        )
        column = _column(_table(parsed, "order_items"), "total")
        assert column["type"] == "DECIMAL(10, 2)"

    def test_ignores_sql_comments(self):
        parsed = parse_schema(
            "-- users table\n"
            "CREATE TABLE users (\n"
            "  id uuid PRIMARY KEY, /* identifier */\n"
            "  name text\n"
            ");",
            "postgresql",
        )
        table = _table(parsed, "users")
        assert len(table["columns"]) == 2

    @pytest.mark.parametrize("sql", ["", "SELECT 1;", "not sql at all"])
    def test_raises_when_no_create_table_statement_is_found(self, sql):
        with pytest.raises(SqlParseError):
            parse_schema(sql, "postgresql")

    def test_raises_on_malformed_create_table_statement(self):
        with pytest.raises(SqlParseError):
            parse_schema(
                "CREATE TABLE users id uuid PRIMARY KEY;",
                "postgresql",
            )

    def test_raises_when_schema_qualified_tables_collide_unqualified(self):
        with pytest.raises(SqlParseError):
            parse_schema(
                "CREATE TABLE public.settings (id uuid PRIMARY KEY); "
                "CREATE TABLE audit.settings (id uuid PRIMARY KEY);",
                "postgresql",
            )


class TestMySql:
    def test_parses_auto_increment_primary_key_and_inline_index(self):
        parsed = parse_schema(
            "CREATE TABLE items ("
            "id INT PRIMARY KEY AUTO_INCREMENT, sku VARCHAR(64), "
            "KEY idx_sku (sku));",
            "mysql",
        )
        table = _table(parsed, "items")
        assert _constraint(table, "items_pkey")["columns"] == ["id"]
        assert table["indexes"][0]["name"] == "idx_sku"
        assert table["indexes"][0]["columns"] == ["sku"]

    def test_parses_an_inline_enum_column_into_the_top_level_enums_list(self):
        parsed = parse_schema(
            "CREATE TABLE orders (id INT PRIMARY KEY, "
            "status ENUM('pending','shipped','delivered') NOT NULL);",
            "mysql",
        )
        assert parsed["enums"] == [
            {
                "name": "orders.status",
                "values": ["pending", "shipped", "delivered"],
            },
        ]

    def test_a_generated_column_is_still_captured(self):
        parsed = parse_schema(
            "CREATE TABLE t (a INT, b INT GENERATED ALWAYS AS (a * 2) STORED);",
            "mysql",
        )
        column = _column(_table(parsed, "t"), "b")
        assert column["type"] == "INT"

    def test_alter_table_add_foreign_key(self):
        parsed = parse_schema(
            "CREATE TABLE users (id INT PRIMARY KEY); "
            "CREATE TABLE orders "
            "(id INT PRIMARY KEY, user_id INT NOT NULL); "
            "ALTER TABLE orders ADD CONSTRAINT fk_orders_user "
            "FOREIGN KEY (user_id) REFERENCES users(id);",
            "mysql",
        )
        assert parsed["relations"] == [
            {
                "table": "orders",
                "columns": ["user_id"],
                "parent_table": "users",
                "parent_columns": ["id"],
                "cardinality": "many_to_one",
            }
        ]

    def test_raises_when_no_create_table_statement_is_found(self):
        with pytest.raises(SqlParseError):
            parse_schema("SELECT 1;", "mysql")


class TestMsSql:
    def test_parses_identity_pk_and_schema_qualified_foreign_key(self):
        parsed = parse_schema(
            "CREATE TABLE dbo.users "
            "(id INT IDENTITY(1,1) PRIMARY KEY); "
            "CREATE TABLE dbo.orders ("
            "id INT IDENTITY(1,1) PRIMARY KEY, user_id INT NOT NULL, "
            "CONSTRAINT FK_orders_users FOREIGN KEY (user_id) "
            "REFERENCES dbo.users(id)"
            ");",
            "mssql",
        )
        table_names = {table["name"] for table in parsed["tables"]}
        assert table_names == {"users", "orders"}
        orders = _table(parsed, "orders")
        fk = _constraint(orders, "FK_orders_users")
        assert fk["referenced_table"] == "users"
        assert parsed["relations"] == [
            {
                "table": "orders",
                "columns": ["user_id"],
                "parent_table": "users",
                "parent_columns": ["id"],
                "cardinality": "many_to_one",
            }
        ]

    def test_parses_a_partial_index(self):
        parsed = parse_schema(
            "CREATE TABLE orders "
            "(id INT PRIMARY KEY, status VARCHAR(32)); "
            "CREATE INDEX idx_orders_status ON orders (status) "
            "WHERE status <> 'cancelled';",
            "mssql",
        )
        table = _table(parsed, "orders")
        assert table["indexes"][0]["columns"] == ["status"]

    def test_raises_when_no_create_table_statement_is_found(self):
        with pytest.raises(SqlParseError):
            parse_schema("SELECT 1;", "mssql")
