"""Message storage using SQLAlchemy."""

from sqlalchemy import create_engine, Column, String, Integer, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Any, Optional
import json

Base = declarative_base()


class StoredMessage(Base):
    """SQLAlchemy model for stored messages."""

    __tablename__ = "groupme_messages"

    id = Column(String(255), primary_key=True)
    group_id = Column(String(255), index=True, nullable=False)
    user_id = Column(String(255), index=True, nullable=False)
    text = Column(Text, nullable=True)
    created_at = Column(Integer, index=True, nullable=False)
    direction = Column(String(20), index=True, nullable=False)  # 'received' or 'sent'
    raw_json = Column(Text, nullable=False)

    __table_args__ = (
        Index("idx_group_user", "group_id", "user_id"),
        Index("idx_created_at_desc", created_at.desc()),
    )


class MessageStorage:
    """
    Handles storage of GroupMe messages using SQLAlchemy.
    Supports SQLite, PostgreSQL, MySQL, and other SQLAlchemy-compatible databases.
    """

    def __init__(self, connection_string: str = "sqlite:///messages.db"):
        """
        Initialize storage with database connection.

        Args:
            connection_string: SQLAlchemy connection string
                Examples:
                - "sqlite:///messages.db" (default)
                - "postgresql://user:pass@localhost/dbname"
                - "mysql://user:pass@localhost/dbname"
        """
        self.connection_string = connection_string
        self.engine = create_engine(connection_string)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """
        Get a new SQLAlchemy session for custom queries.
        Remember to close the session when done!

        Returns:
            SQLAlchemy Session object

        Example:
            session = storage.get_session()
            try:
                results = session.query(StoredMessage).filter(...).all()
            finally:
                session.close()
        """
        return self.Session()

    def save_received(self, message_data: dict):
        """
        Store incoming webhook payload.

        Args:
            message_data: Raw message dict from GroupMe webhook
        """
        session = self.Session()
        try:
            msg = StoredMessage(
                id=message_data["id"],
                group_id=message_data.get("group_id", ""),
                user_id=message_data.get("user_id", ""),
                text=message_data.get("text", ""),
                created_at=message_data.get("created_at", 0),
                direction="received",
                raw_json=json.dumps(message_data),
            )
            session.merge(msg)  # INSERT or UPDATE if exists
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def save_sent(
        self,
        text: str,
        group_id: str,
        bot_id: str,
        image_url: Optional[str] = None,
    ):
        """
        Store outgoing message.

        Args:
            text: Message text
            group_id: Group ID
            bot_id: Bot ID that sent the message
            image_url: Optional image URL
        """
        import time

        session = self.Session()
        try:
            # Create synthetic message object
            message_data = {
                "id": f"sent_{int(time.time() * 1000)}_{bot_id}",
                "group_id": group_id,
                "user_id": bot_id,
                "text": text,
                "created_at": int(time.time()),
                "sender_type": "bot",
                "direction": "sent",
            }

            if image_url:
                message_data["picture_url"] = image_url

            msg = StoredMessage(
                id=message_data["id"],
                group_id=group_id,
                user_id=bot_id,
                text=text,
                created_at=message_data["created_at"],
                direction="sent",
                raw_json=json.dumps(message_data),
            )
            session.add(msg)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_recent(self, group_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent messages as dicts.

        Args:
            group_id: Group ID to filter by
            limit: Number of messages to retrieve

        Returns:
            List of message dicts (newest first)
        """
        session = self.Session()
        try:
            results = (
                session.query(StoredMessage)
                .filter(StoredMessage.group_id == group_id)
                .order_by(StoredMessage.created_at.desc())
                .limit(limit)
                .all()
            )

            return [json.loads(msg.raw_json) for msg in results]
        finally:
            session.close()
