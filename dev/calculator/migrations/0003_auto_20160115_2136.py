# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0002_group_slice'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='simulations',
            new_name='simulation',
        ),
        migrations.RenameField(
            model_name='slice',
            old_name='simulations',
            new_name='simulation',
        ),
    ]
