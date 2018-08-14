# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-03-21 08:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wildlifecompliance', '0027_wildlifelicencecategory_activity'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='defaultactivity',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='defaultactivity',
            name='activity_type',
        ),
        migrations.RemoveField(
            model_name='defaultactivity',
            name='category',
        ),
        migrations.RemoveField(
            model_name='wildlifelicencecategory',
            name='activity',
        ),
        migrations.DeleteModel(
            name='DefaultActivity',
        ),
        migrations.DeleteModel(
            name='WildlifeLicenceActivityType',
        ),
    ]