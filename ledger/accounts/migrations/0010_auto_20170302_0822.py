# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-02 00:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_emailuserreport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailuser',
            name='first_name',
            field=models.CharField(max_length=128, verbose_name='Given name(s)'),
        ),
    ]