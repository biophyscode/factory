# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Simulation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('program', models.CharField(default=b'protein', max_length=30, choices=[(b'protein', b'protein'), (b'cgmd-bilayer', b'cgmd-bilayer')])),
                ('started', models.BooleanField(default=False)),
                ('code', models.CharField(unique=True, max_length=200)),
                ('dropspot', models.TextField(default=b'./')),
            ],
            options={
                'verbose_name': 'AUTOMACS simulation',
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', max_length=100)),
                ('dropspot', models.TextField(default=b'./')),
            ],
        ),
        migrations.AddField(
            model_name='simulation',
            name='sources',
            field=models.ManyToManyField(to='simulator.Source'),
        ),
    ]
