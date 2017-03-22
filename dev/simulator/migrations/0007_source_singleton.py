# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0006_auto_20160201_2129'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='singleton',
            field=models.BooleanField(default=False),
        ),
    ]
