from __future__ import annotations

from django.db import migrations, models


CREATE_SQL = """
CREATE FUNCTION listings_validate_listing_relations() RETURNS trigger AS $$
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
CREATE TRIGGER listings_listing_relations_trigger
BEFORE INSERT OR UPDATE OF vertical_id, category_id, state_id, county_id ON listings_listing
FOR EACH ROW EXECUTE FUNCTION listings_validate_listing_relations();

CREATE FUNCTION listings_validate_auto_vertical() RETURNS trigger AS $$
BEGIN
    IF (SELECT slug FROM catalog_vertical v
        JOIN listings_listing l ON l.vertical_id = v.id
        WHERE l.id = NEW.listing_id) != 'autos' THEN
        RAISE EXCEPTION 'auto details require the Autos vertical';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER listings_auto_vertical_trigger
BEFORE INSERT OR UPDATE OF listing_id ON listings_autodetails
FOR EACH ROW EXECUTE FUNCTION listings_validate_auto_vertical();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS listings_auto_vertical_trigger ON listings_autodetails;
DROP FUNCTION IF EXISTS listings_validate_auto_vertical();
DROP TRIGGER IF EXISTS listings_listing_relations_trigger ON listings_listing;
DROP FUNCTION IF EXISTS listings_validate_listing_relations();
"""


def create_postgres_triggers(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE_SQL)


def drop_postgres_triggers(apps, schema_editor) -> None:
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_category_parent_vertical_trigger"),
        ("listings", "0001_initial"),
        ("locations", "0002_county_state_fips_trigger"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.CheckConstraint(
                condition=models.Q(status="draft"),
                name="listings_draft_status_only",
            ),
        ),
        migrations.RunPython(create_postgres_triggers, drop_postgres_triggers),
    ]
