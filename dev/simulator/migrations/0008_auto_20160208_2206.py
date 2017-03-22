# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0007_source_singleton'),
    ]

    operations = [
        migrations.RenameField(
            model_name='source',
            old_name='singleton',
            new_name='elevate',
        ),
    ]
