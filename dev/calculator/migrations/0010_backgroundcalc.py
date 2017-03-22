# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0009_remove_group_collection'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackgroundCalc',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pid', models.IntegerField(default=-1)),
            ],
            options={
                'verbose_name': 'Background Calculation',
            },
        ),
    ]
