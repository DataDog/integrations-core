# Triggering metrics for the Vault integration

While idle, Vault will provide very few metrics. Specifically, many of
the metrics plotted in the default dashboard will have no data unless
some activity is generated.

Assuming you are testing vault using the token auth ddev environment:

```bash
ddev env start vault py38-1.9.0-token-auth
```

Then it's possible to execute the following steps to generate activity
that will trigger metrics:

1. Create a token:

```bash
# The output may have weird characters around the actual token, that's what the tr and sed commands help with here
VAULT_TOKEN="$(docker exec -ti vault-leader vault token create -field=token | tr -dc '[:print:]' | sed 's/\[0m//g')"
```

2. Enable an auth method (e.g. [Username & Password](https://www.vaultproject.io/api-docs/auth/userpass) and the [Consul Secrets Engine](https://www.vaultproject.io/api-docs/secret/consul).

```bash
docker exec -ti vault-leader vault auth enable userpass
docker exec -ti vault-leader vault secrets enable consul
```

3. Hit endpoints to trigger metrics: 
   
- Generate metrics for login requests via the API. With this example
  the login request will fail, but it will generate the metrics which
  is what we are after.

```bash
curl \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -H "X-Vault-Request: true" \
  -X POST \
  -d '{"password": "bar"}' \
  "http://127.0.0.1:8200/v1/auth/userpass/login/foo"
```

- Generate metrics for consul methods.
    
```bash
# PUT (POST)
curl \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -H "X-Vault-Request: true" \
  -X POST \
  -d '{"policies": "global-management"}' \
  "http://127.0.0.1:8200/v1/consul/roles/foo"

# LIST
curl \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -H "X-Vault-Request: true" \
  -X LIST \
 "http://127.0.0.1:8200/v1/consul/roles"

# GET
curl \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -H "X-Vault-Request: true" \
  -X GET \
  "http://127.0.0.1:8200/v1/consul/roles/foo"

# DELETE
curl \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -H "X-Vault-Request: true" \
  -X DELETE \
  "http://127.0.0.1:8200/v1/consul/roles/foo"
```


Notes: 

- It may possible to do any of these steps in general both with the
  `vault` CLI as well as via the HTTP API.
- More can be found on https://www.vaultproject.io/api-docs and by
  exploring the `vault` CLI.
