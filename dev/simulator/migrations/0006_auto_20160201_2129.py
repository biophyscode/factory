# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0005_simulation_time_sequence'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='simulation',
            name='dropspot',
        ),
        migrations.RemoveField(
            model_name='source',
            name='dropspot',
        ),
    ]
