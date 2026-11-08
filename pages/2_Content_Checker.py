import streamlit as st
import io
import re
import json
import html
import fitz

from docx import Document
from database import get_connection


# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="BrandGuard AI - Content Checker",
    page_icon="🔍",
    layout="wide"
)


# ==================================================
# 2. ANALYSIS CONFIGURATION
# ==================================================

SEVERITY_WEIGHTS = {
    "Low": 5,
    "Medium": 10,
    "High": 20,
    "Critical": 30
}


# Each rule contains:
# Pattern, Severity, Explanation, Suggested correction

RISK_PATTERNS = [

    # Guaranteed outcomes
    (
        r"\b100\s*%\s*guaranteed\b|\bguarantees?\s+100\s*%\s+results\b",
        "High",
        "An absolute guaranteed-results claim requires strong supporting evidence.",
        "Use measurable results supported by verified data."
    ),
    (
        r"\bguaranteed\b|\bguarantees\b",
        "High",
        "Guarantee language may create unrealistic expectations.",
        "Describe the product's actual benefits without promising an unsupported outcome."
    ),
    (
        r"\bguaranteed\s+to\s+\w+|\bguarantees?\s+(?:to\s+)?(?:deliver|get|achieve|provide)\b",
        "High",
        "A promised outcome should be supported by verifiable evidence.",
        "Replace the absolute promise with a specific, measurable benefit."
    ),

    # Safety and risk claims
    (
        r"\brisk[- ]free\b|\bzero risk\b|\bno risk whatsoever\b",
        "High",
        "Absolute risk claims require strong supporting evidence.",
        "Explain the actual risks and relevant safety measures."
    ),
    (
        r"\bno side effects\b|\bside[- ]effect[- ]free\b",
        "High",
        "Absolute safety claims should be verified.",
        "Use appropriately qualified safety information."
    ),
    (
        r"\bcompletely safe\b|\b100\s*%\s*safe\b",
        "High",
        "Absolute safety statements require reliable evidence.",
        "Describe verified safety features without making absolute claims."
    ),

    # Medical and scientific claims
    (
        r"\bcures?\b|\bcures all\b",
        "High",
        "Medical cure claims require appropriate scientific evidence.",
        "Use evidence-based wording and cite appropriate research."
    ),
    (
        r"\bclinically proven\b|\bscientifically proven\b",
        "High",
        "Scientific claims require reliable supporting sources.",
        "Provide the relevant study or verified scientific source."
    ),

    # Ranking and superiority
    (
        r"\bnumber one\b|#1|\bthe best\b",
        "Medium",
        "Ranking and superiority claims should have verifiable evidence.",
        "Provide a credible ranking source or use a descriptive benefit."
    ),
    (
        r"\bbetter than all\b|\bworld's best\b|\bmarket leader\b",
        "Medium",
        "A market superiority claim should be supported by evidence.",
        "Support the comparison with reliable market research."
    ),

    # Financial claims
    (
        r"\bdouble your money\b|\bguaranteed profits\b",
        "High",
        "Financial outcome claims may be misleading without evidence.",
        "Use transparent financial information and avoid guaranteed returns."
    ),

    # Performance claims
    (
        r"\binstant results\b|\bimmediate results\b",
        "Medium",
        "Immediate-results claims may create unrealistic expectations.",
        "Describe realistic timelines and expected performance."
    ),
    (
        r"\bnever fails\b|\balways works\b|\bworks for everyone\b",
        "High",
        "Universal performance claims require strong verification.",
        "Describe the tested performance and any relevant limitations."
    )
]


# ==================================================
# 3. HELPER FUNCTIONS
# ==================================================

def get_snippet(content, start, end, radius=65):

    left = max(0, start - radius)
    right = min(len(content), end + radius)

    snippet = content[left:right].replace("\n", " ")

    return (
        ("..." if left > 0 else "")
        + snippet
        + ("..." if right < len(content) else "")
    )


def add_finding(
    findings,
    category,
    rule,
    severity,
    reason,
    evidence,
    suggestion,
    start=None,
    end=None
):

    findings.append({
        "category": category,
        "rule": rule,
        "severity": severity,
        "reason": reason,
        "evidence": evidence,
        "suggestion": suggestion,
        "start": start,
        "end": end
    })


# ==================================================
# 4. ANALYSIS ENGINE
# ==================================================

