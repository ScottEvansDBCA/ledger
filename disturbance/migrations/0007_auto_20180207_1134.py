# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-02-07 03:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0006_compliance_approval'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proposal',
            name='processing_status',
            field=models.CharField(choices=[('temp', 'Temporary'), ('draft', 'Draft'), ('with_assessor', 'With Assessor'), ('with_referral', 'With Referral'), ('with_assessor_requirements', 'With Assessor (Requirements)'), ('with_approver', 'With Approver'), ('renewal', 'Renewal'), ('licence_amendment', 'Licence Amendment'), ('awaiting_applicant_response', 'Awaiting Applicant Response'), ('awaiting_assessor_response', 'Awaiting Assessor Response'), ('awaiting_responses', 'Awaiting Responses'), ('ready_for_conditions', 'Ready for Conditions'), ('ready_to_issue', 'Ready to Issue'), ('approved', 'Approved'), ('declined', 'Declined'), ('discarded', 'Discarded')], default='draft', max_length=30, verbose_name='Processing Status'),
        ),
    ]
