# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-11-07 00:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bpay', '0011_parkstay_rebase'),
    ]

    operations = [
        migrations.AddField(
            model_name='bpaytransaction',
            name='original_crn',
            field=models.CharField(blank=True, help_text=b'Customer Referencer Number', max_length=20, null=True),
        ),
    ]
