import frappe
import requests
from typing import Dict

# Load Keycloak configuration from site_config or environment variables
KEYCLOAK_URL = frappe.get_conf().get("keycloak_url")
REALM = frappe.get_conf().get("keycloak_realm")
CLIENT_ID = frappe.get_conf().get("keycloak_client_id")
CLIENT_SECRET = frappe.get_conf().get("keycloak_client_secret")


def _get_token() -> str:
    """Obtain a service-account access token from Keycloak."""
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json().get("access_token")


def _headers() -> Dict[str, str]:
    """Build authorization headers for Keycloak Admin API calls."""
    token = _get_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_keycloak_user(doc, method) -> None:
    """Create a new user in Keycloak when an ERPNext User is inserted."""
    try:
        payload = {
            "username": doc.name,
            "email": doc.email,
            "firstName": doc.get("first_name") or doc.get("full_name") or "",
            "lastName": doc.get("last_name") or "",
            "enabled": True,
        }
        url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
        response = requests.post(url, json=payload, headers=_headers())
        response.raise_for_status()
    except Exception as e:
        frappe.log_error(message=str(e), title="Keycloak Sync: create user failed")


def update_keycloak_user(doc, method) -> None:
    """Update an existing Keycloak user when an ERPNext User is updated."""
    try:
        # Search for the user by username
        search_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
        resp_search = requests.get(search_url, headers=_headers(), params={"username": doc.name})
        resp_search.raise_for_status()
        users = resp_search.json()

        if not users:
            # If the user does not exist in Keycloak, create it
            create_keycloak_user(doc, method)
            return

        user_id = users[0]["id"]
        payload = {
            "email": doc.email,
            "firstName": doc.get("first_name") or doc.get("full_name") or "",
            "lastName": doc.get("last_name") or "",
            "enabled": doc.get("enabled", True),
        }
        url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}"
        resp_update = requests.put(url, json=payload, headers=_headers())
        resp_update.raise_for_status()
    except Exception as e:
        frappe.log_error(message=str(e), title="Keycloak Sync: update user failed")


def delete_keycloak_user(doc, method) -> None:
    """Delete the corresponding Keycloak user when an ERPNext User is deleted."""
    try:
        # Find Keycloak user by username
        search_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users"
        resp_search = requests.get(search_url, headers=_headers(), params={"username": doc.name})
        resp_search.raise_for_status()
        users = resp_search.json()

        if not users:
            return

        user_id = users[0]["id"]
        url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}"
        resp_delete = requests.delete(url, headers=_headers())
        resp_delete.raise_for_status()
    except Exception as e:
        frappe.log_error(message=str(e), title="Keycloak Sync: delete user failed")

