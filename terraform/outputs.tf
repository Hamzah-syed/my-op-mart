output "inventory_service_container_app_url" {
  value = azurerm_container_app.inventory_service.latest_revision_fqdn
}

# output "user_service_container_app_url" {
#   value = azurerm_container_app.user_service.latest_revision_fqdn
# }

# output "kafka_container_app_url" {
#   value = azurerm_container_app.kafka.latest_revision_fqdn
# }
output "eventhub_primary_connection_string" {
  value     = azurerm_eventhub_authorization_rule.kafka_authorization_rule.primary_connection_string
  sensitive = true
}

output "eventhub_primary_key" {
  value     = azurerm_eventhub_authorization_rule.kafka_authorization_rule.primary_key
  sensitive = true
}

output "eventhub_secondary_connection_string" {
  value     = azurerm_eventhub_authorization_rule.kafka_authorization_rule.secondary_connection_string
  sensitive = true
}

output "eventhub_secondary_key" {
  value     = azurerm_eventhub_authorization_rule.kafka_authorization_rule.secondary_key
  sensitive = true
}


output "kafka_ui_container_app_url" {
  value = azurerm_container_app.kafka_ui.latest_revision_fqdn
}

output "notification_service_container_app_url" {
  value = azurerm_container_app.notification_service.latest_revision_fqdn
}

# output "postgresql_fqdn" {
#   value = azurerm_postgresql_flexible_server.postgresql.fqdn
# }
output "user_db_connection_string" {
  value = "postgresql://postgres:password@${azurerm_container_app.user_db.latest_revision_fqdn}:5432/users"
}
