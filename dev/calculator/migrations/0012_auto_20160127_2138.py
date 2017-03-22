# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0011_calculation'),
    ]

    operations = [
        migrations.RenameField(
            model_name='calculation',
            old_name='simulation',
            new_name='group',
        ),
    ]