def analyse_content(content, guidelines, brand_voice="Not configured"):

    findings = []
    tone_notes = []
        # ----------------------------------------------
    # BRAND VOICE INTELLIGENCE
    # ----------------------------------------------

    voice = str(brand_voice).strip().lower()

    voice_checks = {
        "professional": {
            "bad": ["lol", "gonna", "wanna", "hey guys"],
            "reason": "Casual expressions may conflict with a professional brand voice."
        },
        "friendly": {
            "bad": ["hereby", "pursuant to", "aforementioned"],
            "reason": "Overly formal expressions may conflict with a friendly brand voice."
        },
        "luxury": {
            "bad": ["cheap", "super cheap", "hey guys", "lol"],
            "reason": "Casual or price-focused expressions may conflict with a luxury brand voice."
        },
        "innovative": {
            "bad": ["old-fashioned", "nothing new", "same as everyone"],
            "reason": "These expressions may weaken an innovative brand voice."
        },
        "minimalist": {
            "bad": ["!!!", "???", "very very"],
            "reason": "Excessive emphasis may conflict with a minimalist brand voice."
        },
        "persuasive": {
            "bad": [],
            "reason": ""
        },
        "technical": {
            "bad": ["stuff", "things", "somehow"],
            "reason": "Vague expressions may conflict with a technical brand voice."
        }
    }

    if voice in voice_checks:

        config = voice_checks[voice]

        for phrase in config["bad"]:

            match = re.search(
                re.escape(phrase),
                content,
                re.IGNORECASE
            )

            if match:

                add_finding(
                    findings,
                    "Brand Voice",
                    brand_voice,
                    "Medium",
                    config["reason"],
                    match.group(),
                    "Consider replacing this expression to better match the selected brand voice.",
                    match.start(),
                    match.end()
                )

    # ----------------------------------------------
    # A. BRAND GUIDELINE ANALYSIS
    # ----------------------------------------------

    for category, rule, severity in guidelines:

        category = str(category).strip()
        rule = str(rule).strip()
        severity = str(severity).strip().title()

        if not rule:
            continue

        if severity not in SEVERITY_WEIGHTS:
            severity = "Medium"

        # Restricted phrases
        if category == "Restricted Phrase":

            matches = re.finditer(
                re.escape(rule),
                content,
                re.IGNORECASE
            )

            for match in list(matches)[:20]:

                add_finding(
                    findings,
                    category,
                    rule,
                    severity,
                    "This phrase matches a restricted brand guideline.",
                    match.group(),
                    "Replace the restricted phrase with approved brand wording.",
                    match.start(),
                    match.end()
                )

        # Approved terminology
        elif category == "Approved Term":

            pattern = (
                r"(?<!\w)"
                + re.escape(rule)
                + r"(?!\w)"
            )

            if not re.search(pattern, content, re.IGNORECASE):

                add_finding(
                    findings,
                    category,
                    rule,
                    severity,
                    "Required approved terminology was not found.",
                    "Required term missing: " + rule,
                    "Include the approved terminology where appropriate."
                )

        # Factual claims
        elif category == "Factual Claim":

            match = re.search(
                re.escape(rule),
                content,
                re.IGNORECASE
            )

            if match:

                add_finding(
                    findings,
                    category,
                    rule,
                    severity,
                    "This configured claim requires manual source verification.",
                    match.group(),
                    "Verify this claim against an official company source.",
                    match.start(),
                    match.end()
                )

        # Tone analysis
        elif category == "Tone of Voice":

            tone = rule.lower()

            tone_checks = {
                "professional": {
                    "bad": [
                        "lol", "gonna", "wanna", "hey guys"
                    ],
                    "reason": "Casual expressions may conflict with a professional tone."
                },

                "formal": {
                    "bad": [
                        "lol", "gonna", "wanna", "hey guys"
                    ],
                    "reason": "Informal expressions may conflict with a formal tone."
                },

                "friendly": {
                    "bad": [
                        "hereby", "pursuant to", "aforementioned"
                    ],
                    "reason": "Overly formal expressions may conflict with a friendly tone."
                },

                "confident": {
                    "bad": [
                        "maybe", "perhaps", "might possibly",
                        "we are not sure"
                    ],
                    "reason": "Hesitant expressions may weaken a confident tone."
                }
            }

            matched_tone = None

            for tone_name in tone_checks:

                if tone_name in tone:
                    matched_tone = tone_name
                    break

            if matched_tone:

                config = tone_checks[matched_tone]

                for phrase in config["bad"]:

                    match = re.search(
                        re.escape(phrase),
                        content,
                        re.IGNORECASE
                    )

                    if match:

                        add_finding(
                            findings,
                            category,
                            rule,
                            severity,
                            config["reason"],
                            match.group(),
                            "Rewrite this expression to better match the configured brand tone.",
                            match.start(),
                            match.end()
                        )

            else:

                tone_notes.append(
                    "Tone guideline '"
                    + rule
                    + "' needs human interpretation because it is not covered by current automated checks."
                )

    # ----------------------------------------------
    # B. BUILT-IN CLAIM-RISK ANALYSIS
    # ----------------------------------------------

    for pattern, severity, reason, suggestion in RISK_PATTERNS:

        matches = re.finditer(
            pattern,
            content,
            re.IGNORECASE
        )

        for match in list(matches)[:20]:

            start = match.start()
            end = match.end()

            # Avoid duplicate or overlapping claim-risk findings
            duplicate = any(
                item["category"] == "Claim Risk"
                and (
                    (
                        item["start"] == start
                        and item["end"] == end
                    )
                    or (
                        item["start"] is not None
                        and item["end"] is not None
                        and start < item["end"]
                        and end > item["start"]
                    )
                )
                for item in findings
            )

            if duplicate:
                continue

            add_finding(
                findings,
                "Claim Risk",
                "Built-in claim-risk screening",
                severity,
                reason,
                match.group(),
                suggestion,
                start,
                end
            )

    # ----------------------------------------------
    # C. SORT FINDINGS
    # ----------------------------------------------

    findings.sort(
        key=lambda item: (
            item["start"] is None,
            item["start"] if item["start"] is not None else 0
        )
    )

    # ----------------------------------------------
    # D. COMPLIANCE SCORE
    # ----------------------------------------------

    total_weight = sum(
        SEVERITY_WEIGHTS.get(
            item["severity"],
            10
        )
        for item in findings
    )

    score = max(
        0,
        100 - total_weight
    )

    return findings, score, tone_notes
