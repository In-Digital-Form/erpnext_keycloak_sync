app_name = "erpnext_keycloak_sync"
app_title = "Erpnext Keycloak Sync"
app_publisher = "In Digital Form GmbH"
app_description = "Erpnext Keycloak Sync"
app_email = "guenther.eder@indigitalform.com"
app_license = "unlicense"
# required_apps = []

doc_events = {
  "User": {
    "after_insert":  "erpnext_keycloak_sync.api.create_keycloak_user",
    "on_update":     "erpnext_keycloak_sync.api.update_keycloak_user",
    "after_delete":  "erpnext_keycloak_sync.api.delete_keycloak_user",
  }
}
# "on_trash":     "erpnext_keycloak_sync.api.delete_keycloak_user",