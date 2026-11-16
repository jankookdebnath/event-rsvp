variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance type (t3.micro is free-tier eligible)"
  type        = string
  default     = "t3.micro"
}

variable "repo_url" {
  description = "Public Git repository the server clones the app from"
  type        = string
}

variable "git_commit" {
  description = "Commit to deploy; Jenkins passes the commit it just checked out"
  type        = string
  default     = "main"
}
