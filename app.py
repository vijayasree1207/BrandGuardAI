
import streamlit as st
from database import create_tables

st.set_page_config(
    page_title="BrandGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

create_tables()

st.markdown("""
<style>

/* MAIN BACKGROUND */
.stApp {
    background: linear-gradient(135deg, #080f25 0%, #111c3d 55%, #172b50 100%);
    color: #f1f5ff;
}

/* MAIN CONTENT */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* DEFAULT TEXT */
.stApp p,
.stApp label,
.stApp .stMarkdown {
    color: #dbe5f5;
}

/* HERO SECTION */
.hero {
    background: linear-gradient(120deg, #172554, #1d4ed8, #4338ca);
    padding: 42px;
    border-radius: 22px;
    margin-bottom: 30px;
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 12px 35px rgba(0,0,0,0.25);
}

.hero h1 {
    color: #ffffff !important;
    font-size: 44px !important;
    font-weight: 800 !important;
    margin-bottom: 12px;
}

.hero p {
    color: #e0eaff !important;
    font-size: 18px !important;
}

/* SECTION HEADINGS */
.stApp h2,
.stApp h3 {
    color: #ffffff !important;
}

/* FEATURE CARDS */
.feature-card {
    padding: 25px;
    border-radius: 18px;
    min-height: 175px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 8px 24px rgba(0,0,0,0.22);
    transition: transform 0.2s ease;
}

.feature-card h3 {
    color: #ffffff !important;
    font-size: 21px !important;
    font-weight: 700 !important;
}

.feature-card p {
    color: #f0f4ff !important;
    font-size: 15px !important;
    line-height: 1.7;
}

/* INDIVIDUAL CARD COLOURS */
.blue-card {
    background: linear-gradient(135deg, #173b79, #1d4ed8);
}

.purple-card {
    background: linear-gradient(135deg, #54258b, #7c3aed);
}

.green-card {
    background: linear-gradient(135deg, #075e53, #059669);
}

.orange-card {
    background: linear-gradient(135deg, #873b16, #ea580c);
}

/* WORKFLOW */
.workflow-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.14);
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
}

.workflow-number {
    color: #60a5fa !important;
    font-size: 25px !important;
    font-weight: 800;
}

.workflow-title {
    color: #ffffff !important;
    font-size: 18px;
    font-weight: 700;
}

.workflow-description {
    color: #cbd5e1 !important;
    font-size: 14px;
}

/* DIVIDER */
.stApp hr {
    border-color: rgba(255,255,255,0.16);
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #0b1530;
}

[data-testid="stSidebar"] * {
    color: #e2e8f0;
}

/* INFO BOX */
.stAlert {
    background: rgba(37,99,235,0.15);
    border: 1px solid rgba(96,165,250,0.4);
}

/* FOOTER */
.footer {
    text-align: center;
    color: #94a3b8 !important;
    padding: 20px;
    font-size: 14px;
}

</style>
""", unsafe_allow_html=True)


# HERO SECTION
st.markdown("""
<div class="hero">
    <h1>🛡️ BrandGuard AI</h1>
    <p>Ensuring every piece of content stays true to your brand.</p>
    <p>AI-Powered Brand Governance and Content Compliance Platform</p>
</div>
""", unsafe_allow_html=True)


# INTRODUCTION
st.subheader("Welcome to BrandGuard AI")

st.write(
    "BrandGuard AI helps organizations maintain consistent brand "
    "communication by checking content against configured brand "
    "guidelines, identifying potential compliance issues and "
    "supporting human review."
)

st.divider()


# PLATFORM CAPABILITIES
st.subheader("🚀 Platform Capabilities")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card blue-card">
        <h3>📋 Brand Guidelines</h3>
        <p>Create, edit and manage approved terminology,
        restricted phrases and brand communication rules.</p>
    </div>

    <div class="feature-card purple-card">
        <h3>🔍 Content Compliance</h3>
        <p>Analyse text and uploaded documents against
        configured brand guidelines.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card green-card">
        <h3>✅ Human Review</h3>
        <p>Review findings and record approval or rejection
        decisions.</p>
    </div>

    <div class="feature-card orange-card">
        <h3>📊 Analytics & Reports</h3>
        <p>Monitor compliance scores, review activity
        and download compliance reports.</p>
    </div>
    """, unsafe_allow_html=True)


st.divider()


# WORKFLOW
st.subheader("⚙️ How It Works")

steps = [
    ("01", "Configure Brand", "Create your brand identity and guidelines."),
    ("02", "Submit Content", "Enter text or upload a document."),
    ("03", "Analyse Content", "Identify potential compliance issues."),
    ("04", "Human Review", "Approve or reject the analysed content."),
    ("05", "Track Results", "Monitor compliance and download reports.")
]

for number, title, description in steps:
    st.markdown(f"""
    <div class="workflow-card">
        <span class="workflow-number">{number}</span>
        <span class="workflow-title"> &nbsp; {title}</span>
        <p class="workflow-description">{description}</p>
    </div>
    """, unsafe_allow_html=True)


st.divider()


# DISCLAIMER
st.info(
    "Note: Automated findings are preliminary. "
    "Human verification is required before content is published."
)


# FOOTER
st.markdown("""
<div class="footer">
    🛡️ BrandGuard AI | Evidence-Based Brand Governance
</div>
""", unsafe_allow_html=True)
