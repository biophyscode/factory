# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0002_auto_20160108_2219'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='backgroundjob',
            name='name',
        ),
        migrations.AddField(
            model_name='backgroundjob',
            name='pid',
            field=models.IntegerField(default=-1),
        ),
    ]
