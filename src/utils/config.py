from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ----------------------------------
    # Azure OpenAI
    # ----------------------------------
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_API_VERSION: str

    # ----------------------------------
    # Azure DevOps
    # ----------------------------------
    ADO_ORG_URL: str
    ADO_PROJECT: str

    # ----------------------------------
    # Service Principal
    # ----------------------------------
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str

    # ----------------------------------
    # Environment
    # ----------------------------------
    ENVIRONMENT: str = "local"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
