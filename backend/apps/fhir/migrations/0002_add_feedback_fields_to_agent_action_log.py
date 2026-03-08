from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fhir", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="agentactionlog",
            name="feedback_rating",
            field=models.SmallIntegerField(
                blank=True,
                help_text="Clinician quality rating: 1 (not helpful) or 2 (helpful)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="agentactionlog",
            name="feedback_comment",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="agentactionlog",
            name="feedback_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
