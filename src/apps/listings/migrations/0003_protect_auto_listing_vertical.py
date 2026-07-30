from __future__ import annotations

from django.db import migrations


CREATE_SQL = """
CREATE OR REPLACE FUNCTION listings_validate_listing_relations() RETURNS trigger AS $$
BEGIN
    IF NEW.vertical_id != (SELECT vertical_id FROM catalog_category WHERE id = NEW.category_id) THEN
        RAISE EXCEPTION 'listing category must belong to listing vertical';
    END IF;
    IF NEW.state_id != (SELECT state_id FROM locations_county WHERE id = NEW.county_id) THEN
        RAISE EXCEPTION 'listing county must belong to listing state';
    END IF;
    IF EXISTS (SELECT 1 FROM listings_autodetails WHERE listing_id = NEW.id)
       AND (SELECT slug FROM catalog_vertical WHERE id = NEW.vertical_id) != 'autos' THEN
        RAISE EXCEPTION 'an automobile listing must retain the Autos vertical';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

REVERSE_SQL = """
CREATE OR REPLACE FUNCTION listings_validate_listing_relations() RETURNS trigger AS $$
BEGIN
    IF NEW.vertical_id != (SELECT vertical_id FROM catalog_category WHERE id = NEW.category_id) THEN
        RAISE EXCEPTION 'listing category must belong to listing vertical';
    END IF;
    IF NEW.state_id != (SELECT state_id FROM locations_county WHERE id = NEW.county_id) THEN
        RAISE EXCEPTION 'listing county must belong to listing state';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def replace_postgres_trigger_function(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE_SQL)


def restore_postgres_trigger_function(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("listings", "0002_relational_triggers")]

    operations = [
        migrations.RunPython(replace_postgres_trigger_function, restore_postgres_trigger_function)
    ]
