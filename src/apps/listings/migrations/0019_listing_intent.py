from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0018_alter_listingcustomfield_normalized_label_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="intent",
            field=models.CharField(
                choices=[("offer", "For sale"), ("wanted", "Wanted")],
                default="offer",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.CheckConstraint(
                condition=models.Q(("intent__in", ["offer", "wanted"])),
                name="listings_intent_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(
                fields=["status", "intent", "state", "-published_at"],
                name="listings_public_intent_idx",
            ),
        ),
    ]