# ==================================================
# 5. SUGGESTED SENTENCE REWRITE ENGINE
# ==================================================



def build_suggested_rewrite(content, item):
    """
    Generates a finding-specific rewrite using the exact
    detected evidence wherever possible.

    This is rule-based assistance, not full semantic AI.
    """

    if not isinstance(content, str) or not isinstance(item, dict):
        return None

    # Get the exact detected phrase
    evidence = str(
        item.get("matched_text")
        or item.get("evidence")
        or ""
    ).strip()

    start = item.get("start")
    end = item.get("end")

    # First preference: identify the exact matched phrase
    # using the finding's character positions.
    matched_phrase = ""

    if (
        isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start < end <= len(content)
    ):
        matched_phrase = content[start:end].strip()

    # Fallback: use the stored evidence text
    if not matched_phrase:
        matched_phrase = evidence

    if not matched_phrase:
        return None
        # Missing approved terms need human review,
    # not an automatic claim-risk rewrite.
    category = str(item.get("category", "")).lower()

    if "approved term" in category:
        return (
            "Review the brand's approved terminology and "
            "include an appropriate, verified term where relevant. "
            "Do not add unsupported guarantees."
        )

    if matched_phrase.lower().startswith("required term missing:"):
        return (
            "Review the brand's approved terminology and "
            "include an appropriate, verified term where relevant. "
            "Do not add unsupported guarantees."
        )

    phrase = matched_phrase.lower().strip()

    # Normalize punctuation around the phrase
    phrase = re.sub(r"^[^\w#]+|[^\w]+$", "", phrase)

    # 1. Universal performance claims
    if re.search(
        r"\b(works for everyone|suitable for everyone|"
        r"always works|never fails)\b",
        phrase
    ):
        return (
            "Our solution is designed to support a range of users. "
            "Performance may vary depending on individual needs, "
            "usage conditions and requirements."
        )

    # 2. Absolute safety claims
    if re.search(
        r"\b(completely safe|100\s*%\s*safe)\b",
        phrase
    ):
        return (
            "Our solution includes safety measures designed "
            "to support users. Please review the verified "
            "safety information and applicable limitations."
        )

    # 3. Zero-risk claims
    if re.search(
        r"\b(zero risk|risk-free|no risk whatsoever)\b",
        phrase
    ):
        return (
            "Our solution is designed with risk-reduction "
            "measures. Please review the relevant risks, "
            "precautions and limitations."
        )

    # 4. Side-effect claims
    if re.search(
        r"\b(no side effects|side-effect-free)\b",
        phrase
    ):
        return (
            "Describe only verified side-effect information "
            "and clearly communicate relevant precautions."
        )

    # 5. Medical and scientific claims
    if re.search(
        r"\b(cure|cures|clinically proven|scientifically proven)\b",
        phrase
    ):
        return (
            "Describe health or scientific benefits only when "
            "supported by relevant, verifiable research."
        )

    # 6. Financial claims
    if re.search(
        r"\b(double your money|guaranteed profits)\b",
        phrase
    ):
        return (
            "Financial outcomes are not guaranteed. Clearly "
            "explain potential risks and the factors that "
            "may affect results."
        )

    # 7. Instant-result claims
    if re.search(
        r"\b(instant results|immediate results)\b",
        phrase
    ):
        return (
            "Our solution is designed to provide timely results. "
            "Actual delivery time may vary depending on "
            "usage conditions."
        )

    # 8. Guarantee claims
    if re.search(
        r"\b(guarantee|guaranteed|guarantees)\b",
        phrase
    ):
        return (
            "Our solution aims to deliver the stated outcomes. "
            "Actual results may vary depending on usage "
            "conditions and individual requirements."
        )

    # 9. Superiority and ranking claims
    if re.search(
        r"\b(number one|#1|the best|market leader|"
        r"world's best|better than all)\b",
        phrase
    ):
        return (
            "Our solution offers features designed to meet "
            "customer needs. Include reliable comparative "
            "evidence before making superiority claims."
        )

        # 10. Professional brand voice
    if phrase == "hey guys":
        return "Hello everyone"

    if phrase == "gonna":
        return "going to"

    if phrase == "wanna":
        return "want to"

    if phrase == "lol":
         return " "

    # 11. Friendly brand voice
    if phrase == "hereby":
        return "here"

    if phrase == "pursuant to":
        return "in accordance with"

    # No matching rewrite rule
    return None

    
