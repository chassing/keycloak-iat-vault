import logging
from typing import (
    Mapping,
    Optional,
)

import hvac
from sretoolbox.utils import retry


class PathAccessForbidden(Exception):
    pass


class SecretNotFound(Exception):
    pass


class SecretAccessForbidden(Exception):
    pass


class SecretVersionIsNone(Exception):
    pass


class SecretVersionNotFound(Exception):
    pass


log = logging.getLogger(__name__)
SECRET_VERSION_LATEST = "LATEST"


class VaultAPI:
    def __init__(self, url: str, approle_role_id: str, approle_secret_id: str) -> None:
        self.url = url
        self.approle_role_id = approle_role_id
        self.approle_secret_id = approle_secret_id

        self._client = self._init_client()

    def _init_client(self) -> hvac.Client:
        client = hvac.Client(url=self.url)
        # client.token = "1234567890"
        client.auth.approle.login(self.approle_role_id, self.approle_secret_id)
        if not client.is_authenticated():
            raise RuntimeError("Vault authentication failed.")
        return client

    def _get_mount_version_by_secret_path(self, path):
        path_split = path.split("/")
        mount_point = path_split[0]
        return self.__get_mount_version(mount_point)

    def __get_mount_version(self, mount_point):
        try:
            self._client.secrets.kv.v2.read_configuration(mount_point)
            version = 2
        except Exception:
            version = 1

        return version

    @retry(
        no_retry_exceptions=(PathAccessForbidden, SecretAccessForbidden, SecretNotFound)
    )
    def read_all_with_version(
        self, path: str, version: Optional[str] = None
    ) -> tuple[Mapping, Optional[str]]:
        """Returns a dictionary of keys and values in a Vault secret and the
        version of the secret, for V1 secrets, version will be None.

        The input secret is a dictionary which contains the following fields:
        * path - path to the secret in Vault
        * version (optional) - secret version to read (if this is
                               a v2 KV engine)
        """
        kv_version = self._get_mount_version_by_secret_path(path)

        data = None
        if kv_version == 2:
            data, version = self._read_all_v2(path, version)
        else:
            data = self._read_all_v1(path)
            version = None

        if data is None:
            raise SecretNotFound

        return data, version

    @retry(
        no_retry_exceptions=(PathAccessForbidden, SecretAccessForbidden, SecretNotFound)
    )
    def read_all(self, path: str, version: Optional[str] = None) -> dict:
        """Returns a dictionary of keys and values in a Vault secret.

        The input secret is a dictionary which contains the following fields:
        * path - path to the secret in Vault
        * version (optional) - secret version to read (if this is
                               a v2 KV engine)
        """
        return self.read_all_with_version(path, version)[0]

    def _read_all_v2(
        self, path: str, version: Optional[str]
    ) -> tuple[dict, Optional[str]]:
        path_split = path.split("/")
        mount_point = path_split[0]
        read_path = "/".join(path_split[1:])
        if version is None:
            msg = "version can not be null " f"for secret with path '{path}'."
            raise SecretVersionIsNone(msg)
        if version == SECRET_VERSION_LATEST:
            # https://github.com/hvac/hvac/blob/
            # ec048ded30d21c13c21cfa950d148c8bfc1467b0/
            # hvac/api/secrets_engines/kv_v2.py#L85
            version = None
        try:
            secret = self._client.secrets.kv.v2.read_secret_version(
                mount_point=mount_point,
                path=read_path,
                version=version,
            )
        except hvac.exceptions.InvalidPath:
            msg = f"version '{version}' not found " f"for secret with path '{path}'."
            raise SecretVersionNotFound(msg)
        except hvac.exceptions.Forbidden:
            msg = f"permission denied accessing secret '{path}'"
            raise SecretAccessForbidden(msg)
        if secret is None or "data" not in secret or "data" not in secret["data"]:
            raise SecretNotFound(path)

        data = secret["data"]["data"]
        secret_version = secret["data"]["metadata"]["version"]
        return data, secret_version

    def _read_all_v1(self, path):
        try:
            secret = self._client.read(path)
        except hvac.exceptions.Forbidden:
            msg = f"permission denied accessing secret '{path}'"
            raise SecretAccessForbidden(msg)

        if secret is None or "data" not in secret:
            raise SecretNotFound(path)

        return secret["data"]

    @retry()
    def write(self, path: str, data: Mapping, force: bool = False) -> None:
        """Write a secret to Vault.

        Args:
            path (str): Path to write secret to.
            data (dict): Data to write to Vault.
        """
        kv_version = self._get_mount_version_by_secret_path(path)
        if kv_version == 2:
            self._write_v2(path, data, force)
        else:
            self._write_v1(path, data)

    def _write_v2(self, path: str, data: Mapping, force: bool = False) -> None:
        path_split = path.split("/")
        mount_point = path_split[0]
        write_path = "/".join(path_split[1:])

        try:
            current_data, _ = self._read_all_v2(path, version=SECRET_VERSION_LATEST)
            if current_data == data and not force:
                log.debug(f"current data is up-to-date, skipping {path}")
                return
        except SecretVersionNotFound:
            # if the secret is not found we need to write it
            log.debug(f"secret not found in {path}, will create it")

        try:
            self._client.secrets.kv.v2.create_or_update_secret(
                mount_point=mount_point,
                path=write_path,
                secret=data,
            )
        except hvac.exceptions.Forbidden:
            msg = f"permission denied accessing secret '{path}'"
            raise SecretAccessForbidden(msg)

    def _write_v1(self, path, data):
        self._client.write(path, **data)
