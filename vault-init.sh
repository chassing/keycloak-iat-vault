#!/bin/bash
set -e

vault="docker run --rm -i --network keycloak --cap-add IPC_LOCK -e VAULT_ADDR=http://vault:8200 -e VAULT_TOKEN=vault-plaintext-root-token hashicorp/vault"

$vault auth enable approle
$vault write auth/approle/role/test-role bind_secret_id=true
$vault read auth/approle/role/test-role/role-id
$vault write -f auth/approle/role/test-role/secret-id

$vault secrets enable -version=1 -path=app-sre kv
$vault policy write app-sre - <<_EOF
  path "app-sre/*" {
    capabilities = ["create", "update", "read", "list", "delete"]
  }
_EOF
$vault write auth/approle/role/test-role token_policies=app-sre
