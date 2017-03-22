# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0010_backgroundcalc'),
    ]

    operations = [
        migrations.CreateModel(
            name='Calculation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', max_length=100)),
                ('uptype', models.CharField(default=b'simulation', max_length=30, choices=[(b'simulation', b'simulation'), (b'post', b'post')])),
                ('slice_name', models.CharField(blank=True, max_length=50, null=True, choices=[(b'modest', b'modest'), (b'lengthy', b'lengthy')])),
                ('collections', models.ManyToManyField(to='calculator.Collection')),
                ('simulation', models.ForeignKey(to='calculator.Group')),
            ],
        ),
    ]
