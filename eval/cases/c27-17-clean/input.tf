resource "aws_security_group_rule" "ntp_internal" {
  type        = "egress"
  from_port   = 123
  to_port     = 123
  protocol    = "udp"
  cidr_blocks = ["10.0.0.0/16"]
}
