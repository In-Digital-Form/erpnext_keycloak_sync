## Erpnext Keycloak Sync

Erpnext Keycloak Sync

### Setup

In sites/common_site_config.json (or via env vars) add:

`
{
  "keycloak_url":    "https://keycloak.example.com/auth",
  "keycloak_realm":  "myrealm",
  "keycloak_client_id":     "erpnext-sync",
  "keycloak_client_secret": "YOUR_SECRET"
}
`

#### License

unlicense
