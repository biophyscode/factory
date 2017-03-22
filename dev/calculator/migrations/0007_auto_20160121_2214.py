# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0006_auto_20160121_2202'),
    ]

    operations = [
        migrations.AddField(
            model_name='slice',
            name='end',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='slice',
            name='skip',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='slice',
            name='start',
            field=models.IntegerField(null=True),
        ),
    ]
