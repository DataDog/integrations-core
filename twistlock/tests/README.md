# Setup Prisma Cloud Twistlock

## Prerequisite

- Prisma Cloud account
- Docker hub account

## Setup

### Add a Defender

- https://app3.prismacloud.io/ > Compute > Manage > Defenders > Deploy
- Copy the script and run it on a new VM to use it as Defender

### Add Registry

https://app3.prismacloud.io/ > Compute > Defend > Vulnerabilities > Registry > Add registry

Form:

- Registry: Leave empty if you are using Docker Hub
- Repository: e.g. your docker hub repository, library/alpine, etc 
- Credential: Use Docker Hub credentials

### Add Vulnerabilities rules

https://app3.prismacloud.io/ > Compute > Defend > Vulnerabilities > Images > Add rule
