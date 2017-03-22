# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0005_simulation_time_sequence'),
        ('calculator', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', unique=True, max_length=100)),
                ('selection', models.TextField(default=b'all')),
                ('simulations', models.ForeignKey(to='simulator.Simulation')),
            ],
        ),
        migrations.CreateModel(
            name='Slice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', unique=True, max_length=100)),
                ('simulations', models.ForeignKey(to='simulator.Simulation')),
            ],
        ),
    ]
