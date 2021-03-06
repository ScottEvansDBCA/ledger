# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-04-11 02:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0018_comprequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplianceAmendmentRequest',
            fields=[
                ('comprequest_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='disturbance.CompRequest')),
                ('status', models.CharField(choices=[('requested', 'Requested'), ('amended', 'Amended')], default='requested', max_length=30, verbose_name='Status')),
                ('reason', models.CharField(choices=[('insufficient_detail', 'The information provided was insufficient'), ('missing_information', 'There was missing information'), ('other', 'Other')], default='insufficient_detail', max_length=30, verbose_name='Reason')),
            ],
            bases=('disturbance.comprequest',),
        ),
    ]
