variable aws_account_id {
  type        = string
  description = "AWS account ID to apply changes to"
  default     = ""
}

variable aws_role {
  type        = string
  description = "Name of the AWS role to assume to apply changes"
  default     = ""
}

variable image_tag {
   type        = string
  description = "Please provide an image tag"
}

variable priority {
  type        = number
  description = "Listener rule priority number within the given listener"
}

variable happymeta_ {
  type        = string
  description = "Happy Path metadata. Ignored by actual terraform."
}

variable stack_name {
  type        = string
  description = "Happy Path stack name"
}

variable happy_config_secret {
  type        = string
  description = "Happy Path configuration secret name"
}

variable "task_storage_size_gb" {
  type        = number
  description = "ephemeral disk storage in GB available for the task"
  default     = 30 
}

variable deployment_stage {
  type        = string
  description = "Deployment stage for the app"
}

variable delete_protected {
  type        = bool
  description = "Whether to protect this stack from being deleted."
  default     = false
}

variable require_okta {
  type        = bool
  description = "Whether the ALB's should be on private subnets"
  default     = true
}

variable backend_url {
  type        = string
  description = "For non-proxied stacks, send in the canonical front/backend URL's"
  default     = ""
}

variable backend_de_url {
  type        = string
  description = "For non-proxied stacks, send in the canonical front/backend URL's"
  default     = ""
}

variable backend_wmg_url {
  type        = string
  description = "For non-proxied stacks, send in the canonical front/backend URL's"
  default     = ""
}

variable frontend_url {
  type        = string
  description = "For non-proxied stacks, send in the canonical front/backend URL's"
  default     = ""
}

variable stack_prefix {
  type        = string
  description = "Do bucket storage paths and db schemas need to be prefixed with the stack name? (Usually '/{stack_name}' for dev stacks, and '' for staging/prod stacks)"
  default     = ""
}

variable wait_for_steady_state {
  type        = bool
  description = "Should terraform block until ECS services reach a steady state?"
  default     = false
}

variable batch_container_memory_limit {
  type        = number
  description = "Memory hard limit for the batch container"
  default     = 28000
}

variable wmg_batch_container_memory_limit {
  type        = number
  description = "Memory hard limit for the wmg processing batch container"
  default     = 248000
}

variable wmg_desired_vcpus {
  type        = number
  description = "Number of desired vCPUs"
  default     = 128
}

variable cg_batch_container_memory_limit {
  type        = number
  description = "Memory hard limit for the cellguide pipeline batch container"
  default     = 248000
}

variable cg_desired_vcpus {
  type        = number
  description = "Number of desired vCPUs for cellguide pipeline"
  default     = 128
}

variable frontend_memory {
  type        = number
  description = "Memory reservation for the frontend task"
  default     = 4096
}

variable frontend_instance_count {
  type        = number
  description = "How many frontend tasks to run"
  default     = 2
}

variable backend_instance_count {
  type        = number
  description = "How many backend tasks to run"
  default     = 2
}

variable backend_de_instance_count {
  type        = number
  description = "How many backend_de tasks to run"
  default     = 2
}

variable backend_wmg_instance_count {
  type        = number
  description = "How many backend_wmg tasks to run"
  default     = 2
}

variable backend_memory {
  type        = number
  description = "Memory reservation for the backend task"
  default     = 2048
}

variable backend_de_memory {
  type        = number
  description = "Memory reservation for the backend_de task"
  default     = 2048
}

variable backend_wmg_memory {
  type        = number
  description = "Memory reservation for the backend_wmg task"
  default     = 2048
}

variable "backend_cpus" {
  type        = number
  description = "CPUs for the backend task"
  default     = 2
}
variable "backend_de_cpus" {
  type        = number
  description = "CPUs for the backend_de task"
  default     = 2
}
variable "backend_wmg_cpus" {
  type        = number
  description = "CPUs for the backend_wmg task"
  default     = 2
}



variable schema_migration_ecs_memory {
  type        = number
  description = "Memory reservation for the schema_migration ecs task"
  default     = 2048
}

variable backend_workers {
  type        = number
  description = "Number of backend workers to run. Set to 1 by default for dev and staging."
  default     = 1
}
variable backend_de_workers {
  type        = number
  description = "Number of backend_de workers to run. Set to 1 by default for dev and staging."
  default     = 1
}

variable backend_wmg_workers {
  type        = number
  description = "Number of backend_wmg workers to run. Set to 1 by default for dev and staging."
  default     = 1
}

variable dd_key_secret_arn {
  type        = string
  description = "ARN for the Datadog secret key"
}