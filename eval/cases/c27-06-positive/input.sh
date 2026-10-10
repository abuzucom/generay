#!/bin/sh
# Check the host is synced before starting the job (runs on laptops and servers).
timedatectl show -p NTPSynchronized --value | grep -q yes || exit 1
