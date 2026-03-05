"""
Stub migration: reconciles index names from 0001_initial with model Meta.indexes.

In development environments this migration may already be recorded in
django_migrations under the auto-generated name
"0002_rename_accounts_auditlog_user_id_timestamp_047d90_idx_accounts_au_user_id_d4cccd_idx_and_more".
This file uses a clean short name so fresh installations apply the no-op
and existing databases that already have the ghost migration recorded can
be fake-applied (`migrate accounts 0002 --fake`) if needed.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        # Index names were already aligned in 0001_initial.py (short ≤30-char
        # names used throughout).  No rename operations needed here.
    ]
