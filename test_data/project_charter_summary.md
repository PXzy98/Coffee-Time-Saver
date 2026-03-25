# Project Charter Summary
**Project:** Enterprise Data Integration Initiative
**Charter Version:** 1.3
**Approval Date:** January 22, 2026
**Project Sponsor:** DG, Digital Services Branch
**Project Manager:** Sarah
**Classification:** Unclassified | Non classifié

> *This is a summarized version of the full charter for distribution. Full charter available via GCDOCS.*

---

## 1. Business Justification

The organization currently operates with data distributed across multiple legacy systems maintained by distinct business units. Team A and Team B have operated independently for over 15 years with divergent data models, labelling conventions, and operational processes. The absence of a unified data layer creates:

- Duplicate effort in reporting and reconciliation
- Inconsistent data used to inform management decisions
- Barriers to cross-functional analytics and audit readiness

The Enterprise Data Integration Initiative will consolidate these systems into a single authoritative data platform, enabling consistent reporting and reducing administrative burden across the organization.

---

## 2. Project Objectives

1. Deliver a unified data platform integrating Team A and Team B source systems
2. Migrate all active and archival records to the new system with validated data integrity
3. Decommission legacy Team A and Team B systems within 90 days of go-live
4. Deliver configured reporting dashboards meeting defined business requirements
5. Complete user training and change management for all impacted staff

---

## 3. Scope

### In Scope
- Data migration from Team A legacy system (15 years of records)
- Data migration from Team B legacy system (15 years of records)
- New system configuration and deployment (vendor platform, not custom build)
- Configured reporting dashboards (standard vendor functionality)
- Role-based access configuration
- User training (all business units)
- Change management and communications

### Out of Scope
- **Custom development** of any reporting, workflow, or integration modules
- Real-time integration with external departmental systems
- Retroactive standardization of legacy data definitions *(Note: assumes data model alignment between source systems — ref. section 4.2)*
- AI or machine learning capabilities
- Mobile application development

---

## 4. Key Assumptions

| # | Assumption | Owner | Risk if Wrong |
|---|-----------|-------|----------------|
| 4.1 | Vendor platform will support all required dashboard configurations without custom development | Technical Authority | Medium — may require workaround or scope expansion |
| **4.2** | **Data model alignment exists between Team A and Team B source systems** | **Chloe (Data Lead)** | **High — migration plan requires rework if not valid** |
| 4.3 | Cyber Ops will complete production security sign-off within 6 weeks of environment build | Mark (Infrastructure) | High — blocks deployment planning |
| 4.4 | All business units will provide dedicated representatives for UAT (5 days minimum) | Alex (Change Lead) | Medium — testing timeline at risk |
| 4.5 | Legal review of data handling procedures will be complete before system go-live | Privacy Advisor | Low — review scoped and in progress |

---

## 5. Constraints

- **Budget:** $857,000 total approved (not to exceed without Steering Committee amendment)
- **Schedule:** Go-live by May 1, 2026 (hard constraint — tied to fiscal year reporting cycle)
- **Security:** All environments to meet Cyber Ops security configuration standards prior to use
- **Architecture:** No custom development; vendor platform must be used as-is with configuration only
- **Data:** No personal information to be processed outside approved privacy controls

---

## 6. Deliverables

| # | Deliverable | Owner | Target Date |
|---|------------|-------|-------------|
| D-01 | Architecture Design Document | Daniel | Feb 21, 2026 ✓ |
| D-02 | Security & Privacy Assessment | IT Security + Privacy | Mar 14, 2026 |
| D-03 | Migrated data — Team A | Chloe | Apr 4, 2026 |
| D-04 | Migrated data — Team B | Chloe | Apr 11, 2026 |
| D-05 | Configured dashboards | Daniel | Apr 18, 2026 |
| D-06 | User training complete (all units) | Alex | Apr 25, 2026 |
| D-07 | Go-live (Phase 1) | Sarah | May 1, 2026 |
| D-08 | Legacy system decommission plan | Mark | May 15, 2026 |

---

## 7. Risks (Summary — see Risk Register for detail)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Production security sign-off delay | High | High | Escalation path documented; parallel staging testing |
| Data model misalignment (Assumption 4.2) | Medium | High | Discovery in progress; scope decision pending |
| Budget overrun (consulting) | Medium | Medium | Monthly forecast tracking; contingency available |
| Team B disengagement | Medium | High | Change management plan; engagement sessions |

---

## 8. Governance

| Role | Name | Responsibility |
|------|------|---------------|
| Project Sponsor | DG, Digital Services Branch | Final authority; escalation point |
| Steering Committee | PM Director + 3 ADM representatives | Scope/budget decisions; milestone approvals |
| Project Manager | Sarah | Day-to-day delivery; risk and issue management |
| Technical Authority | Daniel | Architecture decisions; vendor management |
| Change Lead | Alex | Stakeholder engagement; training coordination |

**Steering Committee meets:** Bi-weekly (every second Wednesday, 2:00 PM EST)

---

## 9. Change Control

All changes to scope, schedule, or budget require:
1. Formal change request submitted to Project Manager
2. Impact assessment prepared within 5 business days
3. Steering Committee approval for changes exceeding $10,000 or 1 week schedule impact
4. DG approval for changes exceeding $50,000 or 3 weeks schedule impact

No work to begin on any change prior to written approval.

---

*Approved by: DG, Digital Services Branch — January 22, 2026*
*Next charter review: At project mid-point (March 2026) or upon material change*
