"""
Multimodal Construction Intelligence Platform
Skill Wallet Capstone Project 1

Single-file Streamlit app. No database. Deploys on Streamlit Community Cloud.
Gemini key is entered in the sidebar (or via st.secrets["GEMINI_API_KEY"]);
without a key the app runs in Demonstration Mode.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import urllib.parse
from datetime import datetime

import streamlit as st
from PIL import Image

try:
    from google import genai
    from google.genai import types as genai_types

    GENAI_AVAILABLE = True
except Exception:  # SDK missing -> demo mode only
    GENAI_AVAILABLE = False

# ----------------------------------------------------------------------------
# Page config & styling
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Construction Intelligence Platform",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
.block-container {padding-top: 1.5rem; max-width: 1250px;}
.hero {
    background: linear-gradient(120deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    padding: 1.6rem 2rem; border-radius: 16px; color: #fff; margin-bottom: 1.2rem;
}
.hero h1 {margin: 0; font-size: 1.9rem; color: #fff;}
.hero p {margin: .3rem 0 0 0; color: #cfe3ee; font-size: .95rem;}
.card {
    background: rgba(127,127,127,.08); border: 1px solid rgba(127,127,127,.25);
    border-radius: 14px; padding: 1rem 1.2rem; height: 100%;
}
.card .label {font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; opacity: .7;}
.card .value {font-size: 1.7rem; font-weight: 700; margin-top: .15rem;}
.card .sub {font-size: .8rem; opacity: .7; margin-top: .1rem;}
.pill {
    display: inline-block; padding: .2rem .75rem; border-radius: 999px;
    font-size: .78rem; font-weight: 600; color: #fff; white-space: nowrap;
}
.pill.green {background: #1e9e5a;} .pill.amber {background: #d98e04;}
.pill.orange {background: #e0661a;} .pill.red {background: #d93030;}
.pill.dark {background: #7a1022;}  .pill.blue {background: #2b6cb0;}
.pill.grey {background: #6b7280;}
.hazard {
    border-left: 5px solid #888; background: rgba(127,127,127,.07);
    border-radius: 8px; padding: .7rem 1rem; margin-bottom: .6rem;
}
.hazard.Low {border-color:#1e9e5a;} .hazard.Medium {border-color:#d98e04;}
.hazard.High {border-color:#e0661a;} .hazard.Critical {border-color:#7a1022;}
.alert {border-radius: 12px; padding: .9rem 1.1rem; margin-bottom: .6rem;
        border: 1px solid rgba(127,127,127,.3); background: rgba(127,127,127,.07);}
.alert b {display:block; margin-bottom:.2rem;}
.demo-banner {
    background: rgba(217,142,4,.15); border: 1px solid #d98e04; color: inherit;
    padding: .6rem 1rem; border-radius: 10px; margin-bottom: 1rem; font-size: .9rem;
}
.footer {text-align:center; opacity:.55; font-size:.8rem; margin-top:2rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Constants & reference data
# ----------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_IMAGE_SIDE = 1600

SEVERITY_COLOR = {"Low": "green", "Medium": "amber", "High": "orange", "Critical": "dark"}
URGENCY_COLOR = {"Low": "green", "Medium": "amber", "High": "orange", "Immediate": "dark", "Critical": "dark"}

PPE_ITEMS = ["Safety Helmet", "High-Vis Vest", "Steel-Toe Boots", "Safety Harness"]

SAFETY_PROMPT = """You are a certified construction safety officer (OSHA 1926 and Indian IS 456:2000 /
BOCW Act aware). Analyse the attached construction site photograph.

Assess worker PPE compliance for: safety helmets, high-visibility vests, steel-toe boots and
safety harnesses (harness only required for work at height >1.8 m). Identify site hazards
(open edges, unguarded excavations, poor scaffolding, exposed rebar, housekeeping, electrical
risks, formwork/shuttering issues, etc.).

Respond with ONLY valid JSON (no markdown) in exactly this schema:
{
  "safety_score": <integer 0-100>,
  "overall_status": "<Compliant | Needs Improvement | Non-Compliant | Critical Risk>",
  "workers_detected": <integer>,
  "summary": "<2-3 sentence summary>",
  "ppe_detection": [
    {"item": "Safety Helmet", "status": "<Compliant | Non-Compliant | Not Applicable | Not Visible>", "note": "<short>"},
    {"item": "High-Vis Vest", "status": "...", "note": "..."},
    {"item": "Steel-Toe Boots", "status": "...", "note": "..."},
    {"item": "Safety Harness", "status": "...", "note": "..."}
  ],
  "hazards": [
    {"hazard": "<description>", "severity": "<Low | Medium | High | Critical>",
     "standard_reference": "<e.g. OSHA 1926.501 / IS 456:2000 cl. ...>",
     "remedy": "<specific corrective action>"}
  ]
}
If the image is not a construction site, set safety_score to 0, overall_status to
"Not Assessable" and explain in summary."""

CRACK_PROMPT = """You are a senior structural engineer specialising in forensic diagnostics of
concrete and masonry (IS 456:2000, IS 15988, IS 13935, ACI 224R). Analyse the attached image of a
concrete/wall surface.

