"""
Migration: rebuild FULLTEXT index product_fulltext_search_idx with ngram parser.

Prerequisites (must be configured in MySQL server before applying):
  - ngram_token_size=2
  - innodb_ft_enable_stopword=OFF

The index is rebuilt to enable CJK tokenisation and improve sub-word search
accuracy via the ngram full-text parser. The three covered columns and the
index name are unchanged; only the parser is added.

This migration is MySQL-only and is a no-op on SQLite / PostgreSQL.
"""

from django.db import migrations


class MysqlOnlyRunSQL(migrations.RunSQL):
    """Execute SQL only on MySQL — mirrors the helper from 0004."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "mysql":
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "mysql":
            super().database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_product_catalog_indexes"),
    ]

    operations = [
        # Step 1: drop the existing plain FULLTEXT index (created in 0004).
        # reverse_sql restores it without a parser (reverts to 0004 state).
        MysqlOnlyRunSQL(
            sql="""
                ALTER TABLE products_product
                DROP INDEX product_fulltext_search_idx
            """,
            reverse_sql="""
                ALTER TABLE products_product
                ADD FULLTEXT INDEX product_fulltext_search_idx
                    (name, short_description, full_description)
            """,
        ),
        # Step 2: recreate the index with WITH PARSER ngram.
        # reverse_sql drops it so Step 1's reverse_sql can cleanly restore the
        # plain-parser index (Django applies reverse_sql in reverse operation order).
        MysqlOnlyRunSQL(
            sql="""
                ALTER TABLE products_product
                ADD FULLTEXT INDEX product_fulltext_search_idx
                    (name, short_description, full_description)
                WITH PARSER ngram
            """,
            reverse_sql="""
                ALTER TABLE products_product
                DROP INDEX product_fulltext_search_idx
            """,
        ),
    ]
