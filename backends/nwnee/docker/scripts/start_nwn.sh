#!/bin/bash
userid=$1
groupid=$2
org_entrypoint=$3
groupadd -g $groupid nwn
useradd nwn -u $userid -g nwn -m -s /bin/bash
chown -R nwn:nwn /nwn
/bin/su -c $org_entrypoint nwn

