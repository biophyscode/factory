# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackgroundJob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('simulation', models.ForeignKey(to='simulator.Simulation')),
            ],
            options={
                'verbose_name': 'process',
            },
        ),
        migrations.AlterField(
            model_name='source',
            name='name',
            field=models.CharField(default=b'', unique=True, max_length=100),
        ),
    ]
