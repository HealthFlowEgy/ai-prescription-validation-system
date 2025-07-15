# Terraform configuration for Digital Ocean infrastructure
# This creates the necessary infrastructure for the Prescription Validation System

terraform {
  required_version = ">= 1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# Configure the DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}

# Variables
variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "prescription-validator"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  type        = string
  default     = "production"
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc3"
}

variable "droplet_size" {
  description = "Size of the droplet"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "ssh_key_name" {
  description = "Name of the SSH key in DigitalOcean"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# Data sources
data "digitalocean_ssh_key" "main" {
  name = var.ssh_key_name
}

data "digitalocean_image" "ubuntu" {
  slug = "ubuntu-22-04-x64"
}

# Create a VPC
resource "digitalocean_vpc" "main" {
  name     = "${var.project_name}-${var.environment}-vpc"
  region   = var.region
  ip_range = "10.10.0.0/16"
}

# Create a firewall
resource "digitalocean_firewall" "web" {
  name = "${var.project_name}-${var.environment}-firewall"

  droplet_ids = [digitalocean_droplet.web.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# Create the main droplet
resource "digitalocean_droplet" "web" {
  image    = data.digitalocean_image.ubuntu.id
  name     = "${var.project_name}-${var.environment}"
  region   = var.region
  size     = var.droplet_size
  vpc_uuid = digitalocean_vpc.main.id
  ssh_keys = [data.digitalocean_ssh_key.main.id]

  user_data = templatefile("${path.module}/cloud-init.yml", {
    project_name = var.project_name
    environment  = var.environment
  })

  tags = [
    var.project_name,
    var.environment,
    "web-server"
  ]
}

# Create staging droplet (optional)
resource "digitalocean_droplet" "staging" {
  count = var.environment == "production" ? 1 : 0

  image    = data.digitalocean_image.ubuntu.id
  name     = "${var.project_name}-staging"
  region   = var.region
  size     = "s-1vcpu-2gb"
  vpc_uuid = digitalocean_vpc.main.id
  ssh_keys = [data.digitalocean_ssh_key.main.id]

  user_data = templatefile("${path.module}/cloud-init.yml", {
    project_name = var.project_name
    environment  = "staging"
  })

  tags = [
    var.project_name,
    "staging",
    "web-server"
  ]
}

# Create a container registry
resource "digitalocean_container_registry" "main" {
  name                   = "${var.project_name}-registry"
  subscription_tier_slug = "basic"
  region                 = var.region
}

# Create a database cluster (optional)
resource "digitalocean_database_cluster" "postgres" {
  count = var.environment == "production" ? 1 : 0

  name       = "${var.project_name}-${var.environment}-db"
  engine     = "pg"
  version    = "15"
  size       = "db-s-1vcpu-1gb"
  region     = var.region
  node_count = 1

  tags = [
    var.project_name,
    var.environment,
    "database"
  ]
}

# Create a database
resource "digitalocean_database_db" "app_db" {
  count      = var.environment == "production" ? 1 : 0
  cluster_id = digitalocean_database_cluster.postgres[0].id
  name       = "prescription_validator"
}

# Create a database user
resource "digitalocean_database_user" "app_user" {
  count      = var.environment == "production" ? 1 : 0
  cluster_id = digitalocean_database_cluster.postgres[0].id
  name       = "app_user"
}

# Create a load balancer (for production)
resource "digitalocean_loadbalancer" "web" {
  count = var.environment == "production" ? 1 : 0

  name   = "${var.project_name}-${var.environment}-lb"
  region = var.region

  forwarding_rule {
    entry_protocol  = "http"
    entry_port      = 80
    target_protocol = "http"
    target_port     = 80
  }

  forwarding_rule {
    entry_protocol  = "https"
    entry_port      = 443
    target_protocol = "http"
    target_port     = 80
    tls_passthrough = false
  }

  healthcheck {
    protocol = "http"
    port     = 80
    path     = "/api/health"
  }

  droplet_ids = [digitalocean_droplet.web.id]
}

# Create a domain (if provided)
resource "digitalocean_domain" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

# Create DNS records
resource "digitalocean_record" "main" {
  count  = var.domain_name != "" ? 1 : 0
  domain = digitalocean_domain.main[0].name
  type   = "A"
  name   = "@"
  value  = var.environment == "production" && length(digitalocean_loadbalancer.web) > 0 ? digitalocean_loadbalancer.web[0].ip : digitalocean_droplet.web.ipv4_address
}

resource "digitalocean_record" "www" {
  count  = var.domain_name != "" ? 1 : 0
  domain = digitalocean_domain.main[0].name
  type   = "CNAME"
  name   = "www"
  value  = "@"
}

resource "digitalocean_record" "staging" {
  count  = var.domain_name != "" && length(digitalocean_droplet.staging) > 0 ? 1 : 0
  domain = digitalocean_domain.main[0].name
  type   = "A"
  name   = "staging"
  value  = digitalocean_droplet.staging[0].ipv4_address
}

# Create a project
resource "digitalocean_project" "main" {
  name        = "${var.project_name}-${var.environment}"
  description = "Prescription Validation System - ${var.environment}"
  purpose     = "Web Application"
  environment = var.environment

  resources = concat(
    [digitalocean_droplet.web.urn],
    [digitalocean_container_registry.main.urn],
    length(digitalocean_droplet.staging) > 0 ? [digitalocean_droplet.staging[0].urn] : [],
    length(digitalocean_database_cluster.postgres) > 0 ? [digitalocean_database_cluster.postgres[0].urn] : [],
    length(digitalocean_loadbalancer.web) > 0 ? [digitalocean_loadbalancer.web[0].urn] : [],
    var.domain_name != "" ? [digitalocean_domain.main[0].urn] : []
  )
}

# Outputs
output "web_droplet_ip" {
  description = "IP address of the web droplet"
  value       = digitalocean_droplet.web.ipv4_address
}

output "staging_droplet_ip" {
  description = "IP address of the staging droplet"
  value       = length(digitalocean_droplet.staging) > 0 ? digitalocean_droplet.staging[0].ipv4_address : null
}

output "container_registry_endpoint" {
  description = "Container registry endpoint"
  value       = digitalocean_container_registry.main.endpoint
}

output "container_registry_name" {
  description = "Container registry name"
  value       = digitalocean_container_registry.main.name
}

output "database_connection_string" {
  description = "Database connection string"
  value       = length(digitalocean_database_cluster.postgres) > 0 ? digitalocean_database_cluster.postgres[0].private_uri : null
  sensitive   = true
}

output "load_balancer_ip" {
  description = "Load balancer IP address"
  value       = length(digitalocean_loadbalancer.web) > 0 ? digitalocean_loadbalancer.web[0].ip : null
}

output "domain_name" {
  description = "Domain name"
  value       = var.domain_name != "" ? var.domain_name : null
}

output "application_url" {
  description = "Application URL"
  value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${digitalocean_droplet.web.ipv4_address}"
}

output "staging_url" {
  description = "Staging URL"
  value = length(digitalocean_droplet.staging) > 0 ? (
    var.domain_name != "" ? "https://staging.${var.domain_name}" : "http://${digitalocean_droplet.staging[0].ipv4_address}:8080"
  ) : null
}

