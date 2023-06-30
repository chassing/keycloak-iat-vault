from pydantic import (
    AnyHttpUrl,
    BaseSettings,
)


class Config(BaseSettings):
    max_client_count: int = 100
    expiration_in_days: int = 30

    keycloak_url: AnyHttpUrl
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str

    vault_url: AnyHttpUrl
    vault_approle_role_id: str
    vault_approle_secret_id: str
    vault_secret_path: str

    class Config:
        case_sensitive = False
        env_prefix = "kia_"


config = Config()  # type: ignore # attributes must be set via environment variables
