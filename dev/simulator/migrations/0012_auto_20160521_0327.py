# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0011_auto_20160519_2028'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simulation',
            name='program',
            field=models.CharField(default=b'protein', max_length=100),
        ),
    ]
