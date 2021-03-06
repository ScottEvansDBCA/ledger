# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-04-10 04:39
from __future__ import unicode_literals

import disturbance.components.compliances.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0016_compliancelogentry_complianceuseraction'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplianceLogDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100, verbose_name='name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('uploaded_date', models.DateTimeField(auto_now_add=True)),
                ('_file', models.FileField(upload_to=disturbance.components.compliances.models.update_compliance_comms_log_filename)),
                ('log_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='disturbance.ComplianceLogEntry')),
            ],
        ),
    ]