# ==================================================
# 6. PDF REPORT GENERATOR
# ==================================================

def generate_pdf(result, brand_name):

    from reportlab.lib.pagesizes import A4

    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        KeepTogether
    )

    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    story = []

    # Report title
    story.append(
        Paragraph(
            "BrandGuard AI - Compliance Report",
            styles["Title"]
        )
    )

    story.append(
        Spacer(1, 0.2 * inch)
    )

    # Brand name
    story.append(
        Paragraph(
            "<b>Brand:</b> "
            + html.escape(str(brand_name)),
            styles["Normal"]
        )
    )
        # Content channel
    content_channel = result.get(
        "content_channel",
        "General Document"
    )

    story.append(
        Paragraph(
            "<b>Content Channel:</b> "
            + html.escape(str(content_channel)),
            styles["Normal"]
        )
    )

    # Compliance score
    story.append(
        Paragraph(
            "<b>Compliance Score:</b> "
            + str(result["score"])
            + "/100",
            styles["Normal"]
        )
    )

    # Number of findings
    story.append(
        Paragraph(
            "<b>Potential Findings:</b> "
            + str(len(result["violations"])),
            styles["Normal"]
        )
    )

    story.append(
        Spacer(1, 0.2 * inch)
    )

    # Submitted content
    story.append(
        Paragraph(
            "Submitted Content",
            styles["Heading2"]
        )
    )

    safe_content = html.escape(
        result["content"]
    ).replace("\n", "<br/>")

    story.append(
        Paragraph(
            safe_content,
            styles["BodyText"]
        )
    )

    story.append(
        Spacer(1, 0.2 * inch)
    )

    # Analysis findings
    story.append(
        Paragraph(
            "Analysis Findings",
            styles["Heading2"]
        )
    )

    if result["violations"]:

        for item in result["violations"]:

            details = (
                "<b>Category:</b> "
                + html.escape(item["category"])

                + "<br/><b>Severity:</b> "
                + html.escape(item["severity"])

                + "<br/><b>Rule:</b> "
                + html.escape(item["rule"])

                + "<br/><b>Evidence:</b> "
                + html.escape(item["evidence"])

                + "<br/><b>Reason:</b> "
                + html.escape(item["reason"])

                + "<br/><b>Suggestion:</b> "
                + html.escape(item["suggestion"])
            )

            # Include suggested rewrite when available
            rewrite = build_suggested_rewrite(
                result["content"],
                item
            )

            if rewrite:

                details += (
                    "<br/><b>Suggested Rewrite:</b> "
                    + html.escape(rewrite)
                )

            story.append(
                KeepTogether([
                    Paragraph(
                        details,
                        styles["BodyText"]
                    ),
                    Spacer(1, 0.15 * inch)
                ])
            )

    else:

        story.append(
            Paragraph(
                "No potential issues were detected by the configured checks.",
                styles["BodyText"]
            )
        )

    story.append(
        Spacer(1, 0.2 * inch)
    )

    # Disclaimer
    story.append(
        Paragraph(
            "Disclaimer: Automated findings and rewrites are preliminary. "
            "Human verification is required before publishing.",
            styles["Italic"]
        )
    )

    document.build(story)

    return buffer.getvalue()
