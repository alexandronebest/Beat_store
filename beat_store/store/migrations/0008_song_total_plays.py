# Generated by Django 5.1.5 on 2025-03-17 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_song_likes'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='total_plays',
            field=models.PositiveIntegerField(default=0, verbose_name='Количество прослушиваний'),
        ),
    ]
