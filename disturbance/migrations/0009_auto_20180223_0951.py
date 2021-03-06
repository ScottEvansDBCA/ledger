# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-02-23 01:51
from __future__ import unicode_literals

import disturbance.components.organisations.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_auto_20171228_1221'),
        ('disturbance', '0008_auto_20180207_1317'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationLogDocument',
            fields=[
                ('document_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='accounts.Document')),
                ('_file', models.FileField(upload_to=disturbance.components.organisations.models.update_organisation_comms_log_filename)),
                ('log_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='disturbance.OrganisationLogEntry')),
            ],
            bases=('accounts.document',),
        ),
        migrations.AlterField(
            model_name='communicationslogentry',
            name='type',
            field=models.CharField(choices=[('email', 'Email'), ('phone', 'Phone Call'), ('mail', 'Mail'), ('person', 'In Person')], default='email', max_length=20),
        ),
    ]
