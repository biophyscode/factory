# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0004_auto_20160119_2004'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='simulation',
        ),
        migrations.AddField(
            model_name='group',
            name='collection',
            field=models.ManyToManyField(to='calculator.Collection'),
        ),
    ]
