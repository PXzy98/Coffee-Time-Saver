# Infrastructure Security Assessment Report
**Classification:** Internal — Restricted
**Prepared by:** Cybersecurity Team (InfoSec)
**Assessment period:** February 1 – March 10, 2026
**Ref:** INFOSEC-2026-ASM-017

---

## Executive Overview

This report summarises findings from a quarterly infrastructure security assessment covering the organisation's on-premises data centre, cloud workloads (AWS us-east-1), and remote access infrastructure. The assessment used a combination of automated scanning (Tenable.io, Qualys), manual penetration testing, and configuration review.

**Overall risk rating: HIGH**

Critical findings requiring immediate action are detailed in Section 3.

---

## Scope

- On-premises: 3 physical servers, 47 virtual machines, 4 network switches, 2 firewalls
- Cloud: 12 EC2 instances, 3 RDS databases, 6 S3 buckets
- Remote access: Cisco AnyConnect VPN gateway, Azure AD (MFA enforcement review)
- Excluded: OT/SCADA systems (separate assessment track)

---

## Key Findings

### CRITICAL — CVE-2024-21762 (Fortinet FortiOS SSL-VPN)

The organisation's FortiGate 200F firewall is running FortiOS 7.2.4, which is vulnerable to CVE-2024-21762 (CVSS 9.6 — unauthenticated remote code execution via the SSL-VPN interface). A public exploit is available.

**Current exposure:** The SSL-VPN interface is internet-facing on port 443. Approximately 220 staff connect via this gateway daily.

**Required action:** Upgrade FortiOS to version 7.4.3 or later. Fortinet patch is available. Estimated downtime: 45 minutes during off-hours.

---

### HIGH — S3 Bucket Public Access Not Enforced Globally

Three S3 buckets (`reports-archive-prod`, `finance-exports-2024`, `hr-docs-staging`) have public access block settings disabled at the bucket level. While no bucket policies currently grant public access, the absence of the block creates risk from accidental policy misconfiguration.

**Required action:** Enable "Block all public access" on all three buckets.

---

### HIGH — MFA Not Enforced for 14 Azure AD Accounts

14 user accounts (including 3 accounts with Global Admin role) do not have MFA enrolled in Azure AD. Organisation's security policy (POL-SEC-003) requires MFA for all accounts.

**Required action:** Enforce MFA enrollment for all 14 accounts. Accounts that do not comply within 7 days should be disabled.

---

### MEDIUM — Outdated SSL/TLS Configuration on Internal Web Portals

Two internal web portals (HR self-service, expense reporting) accept TLS 1.0 and 1.1 connections. These protocols are deprecated and known to be weak.

**Required action:** Disable TLS 1.0/1.1 on both portals and enforce TLS 1.2 minimum.

---

### MEDIUM — Excessive IAM Permissions (AWS)

12 IAM roles have `*:*` (full access) policies attached. Least privilege principle is not being followed.

**Required action:** Review and scope-down IAM roles to minimum required permissions. Priority: roles attached to production EC2 instances.

---

### LOW — SSH Password Authentication Enabled on 6 Servers

Six Linux servers allow SSH password authentication in addition to key-based authentication. This increases brute-force risk.

**Required action:** Disable password authentication in `/etc/ssh/sshd_config` and restart the SSH service on all affected servers.

---

## Recommended Remediation Schedule

| Finding | Owner | Deadline |
|---|---|---|
| FortiOS upgrade (CVE-2024-21762) | Marcus Webb (IT Infrastructure) | March 20, 2026 |
| S3 public access block | Cloud Ops team | March 18, 2026 |
| Azure AD MFA enforcement | IT Security | March 17, 2026 (7-day policy window starts today) |
| TLS 1.0/1.1 disable | Marcus Webb | April 4, 2026 |
| IAM role scoping | Cloud Ops team | April 11, 2026 |
| SSH password auth disable | Linux Ops | March 25, 2026 |

---

## Compliance Notes

Failure to remediate CVE-2024-21762 before March 20 will be escalated to the CISO and reported as a compliance exception under the organisation's Cyber Risk Management Framework (CRMF §4.3). If a breach occurs while the vulnerability remains open, this finding constitutes a known unmitigated risk and may affect cyber insurance coverage.

The three Azure AD Global Admin accounts without MFA are in breach of POL-SEC-003 as of the date of this report.

---

## Next Steps

1. InfoSec team to schedule FortiOS maintenance window with IT Infrastructure by March 16, 2026.
2. IT Security to send MFA enrollment notices to 14 affected users by March 16, 2026.
3. Cloud Ops to confirm S3 remediation complete by March 18, 2026 and notify InfoSec.
4. All findings to be tracked in the risk register (JIRA project: INFOSEC).
5. Follow-up validation scan scheduled for April 15, 2026.

Report prepared by: Chen Liu, Senior Security Analyst
Reviewed by: CISO (pending)
