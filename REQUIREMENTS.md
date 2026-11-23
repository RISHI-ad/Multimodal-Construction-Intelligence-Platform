# Requirements Specification
## Multimodal Construction Intelligence Platform (Skill Wallet Capstone Project 1)

## 1. Purpose
Construction teams face unsafe sites, late detection of structural defects, manual cost estimation, delayed planning and no single place for decision support. This platform accepts construction photos and project parameters and returns **structured, actionable** outputs (scores, checklists, costs, advisories) instead of raw AI text.

**Users:** site engineers, contractors, safety officers, project managers.

## 2. Approach
1. Studied the construction lifecycle: planning, execution, monitoring, reporting.
2. Identified problem areas: site safety risks, manual cost estimation, delayed planning, no centralised decision support.
3. Defined feature-wise functional requirements (Section 3).
4. Defined non-functional requirements (Section 4).
5. Documented input and output formats for every feature (Section 5).

## 3. Functional Requirements

| ID | Feature | Requirement | Implemented in |
|----|---------|-------------|----------------|
| FR-1 | Site safety monitoring | Accept a site photo (JPG/PNG); check PPE (helmet, high-vis vest, steel-toe boots, harness); list hazards with severity and remedies; give a 0-100 safety score | Tab 1 |
| FR-2 | Crack detection & severity | Accept a concrete/wall photo; classify defect (Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling); estimate width (mm); give root causes, repairs, urgency | Tab 2 |
| FR-3 | Real estate valuation | Take structure type, built-up area, location tier and completion %; output budget, capex, asset value in INR (Lakhs/Crores) | Tab 3 |
| FR-4 | Project planning | Estimate steel and cement quantities; show milestone progress. *Planned: dated task schedule and Gantt visualisation* | Tab 3 |
| FR-5 | Daily site assistance & weather advisory | Weather selector (High Wind, Heavy Rain, Extreme Heat, Normal) shows safety alerts | Tab 4 |
| FR-6 | Construction knowledge assistance | Multi-turn chatbot for engineering and safety questions. *Planned: downloadable generated documents (e.g. toolbox-talk sheets)* | Tab 4 |
| FR-7 | API key handling | Secure key entry; automatic demonstration mode without a key | Sidebar |
| FR-8 | Report export | Download safety and crack results as JSON | Tabs 1, 2 |

## 4. Non-Functional Requirements

| ID | Requirement | How it is met |
|----|-------------|---------------|
| NFR-1 | **Frontend stability, no runtime crashes** | Each tab has exception handling; image and API failures show messages, not crashes |
| NFR-2 | **Structured, machine-readable AI output** | Prompts demand strict JSON; the app parses it and fills defaults for missing fields |
| NFR-3 | **Scalability and modularity** | One function per tab, separate helpers for AI calls, demo data and formatting |
| NFR-4 | **Maintainability and easy extension** | Rates, advisories and prompts are kept in dictionaries and constants at the top of the file |
| NFR-5 | **Deployability** | No database; runs on Streamlit Community Cloud with 3 dependencies |
| NFR-6 | **Security** | API key held only in session memory or Streamlit secrets; never written to code |

## 5. Input and Output Formats

### 5.1 Safety audit
**Input:** image (JPG/PNG, resized to max 1600 px).
**Output (JSON):**
```json
{
  "safety_score": 0,
  "overall_status": "Compliant | Needs Improvement | Non-Compliant | Critical Risk",
  "workers_detected": 0,
  "summary": "text",
  "ppe_detection": [{"item": "Safety Helmet", "status": "Compliant", "note": "text"}],
  "hazards": [{"hazard": "text", "severity": "Low|Medium|High|Critical",
               "standard_reference": "OSHA / IS code", "remedy": "text"}]
}
```

### 5.2 Crack diagnostics
**Input:** image of concrete or wall surface.
**Output (JSON):**
```json
{
  "defect_type": "Hairline | Settlement | Structural Shear | Thermal Expansion | Spalling | No Defect",
  "confidence_pct": 0,
  "estimated_crack_width_mm": 0.0,
  "crack_pattern": "text",
  "severity": "Low|Medium|High|Critical",
  "structural_risk": "Cosmetic | Serviceability | Structural | Life-Safety",
  "urgency": "Low|Medium|High|Immediate",
  "root_causes": ["text"],
  "recommended_repairs": [{"method": "Epoxy injection", "details": "text"}],
  "monitoring_plan": "text",
  "summary": "text"
}
```

### 5.3 Planning and valuation
**Input:** structure type (list), built-up area (sq ft, 100 to 5,000,000), location tier (Tier 1/2/3), completion (0-100 %).
**Output:** total budget, capex incurred, current asset value, value on completion (INR, Lakhs/Crores); steel (tonnes) and cement (bags) required and remaining; current milestone phase.

### 5.4 Weather advisory
**Input:** one of High Wind, Heavy Rain, Extreme Heat, Normal.
**Output:** risk level and a list of alerts (title and instruction).

### 5.5 Chat assistant
**Input:** free-text question plus the selected weather as context.
**Output:** text answer in Markdown; conversation history kept for the session.

## 6. Assumptions and Limits
- Cost and valuation rates are indicative and must be calibrated with local quotations.
- AI outputs are advisory; a licensed structural engineer or certified safety officer must verify them.
- No data is stored after the session ends.
