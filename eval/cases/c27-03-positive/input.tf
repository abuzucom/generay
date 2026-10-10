resource "aws_instance" "worker" {
  count         = 200
  ami           = "ami-0abcdef1234567890"
  instance_type = "m6i.large"
  user_data     = "#!/bin/sh\nsystemctl disable chronyd\n"
}
