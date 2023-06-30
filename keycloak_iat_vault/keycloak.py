import requests
from pydantic import (
    BaseModel,
    Field,
)
from sretoolbox.utils import retry


class ClientInitialAccessCreate(BaseModel):
    count: int
    expiration: int


class ClientInitialAccess(BaseModel):
    count: int
    expiration: int
    id: str
    remaining_count: int = Field(None, alias="remainingCount")
    timestamp: int
    token: str

    class Config:
        extra = "ignore"


class ClientInitialAccessList(BaseModel):
    id: str
    timestamp: int
    expiration: int
    count: int
    remaining_count: int = Field(None, alias="remainingCount")

    class Config:
        extra = "ignore"


class Token(BaseModel):
    access_token: str
    expires_in: int
    refresh_expires_in: int
    token_type: str
    not_before_policy: int = Field(..., alias="not-before-policy")
    scope: str


class KeycloakAPI:
    def __init__(
        self,
        url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        timeout: int = 30,
    ) -> None:
        self.url = url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._init_openid_configuration()
        self._token = self._init_token()

    def _init_openid_configuration(self) -> None:
        self._openid_configuration = requests.get(
            f"{self.realm_url}/.well-known/openid-configuration",
            timeout=self.timeout,
        ).json()

    def _init_token(self) -> Token:
        response = requests.post(
            self._openid_configuration["token_endpoint"],
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return Token(**response.json())

    @property
    def realm_url(self) -> str:
        return f"{self.url}/realms/{self.realm}"

    @property
    def admin_realm_url(self) -> str:
        return f"{self.url}/admin/realms/{self.realm}"

    @retry()
    def create_client_inital_access(
        self, data: ClientInitialAccessCreate
    ) -> ClientInitialAccess:
        response = requests.post(
            f"{self.admin_realm_url}/clients-initial-access",
            headers={
                "Authorization": f"{self._token.token_type} {self._token.access_token}"
            },
            json=data.dict(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return ClientInitialAccess(**response.json())

    @retry()
    def list_client_inital_access(self) -> list[ClientInitialAccessList]:
        response = requests.get(
            f"{self.admin_realm_url}/clients-initial-access",
            headers={
                "Authorization": f"{self._token.token_type} {self._token.access_token}"
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return [ClientInitialAccessList(**item) for item in response.json()]
