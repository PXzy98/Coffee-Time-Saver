# Change Request — CR-001
**Project:** Enterprise Data Integration Initiative
**CR Number:** CR-001
**Title:** Custom Reporting Module — Team C Request
**Submitted by:** Priya (Business Lead, Operations) on behalf of Team C
**Submission Date:** March 12, 2026
**Status:** Under Assessment
**Classification:** Unclassified | Non classifié

---

## 1. Change Description

Team C is requesting the development of a custom reporting module to provide enhanced operational visibility across migrated data. The module would allow business users to define and run parameterized reports against the new system without reliance on the IT team.

The request was initially raised informally during the March 1 workshop. This formal change request was submitted following Project Manager instruction on March 3 that no development proceed without an approved CR.

---

## 2. Justification

- Existing approved scope covers configured dashboards only; business users require ad-hoc reporting capability not available through standard dashboard configuration
- Operations team currently uses custom Access DB reports that will have no equivalent in the new system without this module
- Without this capability, Team C will be unable to meet reporting obligations to senior management at go-live

---

## 3. Scope of Change

**In scope (this CR):**
- Design and build a parameterized report builder UI for authorized business users
- Integration with new system data layer (read-only queries)
- Role-based access control for report creation vs. execution
- Export to Excel and PDF

**Out of scope (this CR):**
- Real-time data feeds or live dashboards
- Automated report distribution
- Integration with external systems

---

## 4. Impact Assessment

### 4.1 Schedule Impact

| Work Package | Estimated Effort | Impact to Project Schedule |
|---|---|---|
| Architecture design for reporting layer | 3 days | +0 weeks (parallel) |
| Backend report query engine | 12 days | +2.5 weeks to critical path |
| Frontend report builder UI | 10 days | +2 weeks (may overlap with backend) |
| Integration testing | 5 days | +1 week |
| User acceptance testing (Team C) | 4 days | +1 week |
| **Total estimate** | **~34 days** | **+3–4 weeks to go-live** |

**Revised go-live estimate if approved:** June 2–15, 2026 (from current target May 1)

### 4.2 Budget Impact

| Category | Estimate |
|---|---|
| Consulting (development) | $68,000 |
| Internal QA and testing | $12,000 |
| Architecture review | $4,500 |
| Contingency (15%) | $12,675 |
| **Total estimated cost** | **~$97,000** |

**Note:** This estimate assumes no requirement changes after design is approved. Estimate accuracy: ±25%.

### 4.3 Technical Risk

- Introducing a custom query engine creates a new attack surface; security review required
- Report builder must use read-only connections — write access must be explicitly blocked at DB layer
- If Team C proceeds with independent development (outside this CR), integration complexity at go-live increases significantly

### 4.4 Interdependencies

- Dependent on completion of data migration (R-07 resolution) — reporting module requires clean, migrated data
- Requires architecture sign-off from Technical Authority before development begins
- Should not proceed in parallel with legacy data inconsistency resolution (R-02) as schema may change

---

## 5. Options

| Option | Description | Schedule Impact | Cost Impact | Recommendation |
|--------|-------------|-----------------|-------------|----------------|
| **A — Approve CR-001** | Build custom reporting module as described | +3–4 weeks | +$97K | Acceptable if timeline flexibility exists |
| **B — Reject CR-001** | Proceed with configured dashboards only; custom reporting deferred to Phase 2 | None | None | Protects current schedule |
| **C — Partial approval** | Deliver report export from existing dashboards only (no custom builder) | +1 week | +$18K | Compromise if reporting need is urgent |

---

## 6. Recommendation

**Project Manager recommendation: Option B — Defer to Phase 2.**

Given current schedule pressure (production sign-off pending, legacy data scope decision outstanding), adding a 3–4 week scope item to the critical path increases delivery risk significantly. The configured dashboard approach in scope can meet minimum reporting requirements at go-live. A Phase 2 scope item for custom reporting can be properly resourced and planned.

If Steering Committee determines reporting gap is critical to go-live success, Option C (export-only) is a lower-risk alternative.

---

## 7. Decision

**Decision required from:** Steering Committee
**Decision deadline:** March 19, 2026

| Outcome | Decision | Date | Authorized by |
|---------|----------|------|---------------|
| ☐ Approved — Option A | | | |
| ☐ Approved — Option B (defer) | | | |
| ☐ Approved — Option C (partial) | | | |
| ☐ Rejected | | | |

**Notes / Conditions of approval:**

---

## 8. Document History

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 0.1 draft | March 12, 2026 | Priya | Initial submission |
| 0.2 | March 13, 2026 | Sarah | Impact assessment added |
