# Cloud VPS Provider Comparison & Sizing Decision Document

**Project**: SupplyChainAgent Production Backend  
**Baseline Sizing**: 4 vCPU, 8 GB RAM, 80–160 GB NVMe/SSD, Public IPv4, Linux (Ubuntu 24.04 LTS)  
**Evaluated Providers**: Hetzner Cloud, DigitalOcean, Amazon Web Services (AWS EC2)

---

## 1. Executive Summary & Recommendation

| Provider | Plan Tier | vCPU / RAM | Storage | Approximate Monthly Cost* | Best Fit For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hetzner Cloud** | `CPX31` (Shared AMD) | 4 vCPU / 8 GB | 160 GB NVMe | **~€13.50 – €15.00 / mo** (~$15 – $17 USD) | **Student / Portfolio / Best Price-to-Performance** |
| **DigitalOcean** | Basic Droplet (Premium AMD) | 4 vCPU / 8 GB | 160 GB NVMe | **~$48.00 / mo** | Developer UX / Beginner-friendly US/EU cloud |
| **AWS EC2** | `t4g.xlarge` (ARM64) or `t3.xlarge` (x86) | 4 vCPU / 16 GB (`t4g`) or 4 vCPU / 16 GB (`t3`) | gp3 EBS (80–160 GB) | **~$45.00 – $65.00 / mo** (+ data transfer & IPv4 charge) | Enterprise ecosystem integration / AWS credentials |

*\*Pricing note: Approximate figures based on publicly published provider catalog rates as of 2024–2026. Exchange rates, local VAT/taxes, IPv4 surcharges, and egress bandwidth overages may adjust final invoicing.*

### Final Recommendation for This Project: **Hetzner Cloud (`CPX31`)**
For an independent, student, or portfolio project, **Hetzner Cloud (`CPX31`)** provides unbeatable price-to-performance:
- **Cost**: Approximately **1/3 the cost** of DigitalOcean or AWS for the identical 4 vCPU / 8 GB RAM specification.
- **NVMe Storage**: Includes 160 GB fast local NVMe SSD (ample for PostgreSQL, Redis, Neo4j, and Docker image caches).
- **Network Traffic**: 20 TB included outbound traffic per month (compared to costly AWS egress fees).
- **Simplicity**: Standard Ubuntu 24.04 LTS installation works immediately with Docker Engine and Compose V2 without complex IAM policies, VPC subnet routing, or security group hierarchies.

If Hetzner is geographically unavailable or account verification is delayed, **DigitalOcean Basic Droplet** is the recommended alternative due to its instant global signup, simple billing, and straightforward control panel.

---

## 2. Detailed Provider Analysis

### 1. Hetzner Cloud

- **Recommended Instance**: `CPX31` (AMD EPYC™) or `CX32` (Intel® Xeon®)
- **Specifications**: 4 vCPU, 8 GB RAM, 160 GB NVMe SSD, 1 IPv4 + /64 IPv6.
- **Approximate Cost**: ~€13.50 – €15.00/month (~$15 – $17 USD).
- **Setup Complexity**: Very Low. Clean web console, instant SSH key injection, fast provisioning (< 30 seconds).
- **Docker & Compose Support**: Outstanding. Runs standard Ubuntu 24.04 LTS kernel; native Docker Engine installs cleanly via official apt repositories without quirks.
- **Networking**:
  - Dedicated public IPv4 included.
  - 20 TB free monthly egress bandwidth.
  - Datacenters in Germany (Nuremberg, Falkenstein), Finland (Helsinki), and US (Ashburn VA, Hillsboro OR).
- **Backups & Snapshots**:
  - Automated daily snapshots available (+20% of server price, ~€2.70/month).
  - Manual snapshots cost ~€0.05/GB/month.
- **Suitability for SupplyChainAgent**: **Highest**. Neo4j JVM heap and PostgreSQL page caches thrive on the fast NVMe disk and 8 GB RAM without generating high cloud bills.

---

### 2. DigitalOcean

- **Recommended Instance**: Basic Droplet (Regular or Premium AMD SSD)
- **Specifications**: 4 vCPU, 8 GB RAM, 160 GB SSD, 1 public IPv4.
- **Approximate Cost**: ~$48.00/month.
- **Setup Complexity**: Very Low. Widely regarded as having the most intuitive developer UI and straightforward documentation.
- **Docker & Compose Support**: Outstanding. DigitalOcean offers a "Docker on Ubuntu" 1-click marketplace image or bare Ubuntu 24.04 LTS.
- **Networking**:
  - 5 TB free transfer included.
  - Global datacenters (NYC, San Francisco, Amsterdam, Frankfurt, London, Singapore, Bangalore).
  - Cloud firewalls configurable via web dashboard.
