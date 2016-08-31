# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-31 06:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wl_main', '0014_communicationslogentry_cc'),
    ]

    operations = [
        migrations.CreateModel(
            name='LicenceVariantLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField()),
                ('licence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wl_main.WildlifeLicence')),
            ],
        ),
        migrations.CreateModel(
            name='Variant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('product_code', models.SlugField(max_length=64, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='VariantGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('child', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wl_main.VariantGroup')),
                ('variants', models.ManyToManyField(to='wl_main.Variant')),
            ],
        ),
        migrations.RenameField(
            model_name='wildlifelicencetype',
            old_name='code_slug',
            new_name='product_code',
        ),
        migrations.AddField(
            model_name='licencevariantlink',
            name='variant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wl_main.Variant'),
        ),
        migrations.AddField(
            model_name='wildlifelicence',
            name='variants',
            field=models.ManyToManyField(blank=True, through='wl_main.LicenceVariantLink', to='wl_main.Variant'),
        ),
        migrations.AddField(
            model_name='wildlifelicencetype',
            name='variant_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wl_main.VariantGroup'),
        ),
    ]