Classify the dominant defect as exactly one of: Hairline, Settlement, Structural Shear,
Thermal Expansion, Spalling (use "No Defect" if none visible). Estimate crack width in mm using
visible scale cues, and state your confidence honestly.

Respond with ONLY valid JSON (no markdown) in exactly this schema:
{
  "defect_type": "<Hairline | Settlement | Structural Shear | Thermal Expansion | Spalling | No Defect>",
  "confidence_pct": <integer 0-100>,
  "estimated_crack_width_mm": <number>,
  "crack_pattern": "<e.g. vertical, diagonal/stair-step, map cracking, horizontal>",
  "severity": "<Low | Medium | High | Critical>",
  "structural_risk": "<Cosmetic | Serviceability | Structural | Life-Safety>",
  "urgency": "<Low | Medium | High | Immediate>",
  "root_causes": ["<cause>", "..."],
  "recommended_repairs": [
    {"method": "<e.g. Epoxy injection>", "details": "<procedure/material/spec>"}
  ],
  "monitoring_plan": "<crack gauges / tell-tales / re-inspection interval>",
  "summary": "<2-3 sentence engineering assessment>"
}
Include a note in summary that a physical inspection by a licensed structural engineer is
required before any structural intervention."""

CHAT_SYSTEM = """You are 'SiteMate', an expert construction engineering assistant for Indian
construction sites. You know IS codes (IS 456, IS 800, IS 875, IS 1893, IS 2502), NBC 2016,
OSHA 1926, BOCW Act, concrete technology, formwork, rebar detailing, scheduling, quantity
estimation and site safety. Give practical, concise, numbered/bulleted guidance with units.
Flag safety-critical points clearly. Say when a licensed engineer must verify a decision.
Current site weather context: {weather}."""

WEATHER_ADVISORIES = {
    "High Wind": {
        "icon": "💨", "pill": "red", "risk": "High",
        "alerts": [
            ("Suspend crane & hoisting operations", "Stop tower/mobile crane lifts when sustained wind exceeds ~36 km/h (20 knots) or per manufacturer limit; lower and secure booms, set slewing brakes to free-weathervane."),
            ("Secure loose materials", "Tie down sheeting, formwork panels, scaffold boards, bricks pallets and bagged cement. Remove debris from edges."),
            ("Scaffold & hoarding check", "Re-inspect ties, bracing and debris netting. Evacuate work at height above 2 m on open faces."),
            ("Exclusion zones", "Barricade areas beneath tall structures; brief workers to shelter in designated areas."),
        ],
    },
    "Heavy Rain": {
        "icon": "🌧️", "pill": "blue", "risk": "High",
        "alerts": [
            ("Electrical hazard mitigation", "Isolate temporary power at the main board; use ELCB/RCCB (30 mA); keep cable joints off the ground and inside IP65 enclosures. No wet-hand tool use."),
            ("Excavation & trench stability", "Stop work in trenches; check shoring and dewater. Keep spoil at least 1 m from edge; watch for slope failure."),
            ("Concrete placement", "Do not pour in rain. Cover fresh concrete with tarpaulin, protect cut joints, and avoid water increasing w/c ratio."),
            ("Slip & access control", "Lay anti-skid planks on ramps; stop work on bamboo/metal scaffolds when wet and slippery."),
        ],
    },
    "Extreme Heat": {
        "icon": "🔥", "pill": "orange", "risk": "High",
        "alerts": [
            ("Concrete curing protocol", "Pour early morning/evening; keep concrete temp below 35 °C (chilled water/ice, shaded aggregates). Start wet curing immediately, use wet hessian + curing compound, cure min. 7 days (10 for blended cements)."),
            ("Heat-stress management", "Mandatory hydration (ORS, 250 ml every 20 min), shaded rest areas, work/rest cycles. Stop heavy work 12:00–15:30 when heat index is extreme."),
            ("Plastic shrinkage cracking", "Use fog misting or evaporation retarder on slabs; windbreaks to reduce surface evaporation."),
            ("Steel & formwork", "Hot rebar/metal surfaces can burn - provide gloves; wet formwork before pour."),
        ],
    },
    "Normal": {
        "icon": "☀️", "pill": "green", "risk": "Low",
        "alerts": [
            ("Routine toolbox talk", "Run a 10-minute daily toolbox talk covering today's tasks, hazards and emergency assembly point."),
            ("Pre-task inspection", "Check scaffolds, lifting tackle, electrical panels and PPE condition before start of shift."),
            ("Housekeeping", "Maintain clear walkways, stack materials safely, and remove nail-studded timber."),
        ],
    },
}

STRUCTURE_TYPES = {
    # cost INR/sqft (Tier-2 baseline), steel kg/sqft, cement bags/sqft, market-value premium
    "Residential Apartment (RCC)": {"cost": 2000, "steel": 4.0, "cement": 0.42, "premium": 1.00},
    "Independent House / Villa": {"cost": 2400, "steel": 3.6, "cement": 0.45, "premium": 1.15},
    "Commercial Building": {"cost": 2800, "steel": 4.8, "cement": 0.45, "premium": 1.35},
    "High-Rise Tower (G+15+)": {"cost": 3400, "steel": 6.0, "cement": 0.50, "premium": 1.25},
    "Industrial Shed (PEB)": {"cost": 1700, "steel": 7.5, "cement": 0.25, "premium": 0.70},
    "Institutional (School/Hospital)": {"cost": 3000, "steel": 4.5, "cement": 0.45, "premium": 1.10},
}
LOCATION_TIERS = {
    "Tier 1 (Mumbai, Delhi NCR, Bengaluru, Hyderabad, Chennai)": {"cost_mult": 1.30, "market": 11000},
    "Tier 2 (Pune, Bhopal, Indore, Jaipur, Lucknow)": {"cost_mult": 1.00, "market": 6000},
    "Tier 3 (Smaller cities & towns)": {"cost_mult": 0.82, "market": 3500},
}
MILESTONES = [
    (0, 10, "Site prep & excavation"), (10, 25, "Foundation & plinth"),
    (25, 55, "Superstructure (columns, slabs)"), (55, 70, "Masonry & plastering"),
    (70, 90, "MEP & finishing"), (90, 100, "Snagging & handover"),
]

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def fmt_inr(value: float) -> str:
    """Format INR in Lakhs / Crores."""
    if value >= 1e7:
        return f"₹ {value / 1e7:,.2f} Cr"
    if value >= 1e5:
        return f"₹ {value / 1e5:,.2f} Lakhs"
    return f"₹ {value:,.0f}"


def esc(x) -> str:
    return html.escape(str(x))


def metric_card(label: str, value: str, sub: str = "") -> str:
    return (f'<div class="card"><div class="label">{esc(label)}</div>'
            f'<div class="value">{esc(value)}</div><div class="sub">{esc(sub)}</div></div>')


def pill(text: str, color: str) -> str:
    return f'<span class="pill {color}">{esc(text)}</span>'


def status_color(status: str) -> str:
    s = str(status).lower()
    if s in ("compliant", "pass"):
        return "green"
    if "needs" in s:
        return "amber"
    if "non" in s or "critical" in s:
        return "red"
    return "grey"


def get_api_key() -> str:
    key = st.session_state.get("api_key", "").strip()
    if key:
        return key
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        return ""


def live_mode() -> bool:
    return GENAI_AVAILABLE and bool(get_api_key())


def prepare_image(uploaded) -> tuple[Image.Image, bytes]:
    img = Image.open(uploaded)
    img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return img, buf.getvalue()


def extract_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def call_gemini_vision(prompt: str, img: Image.Image) -> dict:
    client = genai.Client(api_key=get_api_key())
    resp = client.models.generate_content(
        model=st.session_state.get("model_name", DEFAULT_MODEL),
        contents=[prompt, img],
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0.2
        ),
    )
    return extract_json(resp.text)


def seed_from(data: bytes, mod: int) -> int:
    return int(hashlib.md5(data).hexdigest(), 16) % mod


# ----------------------------------------------------------------------------
# Demo-mode generators (deterministic by image hash)
# ----------------------------------------------------------------------------
def demo_safety(data: bytes) -> dict:
    s = seed_from(data, 4)
    scores = [86, 64, 47, 28]
    status = ["Compliant", "Needs Improvement", "Non-Compliant", "Critical Risk"][s]
    ppe_pool = [
        ("Compliant", "Helmets worn by all visible workers."),
        ("Non-Compliant", "One or more workers without helmet."),
    ]
    ppe = [
        {"item": "Safety Helmet", "status": "Compliant" if s < 2 else "Non-Compliant",
         "note": ppe_pool[0][1] if s < 2 else ppe_pool[1][1]},
        {"item": "High-Vis Vest", "status": "Compliant" if s < 3 else "Non-Compliant",
         "note": "Reflective vests visible." if s < 3 else "Workers lack reflective vests."},
        {"item": "Steel-Toe Boots", "status": "Compliant" if s == 0 else "Non-Compliant",
         "note": "Safety footwear observed." if s == 0 else "Sandals/open footwear observed."},
        {"item": "Safety Harness", "status": "Not Applicable" if s == 0 else "Non-Compliant",
         "note": "No work at height visible." if s == 0 else "Work at height without harness/anchorage."},
    ]
    hazards_all = [
        {"hazard": "Exposed reinforcement bars at slab edge", "severity": "Medium",
         "standard_reference": "OSHA 1926.701(b)",
         "remedy": "Fit mushroom caps/rebar protectors on all projecting bars."},
        {"hazard": "Unprotected floor edge / missing guardrails", "severity": "Critical",
         "standard_reference": "OSHA 1926.502 / BOCW Rules",
         "remedy": "Install 1 m top rail, 0.5 m mid rail and toe-board; use safety nets."},
        {"hazard": "Poor housekeeping - debris and loose material on walkways", "severity": "Low",
         "standard_reference": "OSHA 1926.25",
         "remedy": "Assign housekeeping crew; stack materials in designated areas."},
        {"hazard": "Scaffold lacking proper bracing and access ladder", "severity": "High",
         "standard_reference": "OSHA 1926.451 / IS 4014",
         "remedy": "Add diagonal bracing, base plates, and tagged inspection before use."},
        {"hazard": "Temporary electrical cables on wet ground", "severity": "High",
         "standard_reference": "OSHA 1926.405",
         "remedy": "Elevate cables, use ELCB/RCCB and IP-rated connectors."},
    ]
    return {
        "safety_score": scores[s], "overall_status": status,
        "workers_detected": 3 + s,
        "summary": "DEMO OUTPUT: Illustrative audit generated without a Gemini key. "
                   "Add an API key for a real analysis of your photo.",
        "ppe_detection": ppe,
        "hazards": hazards_all[: 2 + s] if s else hazards_all[:1] + hazards_all[2:3],
    }


def demo_crack(data: bytes) -> dict:
    cases = [
        ("Hairline", 0.2, "Low", "Cosmetic", "Low",
         ["Plastic shrinkage during curing", "Minor thermal cycling"],
         [("Surface sealing", "Apply elastomeric crack filler / polymer-modified cement slurry after cleaning.")]),
        ("Settlement", 3.5, "High", "Structural", "High",
         ["Differential foundation settlement", "Poor soil bearing / water-table fluctuation"],
         [("Epoxy injection", "Low-viscosity epoxy (IS 15988 compatible) by pressure injection after stabilising movement."),
          ("Underpinning review", "Geotechnical investigation; consider micro-piling or underpinning.")]),
        ("Structural Shear", 5.0, "Critical", "Life-Safety", "Immediate",
         ["Inadequate shear reinforcement / stirrup spacing", "Overloading or seismic demand"],
         [("Propping & evacuation", "Install temporary shoring and restrict occupancy immediately."),
          ("Structural re-grouting & jacketing", "Non-shrink cementitious grout plus RC/steel jacketing designed by a structural engineer.")]),
        ("Thermal Expansion", 1.0, "Medium", "Serviceability", "Medium",
         ["Absence of expansion joints", "Large diurnal temperature variation"],
         [("Expansion joint retrofit", "Saw-cut and fill with polysulphide sealant over backer rod."),
          ("Reflective coating", "Apply heat-reflective waterproof coating to reduce thermal swings.")]),
        ("Spalling", 2.0, "High", "Serviceability", "High",
         ["Rebar corrosion from chloride/carbonation", "Insufficient concrete cover"],
         [("Patch repair", "Remove loose concrete, clean/passivate rebar, apply polymer-modified repair mortar."),
          ("Corrosion protection", "Anti-corrosive coating and migrating corrosion inhibitor; consider cathodic protection.")]),
    ]
    c = cases[seed_from(data, len(cases))]
    return {
        "defect_type": c[0], "confidence_pct": 78, "estimated_crack_width_mm": c[1],
        "crack_pattern": "Diagonal / stair-step" if c[0] in ("Settlement", "Structural Shear") else "Irregular / map pattern",
        "severity": c[2], "structural_risk": c[3], "urgency": c[4],
        "root_causes": c[5],
        "recommended_repairs": [{"method": m, "details": d} for m, d in c[6]],
        "monitoring_plan": "Install tell-tale/crack gauges; record width weekly for 8 weeks, then monthly.",
        "summary": "DEMO OUTPUT: Illustrative diagnosis without a Gemini key. A physical inspection by a "
                   "licensed structural engineer is required before any structural intervention.",
    }


def demo_chat(question: str, weather: str) -> str:
    q = question.lower()
    rules = [
        (("m20", "mix", "concrete grade", "mix design"),
         "**Nominal mix M20 (IS 456):** 1 : 1.5 : 3 (cement : sand : 20 mm aggregate), w/c ≈ 0.50, "
         "cement ≈ 8 bags (50 kg) per m³ (≈ 320-360 kg/m³). Use design mix for M25 and above."),
        (("curing", "cure"),
         "**Curing (IS 456 cl. 13.5):** begin as soon as concrete is hard enough not to be marred; "
         "keep moist min. **7 days** (OPC) or **10 days** for blended cement / hot-dry weather. "
         "Use ponding, wet hessian or curing compound."),
        (("cover", "clear cover"),
         "**Nominal cover (IS 456 Table 16):** Mild 20 mm, Moderate 30 mm, Severe 45 mm, Very severe 50 mm, "
         "Extreme 75 mm. Footings: min 50 mm."),
        (("steel", "rebar", "reinforcement"),
         "**Quick estimate:** ~3.5-4.5 kg/sqft for low-rise RCC; 6+ kg/sqft for high-rise. "
         "Use Fe500/Fe500D with proper lap lengths (typically 40-50 Φ in tension)."),
        (("scaffold",),
         "**Scaffold safety:** base plates & sole boards, bracing, full platform boarding, guardrails at 1 m, "
         "toe-boards, tagged inspection before each shift, max load per design, no work in high wind."),
        (("harness", "height", "fall"),
         "**Work at height:** fall protection above 1.8 m. Use full-body harness with double lanyard, "
         "certified anchorage (≥ 15 kN), safety nets, and rescue plan."),
        (("crack",),
         "Classify first: hairline (<0.3 mm), settlement (diagonal, widening), shear (45° near supports), "
         "thermal (regular joints), spalling (rebar corrosion). Use tab 2 to analyse a photo."),
        (("slump",),
         "**Slump guidance:** slabs/beams 50-100 mm, columns 75-100 mm, pumped concrete 100-150 mm. "
         "Never add water at site - use superplasticiser."),
    ]
    for keys, ans in rules:
        if any(k in q for k in keys):
            return ans + f"\n\n_(Demo mode · weather: {weather})_"
    return ("I'm running in **demonstration mode** (no Gemini key), so I answer a limited set of topics: "
            "concrete mixes, curing, cover, rebar estimates, scaffolds, work at height, cracks and slump.\n\n"
            "Add your API key in the sidebar for full multi-turn engineering support.")


def gemini_chat(history: list[dict], weather: str) -> str:
    client = genai.Client(api_key=get_api_key())
    contents = [
        genai_types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[genai_types.Part(text=m["content"])],
        )
        for m in history
    ]
    resp = client.models.generate_content(
        model=st.session_state.get("model_name", DEFAULT_MODEL),
        contents=contents,
        config=genai_types.GenerateContentConfig(
            system_instruction=CHAT_SYSTEM.format(weather=weather), temperature=0.4
        ),
    )
    return resp.text or "(No response returned.)"


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
def render_sidebar() -> None:
    st.session_state.setdefault("api_key", "")
    st.session_state.setdefault("model_name", DEFAULT_MODEL)
    with st.sidebar:
        st.markdown("## 🏗️ Control Panel")
        st.text_input(
            "Google Gemini API Key", type="password", key="api_key",
            placeholder="AIza...", help="Stored only in this session's memory. Never logged or persisted.",
        )
        st.text_input("Model", key="model_name", help="e.g. gemini-2.5-flash")
        if live_mode():
            st.success("🟢 Live Gemini mode")
        else:
            reason = "" if GENAI_AVAILABLE else " (google-genai not installed)"
            st.warning(f"🟡 Demonstration mode{reason}")
            st.caption("Get a free key at aistudio.google.com/apikey")
        st.markdown("---")
        st.markdown("### 🧭 Features")
        st.markdown(
            "- 🦺 **Site Safety & PPE Audit**\n- 🧱 **Crack Diagnostics**\n"
            "- 💰 **Planning & Valuation**\n- 🌦️ **Weather Advisory & Assistant**"
        )
        with st.expander("🏛️ Architecture overview"):
            st.markdown(
                "```\nStreamlit UI (4 tabs)\n   │\n   ├─ Vision prompts ─► Gemini (JSON mode)\n"
                "   │        └─► schema normalisation\n   ├─ Rule engine: cost / valuation\n"
                "   ├─ Weather rule-base\n   ├─ Chat ─► Gemini multi-turn\n"
                "   └─ Pollinations.ai image URL\n\n"
                "State: st.session_state only\nDB: none\n```"
            )
        st.caption("Guidance is advisory. Verify with licensed engineers / safety officers.")


# ----------------------------------------------------------------------------
# Tab 1 - Safety
# ----------------------------------------------------------------------------
def render_safety_tab() -> None:
    st.subheader("🦺 Site Safety & PPE Audit")
    st.caption("Upload a site photograph for an OSHA / IS 456 aligned compliance audit.")
    up = st.file_uploader("Construction site photo", type=["jpg", "jpeg", "png"], key="safety_up")
    if not up:
        st.info("Upload a JPG/PNG to begin.")
        return
    try:
        img, raw = prepare_image(up)
    except Exception as e:
        st.error(f"Could not read image: {e}")
        return

    left, right = st.columns([1, 1.4], gap="large")
    with left:
        st.image(img, caption="Uploaded photo", use_container_width=True)
        run = st.button("🔍 Run Safety Audit", type="primary", use_container_width=True)

    if run:
        with st.spinner("Analysing site conditions..."):
            try:
                result = call_gemini_vision(SAFETY_PROMPT, img) if live_mode() else demo_safety(raw)
                st.session_state["safety_result"] = result
                st.session_state["safety_demo"] = not live_mode()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                if GENAI_AVAILABLE and get_api_key():
                    st.info("Showing demonstration output instead.")
                    st.session_state["safety_result"] = demo_safety(raw)
                    st.session_state["safety_demo"] = True

    result = st.session_state.get("safety_result")
    if not result:
        return
    with right:
        if st.session_state.get("safety_demo"):
            st.markdown('<div class="demo-banner">⚠️ Demonstration data - not a real analysis.</div>', unsafe_allow_html=True)
        try:
            score = int(max(0, min(100, float(result.get("safety_score", 0)))))
        except (TypeError, ValueError):
            score = 0
        status = result.get("overall_status", "Unknown")
        hazards = result.get("hazards", []) or []
        crit = sum(1 for h in hazards if h.get("severity") in ("High", "Critical"))
        c1, c2, c3 = st.columns(3)
        c1.markdown(metric_card("Safety Score", f"{score}/100", "OSHA / IS aligned"), unsafe_allow_html=True)
        c2.markdown(metric_card("Workers Detected", str(result.get("workers_detected", "-")), "in frame"), unsafe_allow_html=True)
        c3.markdown(metric_card("High/Critical Hazards", str(crit), f"{len(hazards)} total"), unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**Overall status:** {pill(status, status_color(status))}", unsafe_allow_html=True)
        st.progress(score / 100)
        if result.get("summary"):
            st.write(result["summary"])

    st.markdown("#### ✅ PPE Detection Checklist")
    ppe = result.get("ppe_detection", []) or []
    cols = st.columns(max(1, min(4, len(ppe))))
    for i, p in enumerate(ppe):
        stt = p.get("status", "Unknown")
        with cols[i % len(cols)]:
            st.markdown(
                f'<div class="card"><div class="label">{esc(p.get("item", "Item"))}</div>'
                f'<div style="margin:.4rem 0">{pill(stt, status_color(stt))}</div>'
                f'<div class="sub">{esc(p.get("note", ""))}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("#### ⚠️ Identified Hazards & Remedies")
    if not hazards:
        st.success("No hazards identified.")
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    for h in sorted(hazards, key=lambda x: order.get(x.get("severity"), 9)):
        sev = h.get("severity", "Low")
        st.markdown(
            f'<div class="hazard {esc(sev)}"><b>{esc(h.get("hazard", ""))}</b> '
            f'{pill(sev, SEVERITY_COLOR.get(sev, "grey"))}<br>'
            f'<span class="sub">📖 {esc(h.get("standard_reference", "-"))}</span><br>'
            f'🛠️ <b>Remedy:</b> {esc(h.get("remedy", ""))}</div>',
            unsafe_allow_html=True,
        )
    report = {"generated_at": datetime.now().isoformat(timespec="seconds"),
              "module": "site_safety_ppe_audit", "mode": "demo" if st.session_state.get("safety_demo") else "live",
              "report": result}
    st.download_button("⬇️ Download JSON report", json.dumps(report, indent=2),
                       file_name="safety_audit_report.json", mime="application/json")


# ----------------------------------------------------------------------------
# Tab 2 - Cracks
# ----------------------------------------------------------------------------
def render_crack_tab() -> None:
    st.subheader("🧱 Crack Diagnostics & Structural Integrity")
    st.caption("Classify defects, estimate crack width, and get repair recommendations.")
    up = st.file_uploader("Concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crack_up")
    if not up:
        st.info("Upload a close-up photo (include a coin/ruler for scale if possible).")
        return
    try:
        img, raw = prepare_image(up)
    except Exception as e:
        st.error(f"Could not read image: {e}")
        return

    left, right = st.columns([1, 1.4], gap="large")
    with left:
        st.image(img, caption="Uploaded surface", use_container_width=True)
        run = st.button("🔬 Diagnose Defect", type="primary", use_container_width=True)
    if run:
        with st.spinner("Running structural diagnostics..."):
            try:
                result = call_gemini_vision(CRACK_PROMPT, img) if live_mode() else demo_crack(raw)
                st.session_state["crack_result"] = result
                st.session_state["crack_demo"] = not live_mode()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                if GENAI_AVAILABLE and get_api_key():
                    st.session_state["crack_result"] = demo_crack(raw)
                    st.session_state["crack_demo"] = True

    r = st.session_state.get("crack_result")
    if not r:
        return
    with right:
        if st.session_state.get("crack_demo"):
            st.markdown('<div class="demo-banner">⚠️ Demonstration data - not a real analysis.</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.markdown(metric_card("Defect Type", str(r.get("defect_type", "-")), f"Confidence {r.get('confidence_pct', '-')}%"), unsafe_allow_html=True)
        c2.markdown(metric_card("Crack Width", f"{r.get('estimated_crack_width_mm', '-')} mm", str(r.get("crack_pattern", ""))), unsafe_allow_html=True)
        c3.markdown(metric_card("Structural Risk", str(r.get("structural_risk", "-")), "classification"), unsafe_allow_html=True)
        st.write("")
        sev, urg = r.get("severity", "Low"), r.get("urgency", "Low")
        st.markdown(
            f"**Severity:** {pill(sev, SEVERITY_COLOR.get(sev, 'grey'))} &nbsp; "
            f"**Urgency:** {pill(urg, URGENCY_COLOR.get(urg, 'grey'))}",
            unsafe_allow_html=True,
        )
        if r.get("summary"):
            st.write(r["summary"])
        if urg in ("Immediate", "Critical") or r.get("structural_risk") == "Life-Safety":
            st.error("🚨 Potential life-safety issue: restrict access and call a licensed structural engineer immediately.")

    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### 🔎 Probable Root Causes")
        for cause in r.get("root_causes", []) or []:
            st.markdown(f"- {cause}")
        st.markdown("#### 📈 Monitoring Plan")
        st.write(r.get("monitoring_plan", "-"))
    with b:
        st.markdown("#### 🛠️ Recommended Engineering Repairs")
        for rep in r.get("recommended_repairs", []) or []:
            if isinstance(rep, dict):
                st.markdown(f"**{rep.get('method', 'Repair')}** - {rep.get('details', '')}")
            else:
                st.markdown(f"- {rep}")
    report = {"generated_at": datetime.now().isoformat(timespec="seconds"),
              "module": "crack_diagnostics", "mode": "demo" if st.session_state.get("crack_demo") else "live",
              "report": r}
    st.download_button("⬇️ Download JSON report", json.dumps(report, indent=2),
                       file_name="crack_diagnostic_report.json", mime="application/json")


# ----------------------------------------------------------------------------
# Tab 3 - Planning & valuation
# ----------------------------------------------------------------------------
def render_planning_tab() -> None:
    st.subheader("💰 Planning & Real Estate Valuation")
    c1, c2 = st.columns(2)
    with c1:
        stype = st.selectbox("Structure type", list(STRUCTURE_TYPES))
        tier = st.selectbox("Location tier", list(LOCATION_TIERS))
    with c2:
        sqft = st.number_input("Built-up area (sq ft)", min_value=100, max_value=5_000_000, value=2500, step=100)
        pct = st.slider("Completion (%)", 0, 100, 40)

    s, t = STRUCTURE_TYPES[stype], LOCATION_TIERS[tier]
    construction = sqft * s["cost"] * t["cost_mult"]
    budget = construction * 1.10  # +10% design, approvals & contingency
    capex = budget * pct / 100
    full_value = sqft * t["market"] * s["premium"]
    discount = 1.0 if pct == 100 else 0.90  # under-construction discount
    asset_value = full_value * (pct / 100) * discount
    steel_total = sqft * s["steel"] / 1000  # tonnes
    cement_total = sqft * s["cement"]

    st.write("")
    m = st.columns(4)
    m[0].markdown(metric_card("Total Project Budget", fmt_inr(budget), "incl. 10% soft costs"), unsafe_allow_html=True)
    m[1].markdown(metric_card("Capex Incurred", fmt_inr(capex), f"{pct}% of budget"), unsafe_allow_html=True)
    m[2].markdown(metric_card("Current Asset Valuation", fmt_inr(asset_value), "market-based estimate"), unsafe_allow_html=True)
    m[3].markdown(metric_card("Value on Completion", fmt_inr(full_value), "projected"), unsafe_allow_html=True)
    st.write("")
    m = st.columns(4)
    m[0].markdown(metric_card("Steel Required", f"{steel_total:,.1f} t", f"{s['steel']} kg/sqft"), unsafe_allow_html=True)
    m[1].markdown(metric_card("Steel Remaining", f"{steel_total * (1 - pct / 100):,.1f} t", "to be procured"), unsafe_allow_html=True)
    m[2].markdown(metric_card("Cement Required", f"{cement_total:,.0f} bags", f"{cement_total * 50 / 1000:,.1f} t (50 kg bags)"), unsafe_allow_html=True)
    m[3].markdown(metric_card("Cement Remaining", f"{cement_total * (1 - pct / 100):,.0f} bags", "to be procured"), unsafe_allow_html=True)

    st.markdown("#### 🚩 Milestone Progress")
    st.progress(pct / 100, text=f"{pct}% complete")
    current = next((n for lo, hi, n in MILESTONES if lo <= pct < hi), "Snagging & handover")
    cols = st.columns(len(MILESTONES))
    for col, (lo, hi, name) in zip(cols, MILESTONES):
        done = pct >= hi
        active = lo <= pct < hi
        icon = "✅" if done else ("🔨" if active else "⏳")
        col.markdown(f"{icon} **{name}**  \n<span class='sub'>{lo}-{hi}%</span>", unsafe_allow_html=True)
    st.caption(f"Current phase: **{current}**. Estimates use indicative Indian market rates (₹/sq ft) and "
               "must be calibrated with local quotations; valuation excludes land cost.")

    st.markdown("#### 🎨 Conceptual 3D Architectural Rendering")
    style = st.selectbox("Architectural style", ["Modern minimalist", "Contemporary Indian", "Glass facade", "Sustainable green building", "Neo-classical"])
    prompt = (f"Photorealistic 3D architectural rendering of a {stype.split('(')[0].strip().lower()}, "
              f"{style.lower()} style, approx {sqft:,} sq ft, {tier.split('(')[0].strip()} Indian city, "
              f"golden hour, landscaped surroundings, ultra detailed, 8k")
    prompt = st.text_area("Image prompt (editable)", prompt, height=90)
    if st.button("🖼️ Generate Concept Render", type="primary"):
        seed = int(datetime.now().timestamp()) % 100000
        st.session_state["render_url"] = (
            f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
            f"?width=1024&height=640&seed={seed}&nologo=true"
        )
    if st.session_state.get("render_url"):
        try:
            st.image(st.session_state["render_url"], caption="Concept render via Pollinations AI (illustrative only)",
                     use_container_width=True)
        except Exception as e:
            st.warning(f"Render service unavailable right now: {e}")
        st.markdown(f"[Open image in new tab]({st.session_state['render_url']})")


# ----------------------------------------------------------------------------
# Tab 4 - Weather + assistant
# ----------------------------------------------------------------------------
def render_assistant_tab() -> None:
    st.subheader("🌦️ Daily Site Assistant & Weather-Aware Advisory")
    weather = st.radio("Today's site weather", list(WEATHER_ADVISORIES), horizontal=True, index=3)
    adv = WEATHER_ADVISORIES[weather]
    st.markdown(
        f"### {adv['icon']} {weather} &nbsp; {pill('Risk: ' + adv['risk'], adv['pill'])}",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, (title, body) in enumerate(adv["alerts"]):
        cols[i % 2].markdown(f'<div class="alert"><b>{esc(title)}</b>{esc(body)}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 💬 SiteMate - Construction Engineering Assistant")
    st.session_state.setdefault("chat", [])
    top = st.columns([6, 1])
    if top[1].button("🗑️ Clear"):
        st.session_state["chat"] = []
        st.rerun()
    if not st.session_state["chat"]:
        st.caption("Try: *What's the M20 mix ratio?* · *Curing period in hot weather?* · *Scaffold safety checklist*")
    for m in st.session_state["chat"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    q = st.chat_input("Ask a construction engineering or site safety question...")
    if q:
        st.session_state["chat"].append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    ans = gemini_chat(st.session_state["chat"], weather) if live_mode() else demo_chat(q, weather)
                except Exception as e:
                    ans = f"⚠️ Assistant error: {e}\n\n" + demo_chat(q, weather)
            st.markdown(ans)
        st.session_state["chat"].append({"role": "assistant", "content": ans})


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    render_sidebar()
    st.markdown(
        '<div class="hero"><h1>🏗️ Multimodal Construction Intelligence Platform</h1>'
        "<p>AI-powered safety audits · structural diagnostics · project valuation · site assistant "
        "&nbsp;|&nbsp; Skill Wallet Capstone Project 1</p></div>",
        unsafe_allow_html=True,
    )
    if not live_mode():
        st.markdown('<div class="demo-banner">🟡 <b>Demonstration mode</b> - enter a Gemini API key in the sidebar '
                    "for live multimodal analysis.</div>", unsafe_allow_html=True)
    tabs = st.tabs(["🦺 Safety & PPE Audit", "🧱 Crack Diagnostics", "💰 Planning & Valuation", "🌦️ Site Assistant"])
    for tab, fn in zip(tabs, (render_safety_tab, render_crack_tab, render_planning_tab, render_assistant_tab)):
        with tab:
            try:
                fn()
            except Exception as e:  # keep other tabs alive
                st.error(f"Unexpected error in this module: {e}")
    st.markdown('<div class="footer">Advisory tool only - verify with licensed engineers and certified safety officers.</div>',
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
