# keycloak-iat-vault
This command line tool creates a Keycloak initial access token and stores it in Vault.

# Features

* Create a Keycloak initial access token via API
* Store the initial access token in Vault
* Update the initial access token information in Vault (e.g., client count)
* Recreate the initial access token if it expires in less than a day or doesn't exist anymore in Keycloak

# Keycloak Permissions

The tool requires the following permissions in Keycloak:

* `realm-management` > `manage-clients`

# Vault Permissions

The tool uses the AppRole authentication method to authenticate with Vault. The AppRole role must have the following permissions on the secret path:

* `read`
* `create`
* `update`

# Configuration

In this initial version, the tool only supports configuration via environment variables.

| Variable                      | Description                                                |
| ----------------------------- | ---------------------------------------------------------- |
| `KIA_MAX_CLIENT_COUNT`        | The maximum number of clients to create  [*Default*: 100]  |
| `KIA_EXPIRATION_IN_DAYS`      | The number of days till the token expires [*Default*: 30]  |
| `KIA_KEYCLOAK_URL`            | The URL of the Keycloak server [*required*]                |
| `KIA_KEYCLOAK_REALM`          | The Keycloak realm [*required*]                            |
| `KIA_KEYCLOAK_CLIENT_ID`      | The Keycloak client ID [*required*]                        |
| `KIA_KEYCLOAK_CLIENT_SECRET`  | The Keycloak client secret [*required*]                    |
| `KIA_VAULT_URL`               | The URL of the Vault server [*required*]                   |
| `KIA_VAULT_APPROLE_ROLE_ID`   | The Vault AppRole role ID [*required*]                     |
| `KIA_VAULT_APPROLE_SECRET_ID` | The Vault AppRole secret ID [*required*]                   |
| `KIA_VAULT_SECRET_PATH`       | The Vault secret path to store the create IAT [*required*] |

# Example (Development Environment)

```bash
# start Keycloak and Vault
$ docker-compose up -d

# open a browser to http://localhost:8000 and login to Keycloak with admin:admin
# Enter "admin-cli" client
#   Settingg tab
#     * Enable "Client authentication"
#     * Enable Authentication flow / Service accounts roles
#     * Save
#   Service Account Roles tab
#     * Assign Role
#     * Switch to filter by clients
#     * Select "master-realm manage-clients"
#     * Add selected by clicking "Assign"
#   Credentials tab
#     * Grab the "Client secret" value
#

# initialize Vault
$ bash vault-init.sh

# setup environment variables configuration
$ export KIA_KEYCLOAK_URL=http://keycloak:8080/
$ export KIA_KEYCLOAK_REALM=master
$ export KIA_KEYCLOAK_CLIENT_ID=admin-cli
$ export KIA_KEYCLOAK_CLIENT_SECRET=<the client secret you created above>
$ export KIA_VAULT_URL=http://vault:8200
$ export KIA_VAULT_APPROLE_ROLE_ID=<the AppRole role ID you created above>
$ export KIA_VAULT_APPROLE_SECRET_ID=<the AppRole secret ID you created above>
$ export KIA_VAULT_SECRET_PATH=app-sre/keycloak-example-iat

# run the tool
docker run --rm -it \
    --network keycloak \
    -e KIA_KEYCLOAK_URL="$KIA_KEYCLOAK_URL" \
    -e KIA_KEYCLOAK_REALM="$KIA_KEYCLOAK_REALM" \
    -e KIA_KEYCLOAK_CLIENT_ID="$KIA_KEYCLOAK_CLIENT_ID" \
    -e KIA_KEYCLOAK_CLIENT_SECRET="$KIA_KEYCLOAK_CLIENT_SECRET" \
    -e KIA_VAULT_URL="$KIA_VAULT_URL" \
    -e KIA_VAULT_APPROLE_ROLE_ID="$KIA_VAULT_APPROLE_ROLE_ID" \
    -e KIA_VAULT_APPROLE_SECRET_ID="$KIA_VAULT_APPROLE_SECRET_ID" \
    -e KIA_VAULT_SECRET_PATH="$KIA_VAULT_SECRET_PATH" \
    quay.io/cassing/keycloak-iat-vault

[2023-06-30 11:17:45] Reading IAT from Vault: app-sre/keycloak-example-iat
[2023-06-30 11:17:45] Creating new initial access token: client count (100, expiration: 30 days)
[2023-06-30 11:17:45] Writing IAT to Vault: app-sre/keycloak-example-iat

# check the secret in Vault
#   * open a browser to http://localhost:8200
#   * login with token "vault-plaintext-root-token"
#   * click "Secrets engines" in the left menu
#   * browse to "app-sre/keycloak-example-iat"

# run it again to update the IAT information in Vault
$ docker run ...
[2023-06-30 11:29:52] Reading IAT from Vault: app-sre/integrations-throughput/rhidp/test
[2023-06-30 11:29:52] Updating initial access token (dd9f351a-ca00-46b9-8
[2023-06-30 11:29:52] Writing IAT to Vault: app-sre/integrations-throughput/rhidp/test
```
