# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-03-21 06:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nova', '0090_auto_20180316_1911'),
    ]

    operations = [
        migrations.AlterField(
            model_name='database',
            name='db_name',
            field=models.CharField(max_length=30, verbose_name='\u6570\u636e\u5e93\u540d\u79f0'),
        ),
    ]