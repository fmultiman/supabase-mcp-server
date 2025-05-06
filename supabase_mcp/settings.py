import os
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from supabase_mcp.logger import logger

SUPPORTED_REGIONS = Literal[
    "us-west-1", "us-east-1", "us-east-2", "ca-central-1",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
    "eu-central-2", "eu-north-1", "ap-south-1", "ap-southeast-1",
    "ap-northeast-1", "ap-northeast-2", "ap-southeast-2", "sa-east-1"
]


def find_config_file(env_file: str = ".env") -> str | None:
    cwd_config = Path.cwd() / env_file
    if cwd_config.exists():
        return str(cwd_config)

    home = Path.home()
    if os.name == "nt":
        global_config = Path(os.environ.get("APPDATA", "")) / "supabase-mcp" / ".env"
    else:
        global_config = home / ".config" / "supabase-mcp" / ".env"

    if global_config.exists():
        logger.error(
            f"DEPRECATED: {global_config} is deprecated and will be removed in a future release. "
            "Use your IDE's native .json config file to configure access to MCP."
        )
        return str(global_config)

    return None


class Settings(BaseSettings):
    supabase_project_ref: str = Field(
        default="127.0.0.1:54322",
        description="Supabase project ref - can be a domain, IP or project ID",
        alias="SUPABASE_PROJECT_REF",
    )
    supabase_db_password: str | None = Field(
        default=None,
        description="Database password for Supabase",
        alias="SUPABASE_DB_PASSWORD",
    )
    supabase_region: str = Field(
        default="us-east-1",
        description="Supabase region",
        alias="SUPABASE_REGION",
    )
    supabase_access_token: str | None = Field(
        default=None,
        description="Optional Supabase access token",
        alias="SUPABASE_ACCESS_TOKEN",
    )
    supabase_service_role_key: str | None = Field(
        default=None,
        description="Optional Supabase service role key",
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )
    supabase_api_url: str = Field(
        default="https://api.supabase.com",
        description="Supabase API URL",
    )
    query_api_key: str = Field(
        default="test-key",
        description="TheQuery.dev API key",
        alias="QUERY_API_KEY",
    )
    query_api_url: str = Field(
        default="https://api.thequery.dev/v1",
        description="TheQuery.dev API URL",
        alias="QUERY_API_URL",
    )

    @field_validator("supabase_region")
    @classmethod
    def validate_region(cls, v: str, info: ValidationInfo) -> str:
        """Allow any region, including 'local'."""
        return v

    @field_validator("supabase_project_ref")
    @classmethod
    def validate_project_ref(cls, v: str) -> str:
        """Allow any hostname, IP or string for self-hosted Supabase."""
        if not v:
            raise ValueError("SUPABASE_PROJECT_REF cannot be empty.")
        return v

    @field_validator("supabase_db_password")
    @classmethod
    def validate_db_password(cls, v: str | None, info: ValidationInfo) -> str:
        project_ref = info.data.get("supabase_project_ref", "")
        if project_ref.startswith("127.0.0.1"):
            return v or "postgres"
        if not v:
            logger.error("SUPABASE_DB_PASSWORD is required when connecting to a remote instance")
            raise ValueError("Database password is required for remote Supabase projects.")
        return v

    @classmethod
    def with_config(cls, config_file: str | None = None) -> "Settings":
        class SettingsWithConfig(cls):
            model_config = SettingsConfigDict(env_file=config_file, env_file_encoding="utf-8")

        instance = SettingsWithConfig()

        env_vars_present = any(var in os.environ for var in ["SUPABASE_PROJECT_REF", "SUPABASE_DB_PASSWORD"])
        if env_vars_present and config_file:
            logger.info(f"Using environment variables over config file: {config_file}")
        elif env_vars_present:
            logger.info("Using environment variables for configuration")
        elif config_file:
            logger.info(f"Using settings from config file: {config_file}")
        else:
            logger.info("Using default settings (local development)")

        return instance


settings = Settings.with_config(find_config_file())
