# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-31 06:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wl_main', '0015_auto_20160831_1445'),
        ('wl_applications', '0009_application_is_licence_amendment'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationVariantLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField()),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wl_applications.Application')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wl_main.Variant')),
            ],
        ),
        migrations.AddField(
            model_name='application',
            name='variants',
            field=models.ManyToManyField(blank=True, through='wl_applications.ApplicationVariantLink', to='wl_main.Variant'),
        ),
    ]
