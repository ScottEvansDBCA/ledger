# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-04-06 03:54
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0013_auto_20180406_1139'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='compliance',
            name='lodgement_number',
        ),
    ]
