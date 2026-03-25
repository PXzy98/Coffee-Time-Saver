# Risk Register — Enterprise Data Integration Initiative
**Project:** Enterprise Data Integration Initiative
**Document Version:** 2.4
**Last Updated:** March 10, 2026
**Owner:** Sarah (Project Manager)
**Classification:** Unclassified | Non classifié

---

## Risk Summary

| ID | Category | Description | Likelihood | Impact | Score | Status | Owner |
|----|----------|-------------|------------|--------|-------|--------|-------|
| R-01 | Technical | Production environment security sign-off delayed by Cyber Ops | High | High | 16 | Open | Mark |
| R-02 | Scope | Data standardization of legacy fields requested outside approved SOW | High | High | 16 | Open | Sarah |
| R-03 | Schedule | Custom reporting module development initiated without change request | Medium | High | 12 | Open | Daniel |
| R-04 | Financial | Consulting costs trending above forecast due to extended validation sessions | Medium | Medium | 9 | Monitoring | Jason |
| R-05 | Stakeholder | Team B disengagement — adoption risk if data inconsistency concerns unresolved | High | Medium | 12 | Open | Alex |
| R-06 | Technical | Post-launch operational support model not defined before deployment | Medium | High | 12 | Open | Mark |
| R-07 | Data | Legacy dataset field definition inconsistencies between Team A and Team B | High | High | 16 | Open | Chloe |
| R-08 | Compliance | No threat model documentation completed for sandbox environment | Low | High | 8 | Open | Daniel |
| R-09 | Schedule | Go-live delay if scope expanded to include 15-year data remediation | High | High | 16 | Open | Sarah |
| R-10 | Technical | Integration complexity if Team C custom module built independently | Low | Medium | 4 | Monitoring | Daniel |

---

## Risk Detail

### R-01 — Production Security Sign-Off Delay
**Category:** Technical
**Raised:** February 18, 2026
**Likelihood:** High (5) | **Impact:** High (4) | **Score:** 20

**Description:**
Production environment has been built but security configuration has not been formally signed off by Cyber Ops. No committed date has been provided. Without sign-off, deployment planning cannot be finalized and full integration testing cannot proceed.

**Current Status:** Open — dependency on Cyber Ops. Escalation to Director level recommended if no committed date by March 17.

**Mitigation:**
- Document dependency formally in project risk log
- Escalate to DG level if sign-off not committed by end of sprint
- Continue staging testing in parallel

**Contingency:** Extend testing phase; prepare revised schedule baseline assuming 3-week delay.

---

### R-02 — Legacy Data Standardization Scope Creep
**Category:** Scope / Data
**Raised:** March 3, 2026 (identified in Weekly Sync)
**Likelihood:** High (4) | **Impact:** High (4) | **Score:** 16

**Description:**
During the March 3 sync meeting, it was identified that some stakeholders are requesting that 15 years of historical field definitions be standardized and reconciled before data migration proceeds. This work was not included in the approved Statement of Work and constitutes a significant scope expansion.

**Current Status:** Open — leadership decision required. Two options pending formal assessment:
1. Formally expand scope via change request (schedule and cost impact TBD)
2. Accept post-implementation remediation of legacy data inconsistencies

**Mitigation:**
- Do not begin legacy remediation work without approved change request
- Document stakeholder positions clearly
- Prepare impact assessment for leadership review by March 18

---

### R-03 — Unauthorized Custom Reporting Module
**Category:** Scope / Technical
**Raised:** March 3, 2026
**Likelihood:** Medium (3) | **Impact:** High (4) | **Score:** 12

**Description:**
Team C raised the idea of building a custom reporting module during the March 1 workshop. This was not included in the approved architecture documentation or project scope. If Team C proceeds independently, it will create integration complexity at deployment and potentially conflict with the approved dashboard configuration approach.

**Current Status:** Open — no formal change request submitted as of March 10. Team C intent not confirmed.

**Mitigation:**
- Communicate clearly that no work should proceed without a formal change request
- If CR submitted, assess integration impact against approved architecture

---

### R-05 — Team B Stakeholder Disengagement
**Category:** Stakeholder / Change Management
**Raised:** March 3, 2026 (raised by Alex, Change Lead)
**Likelihood:** High (4) | **Impact:** Medium (3) | **Score:** 12

**Description:**
Team B is attending meetings but not actively participating. Feedback collected by Change Lead indicates the team believes decisions are predetermined before sessions take place. Specific concern relates to proceeding with migration while data inconsistencies remain unresolved (see R-07). If not addressed, adoption risk increases significantly at go-live.

**Current Status:** Open — Change Lead to initiate targeted engagement sessions with Team B.

**Mitigation:**
- Direct 1:1 engagement sessions with Team B lead
- Demonstrate responsiveness to data inconsistency concerns
- Avoid communicating migration decisions before Team B has had input opportunity

---

### R-07 — Legacy Field Definition Inconsistency
**Category:** Data Quality
**Raised:** March 3, 2026
**Likelihood:** High (4) | **Impact:** High (4) | **Score:** 16

**Description:**
Team A and Team B use identical field labels with different semantic meanings. The migration plan was drafted under the assumption of baseline alignment between systems. This assumption is now confirmed to be incorrect. Proceeding without resolution will carry inconsistencies into the new system.

**Current Status:** Open — direct dependency on scope decision for R-02.

---

## Risk Scoring Matrix

| | Low Impact (1-2) | Medium Impact (3) | High Impact (4-5) |
|---|---|---|---|
| **High Likelihood (4-5)** | Monitor | Escalate | Critical |
| **Medium Likelihood (3)** | Accept | Monitor | Escalate |
| **Low Likelihood (1-2)** | Accept | Accept | Monitor |

---

## Change Log

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | Jan 15, 2026 | Sarah | Initial version |
| 2.0 | Feb 5, 2026 | Sarah | Added R-06, R-07 |
| 2.3 | Mar 3, 2026 | Sarah | Added R-02, R-03, R-05 from weekly sync |
| 2.4 | Mar 10, 2026 | Sarah | Updated R-01 status, added contingency |
