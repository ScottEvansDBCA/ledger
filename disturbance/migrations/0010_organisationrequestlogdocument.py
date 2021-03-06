# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-02-23 02:47
from __future__ import unicode_literals

import disturbance.components.organisations.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_auto_20171228_1221'),
        ('disturbance', '0009_auto_20180223_0951'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationRequestLogDocument',
            fields=[
                ('document_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='accounts.Document')),
                ('_file', models.FileField(upload_to=disturbance.components.organisations.models.update_organisation_request_comms_log_filename)),
                ('log_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='disturbance.OrganisationRequestLogEntry')),
            ],
            bases=('accounts.document',),
        ),
    ]
