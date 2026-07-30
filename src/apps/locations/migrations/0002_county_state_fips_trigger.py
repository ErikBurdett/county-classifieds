from __future__ import annotations

from django.db import migrations


CREATE_SQL = """
CREATE FUNCTION locations_validate_county_state_fips() RETURNS trigger AS $$
BEGIN
    IF substring(NEW.fips FROM 1 FOR 2) !=
       (SELECT fips FROM locations_state WHERE id = NEW.state_id) THEN
        RAISE EXCEPTION 'county FIPS must begin with state FIPS';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER locations_county_state_fips_trigger
BEFORE INSERT OR UPDATE OF fips, state_id ON locations_county
FOR EACH ROW EXECUTE FUNCTION locations_validate_county_state_fips();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS locations_county_state_fips_trigger ON locations_county;
DROP FUNCTION IF EXISTS locations_validate_county_state_fips();
"""


def create_postgres_trigger(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE_SQL)


def drop_postgres_trigger(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [("locations", "0001_initial")]

    operations = [migrations.RunPython(create_postgres_trigger, drop_postgres_trigger)]
