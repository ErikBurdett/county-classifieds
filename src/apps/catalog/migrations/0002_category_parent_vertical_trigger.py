from __future__ import annotations

from django.db import migrations


CREATE_SQL = """
CREATE FUNCTION catalog_validate_category_parent_vertical() RETURNS trigger AS $$
BEGIN
    IF NEW.parent_id IS NOT NULL AND NEW.vertical_id !=
       (SELECT vertical_id FROM catalog_category WHERE id = NEW.parent_id) THEN
        RAISE EXCEPTION 'category parent must use the same vertical';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER catalog_category_parent_vertical_trigger
BEFORE INSERT OR UPDATE OF parent_id, vertical_id ON catalog_category
FOR EACH ROW EXECUTE FUNCTION catalog_validate_category_parent_vertical();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS catalog_category_parent_vertical_trigger ON catalog_category;
DROP FUNCTION IF EXISTS catalog_validate_category_parent_vertical();
"""


def create_postgres_trigger(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE_SQL)


def drop_postgres_trigger(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [migrations.RunPython(create_postgres_trigger, drop_postgres_trigger)]
