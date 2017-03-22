# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calculator', '0008_slice_groups'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='collection',
        ),
    ]
