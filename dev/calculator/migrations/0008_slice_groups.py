# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0007_auto_20160121_2214'),
    ]

    operations = [
        migrations.AddField(
            model_name='slice',
            name='groups',
            field=models.ManyToManyField(to='calculator.Group'),
        ),
    ]
