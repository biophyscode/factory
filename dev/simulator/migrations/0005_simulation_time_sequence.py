# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0004_auto_20160111_0529'),
    ]

    operations = [
        migrations.AddField(
            model_name='simulation',
            name='time_sequence',
            field=models.CharField(default=b'', max_length=100),
        ),
    ]
