from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        # Add without unique so existing rows can each get their own UUID first.
        migrations.AddField(
            model_name="user",
            name="email_verification_token",
            field=models.UUIDField(blank=True, null=True),
        ),
        # Assign a distinct UUID to every existing row using gen_random_uuid().
        migrations.RunSQL(
            sql='UPDATE "accounts_user" SET "email_verification_token" = gen_random_uuid() WHERE "email_verification_token" IS NULL',
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Now safe to add the unique constraint.
        migrations.AlterField(
            model_name="user",
            name="email_verification_token",
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
    ]
