"""Tests for Django helper models."""

import pytest
import os

# Configure Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.django_settings')

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'group_py.contrib.django',
        ],
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )

django.setup()

from django.core.management import call_command
from group_py.models import Message
from group_py.contrib.django.models import GroupMeMessage, GroupMeAttachment


@pytest.fixture(scope='module')
def django_db():
    """Set up Django database for tests."""
    call_command('migrate', '--run-syncdb', verbosity=0)
    yield
    # Cleanup handled by in-memory database


@pytest.fixture(autouse=True)
def clean_db(django_db):
    """Clean up database between tests."""
    yield
    # Clean up after each test to avoid data leakage
    GroupMeAttachment.objects.all().delete()
    GroupMeMessage.objects.all().delete()


@pytest.fixture
def sample_message_data():
    """Sample GroupMe message data."""
    return {
        'id': 'msg_123456',
        'text': 'Hello, world!',
        'user_id': 'user_123',
        'name': 'Test User',
        'group_id': 'group_456',
        'created_at': 1234567890,
        'system': False,
        'sender_type': 'user',
        'avatar_url': 'https://example.com/avatar.jpg',
        'attachments': [],
    }


@pytest.fixture
def sample_message(sample_message_data):
    """Create a Message object from sample data."""
    return Message.from_dict(sample_message_data)


@pytest.fixture
def message_with_image():
    """Message with image attachment."""
    return Message.from_dict({
        'id': 'msg_789',
        'text': 'Check this out!',
        'user_id': 'user_123',
        'name': 'Test User',
        'group_id': 'group_456',
        'created_at': 1234567891,
        'system': False,
        'sender_type': 'user',
        'avatar_url': None,
        'attachments': [
            {'type': 'image', 'url': 'https://example.com/image.jpg'}
        ],
    })


@pytest.fixture
def message_with_location():
    """Message with location attachment."""
    return Message.from_dict({
        'id': 'msg_loc_123',
        'text': 'Meet here!',
        'user_id': 'user_123',
        'name': 'Test User',
        'group_id': 'group_456',
        'created_at': 1234567892,
        'system': False,
        'sender_type': 'user',
        'avatar_url': None,
        'attachments': [
            {'type': 'location', 'lat': '37.7749', 'lng': '-122.4194', 'name': 'San Francisco'}
        ],
    })


@pytest.mark.django
class TestGroupMeMessage:
    """Tests for GroupMeMessage model."""

    def test_from_message(self, django_db, sample_message):
        """Test creating Django model from Message."""
        db_msg = GroupMeMessage.from_message(sample_message)

        assert db_msg.message_id == 'msg_123456'
        assert db_msg.text == 'Hello, world!'
        assert db_msg.user_id == 'user_123'
        assert db_msg.user_name == 'Test User'
        assert db_msg.group_id == 'group_456'
        assert db_msg.created_at == 1234567890
        assert db_msg.sender_type == 'user'
        assert db_msg.system is False
        assert db_msg.avatar_url == 'https://example.com/avatar.jpg'
        assert 'id' in db_msg.raw_json

    def test_to_message(self, django_db, sample_message):
        """Test converting Django model back to Message."""
        db_msg = GroupMeMessage.from_message(sample_message)
        converted = db_msg.to_message()

        assert converted.id == sample_message.id
        assert converted.text == sample_message.text
        assert converted.user_id == sample_message.user_id
        assert converted.name == sample_message.name
        assert converted.group_id == sample_message.group_id
        assert converted.created_at == sample_message.created_at

    def test_save_and_retrieve(self, django_db, sample_message):
        """Test saving and retrieving from database."""
        db_msg = GroupMeMessage.from_message(sample_message)
        db_msg.save()

        # Retrieve from database
        retrieved = GroupMeMessage.objects.get(message_id='msg_123456')
        assert retrieved.text == 'Hello, world!'
        assert retrieved.user_name == 'Test User'

    def test_query_by_group(self, django_db):
        """Test querying messages by group_id."""
        # Create messages in different groups
        for i in range(3):
            msg = Message.from_dict({
                'id': f'msg_group_a_{i}',
                'text': f'Message {i}',
                'user_id': 'user_1',
                'name': 'User',
                'group_id': 'group_a',
                'created_at': 1000 + i,
                'system': False,
                'sender_type': 'user',
            })
            GroupMeMessage.from_message(msg).save()

        for i in range(2):
            msg = Message.from_dict({
                'id': f'msg_group_b_{i}',
                'text': f'Message {i}',
                'user_id': 'user_1',
                'name': 'User',
                'group_id': 'group_b',
                'created_at': 2000 + i,
                'system': False,
                'sender_type': 'user',
            })
            GroupMeMessage.from_message(msg).save()

        # Query by group
        group_a_msgs = GroupMeMessage.objects.filter(group_id='group_a')
        group_b_msgs = GroupMeMessage.objects.filter(group_id='group_b')

        assert group_a_msgs.count() == 3
        assert group_b_msgs.count() == 2

    def test_ordering(self, django_db):
        """Test default ordering by created_at descending."""
        # Create messages with different timestamps
        for i, ts in enumerate([3000, 1000, 2000]):
            msg = Message.from_dict({
                'id': f'msg_order_{i}',
                'text': f'Message at {ts}',
                'user_id': 'user_1',
                'name': 'User',
                'group_id': 'group_order',
                'created_at': ts,
                'system': False,
                'sender_type': 'user',
            })
            GroupMeMessage.from_message(msg).save()

        # Query and check order
        msgs = list(GroupMeMessage.objects.filter(group_id='group_order'))
        timestamps = [m.created_at for m in msgs]
        assert timestamps == [3000, 2000, 1000]  # Descending order

    def test_str_representation(self, django_db, sample_message):
        """Test string representation."""
        db_msg = GroupMeMessage.from_message(sample_message)
        assert str(db_msg) == 'Test User: Hello, world!'

    def test_str_long_text_truncated(self, django_db):
        """Test that long text is truncated in string representation."""
        msg = Message.from_dict({
            'id': 'msg_long',
            'text': 'A' * 100,  # 100 characters
            'user_id': 'user_1',
            'name': 'User',
            'group_id': 'group_1',
            'created_at': 1000,
            'system': False,
            'sender_type': 'user',
        })
        db_msg = GroupMeMessage.from_message(msg)
        str_repr = str(db_msg)

        assert len(str_repr) < 100
        assert '...' in str_repr

    def test_null_text(self, django_db):
        """Test message with null text (e.g., image-only message)."""
        msg = Message.from_dict({
            'id': 'msg_no_text',
            'text': None,
            'user_id': 'user_1',
            'name': 'User',
            'group_id': 'group_1',
            'created_at': 1000,
            'system': False,
            'sender_type': 'user',
            'attachments': [{'type': 'image', 'url': 'https://example.com/img.jpg'}],
        })
        db_msg = GroupMeMessage.from_message(msg)
        db_msg.save()

        retrieved = GroupMeMessage.objects.get(message_id='msg_no_text')
        assert retrieved.text is None


