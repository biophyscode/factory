# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0003_auto_20160108_2220'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='backgroundjob',
            options={'verbose_name': 'Background Job'},
        ),
    ]
