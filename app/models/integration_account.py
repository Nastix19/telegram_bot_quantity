from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class IntegrationAccount(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    connected_integration_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    bot_token: Mapped[str] = mapped_column(String, nullable=True)
    integration_url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, default="REGOS Бот")

    def __repr__(self):
        return f"<Account {self.connected_integration_id}>"