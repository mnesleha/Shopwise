from django.db import migrations


class _MySQLOnlyRunSQL(migrations.RunSQL):
    """
    RunSQL subclass that is silently skipped on non-MySQL databases.
    The FK fix it applies is a MySQL-specific NO ACTION → SET NULL correction
    that is irrelevant for SQLite (which does not enforce FK constraints the
    same way) and other backends.
    """

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "mysql":
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, to_state, from_state):
        if schema_editor.connection.vendor != "mysql":
            return
        super().database_backwards(app_label, schema_editor, to_state, from_state)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_customerprofile_address"),
    ]

    operations = [
        _MySQLOnlyRunSQL(
            sql=[
                # Drop existing FKs (currently ON DELETE NO ACTION)
                "ALTER TABLE accounts_customerprofile "
                "DROP FOREIGN KEY accounts_customerpro_default_billing_addr_93e10afe_fk_accounts_;",

                "ALTER TABLE accounts_customerprofile "
                "DROP FOREIGN KEY accounts_customerpro_default_shipping_add_39f623de_fk_accounts_;",

                # Recreate with ON DELETE SET NULL
                "ALTER TABLE accounts_customerprofile "
                "ADD CONSTRAINT accounts_customerpro_default_billing_addr_93e10afe_fk_accounts_ "
                "FOREIGN KEY (default_billing_address_id) "
                "REFERENCES accounts_address(id) "
                "ON DELETE SET NULL;",

                "ALTER TABLE accounts_customerprofile "
                "ADD CONSTRAINT accounts_customerpro_default_shipping_add_39f623de_fk_accounts_ "
                "FOREIGN KEY (default_shipping_address_id) "
                "REFERENCES accounts_address(id) "
                "ON DELETE SET NULL;",
            ],
            reverse_sql=[
                # Reverse: drop and recreate without explicit ON DELETE (defaults to NO ACTION)
                "ALTER TABLE accounts_customerprofile "
                "DROP FOREIGN KEY accounts_customerpro_default_billing_addr_93e10afe_fk_accounts_;",

                "ALTER TABLE accounts_customerprofile "
                "DROP FOREIGN KEY accounts_customerpro_default_shipping_add_39f623de_fk_accounts_;",

                "ALTER TABLE accounts_customerprofile "
                "ADD CONSTRAINT accounts_customerpro_default_billing_addr_93e10afe_fk_accounts_ "
                "FOREIGN KEY (default_billing_address_id) "
                "REFERENCES accounts_address(id);",

                "ALTER TABLE accounts_customerprofile "
                "ADD CONSTRAINT accounts_customerpro_default_shipping_add_39f623de_fk_accounts_ "
                "FOREIGN KEY (default_shipping_address_id) "
                "REFERENCES accounts_address(id);",
            ],
        ),
    ]