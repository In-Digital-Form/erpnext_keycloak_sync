# Erpnext Keycloak Sync

Erpnext Keycloak Sync

## Setup ErpNext

In sites/common_site_config.json (or via env vars) add:

        {
            "keycloak_url":           "https://keycloak.example.com",
            "keycloak_realm":         "myrealm",
            "keycloak_client_id":     "erpnext-sync",
            "keycloak_client_secret": "YOUR_SECRET"
        }

## Setup Keycloak

### A. Enable the service-account for your client

1. In the Keycloak Admin Console, select your realm (e.g. myrealm)
2. Go to Clients → click on your client (e.g. erpnext-sync)
3. Under the Settings tab, scroll down and toggle Service Accounts Enabled to ON
4. Click Save

### B. Grant the service-account the realm-management roles

Depending on your Keycloak version the UI looks slightly different, but you’re always assigning roles to the service-account user, not defining new client roles.

If you see a Service Account Roles tab

1. Still inside your client, click the Service Account Roles tab
2. In the Client Roles dropdown choose realm-management
3. From Available Roles check:
    - view-users
    - manage-users
    (optionally also view-groups/manage-groups)
4. Click Add selected

If you instead have a Service Account sidebar entry

1. In the left‐hand menu under Manage, click Service Account
2. Switch to the Role Mappings sub-tab
3. In the Client Roles panel, select realm-management from the dropdown
4. Move view-users and manage-users into the Assigned Roles box

## License

unlicense
