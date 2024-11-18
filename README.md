# CIDR Block Calculator

## Usage

```text
usage: main.py

Python AWS VPC CIDR Blocks

options:
  -h, --help            show this help message and exit
  -c VPC_CONFIGURATION, --vpc-configuration VPC_CONFIGURATION
                        AWS VPC Configurations (default: /Users/elio/PycharmProjects/cidr-blocks/vpc_configuration.yaml)
  -l {debug,info,warn,warning,error,critical}, --log-level {debug,info,warn,warning,error,critical}
                        Log Levels (default: info)
  -o OUTPUT, --output OUTPUT
                        Output Location (default: /Users/elio/PycharmProjects/cidr-blocks/vpc_configuration_cidr_blocks.yaml)

```

## Configuration Sample:

```yaml
---
sharedtools:
  cidr: 10.20.0.0/16
  region: us-east
  azs:
    - -1a
    - -1b
    - -1c
    - -1d
    - -1f
  subnets:
    public: 3
    private: 3
    database: 2
dev:
  cidr: 10.21.0.0/16
  region: us-east-1
  azs:
    - -1a
    - -1b
    - -1c
    - -1d
    - -1f
  subnets:
    public: 3
    private: 3
    database: 2
qa:
  cidr: 10.22.0.0/16
  region: us-east
  azs:
    - -1a
    - -1b
    - -1c
    - -1d
    - -1f
  subnets:
    public: 2
    private: 2
    database: 2
stage:
  cidr: 10.23.0.0/16
  region: us-east
  azs:
    - -1a
    - -1b
    - -1c
    - -1d
    - -1f
  subnets:
    public: 2
    private: 2
    database: 2
prod:
  cidr: 10.24.0.0/16
  region: us-east
  azs:
    - -1a
    - -1b
    - -1c
    - -1d
    - -1f
  subnets:
    public: 2
    private: 2
    database: 2

```
