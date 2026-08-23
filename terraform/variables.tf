variable "aws_region" {
  description = "AWS Region"
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.micro"
}

variable "key_name" {
  description = "EC2 Key Pair name (AWS Console-ல create பண்ணதோட name)"
  default     = "intern project"
}

variable "app_name" {
  description = "Application name"
  default     = "intern project"
}

variable "github_repo" {
  description = "GitHub repo URL (உங்க repo URL இங்க போடுங்க)"
  default     = "https://github.com/haritha223/AI-Dubs.git"
}
