from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(default="", validation_alias="API_KEY")
    google_api_key: str = Field(default="", validation_alias="GOOGLE_API_KEY")
    google_cse_id: str = Field(default="", validation_alias="GOOGLE_CSE_ID")

    whatsapp_instance: str = Field(
        default="personal-assistant",
        validation_alias="WHATSAPP_INSTANCE",
    )
    whatsapp_gateway_url: str = Field(
        default="http://localhost:3000",
        validation_alias="WHATSAPP_GATEWAY_URL",
    )

    webhook_secret: str = Field(default="", validation_alias="WEBHOOK_SECRET")
    admin_numbers: str = Field(default="", validation_alias="ADMIN_NUMBERS")

    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    @property
    def admin_number_set(self) -> set[str]:
        return {
            number.strip()
            for number in self.admin_numbers.split(",")
            if number.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
