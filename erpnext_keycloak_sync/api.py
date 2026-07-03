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
    if frappe.request.method != "POST":
        frappe.throw("Only POST is allowed", frappe.PermissionError)

    data = frappe.local.form_dict

    event_type = data.get("type") or data.get("action") or ""
    username = data.get("username") or data.get("email")
    email = data.get("email") or username

    keycloak_username = username
    keycloak_email = email
    first_name = data.get("firstName") or data.get("first_name")
    last_name = data.get("lastName") or data.get("last_name")

    if not event_type:
        event_type = _unpack_webhook_bridge_event(data)

    if not event_type:
        return {"status": "skipped", "reason": "no event type"}

    event_type = event_type.upper()

    if event_type in ("REGISTER", "CREATE", "CREATED"):
        if not keycloak_email:
            return {"status": "skipped", "reason": "no email"}
        if not frappe.db.exists("User", keycloak_email):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": keycloak_email,
                    "username": (keycloak_username or keycloak_email).split("@")[0],
                    "first_name": first_name or (keycloak_username or keycloak_email),
                    "last_name": last_name or "",
                    "send_welcome_email": 0,
                }
            )
            user.insert(ignore_permissions=True)
            frappe.db.commit()

    elif event_type in ("UPDATE", "UPDATED"):
        if not keycloak_email:
            return {"status": "skipped", "reason": "no email"}
        if frappe.db.exists("User", keycloak_email):
            user = frappe.get_doc("User", keycloak_email)
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.save(ignore_permissions=True)
            frappe.db.commit()

    elif event_type in ("DELETE", "DELETED"):
        if not keycloak_email:
            return {"status": "skipped", "reason": "no email"}
        if frappe.db.exists("User", keycloak_email):
            frappe.delete_doc("User", keycloak_email, ignore_permissions=True)

    return {"status": "ok"}


def _unpack_webhook_bridge_event(data) -> str:
    event_type = ""
    event_kind = data.get("eventType", "")
    event = data.get("event", {})

    if event_kind == "USER_EVENT":
        event_type = event.get("type", "")
        details = event.get("details", {}) or {}
        frappe.local.form_dict["username"] = details.get("username") or frappe.local.form_dict.get("username")
        frappe.local.form_dict["email"] = details.get("email") or frappe.local.form_dict.get("email")

    elif event_kind == "ADMIN_EVENT":
        op = event.get("operationType", "")
        rp = event.get("resourcePath", "") or ""
        if not rp.startswith("users/"):
            return ""
        event_type = op
        rep = event.get("representation")
        if rep:
            frappe.local.form_dict["username"] = rep.get("username") or frappe.local.form_dict.get("username")
            frappe.local.form_dict["email"] = rep.get("email") or frappe.local.form_dict.get("email")
            frappe.local.form_dict["firstName"] = rep.get("firstName") or frappe.local.form_dict.get("firstName")
            frappe.local.form_dict["lastName"] = rep.get("lastName") or frappe.local.form_dict.get("lastName")

    return event_type