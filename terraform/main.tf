provider "azurerm" {
  features {}
}


resource "azurerm_resource_group" "martapp_rg" {
  name     = "martapp-resource-group"
  location = var.location
}

resource "azurerm_log_analytics_workspace" "example" {
  name                = "example-workspace"
  location            = azurerm_resource_group.martapp_rg.location
  resource_group_name = azurerm_resource_group.martapp_rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "example" {
  name                       = "example-environment"
  location                   = azurerm_resource_group.martapp_rg.location
  resource_group_name        = azurerm_resource_group.martapp_rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.example.id
}

resource "azurerm_eventhub_namespace" "kafka_namespace" {
  name                = "kafkanamespace"
  location            = azurerm_resource_group.martapp_rg.location
  resource_group_name = azurerm_resource_group.martapp_rg.name
  sku                 = "Standard"
}

resource "azurerm_eventhub" "kafka_eventhub" {
  name                = "kafka-eventhub"
  resource_group_name = azurerm_resource_group.martapp_rg.name
  namespace_name      = azurerm_eventhub_namespace.kafka_namespace.name
  partition_count     = 1
  message_retention   = 1
}

resource "azurerm_eventhub_authorization_rule" "kafka_authorization_rule" {
  name                = "kafka-authorization-rule"
  eventhub_name       = azurerm_eventhub.kafka_eventhub.name
  namespace_name      = azurerm_eventhub_namespace.kafka_namespace.name
  resource_group_name = azurerm_resource_group.martapp_rg.name
  listen              = true
  send                = true
  manage              = true
  
}


resource "azurerm_container_app" "kafka_ui" {
  name                         = "kafka-ui-app"
  container_app_environment_id = azurerm_container_app_environment.example.id
  resource_group_name          = azurerm_resource_group.martapp_rg.name
  revision_mode                = "Single"

  template {
    container {
      name   = "kafka-ui"
      image  = "provectuslabs/kafka-ui:latest"
      cpu    = "0.25"
      memory = "0.5Gi"

      env {
        name  = "KAFKA_CLUSTERS_0_NAME"
        value = "azure-eventhub"
      }
      
      env {
        name  = "KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS"
        value = "${azurerm_eventhub_namespace.kafka_namespace.name}.servicebus.windows.net:9093"
      }
      env {
        name  = "KAFKA_CLUSTERS_0_PROPERTIES_SECURITY_PROTOCOL"
        value = "SASL_SSL"
      }
      env {
        name  = "KAFKA_CLUSTERS_0_PROPERTIES_SASL_MECHANISM"
        value = "PLAIN"
      }
      env {
        name  = "KAFKA_CLUSTERS_0_PROPERTIES_SASL_JAAS_CONFIG"
        value = "org.apache.kafka.common.security.plain.PlainLoginModule required username='$$ConnectionString' password='Endpoint=sb://kafkanamespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Oojzo0RhtbwI+USwuVZnwrlTqnRZ07KTr+AEhAb3Lok=';"
      }
      env {
        name  = "KAFKA_CLUSTERS_0_PROPERTIES_SASL_USERNAME"
        value = "$$ConnectionString"
      }
      env {
        name  = "KAFKA_CLUSTERS_0_PROPERTIES_SASL_PASSWORD"
        value = "Endpoint=sb://kafkanamespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Oojzo0RhtbwI+USwuVZnwrlTqnRZ07KTr+AEhAb3Lok="
      }
      env {
        name  = "TEST_PASSWORD"
        value =  azurerm_eventhub_authorization_rule.kafka_authorization_rule.primary_key
      }
      env {
        name  = "TEST_PASSWORD2"
        value =  azurerm_eventhub_authorization_rule.kafka_authorization_rule.secondary_connection_string
      }
      env {
        name  = "TEST_PASSWORD3"
        value =  azurerm_eventhub_authorization_rule.kafka_authorization_rule.secondary_key
      }
    }
    max_replicas = 1
    min_replicas = 0
    
  }

  ingress {
    external_enabled = true
    target_port      = 8080

    traffic_weight {
      percentage      = 100
      latest_revision = true
      # revision_suffix = "default"
    }
  }

  tags = {
    environment = "production"
  }
}


resource "azurerm_container_app" "inventory_db" {
  name                         = "inventory-db-app"
  container_app_environment_id = azurerm_container_app_environment.example.id
  resource_group_name          = azurerm_resource_group.martapp_rg.name
  revision_mode                = "Single"

  template {
    container {
      name   = "inventory-db"
      image  = "postgres:13"
      cpu    = "0.5"
      memory = "1.0Gi"

      env {
        name  = "POSTGRES_USER"
        value = "postgres"
      }
      env {
        name  = "POSTGRES_PASSWORD"
        value = "password"
      }
      env {
        name  = "POSTGRES_DB"
        value = "inventory"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 5432
    allow_insecure_connections = true

    traffic_weight {
      percentage      = 100
      latest_revision = true
      # revision_suffix = "default"
    }
  }

  tags = {
    environment = "production"
  }
}

# Storage Account Resource
resource "azurerm_storage_account" "user_db_storage" {
  name                     = "userdbstorageacct"
  resource_group_name      = azurerm_resource_group.martapp_rg.name
  location                 = azurerm_resource_group.martapp_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    environment = "development"
  }
}

# Storage Share Resource
resource "azurerm_storage_share" "userdbshare" {
  name                 = "postgresdatashare"
  storage_account_name = azurerm_storage_account.user_db_storage.name
  quota                = 5  # Keep the quota small to stay within free tier limits
}

resource "azurerm_container_app_environment_storage" "user_db_env_storage" {
  name                         = "mycontainerappstorage"
  container_app_environment_id = azurerm_container_app_environment.example.id
  account_name                 = azurerm_storage_account.user_db_storage.name
  share_name                   = azurerm_storage_share.userdbshare.name
  access_key                   = azurerm_storage_account.user_db_storage.primary_access_key
  access_mode                  = "ReadWrite"
}

resource "azurerm_container_app" "user_db" {
  name                         = "user-db-app"
  container_app_environment_id = azurerm_container_app_environment.example.id
  resource_group_name          = azurerm_resource_group.martapp_rg.name
  revision_mode                = "Single"
  template {
    container {
      name   = "user-db"
      image  = "postgres:13"
      cpu    = "0.25"
      memory = "0.5Gi"
      env {
        name  = "POSTGRES_USER"
        value = "postgres"
      }
      env {
        name  = "POSTGRES_PASSWORD"
        value = "password"
      }
      env {
        name  = "POSTGRES_DB"
        value = "users"
      }
      # volume_mounts {
      #   name = "postgres-data"
      #   path = "/var/lib/postgresql/data"
      # }
    }

    # volume {
    #   name = "postgres-data"
    #   storage_name = azurerm_container_app_environment_storage.user_db_env_storage.name
    #   storage_type = "AzureFile"
    # }
  }

  ingress {
    external_enabled = false
    target_port      = 5432
    allow_insecure_connections = false
    transport = "tcp"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = {
    environment = "production"
  }
}




resource "azurerm_container_app" "inventory_service" {
  name                         = "inventory-service-app"
  container_app_environment_id = azurerm_container_app_environment.example.id
  resource_group_name          = azurerm_resource_group.martapp_rg.name
  revision_mode                = "Single"
   template {
    container {
      name   = "inventory-service"
      image  = "hamzahrpc/inventory-service:latest"
      cpu    = "0.25"
      memory = "0.5Gi"

      # env {
      #   name  = "KAFKA_BOOTSTRAP_SERVERS"
      #   value = "${azurerm_eventhub_namespace.kafka_namespace.name}.servicebus.windows.net:9093"
      # }
      
      env {
        name  = "KAFKA_PROPERTIES_SECURITY_PROTOCOL"
        value = "SASL_SSL"
      }
      env {
        name  = "KAFKA_PROPERTIES_SASL_MECHANISM"
        value = "PLAIN"
      }
      # env {
      #   name  = "KAFKA_PROPERTIES_SASL_JAAS_CONFIG"
      #   value = "org.apache.kafka.common.security.plain.PlainLoginModule required username='$ConnectionString' password='${azurerm_eventhub_authorization_rule.kafka_authorization_rule.primary_connection_string}';"
      # }
      env {
        name  = "POSTGRES_USER"
        value = "pgadmin@martapp-postgresql-server"
      }
      env {
        name  = "POSTGRES_PASSWORD"
        value = "myPass1234567"
      }
      env {
        name  = "POSTGRES_DB"
        value = "inventory"
      }
    }
    max_replicas = 1
  }


  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
      # revision_suffix = "default"
    }
  }
  dapr {
    app_id  = "inventory-service"
  }

  tags = {
    environment = "production"
  }
}

resource "azurerm_container_app" "user_service" {
  name                         = "user-service-app"
  container_app_environment_id = azurerm_container_app_environment.example.id
  resource_group_name          = azurerm_resource_group.martapp_rg.name
  revision_mode                = "Single"

  template {
    container {
      name   = "user-service"
      image  = "hamzahrpc/user-service:latest"
      cpu    = "0.25"
      memory = "0.5Gi"
      env {
        name  = "KAFKA_BOOTSTRAP_SERVERS"
        value = "${azurerm_eventhub_authorization_rule.kafka_authorization_rule.namespace_name}.servicebus.windows.net:9093"
      }
      env {
        name  = "KAFKA_SASL_USERNAME"
        value = "$$ConnectionString"
      }
      env {
        name  = "KAFKA_SASL_PASSWORD"
        value = "Endpoint=sb://kafkanamespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Oojzo0RhtbwI+USwuVZnwrlTqnRZ07KTr+AEhAb3Lok="
      }
      env {
        name  = "POSTGRES_USER"
        value = azurerm_postgresql_flexible_server.postgresql.administrator_login
      }
      env {
        name  = "POSTGRES_HOST"
        value = azurerm_postgresql_flexible_server.postgresql.fqdn
      }
      env {
        name  = "POSTGRES_PASSWORD"
        value = azurerm_postgresql_flexible_server.postgresql.administrator_password
      }
      env {
        name  = "POSTGRES_DB"
        value = "users"
      }
    }
    
    max_replicas = 1
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    

    traffic_weight {
      percentage      = 100
      latest_revision = true
      # revision_suffix = "default"
    }
  }

  dapr {
    app_id  = "user-service-dap"
  }
  tags = {
    environment = "production"
  }
}

resource "azurerm_container_app" "notification_service" {
  name                         = "notification-service-app"
  container_app_environment_id = azurerm_container_app_environment.example.id
  resource_group_name          = azurerm_resource_group.martapp_rg.name
  revision_mode                = "Single"

    template {
    container {
      name   = "notification-service"
      image  = "hamzahrpc/notification-service:latest"
      cpu    = "0.25"
      memory = "0.5Gi"

      env {
        name  = "KAFKA_BOOTSTRAP_SERVERS"
        value = "${azurerm_eventhub_authorization_rule.kafka_authorization_rule.namespace_name}.servicebus.windows.net:9093"
      }
      env {
        name  = "KAFKA_SASL_USERNAME"
        value = "$$ConnectionString"
      }
      env {
        name  = "KAFKA_SASL_PASSWORD"
        value = "Endpoint=sb://kafkanamespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Oojzo0RhtbwI+USwuVZnwrlTqnRZ07KTr+AEhAb3Lok="
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
      # revision_suffix = "default"
    }
  }
  dapr {
    app_id  = "notification-service-dap"
  }
  tags = {
    environment = "production"
  }
}

resource "azurerm_postgresql_flexible_server" "postgresql" {
  name                           = "martapp-postgresql-server"
  location                       = azurerm_resource_group.martapp_rg.location
  resource_group_name            = azurerm_resource_group.martapp_rg.name
  administrator_login            = "pgadmin"
  administrator_password         = "myPass1234567"
  version                        = "11"
  storage_mb                     = 32768
  sku_name                       = "B_Standard_B1ms"
  geo_redundant_backup_enabled   = false
  auto_grow_enabled              = false
  zone = "3"
  tags = {
    environment = "production"
  }
}

resource "azurerm_postgresql_flexible_server_database" "inventory" {
  name                = "inventory"
  server_id           = azurerm_postgresql_flexible_server.postgresql.id
  charset             = "UTF8"
  # collation           = "English_United States.1252"
}

resource "azurerm_postgresql_flexible_server_database" "users" {
  name                = "users"
  server_id           = azurerm_postgresql_flexible_server.postgresql.id
  charset             = "UTF8"
  # collation           = "English_United States.1252"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_all_ips" {
  name                = "allow_all_ips"
  server_id           = azurerm_postgresql_flexible_server.postgresql.id
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "255.255.255.255"
}


resource "azurerm_container_app_environment_dapr_component" "eventhub_component" {
  name                         = "eventhub-component"
  container_app_environment_id = azurerm_container_app_environment.example.id
  component_type               = "pubsub.azure.eventhubs"
  version                      = "v1"
  metadata {
    name = "ConnectionString"
    value = azurerm_eventhub_authorization_rule.kafka_authorization_rule.primary_connection_string
  }
  metadata {
    name = "eventHubName"
    value = azurerm_eventhub.kafka_eventhub.name
  }
  metadata {
    name = "consumerGroup"
    value = "$Default"
  }
  scopes = ["inventory-service",  "notification-service", "user-service-dap"]
}