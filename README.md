
# Multimodal Construction Intelligence Platform

A Streamlit-based construction decision-support application developed for Skill Wallet Capstone Project 1.

## Features

### 1. Site Safety & PPE Audit
- Upload construction site photographs.
- Display PPE compliance and hazard reports.
- Show safety scores and corrective recommendations.
- Export reports in JSON format.

### 2. Crack Diagnostics
- Upload concrete or wall photographs.
- Display illustrative crack classifications.
- Show severity, structural risks and repair recommendations.
- Export reports in JSON format.

### 3. Planning & Real Estate Valuation
- Estimate construction budgets in INR.
- Calculate capital expenditure.
- Estimate steel and cement requirements.
- Calculate property valuation.
- Display construction milestones.

### 4. Daily Site Assistant
- Weather-based safety advisories.
- Construction knowledge assistance.
- Rule-based demonstration responses.

## Technology Stack
- Python
- Streamlit
- Google GenAI SDK (optional integration)
- Pillow

## Installation

Clone the repository:

```bash
git clone https://github.com/RISHI-ad/Multimodal-Construction-Intelligence-Platform.git
cd Multimodal-Construction-Intelligence-Platform
```

Create a virtual environment:

```bash
py -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the application:

```bash
python -m streamlit run app.py
```

## Demonstration Mode

The application supports demonstration mode without a Gemini API key.

Safety and crack diagnostic outputs in this mode are illustrative sample results, not genuine image-based AI predictions.

The planning and valuation module uses rule-based calculations.

## Project Documentation

See [REQUIREMENTS.md](REQUIREMENTS.md) for functional requirements, non-functional requirements and input/output specifications.

## Disclaimer

This application is an educational prototype. Construction estimates and safety recommendations must be verified by qualified professionals.
