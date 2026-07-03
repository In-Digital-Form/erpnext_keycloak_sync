# Erpnext Keycloak Sync

Erpnext Keycloak Sync

## Setup ErpNext

In sites/common_site_config.json (or via env vars) add:

{
    "keycloak_url":           "https://keycloak.example.com",
    "keycloak_realm":         "myrealm",
    "keycloak_client_id":     "erpnext-sync",
    "keycloak_client_secret": "YOUR_SECRET",
    "keycloak_webhook_secret": "YOUR_SHARED_SECRET"   ← optional, for KC→ERPNext webhook auth
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

### C. (Optional) Configure Keycloak Event Listener for KC→ERPNext sync

This enables **bidirectional** sync: when a user is created/updated/deleted in Keycloak, ERPNext is notified automatically via a webhook.

#### 1. Install a Keycloak Event Listener SPI

Keycloak does not include a built-in webhook sender. Choose one of these open-source SPI extensions:

**Option 1 — `keycloak-user-event-listener`** (recommended for this use case)
- GitHub: https://github.com/huynxtb/keycloak-user-event-listener
- Specifically captures user lifecycle events (CREATE, UPDATE, DELETE)
- Sends username, email, firstName, lastName — exactly what this endpoint needs

**Option 2 — `keycloak-webhook-bridge`** (more general, captures all events)
- GitHub: https://github.com/mabhisheksingh/keycloak-webhook-bridge
- Covers all user + admin events, more production-hardened

Either way: build the JAR with `mvn clean package`, copy it to `/opt/keycloak/providers/`, and restart Keycloak.

#### 2. Configure the event listener

In the Keycloak Admin Console:

1. Go to **Realm Settings → Events → Event Listeners**
2. Click **Add** and select your listener (e.g. `keycloak-user-event-listener`)
3. Set the `WEBHOOK_URL` environment variable (or similar config) to:
   ```
   https://your-erpnext-site.com/api/method/erpnext_keycloak_sync.api.keycloak_webhook
   ```
4. Set the `Authorization: Bearer <YOUR_WEBHOOK_SECRET>` header — use the same value as `keycloak_webhook_secret` in your site config

#### 3. Webhook payload format

The endpoint accepts POST with JSON body (either format works):

```json
// Format from keycloak-user-event-listener
{
    "action": "CREATED",
    "username": "user@example.com",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe"
}

// Or format from keycloak-webhook-bridge
{
    "type": "CREATE",
    "username": "user@example.com",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe"
}
```

Supported event types / actions: `CREATE` / `CREATED`, `UPDATE` / `UPDATED`, `DELETE` / `DELETED`.

## Sync Direction Summary

| Direction | Mechanism | Status |
|-----------|-----------|--------|
| ERPNext → Keycloak | DocType events (`after_insert`, `on_update`, `after_delete`) on User | ✅ Built-in |
| Keycloak → ERPNext | Webhook endpoint + Keycloak Event Listener SPI | 🔧 Optional (step C) |
| Lazy (on JWT login) | `jwt_auth` auto-registers user on first login | ✅ Built-in |

## License

unlicense
