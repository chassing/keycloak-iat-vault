import logging
from datetime import datetime as dt
from datetime import timedelta

from .config import config
from .keycloak import (
    ClientInitialAccess,
    ClientInitialAccessCreate,
    KeycloakAPI,
)
from .vault import (
    SecretNotFound,
    VaultAPI,
)

LOG_FMT = "[%(asctime)s] %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

# setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FMT,
    datefmt=LOG_DATEFMT,
)
log = logging.getLogger(__name__)


def is_expired(iat_secret: ClientInitialAccess) -> bool:
    exp = dt.fromtimestamp(iat_secret.timestamp + iat_secret.expiration)
    # still valid for 1 day?
    return exp < dt.now() + timedelta(days=1)


def run() -> None:
    # init API clients
    keycloak_api = KeycloakAPI(
        url=config.keycloak_url,
        realm=config.keycloak_realm,
        client_id=config.keycloak_client_id,
        client_secret=config.keycloak_client_secret,
    )
    vault_api = VaultAPI(
        url=config.vault_url,
        approle_role_id=config.vault_approle_role_id,
        approle_secret_id=config.vault_approle_secret_id,
    )

    # get all clients
    existing_client_initial_accesses = keycloak_api.list_client_inital_access()

    # get current IAT
    log.info(f"Reading IAT from Vault: {config.vault_secret_path}")
    try:
        existing_iat_secret = ClientInitialAccess(
            **vault_api.read_all(path=config.vault_secret_path)
        )
    except SecretNotFound:
        existing_iat_secret = None
    if (
        not existing_iat_secret
        or is_expired(existing_iat_secret)
        or existing_iat_secret.remaining_count == 0
        # client access token does not exist in keycloak anymore
        or existing_iat_secret.id
        not in [cia.id for cia in existing_client_initial_accesses]
    ):
        log.info(
            f"Creating new initial access token: client count ({config.max_client_count}, expiration: {config.expiration_in_days} days)"
        )
        client_inital_access = keycloak_api.create_client_inital_access(
            data=ClientInitialAccessCreate(
                count=config.max_client_count,
                expiration=config.expiration_in_days * 24 * 60 * 60,
            )
        )
        iat_secret = client_inital_access.dict()
    else:
        log.info(
            f"Updating initial access token ({existing_iat_secret.id}) information"
        )
        cia = [
            cia
            for cia in existing_client_initial_accesses
            if cia.id == existing_iat_secret.id
        ][0]
        existing_iat_secret.remaining_count = cia.remaining_count
        iat_secret = existing_iat_secret.dict()

    log.info(f"Writing IAT to Vault: {config.vault_secret_path}")
    iat_secret["url"] = keycloak_api.realm_url
    vault_api.write(path=config.vault_secret_path, data=iat_secret)


if __name__ == "__main__":
    run()
