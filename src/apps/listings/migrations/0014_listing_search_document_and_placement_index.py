from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import migrations, models


def create_postgres_search_index(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "CREATE INDEX listings_search_document_gin "
            "ON listings_listing USING gin (search_document)"
        )


def drop_postgres_search_index(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP INDEX IF EXISTS listings_search_document_gin")


class Migration(migrations.Migration):
    dependencies = [("listings", "0013_genericlistingdetails_listingcountyplacement")]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="search_document",
            field=SearchVectorField(editable=False, null=True),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_postgres_search_index, drop_postgres_search_index)
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="listing",
                    index=GinIndex(fields=["search_document"], name="listings_search_document_gin"),
                )
            ],
        ),
        migrations.AddIndex(
            model_name="listingcountyplacement",
            index=models.Index(fields=["county"], name="listings_placement_county_idx"),
        ),
    ]
