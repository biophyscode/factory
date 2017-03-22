# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0012_auto_20160127_2138'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calculation',
            name='slice_name',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
