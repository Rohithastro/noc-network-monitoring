# Networking Projects — Rohith Rajesh

## 1. Enterprise Network Infrastructure
https://github.com/Rohithastro/enterprise-network-infrastructure
- Simulated company campus using 3 routers, 4 switches and 4 VLANs.
- Includes inter-VLAN routing, OSPF, DHCP, ACL, topology, port map, IP plan and IOS-style configurations.
- Intended validation: VLAN/trunk state, DHCP leases, inter-VLAN reachability, OSPF adjacencies/routes, guest ACL policy and OSPF reconvergence after a lab link failure.
- Lab environment: GNS3 with authorized Cisco IOSv/IOSvL2 images or equivalent.

## 2. NOC Network Monitoring System
https://github.com/Rohithastro/noc-network-monitoring
- SNMP-based monitoring prototype that polls configured devices and records availability and latency in SQLite.
- Detects up/down transitions, emits alerts and generates uptime/downtime reports.
- Prototype currently uses SNMPv2c; community strings are not encrypted. Use only in a controlled lab and do not expose to untrusted networks.
- Demonstration target is a loopback-only localhost SNMP agent.

## 3. Network Troubleshooting & Incident Management
https://github.com/Rohithastro/network-incident-management
- Ten runbooks covering DNS, DHCP, IP conflict, packet loss, high latency, VLAN misconfiguration, routing failure, network outage, TCP connection failure and firewall blocking.
- Each runbook includes symptoms, safe lab fault injection, evidence-based diagnosis, remediation, verification and rollback.
- Includes a command-line incident register tracking severity, owner, status and chronological notes.

Note: Project repositories document implementations and intended demonstrations. List hands-on testing results separately after completing and recording the tests.