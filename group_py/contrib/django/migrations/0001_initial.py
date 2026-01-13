"""Initial migration for group_py.contrib.django models."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Create GroupMeMessage and GroupMeAttachment tables."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='GroupMeMessage',
            fields=[
                ('message_id', models.CharField(
                    help_text='GroupMe message ID',
                    max_length=255,
                    primary_key=True,
                    serialize=False
                )),
                ('group_id', models.CharField(
                    db_index=True,
                    help_text='GroupMe group ID',
                    max_length=255
                )),
                ('user_id', models.CharField(
                    db_index=True,
                    help_text="Sender's user ID",
                    max_length=255
                )),
                ('created_at', models.IntegerField(
                    db_index=True,
                    help_text='Unix timestamp when message was created'
                )),
                ('user_name', models.CharField(
                    help_text="Sender's display name",
                    max_length=255
                )),
                ('text', models.TextField(
                    blank=True,
                    help_text='Message text content',
                    null=True
                )),
                ('sender_type', models.CharField(
                    help_text="'user' or 'bot'",
                    max_length=20
                )),
                ('system', models.BooleanField(
                    default=False,
                    help_text='Whether this is a system message'
                )),
                ('avatar_url', models.URLField(
                    blank=True,
                    help_text="Sender's avatar URL",
                    max_length=500,
                    null=True
                )),
                ('raw_json', models.JSONField(
                    help_text='Complete message data as JSON'
                )),
            ],
            options={
                'verbose_name': 'GroupMe Message',
                'verbose_name_plural': 'GroupMe Messages',
                'db_table': 'groupme_messages',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GroupMeAttachment',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('attachment_type', models.CharField(
                    db_index=True,
                    help_text='Attachment type (image, location, etc.)',
                    max_length=50
                )),
                ('data', models.JSONField(
                    help_text='Full attachment data as JSON'
                )),
                ('message', models.ForeignKey(
                    help_text='Parent message',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments_set',
                    to='group_py_django.groupmemessage'
                )),
            ],
            options={
                'verbose_name': 'GroupMe Attachment',
                'verbose_name_plural': 'GroupMe Attachments',
                'db_table': 'groupme_attachments',
            },
        ),
        migrations.AddIndex(
            model_name='groupmemessage',
            index=models.Index(
                fields=['group_id', 'created_at'],
                name='groupme_mes_group_i_a1b2c3_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='groupmemessage',
            index=models.Index(
                fields=['group_id', 'user_id'],
                name='groupme_mes_group_i_d4e5f6_idx'
            ),
        ),
    ]
