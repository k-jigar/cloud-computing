# Subnetting and Network Access Control (Task 5)

## 1. Subnet Allocation

We are given the parent CIDR block `10.20.0.0/16`.
Requirements state that we must allocate subnets from largest requirement to smallest, starting at `10.20.0.0`, contiguous with no wasted gaps between allocated subnets, using the smallest prefix (tightest subnet mask) that satisfies the host capacity requirement according to the formula:
$$\text{Usable Hosts} = 2^{32 - \text{prefix}} - 2$$

### Host Requirements and Prefix Sizing
1. **app subnet (1,000 hosts needed)**:
   - $2^9 - 2 = 510 < 1000$ (insufficient)
   - $2^{10} - 2 = 1022 \ge 1000$ (sufficient)
   - Host bits $h = 10 \implies$ Prefix length $= 32 - 10 = \mathbf{/22}$.
   - Address block: `10.20.0.0/22` (spans $1024$ total IP addresses: `10.20.0.0` to `10.20.3.255`).

2. **public subnet (250 hosts needed)**:
   - Positioned immediately after `app` (`10.20.3.255`), starting at `10.20.4.0`.
   - $2^7 - 2 = 126 < 250$ (insufficient)
   - $2^8 - 2 = 254 \ge 250$ (sufficient)
   - Host bits $h = 8 \implies$ Prefix length $= 32 - 8 = \mathbf{/24}$.
   - Address block: `10.20.4.0/24` (spans $256$ total IP addresses: `10.20.4.0` to `10.20.4.255`).

3. **data subnet (100 hosts needed)**:
   - Positioned immediately after `public` (`10.20.4.255`), starting at `10.20.5.0`.
   - $2^6 - 2 = 62 < 100$ (insufficient)
   - $2^7 - 2 = 126 \ge 100$ (sufficient)
   - Host bits $h = 7 \implies$ Prefix length $= 32 - 7 = \mathbf{/25}$.
   - Address block: `10.20.5.0/25` (spans $128$ total IP addresses: `10.20.5.0` to `10.20.5.127`).

4. **management subnet (20 hosts needed)**:
   - Positioned immediately after `data` (`10.20.5.127`), starting at `10.20.5.128`.
   - $2^4 - 2 = 14 < 20$ (insufficient)
   - $2^5 - 2 = 30 \ge 20$ (sufficient)
   - Host bits $h = 5 \implies$ Prefix length $= 32 - 5 = \mathbf{/27}$.
   - Address block: `10.20.5.128/27` (spans $32$ total IP addresses: `10.20.5.128` to `10.20.5.159`).

---

## 2. Subnet Allocation Table

| Subnet Name | Hosts Needed | Network Address | Prefix Length | Netmask | Usable Host Range | Broadcast Address | Usable Hosts |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **app** | 1,000 | `10.20.0.0` | `/22` | `255.255.252.0` | `10.20.0.1` – `10.20.3.254` | `10.20.3.255` | 1,022 |
| **public** | 250 | `10.20.4.0` | `/24` | `255.255.255.0` | `10.20.4.1` – `10.20.4.254` | `10.20.4.255` | 254 |
| **data** | 100 | `10.20.5.0` | `/25` | `255.255.255.128` | `10.20.5.1` – `10.20.5.126` | `10.20.5.127` | 126 |
| **management** | 20 | `10.20.5.128` | `/27` | `255.255.255.224` | `10.20.5.129` – `10.20.5.158` | `10.20.5.159` | 30 |

Remaining unallocated space within `10.20.0.0/16`: `10.20.5.160` to `10.20.255.255`.

---

## 3. Stateless NACL Reasoning & Analysis

### Why Stateless NACLs Require Separate Reply Rules
Unlike stateful inspection firewalls (or Kubernetes Security Groups) which maintain an internal connection state table (`conntrack`) and automatically permit returning traffic associated with an established inbound/outbound session, a **Network Access Control List (NACL) is completely stateless**.

Every individual IP packet traversing the subnet boundary is evaluated independently and in isolation, with no memory of prior packets:
1. When an external client initiates an inbound TCP connection to the public load balancer on port 80 or 443, the client sends packets from its randomly chosen ephemeral source port (1024–65535) to destination port 80/443. The inbound NACL rule permits this incoming packet.
2. When the load balancer generates the TCP response packet back to the client, the outbound packet has source port 80/443 and **destination port equal to the client's ephemeral port (1024–65535)**. Because the NACL is stateless, it has no record that this packet is a reply to an allowed inbound request. Without an explicit outbound allow rule permitting traffic to ephemeral destination ports `1024–65535`, the response packet would hit the default deny rule and be dropped, terminating the connection.
3. Similarly, when the load balancer forwards requests to the internal inference service in the `app` subnet on destination port 8000 (outbound rule 100), the returning response from the app service arrives inbound at the public subnet targeting the load balancer's ephemeral port range `1024–65535` from source CIDR `10.20.0.0/22`. A specific inbound reply rule (rule 140) is strictly required to permit this return traffic.

### Why Rule Order Matters for the `198.51.100.0/24` Block
NACL rules are evaluated sequentially in strictly **ascending numerical order** (lowest rule number first), and evaluation terminates on the **first match** (first match wins).

1. The abusive CIDR block `198.51.100.0/24` is a subset of the global internet address space `0.0.0.0/0`.
2. Rule 100 explicitly denies all traffic from source `198.51.100.0/24`. Rules 110 and 120 allow inbound TCP traffic on ports 80 and 443 from `0.0.0.0/0`.
3. If the deny rule is numbered lower than the allow rules (e.g., Rule 100 < Rule 110/120), any inbound packet originating from an attacker at `198.51.100.x` targeting web ports 80 or 443 is matched by Rule 100 first and immediately dropped (`DENY`).
4. If the order were reversed (e.g., allow `0.0.0.0/0` on port 443 at Rule 100 and deny `198.51.100.0/24` at Rule 120), a malicious packet from `198.51.100.x` to port 443 would match the broader `0.0.0.0/0` allow rule first and be admitted into the subnet, completely bypassing and neutralizing the security block rule. Therefore, specific deny rules must always precede general allow rules in stateless NACL rule tables.

