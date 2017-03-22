# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0009_auto_20160517_2146'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simulation',
            name='program',
            field=models.CharField(default=b'protein', max_length=100, choices=[(b'protein', b'protein'), (b'cgmd-bilayer', b'cgmd-bilayer'), (b'homology', b'homology'), ('trialanine > metarun_test_3ala.py', 'trialanine > metarun_test_3ala.py')]),
        ),
    ]
