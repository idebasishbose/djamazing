# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-02-27 09:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.FileField(upload_to='')),
            ],
        ),
    ]
