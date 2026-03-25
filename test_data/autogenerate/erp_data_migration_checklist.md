# ERP Data Migration — Pre-Cutover Checklist
**Project:** ERP System Upgrade (SAP S/4HANA)
**Phase:** Go-Live Preparation
**Version:** 0.3 DRAFT — Pending final review by Daniel Fortier
**Last updated:** March 15, 2026

---

## Purpose

This checklist must be completed and signed off by all named owners before the production cutover weekend (target: June 28–29, 2026). Any item marked RED on June 26 will trigger an automatic go/no-go escalation to the Steering Committee.

---

## Section 1 — Data Extraction & Transformation (Owner: Daniel Fortier)

- [ ] Extract complete GL transaction history from Oracle (FY2021–FY2025)
- [ ] Extract Vendor Master (AP) — full dataset with banking details
- [ ] Extract Customer Master (AR) — full dataset
- [ ] Extract open Purchase Orders (status: approved or pending)
- [ ] Extract open Sales Orders
- [ ] Extract fixed asset register with depreciation schedules
- [ ] Run ETL transformation scripts against staging environment — zero errors required
- [ ] Validate record counts: source vs. target (tolerance: 0 discrepancy for financial records)
- [ ] **Remediate duplicate vendor records (1,247 identified in UAT Sprint 4)** — Due: March 26, 2026
- [ ] Reconcile GL opening balances: SAP trial balance must match Oracle trial balance exactly
- [ ] Sign off: Daniel Fortier + Finance Director (Catherine Leroux)

---

## Section 2 — User Acceptance Testing (Owner: Hiro Tanaka)

- [ ] UAT test cases written for all 127 business processes
- [ ] UAT executed by Finance team — Finance module (GL, AP, AR)
- [ ] UAT executed by Finance team — sign-off obtained from Finance Director
- [ ] UAT executed by HR team — HR and Payroll module
- [ ] UAT executed by Procurement team — Purchasing module
- [ ] Defect log closed: 0 open P1 defects, ≤3 open P2 defects allowed at go-live
- [ ] Performance test: batch payroll run must complete in ≤4 hours (currently 6.5 hours — remediation needed)
- [ ] Sign off: Hiro Tanaka

---

## Section 3 — Infrastructure & Environment (Owner: Marcus Webb / Greg White — SAP)

- [ ] Production SAP S/4HANA environment provisioned and hardened
- [ ] DR environment provisioned and failover tested
- [ ] Network bandwidth confirmed: SAP GUI response time ≤2 seconds from all office locations
- [ ] Backup schedule configured: full nightly, incremental hourly
- [ ] SAP Basis configuration: transport landscape (DEV → QA → PROD) locked for go-live
- [ ] Single Sign-On (SSO) configured and tested: all 380 user accounts
- [ ] Role-based access control: all 38 SAP roles assigned and tested
- [ ] Printer configuration: payslips, purchase orders, vendor remittances
- [ ] Sign off: Marcus Webb + Greg White

---

## Section 4 — Change Management & Training (Owner: Fatou Sow)

- [ ] Change impact assessment distributed to all department heads — confirmed received
- [ ] Training schedule published for all 380 users
- [ ] Training completion rate ≥ 90% required before go-live approval
- [ ] Quick reference cards printed and distributed (GL, AP, AR, HR modules)
- [ ] Helpdesk briefing completed: support team trained on common SAP issues
- [ ] Hypercare support plan in place: on-site SAP support for 4 weeks post go-live
- [ ] Communication sent to all staff: go-live date, system downtime window (June 27, 18:00 – June 29, 06:00)
- [ ] Sign off: Fatou Sow

---

## Section 5 — Cutover Plan (Owner: Priya Nair)

- [ ] Legacy Oracle system freeze date confirmed: June 27, 17:00
- [ ] Cutover runbook written and rehearsed (dry run by June 14)
- [ ] Rollback plan documented: criteria for rollback decision, rollback steps, rollback decision owner (CTO)
- [ ] Rollback window: rollback must be initiated by June 29, 02:00 if issues arise (after this point, cutover proceeds regardless)
- [ ] Parallel run period defined: June 29 – July 13, both Oracle and SAP running in read-only parallel
- [ ] Sign off: Priya Nair + CTO

---

## Section 6 — Outstanding Issues (as of March 15, 2026)

| # | Issue | Owner | Due |
|---|---|---|---|
| 1 | Batch payroll performance: 6.5h vs 4h target | Greg White (SAP) | April 30, 2026 |
| 2 | 1,247 duplicate vendor records in AP | Amara Diallo + Daniel Fortier | March 26, 2026 |
| 3 | Cost centres CC-4412/CC-4413 missing from GL report | Greg White + Amara Diallo | March 23, 2026 |
| 4 | Finance Director UAT sign-off not received | Priya Nair | March 24, 2026 |
| 5 | SSO integration with Azure AD not yet tested | Marcus Webb | April 15, 2026 |

---

## Go / No-Go Criteria (June 26, 2026)

**STOP — do not proceed if any of the following are true:**
- Finance Director UAT sign-off not obtained
- Open P1 defects in production environment
- Data reconciliation discrepancy in GL opening balances
- Batch payroll run exceeds 4-hour threshold
- Training completion below 90%

**PROCEED with conditions if:**
- ≤3 open P2 defects (with documented workarounds)
- Minor role access issues affecting <5 users (to be resolved during hypercare)

---

*This document is a draft. Final version must be approved by Priya Nair before March 31, 2026.*
