"""
Migration: add price index + MySQL FULLTEXT index for catalogue search.

The FULLTEXT index is MySQL-only and is skipped on all other database engines
(SQLite, PostgreSQL) via MysqlOnlyRunSQL.

The price index is a standard Django index and works on all engines.
"""

from django.db import migrations, models


class MysqlOnlyRunSQL(migrations.RunSQL):
    """
    A RunSQL subclass that executes SQL only when the active DB is MySQL.

    This keeps MySQL-specific DDL out of SQLite / PostgreSQL migrations while
    allowing the same migration file to be shared across environments.
    """

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "mysql":
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "mysql":
            super().database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_product_short_description_full_description"),
    ]

    operations = [
        # Standard index on price — supports min_price / max_price range queries.
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["price"], name="product_price_idx"),
        ),
        # MySQL-only: composite FULLTEXT index for catalogue search.
        # Covers the three text columns queried by MySQLCatalogSearchBackend.
        MysqlOnlyRunSQL(
            sql="""
                ALTER TABLE products_product
                ADD FULLTEXT INDEX product_fulltext_search_idx
                    (name, short_description, full_description)
            """,
            reverse_sql="""
                ALTER TABLE products_product
                DROP INDEX product_fulltext_search_idx
            """,
        ),
    ]
