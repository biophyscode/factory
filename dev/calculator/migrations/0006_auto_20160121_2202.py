# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0005_auto_20160119_2133'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='collection',
            field=models.ManyToManyField(to='calculator.Collection', blank=True),
        ),
        migrations.AlterField(
            model_name='slice',
            name='name',
            field=models.CharField(default=b'', max_length=100),
        ),
    ]
