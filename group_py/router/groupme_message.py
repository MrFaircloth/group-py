from typing import List
from datetime import datetime


class Message:
    '''
    Contains message data sent via Groupme bot callbacks url.
    '''

    def __init__(self, raw_message_data: dict):
        self.attachments: List[str] = raw_message_data.get('attachments')
        self.avatar_url: str = raw_message_data.get('avatar_url')
        self.created_at: datetime = datetime.fromtimestamp(
            raw_message_data.get('created_at')
        )
        self.group_id: str = raw_message_data.get('group_id')
        self.id: str = raw_message_data.get('id')
        self.name: str = raw_message_data.get('name')
        self.sender_id: str = raw_message_data.get('sender_id')
        self.sender_type: str = raw_message_data.get('sender_type')
        self.source_guid: str = raw_message_data.get('source_guid')
        self.system: bool = raw_message_data.get('system')
        self.text: str = raw_message_data.get('text')
        self.user_id: str = raw_message_data.get('user_id')
        self._raw: dict = raw_message_data

    def __repr__(self) -> str:
        return f'<Message id=\'{self.id}\', name=\'{self.name}\''

    def __str__(self) -> str:
        return f'{self.created_at.strftime("%I:%M")} {self.name} {self.text}'
