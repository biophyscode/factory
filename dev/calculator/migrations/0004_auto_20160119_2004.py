# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0005_simulation_time_sequence'),
        ('calculator', '0003_auto_20160115_2136'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='simulation',
        ),
        migrations.AddField(
            model_name='group',
            name='simulation',
            field=models.ManyToManyField(to='simulator.Simulation'),
        ),
    ]
