# app/models/integration_account.py — 100% РАБОТАЕТ С SQLALCHEMY 2.0+
from sqlalchemy import String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class IntegrationAccount(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connected_integration_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    bot_token: Mapped[str] = mapped_column(String, nullable=True)
    integration_url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, default="REGOS Бот")

    def __repr__(self):
        return f"<IntegrationAccount {self.connected_integration_id}>"