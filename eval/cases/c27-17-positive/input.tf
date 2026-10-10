resource "aws_security_group_rule" "ntp_out" {
  type        = "egress"
  from_port   = 123
  to_port     = 123
  protocol    = "udp"
  cidr_blocks = ["0.0.0.0/0"]
}