# ==================================================
# 7. PAGE HEADER AND BRAND SELECTION
# ==================================================

st.title("🔍 AI Content Compliance Checker")

st.write(
    "Analyse marketing content against brand rules, "
    "approved terminology, tone guidelines and potential claim risks."
)

conn = get_connection()

brands = conn.execute(
    "SELECT id, brand_name, description FROM brands"
).fetchall()

conn.close()

if not brands:

    st.warning(
        "Please create a brand and add guidelines first."
    )

    st.stop()

brand_options = {
    row[0]: row[1]
    for row in brands
}

brand_descriptions = {
    row[0]: row[2] or ""
    for row in brands
}

selected_brand_id = st.selectbox(
    "Select Brand",
    list(brand_options.keys()),
    format_func=lambda brand_id: brand_options[brand_id]
)
selected_brand_description = brand_descriptions.get(
    selected_brand_id,
    ""
)

if selected_brand_description.startswith("Brand Voice:"):

    selected_brand_voice = (
        selected_brand_description
        .split(".", 1)[0]
        .replace("Brand Voice:", "")
        .strip()
    )

else:
    selected_brand_voice = "Not configured"

st.info(f"🎨 Brand Voice: {selected_brand_voice}")
# ==================================================
# CONTENT CHANNEL SELECTION
# ==================================================

st.subheader("📢 Select Content Channel")

content_channel = st.selectbox(
    "Where will this content be published?",
    [
        "Instagram Post",
        "Facebook Post",
        "Facebook Advertisement",
        "LinkedIn Post",
        "Website Content",
        "Email Campaign",
        "General Document"
    ],
    key="content_channel"
)

st.caption(
    f"Selected channel: {content_channel}"
)

# Clear previous analysis when the brand changes
if (
    "analysis" in st.session_state
    and st.session_state["analysis"].get("brand_id")
    != selected_brand_id
):

    del st.session_state["analysis"]


# ==================================================
# 8. DOCUMENT UPLOAD
# ==================================================

st.subheader("📄 Upload Your Document")

uploaded_file = st.file_uploader(
    "Upload a PDF or Word document",
    type=["pdf", "docx"]
)

uploaded_content = ""

if uploaded_file is not None:

    try:

        file_bytes = uploaded_file.getvalue()

        # Extract PDF content
        if uploaded_file.name.lower().endswith(".pdf"):

            document = fitz.open(
                stream=file_bytes,
                filetype="pdf"
            )

            uploaded_content = "\n".join(
                page.get_text()
                for page in document
            )

            document.close()

        # Extract Word document content
        elif uploaded_file.name.lower().endswith(".docx"):

            document = Document(
                io.BytesIO(file_bytes)
            )

            uploaded_content = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

            uploaded_content += "\n" + "\n".join(
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            )

        if uploaded_content.strip():

            st.success(
                "Document text extracted successfully!"
            )

            st.text_area(
                "Extracted Document Content",
                value=uploaded_content,
                height=160,
                disabled=True
            )

        else:

            st.warning(
                "No readable text found. "
                "Scanned image documents need OCR."
            )

    except Exception as error:

        st.error(
            "Unable to read document: " + str(error)
        )


# ==================================================
# 9. MANUAL CONTENT INPUT
# ==================================================

st.subheader("✍️ Enter Content Manually")

manual_content = st.text_area(
    "Enter Your Content",
    height=200,
    placeholder=(
        "Paste your advertisement, email or "
        "social media content here..."
    )
)

