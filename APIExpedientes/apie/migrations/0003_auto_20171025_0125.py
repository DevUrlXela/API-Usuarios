# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-25 08:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apie', '0002_auto_20171025_0055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expediente',
            name='fecha_entrada',
            field=models.DateField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='expediente',
            name='fecha_finalizacion',
            field=models.DateField(null=True),
        ),
    ]