- **Backups & Snapshots**:
  - Automated weekly backups available for +20% of droplet cost (~$9.60/month).
  - Snapshots cost $0.06/GB/month.
- **Suitability for SupplyChainAgent**: **High**. Excellent reliability and simple firewall/DNS management, though priced significantly higher than Hetzner.

---

### 3. Amazon Web Services (AWS EC2)

- **Recommended Instance**:
  - `t4g.xlarge` (ARM64 Graviton2): 4 vCPU, 16 GB RAM &rarr; ~$40.00/month (compute) + EBS storage
  - `t3.xlarge` (x86_64 Intel): 4 vCPU, 16 GB RAM &rarr; ~$120.00/month (on-demand compute)
  - `c6i.xlarge` (4 vCPU, 8 GB RAM): ~$100.00/month
- **Storage**: Amazon EBS `gp3` (80 GB at $0.08/GB-month = ~$6.40/month).
- **Approximate Cost**: ~$45.00 – $75.00/month for `t4g.xlarge` with storage, or $100+/month for `t3.xlarge`.
- **Public IPv4 Surcharge**: AWS charges $0.005/hour (~$3.65/month) per public IPv4 address.
- **Setup Complexity**: High. Requires navigating AWS Management Console, VPCs, Internet Gateways, Subnets, Security Groups, IAM roles, and Key Pairs.
- **Docker & Compose Support**: Excellent, but requires manual Docker installation on Ubuntu AMI or Amazon Linux 2023.
- **Networking**:
  - Outbound data transfer costs ~$0.09/GB after first 100 GB.
  - Complex network security group rules.
- **Backups & Snapshots**:
  - AWS Backup / EBS Snapshots ($0.05/GB/month). Highly granular, enterprise-grade lifecycle rules.
- **Suitability for SupplyChainAgent**: **Moderate**. While offering boundless enterprise scale, it introduces unnecessary complexity, egress billing uncertainty, and configuration overhead for a single-node Compose deployment.

---

## 3. Cost & Specification Comparison Matrix

| Attribute | Hetzner Cloud (`CPX31`) | DigitalOcean (Droplet) | AWS EC2 (`t4g.xlarge`) |
| :--- | :--- | :--- | :--- |
| **vCPU** | 4 AMD EPYC Cores | 4 AMD Cores | 4 Graviton2 Cores |
| **RAM** | 8 GB | 8 GB | 16 GB |
| **Local Disk** | 160 GB NVMe SSD | 160 GB NVMe SSD | 80–160 GB EBS gp3 |
| **Bandwidth** | 20 TB / month | 5 TB / month | 100 GB free, then $0.09/GB |
| **Public IPv4** | Included | Included | ~$3.65 / month surcharge |
| **Base Monthly Cost** | **~€13.50 (~$15 USD)** | **~$48.00 USD** | **~$45 – $75 USD** |
| **Backup Cost** | ~€2.70 / month | ~$9.60 / month | ~$4.00 – $8.00 / month |
| **Billing Model** | Hourly / Monthly | Hourly / Monthly | Per-second / Hourly |
| **Setup Time** | ~5 minutes | ~5 minutes | ~20–30 minutes |
| **Learning Curve** | Minimal | Minimal | Moderate to High |

---

## 4. Minimum VPS Sizing Justification

Why is 4 vCPU and 8 GB RAM required rather than a smaller 1 vCPU / 2 GB droplet?

1. **Neo4j 5 Community Graph Database**:
   - JVM Heap allocation: 512 MB min, 1536 MB max.
   - Pagecache allocation: 512 MB.
   - Total Neo4j footprint: **~2.2 GB RAM**. On a 2 GB server, Neo4j will trigger an immediate Linux Out-Of-Memory (OOM) kill.
2. **PostgreSQL 16**:
   - Shared buffers, work memory, and connection pools: **~1.0 GB RAM**.
3. **Redis 7 & Celery Workers**:
   - Redis in-memory cache + Celery 2-process concurrency: **~1.0 GB RAM**.
4. **FastAPI ASGI Backend (Uvicorn)**:
   - Python runtime + simulation logic + NumPy/Pandas: **~1.0 GB RAM**.
5. **Operating System & Caddy Reverse Proxy**:
   - Linux kernel buffers, systemd, Caddy proxy cache: **~1.0 GB RAM**.
6. **Total Working Footprint**: **~6.2 GB RAM**.
   - An 8 GB RAM instance provides a safe **~1.8 GB buffer** preventing swap thrashing and guaranteeing low-latency response times during simulation execution.
