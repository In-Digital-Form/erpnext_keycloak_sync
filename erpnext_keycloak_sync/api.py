import frappe
import requests
from typing import Dict


def _get_config(key: str):
    return frappe.get_conf().get(key)


def _get_token() -> str:
    token_url = f"{_get_config('keycloak_url')}/realms/{_get_config('keycloak_realm')}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": _get_config("keycloak_client_id"),
        "client_secret": _get_config("keycloak_client_secret"),
    }
    response = requests.post(token_url, data=data, timeout=10)
    response.raise_for_status()
    return response.json().get("access_token")


def _headers() -> Dict[str, str]:
    token = _get_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _search_keycloak_user(username: str) -> list:
    search_url = f"{_get_config('keycloak_url')}/admin/realms/{_get_config('keycloak_realm')}/users"
    resp = requests.get(search_url, headers=_headers(), params={"username": username}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def create_keycloak_user(doc, method) -> None:
    if frappe.flags.get("jwt_auth_creating_user"):
        return

    try:
        existing = _search_keycloak_user(doc.name)
        if existing:
            update_keycloak_user(doc, method)
            return

        payload = {
            "username": doc.name,
            "email": doc.email,
            "firstName": doc.get("first_name") or doc.get("full_name") or "",
            "lastName": doc.get("last_name") or "",
            "enabled": True,
        }
        url = f"{_get_config('keycloak_url')}/admin/realms/{_get_config('keycloak_realm')}/users"
        response = requests.post(url, json=payload, headers=_headers(), timeout=10)
        response.raise_for_status()
    except Exception as e:
        frappe.log_error(message=str(e), title="Keycloak Sync: create user failed")


def update_keycloak_user(doc, method) -> None:
    if frappe.flags.get("jwt_auth_creating_user"):
        return

    try:
        users = _search_keycloak_user(doc.name)

        if not users:
            create_keycloak_user(doc, method)
            return

        user_id = users[0]["id"]
        payload = {
            "email": doc.email,
            "firstName": doc.get("first_name") or doc.get("full_name") or "",
            "lastName": doc.get("last_name") or "",
            "enabled": doc.get("enabled", True),
        }
        url = f"{_get_config('keycloak_url')}/admin/realms/{_get_config('keycloak_realm')}/users/{user_id}"
        resp_update = requests.put(url, json=payload, headers=_headers(), timeout=10)
        resp_update.raise_for_status()
    except Exception as e:
        frappe.log_error(message=str(e), title="Keycloak Sync: update user failed")


def delete_keycloak_user(doc, method) -> None:
    try:
        users = _search_keycloak_user(doc.name)

        if not users:
            return

        user_id = users[0]["id"]
        url = f"{_get_config('keycloak_url')}/admin/realms/{_get_config('keycloak_realm')}/users/{user_id}"
        resp_delete = requests.delete(url, headers=_headers(), timeout=10)
        resp_delete.raise_for_status()
    except Exception as e:
        frappe.log_error(message=str(e), title="Keycloak Sync: delete user failed")


@frappe.whitelist(allow_guest=True)
def keycloak_webhook():
    """
    Webhook endpoint for Keycloak Event Listener SPI.

    Keycloak sends POST requests with a JSON payload when user events occur.
    Expected payload format (Keycloak Event Listener SPI standard):
    {
        "type": "CREATE" | "UPDATE" | "DELETE",
        "username": "user@example.com",
        "email": "user@example.com",
        "firstName": "John",
        "lastName": "Doe"
    }

    Configure in Keycloak Admin Console:
    - Realm Settings → Events → Event Listeners → Add "ext-event-webhook"
    - Or use the built-in Event Listener SPI with a custom listener
    """
    if frappe.request.method != "POST":
        frappe.throw("Only POST is allowed", frappe.PermissionError)

    auth_header = frappe.get_request_header("Authorization", "")
    if not auth_header.startswith("Bearer "):
        frappe.throw("Missing or invalid Authorization header", frappe.PermissionError)

    token = auth_header[len("Bearer "):].strip()
    expected_token = _get_config("keycloak_webhook_secret") or _get_config("keycloak_client_secret")

    if token != expected_token:
        frappe.throw("Invalid token", frappe.PermissionError)

    data = frappe.local.form_dict
    event_type = (data.get("type") or data.get("action") or "").upper()
    username = data.get("username") or data.get("email")
    email = data.get("email") or username

    if not username:
        return {"status": "skipped", "reason": "no username"}

    if event_type in ("CREATE", "CREATED"):
        if not frappe.db.exists("User", email):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "username": username.split("@")[0],
                    "first_name": data.get("firstName", username),
                    "last_name": data.get("lastName", ""),
                    "send_welcome_email": 0,
                }
            )
            user.insert(ignore_permissions=True)
            frappe.db.commit()

    elif event_type in ("UPDATE", "UPDATED"):
        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
            if data.get("firstName"):
                user.first_name = data["firstName"]
            if data.get("lastName"):
                user.last_name = data["lastName"]
            if data.get("email"):
                user.email = data["email"]
            user.save(ignore_permissions=True)
            frappe.db.commit()

    elif event_type in ("DELETE", "DELETED"):
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, ignore_permissions=True)

    return {"status": "ok"}