# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0008_auto_20160208_2206'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bundle',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', unique=True, max_length=100)),
                ('path', models.CharField(max_length=200)),
            ],
            options={
                'verbose_name': 'AUTOMACS bundle',
            },
        ),
        migrations.RemoveField(
            model_name='backgroundjob',
            name='simulation',
        ),
        migrations.AlterField(
            model_name='simulation',
            name='code',
            field=models.CharField(unique=True, max_length=200, blank=True),
        ),
        migrations.AlterField(
            model_name='simulation',
            name='program',
            field=models.CharField(default=b'protein', max_length=30, choices=[(b'protein', b'protein'), (b'cgmd-bilayer', b'cgmd-bilayer'), (b'homology', b'homology')]),
        ),
        migrations.DeleteModel(
            name='BackgroundJob',
        ),
    ]