content = (
    uploaded_content
    if uploaded_content.strip()
    else manual_content
)


# ==================================================
# 10. RUN ANALYSIS
# ==================================================

if st.button(
    "🚀 Analyse Content",
    type="primary"
):

    if not content.strip():

        st.warning(
            "Please enter content or upload a readable document."
        )

    else:

        conn = get_connection()

        guidelines = conn.execute(
            """
            SELECT category, rule, severity
            FROM guidelines
            WHERE brand_id = ?
            """,
            (selected_brand_id,)
        ).fetchall()

        conn.close()

        violations, score, tone_notes = analyse_content(
        content,
        guidelines,
        selected_brand_voice
)

        st.session_state["analysis"] = {
            "version": 4,
            "brand_id": selected_brand_id,
            "content_channel": content_channel,
            "content": content,
            "violations": violations,
            "score": score,
            "tone_notes": tone_notes
        }
        # ==================================================
# 11. DISPLAY ANALYSIS RESULTS
# ==================================================

if "analysis" in st.session_state:

    result = st.session_state["analysis"]

    if result.get("version") == 4:

        st.divider()

        st.subheader("📊 Compliance Analysis Report")
                # Display selected content channel
        content_channel = result.get(
            "content_channel",
            "General Document"
        )

        st.info(
            f"📢 Content Channel: {content_channel}"
        )

        score = result["score"]
        violations = result["violations"]

        critical_count = sum(
            1 for item in violations
            if item.get("severity") == "Critical"
        )

        high_count = sum(
            1 for item in violations
            if item.get("severity") == "High"
        )

        medium_count = sum(
            1 for item in violations
            if item.get("severity") == "Medium"
        )

        low_count = sum(
            1 for item in violations
            if item.get("severity") == "Low"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Compliance Score",
                f"{score}/100"
            )

        with col2:
            st.metric(
                "Potential Findings",
                len(violations)
            )

        with col3:
            st.metric(
                "Critical Findings",
                critical_count
            )

        st.write("### Finding Severity")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Critical", critical_count)
        c2.metric("High", high_count)
        c3.metric("Medium", medium_count)
        c4.metric("Low", low_count)

        if score >= 80:
            st.success(
                "Lower detected risk. Review findings before publishing."
            )

        elif score >= 50:
            st.warning(
                "Moderate detected risk. Review and correct the findings."
            )

        else:
            st.error(
                "High detected risk. Review before publishing."
            )

        # ------------------------------------------
        # Evidence-based findings
        # ------------------------------------------

        st.subheader("⚠️ Evidence-Based Findings")

        if violations:

            for index, finding in enumerate(violations, start=1):

                severity = finding.get(
                    "severity",
                    "Medium"
                )

                category = finding.get(
                    "category",
                    finding.get("type", "Content Risk")
                )

                rule = finding.get(
                    "rule",
                    "Content compliance rule"
                )

                evidence = finding.get(
                    "matched_text",
                    finding.get("evidence", "")
                )

                reason = finding.get(
                    "reason",
                    "This content may require additional review."
                )

                suggestion = finding.get(
                    "suggestion",
                    "Review the statement and provide supporting evidence."
                )

                context = finding.get(
                    "context",
                    ""
                )

                with st.expander(
                    f"{index}. {severity} | {category}",
                    expanded=False
                ):

                    st.write("**Why was this flagged?**")

                    st.write(reason)

                    st.write("**Matched Brand Rule / Risk Pattern:**")

                    st.write(rule)

                    if evidence:
                        st.write("**Detected Evidence:**")
                        st.code(evidence)

                    if context:
                        st.write("**Context:**")
                        st.write(context)

                    st.write("**Suggested Action:**")

                    st.info(suggestion)

                    # Suggested sentence rewrite
                    suggested_rewrite = build_suggested_rewrite(
                        result["content"],
                        finding
                    )

                    if suggested_rewrite:

                        st.write("**Suggested Rewrite:**")

                        st.code(
                            suggested_rewrite,
                            language=None
                        )

                    else:

                        st.caption(
                            "No automatic rewrite is available for this finding. "
                            "Please review it manually."
                        )

        else:

            st.success(
                "No potential findings detected by the configured checks."
            )
                # ==========================================
        # BEFORE AND AFTER CONTENT OPTIMIZER
        # ==========================================

        st.divider()

        st.subheader("✨ Before-and-After Content Optimizer")

        st.write(
            "Improve your content using the detected compliance findings."
        )

        original_content = result["content"]

        improved_content = original_content

        if violations:

            # Apply replacements from right to left
            sorted_findings = sorted(
                violations,
                key=lambda item: (
                    item.get("start")
                    if isinstance(item.get("start"), int)
                    else -1
                ),
                reverse=True
            )

            for finding in sorted_findings:

                evidence = str(
                    finding.get("matched_text")
                    or finding.get("evidence")
                    or ""
                ).strip()

                rewrite = build_suggested_rewrite(
                    original_content,
                    finding
                )

                if rewrite is None:
                    continue

                start = finding.get("start")
                end = finding.get("end")

                if (
                    isinstance(start, int)
                    and isinstance(end, int)
                    and 0 <= start < end <= len(improved_content)
                    and improved_content[start:end].lower()
                    == evidence.lower()
                ):

                    improved_content = (
                        improved_content[:start]
                        + rewrite
                        + improved_content[end:]
                    )

                elif evidence and evidence in improved_content:

                    improved_content = improved_content.replace(
                        evidence,
                        rewrite,
                        1
                    )

            # Clean spaces and punctuation
            improved_content = re.sub(
                r"[ \t]+([,.!?;:])",
                r"\1",
                improved_content
            )

            improved_content = re.sub(
                r"([.!?])\s*[.!?]+",
                r"\1",
                improved_content
            )

            improved_content = re.sub(
                r" {2,}",
                " ",
                improved_content
            )

        st.write("### Original Content")

        st.text_area(
            "Original",
            value=original_content,
            height=130,
            disabled=True,
            key="optimizer_original"
        )

        st.write("### Improved Content")

        optimized_content = st.text_area(
            "Edit your improved content before publishing",
            value=improved_content,
            height=160,
            key="optimizer_improved"
        )

        st.caption(
            "Review and edit the improved version before publishing. "
            "Automated rewrites require human verification."
        )

        st.download_button(
            "📥 Download Improved Content",
            data=optimized_content,
            file_name="brandguard_improved_content.txt",
            mime="text/plain",
            key="download_improved_content"
        )
        # ------------------------------------------
        # Tone observations
        # ------------------------------------------

        if result.get("tone_notes"):

            st.subheader("🗣️ Tone Observations")

            for note in result["tone_notes"]:
                st.write("• " + str(note))

        # ------------------------------------------
        # Disclaimer
        # ------------------------------------------

        st.caption(
            "Note: This version uses configured brand rules and "
            "transparent keyword-based risk and tone heuristics. "
            "It does not provide full semantic AI verification. "
            "Suggested rewrites are preliminary and require human review."
        )

        st.divider()

              # ==================================================
        # 12. DOWNLOAD COMPLIANCE REPORT
        # ==================================================

        st.subheader("📥 Export Compliance Report")

        pdf_data = generate_pdf(
    result,
    brand_options[result["brand_id"]]
)
        st.download_button(
            label="📄 Download PDF Compliance Report",
            data=pdf_data,
            file_name="BrandGuard_Compliance_Report.pdf",
            mime="application/pdf"
        )

        # ==================================================
        # 13. SAVE FOR HUMAN REVIEW
        # ==================================================

        st.subheader("👥 Submit for Human Review")

        st.write(
            "Save this analysis to the review workflow "
            "so an authorised reviewer can approve or reject it."
        )

        if st.button(
            "💾 Save for Human Review",
            type="primary"
        ):

            try:

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO content_history
                    (brand_id, content, score, status, violations)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        result["brand_id"],
                        result["content"],
                        result["score"],
                        "Pending",
                        json.dumps(result["violations"])
                    )
                )

                content_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO content_reviews
                    (content_id, review_status, reviewer_notes)
                    VALUES (?, ?, ?)
                    """,
                    (
                        content_id,
                        "Pending",
                        "Awaiting human review"
                    )
                )

                conn.commit()

                st.success(
                    f"Content saved successfully for human review! "
                    f"Content ID: {content_id}"
                )

                st.session_state["last_saved_content_id"] = content_id

            except Exception as error:

                st.error(
                    "Unable to save content: " + str(error)
                )

            finally:

                if "conn" in locals():
                    conn.close()


# ==================================================
# 14. FOOTER
# ==================================================

st.divider()

st.caption(
    "BrandGuard AI | Evidence-Based Brand Compliance "
    "and Governance Platform"
)