from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0021_listing_available_for_pickup_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="first_published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="sold_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="sold_public_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(
                fields=["seller", "status", "sold_public_until"],
                name="listings_seller_sold_feed_idx",
            ),
        ),
    ]