@pytest.mark.django
class TestGroupMeAttachment:
    """Tests for GroupMeAttachment model."""

    def test_create_image_attachment(self, django_db, message_with_image):
        """Test creating image attachment."""
        db_msg = GroupMeMessage.from_message(message_with_image)
        db_msg.save()

        att_data = message_with_image.attachments[0]
        attachment = GroupMeAttachment.objects.create(
            message=db_msg,
            attachment_type=att_data['type'],
            data=att_data
        )

        assert attachment.attachment_type == 'image'
        assert attachment.url == 'https://example.com/image.jpg'
        assert attachment.location is None

    def test_create_location_attachment(self, django_db, message_with_location):
        """Test creating location attachment."""
        db_msg = GroupMeMessage.from_message(message_with_location)
        db_msg.save()

        att_data = message_with_location.attachments[0]
        attachment = GroupMeAttachment.objects.create(
            message=db_msg,
            attachment_type=att_data['type'],
            data=att_data
        )

        assert attachment.attachment_type == 'location'
        assert attachment.location == ('37.7749', '-122.4194', 'San Francisco')
        assert attachment.url is None

    def test_cascade_delete(self, django_db, message_with_image):
        """Test that attachments are deleted when message is deleted."""
        db_msg = GroupMeMessage.from_message(message_with_image)
        db_msg.save()

        att_data = message_with_image.attachments[0]
        GroupMeAttachment.objects.create(
            message=db_msg,
            attachment_type=att_data['type'],
            data=att_data
        )

        assert GroupMeAttachment.objects.filter(message=db_msg).count() == 1

        # Delete message
        db_msg.delete()

        # Attachment should be gone
        assert GroupMeAttachment.objects.filter(message_id='msg_789').count() == 0

    def test_query_by_type(self, django_db, message_with_image, message_with_location):
        """Test querying attachments by type."""
        # Save image message and attachment
        db_img = GroupMeMessage.from_message(message_with_image)
        db_img.save()
        GroupMeAttachment.objects.create(
            message=db_img,
            attachment_type='image',
            data=message_with_image.attachments[0]
        )

        # Save location message and attachment
        db_loc = GroupMeMessage.from_message(message_with_location)
        db_loc.save()
        GroupMeAttachment.objects.create(
            message=db_loc,
            attachment_type='location',
            data=message_with_location.attachments[0]
        )

        # Query by type
        images = GroupMeAttachment.objects.filter(attachment_type='image')
        locations = GroupMeAttachment.objects.filter(attachment_type='location')

        assert images.count() == 1
        assert locations.count() == 1

    def test_str_representation(self, django_db, message_with_image):
        """Test string representation."""
        db_msg = GroupMeMessage.from_message(message_with_image)
        db_msg.save()

        attachment = GroupMeAttachment.objects.create(
            message=db_msg,
            attachment_type='image',
            data=message_with_image.attachments[0]
        )

        assert 'image' in str(attachment)
        assert 'msg_789' in str(attachment)


@pytest.mark.django
class TestRoundTrip:
    """Test complete round-trip: Message -> Django -> Message."""

    def test_full_round_trip(self, django_db, sample_message_data):
        """Test complete data preservation through round trip."""
        # Original message
        original = Message.from_dict(sample_message_data)

        # Convert to Django and save
        db_msg = GroupMeMessage.from_message(original)
        db_msg.save()

        # Retrieve from database
        retrieved = GroupMeMessage.objects.get(message_id=original.id)

        # Convert back to Message
        converted = retrieved.to_message()

        # Verify all fields preserved
        assert converted.id == original.id
        assert converted.text == original.text
        assert converted.user_id == original.user_id
        assert converted.name == original.name
        assert converted.group_id == original.group_id
        assert converted.created_at == original.created_at
        assert converted.system == original.system
        assert converted.sender_type == original.sender_type
        assert converted.avatar_url == original.avatar_url
        assert converted.attachments == original.attachments

    def test_round_trip_with_attachments(self, django_db, message_with_image):
        """Test round trip preserves attachments."""
        db_msg = GroupMeMessage.from_message(message_with_image)
        db_msg.save()

        retrieved = GroupMeMessage.objects.get(message_id=message_with_image.id)
        converted = retrieved.to_message()

        assert len(converted.attachments) == 1
        assert converted.attachments[0]['type'] == 'image'
        assert converted.attachments[0]['url'] == 'https://example.com/image.jpg'
