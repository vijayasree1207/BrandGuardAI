
import os
import re

import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

from database import get_connection


# ------------------------------------------
# TESSERACT OCR CONFIGURATION
# ------------------------------------------

if os.name == "nt":
    windows_tesseract = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if os.path.exists(windows_tesseract):
        pytesseract.pytesseract.tesseract_cmd = windows_tesseract


# ------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------

def normalize_ocr_text(value):
    """Convert OCR text into a consistent searchable format."""
    value = str(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def phrase_matches(rule, normalized_text, max_gap=4):
    """
    Match a phrase even when OCR inserts a few extra words
    between the expected words.
    """

    rule_words = normalize_ocr_text(rule).split()
    text_words = normalized_text.split()

    if not rule_words or not text_words:
        return False

    # First try exact phrase matching.
    normalized_rule = " ".join(rule_words)

    if normalized_rule in normalized_text:
        return True

    # Then allow a small gap between phrase words.
    first_word = rule_words[0]

    for start, word in enumerate(text_words):

        if word != first_word:
            continue

        position = start
        matched = True

        for next_word in rule_words[1:]:

            found = False

            search_end = min(
                len(text_words),
                position + max_gap + 2
            )

            for index in range(position + 1, search_end):

                if text_words[index] == next_word:
                    position = index
                    found = True
                    break

            if not found:
                matched = False
                break

        if matched:
            return True

    return False


# ------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------

st.set_page_config(
    page_title="Visual Compliance Scanner",
    page_icon="🖼️",
    layout="wide"
)

st.title("🖼️ Visual Brand Compliance Scanner")

st.write(
    "Upload a marketing creative or social media poster "
    "to extract its text and check brand compliance."
)


# ------------------------------------------
# BRAND SELECTION
# ------------------------------------------

conn = get_connection()

brands = conn.execute(
    "SELECT id, brand_name FROM brands ORDER BY brand_name"
).fetchall()

conn.close()

if not brands:
    st.warning("Please create a brand first.")
    st.stop()

brand_options = {
    row[0]: row[1]
    for row in brands
}

selected_brand_id = st.selectbox(
    "Select Brand",
    list(brand_options.keys()),
    format_func=lambda brand_id: (
        f"{brand_options[brand_id]} (ID: {brand_id})"
    )
)


# ------------------------------------------
# IMAGE UPLOAD
# ------------------------------------------

uploaded_image = st.file_uploader(
    "Upload your marketing creative",
    type=["png", "jpg", "jpeg"]
)


if uploaded_image is not None:

    try:
        image = Image.open(uploaded_image).convert("RGB")

        st.image(
            image,
            caption="Uploaded Creative",
            use_container_width=True
        )

    except Exception as error:
        st.error(f"Unable to open this image: {error}")
        st.stop()

    # --------------------------------------
    # OCR EXTRACTION
    # --------------------------------------

    if st.button(
        "Extract Text Using OCR",
        type="primary"
    ):

        try:
            processed_image = ImageOps.grayscale(image)

            processed_image = ImageOps.autocontrast(
                processed_image
            )

            processed_image = processed_image.resize(
                (
                    processed_image.width * 2,
                    processed_image.height * 2
                )
            )

            processed_image = ImageEnhance.Contrast(
                processed_image
            ).enhance(2)

            processed_image = processed_image.filter(
                ImageFilter.SHARPEN
            )

            # OCR pass 1
            text_1 = pytesseract.image_to_string(
                processed_image,
                lang="eng",
                config="--psm 6"
            )

            # OCR pass 2
            text_2 = pytesseract.image_to_string(
                processed_image,
                lang="eng",
                config="--psm 11"
            )

            extracted_text = text_1 + "\n" + text_2

            st.session_state["visual_extracted_text"] = (
                extracted_text
            )

            # Clear previous analysis after a new extraction.
            st.session_state.pop("visual_findings", None)
            st.session_state.pop("visual_score", None)

            st.success("OCR text extraction completed!")

        except Exception as error:
            st.error(f"OCR extraction failed: {error}")


# ------------------------------------------
# DISPLAY EXTRACTED TEXT
# ------------------------------------------

if st.session_state.get("visual_extracted_text", "").strip():

    st.subheader("Extracted Text")

    st.text_area(
        "OCR Result",
        value=st.session_state["visual_extracted_text"],
        height=200
    )


# ------------------------------------------
# BRAND COMPLIANCE CHECK
# ------------------------------------------

if st.session_state.get("visual_extracted_text", "").strip():

    st.divider()

    st.subheader("🔍 Visual Content Compliance Check")

    if st.button(
        "Check Brand Compliance",
        type="primary"
    ):

        extracted_text = st.session_state[
            "visual_extracted_text"
        ]

        normalized_text = normalize_ocr_text(
            extracted_text
        )

        # Retrieve selected brand guidelines.
        conn = get_connection()

        guidelines = conn.execute(
            """
            SELECT category, rule, severity
            FROM guidelines
            WHERE brand_id = ?
            """,
            (selected_brand_id,)
        ).fetchall()

        # Retrieve approved brand facts.
        approved_facts = conn.execute(
            """
            SELECT fact, source
            FROM brand_facts
            WHERE brand_id = ?
            """,
            (selected_brand_id,)
        ).fetchall()

        conn.close()

        findings = []

        # ----------------------------------
        # GUIDELINE CHECKS
        # ----------------------------------

        for category, rule, severity in guidelines:

            category_lower = category.lower()

            rule_normalized = normalize_ocr_text(rule)

            if "restricted phrase" in category_lower:

                if phrase_matches(
                    rule,
                    normalized_text
                ):

                    findings.append({
                        "category": category,
                        "rule": rule,
                        "severity": severity,
                        "evidence": (
                            "Potential restricted phrase detected "
                            "in OCR text."
                        )
                    })

            elif "approved term" in category_lower:

                if rule_normalized not in normalized_text:

                    findings.append({
                        "category": category,
                        "rule": rule,
                        "severity": severity,
                        "evidence": (
                            "Approved term not found "
                            "in extracted text."
                        )
                    })

            elif "tone of voice" in category_lower:

                if rule_normalized in normalized_text:

                    findings.append({
                        "category": category,
                        "rule": rule,
                        "severity": severity,
                        "evidence": (
                            "Potential tone-of-voice issue detected."
                        )
                    })

        # ----------------------------------
        # APPROVED FACT CONTRADICTION CHECK
        # ----------------------------------

        negations = [
            "not",
            "never",
            "cannot",
            "can't",
            "doesn't",
            "isn't"
        ]

        sentences = re.split(
            r"[.!?\n]+",
            extracted_text
        )

        for fact, source in approved_facts:

            fact_words = [
                word
                for word in normalize_ocr_text(fact).split()
                if len(word) > 3
            ]

            if not fact_words:
                continue

            for sentence in sentences:

                sentence_normalized = normalize_ocr_text(
                    sentence
                )

                matching_words = [
                    word
                    for word in fact_words
                    if word in sentence_normalized.split()
                ]

                if (
                    len(matching_words) >= 3
                    and any(
                        normalize_ocr_text(n) in sentence_normalized.split()
                        for n in negations
                    )
                ):

                    findings.append({
                        "category": "Approved Fact Contradiction",
                        "rule": fact,
                        "severity": "High",
                        "evidence": sentence.strip()
                    })

                    break

        # ----------------------------------
        # COMPLIANCE SCORE
        # ----------------------------------

        severity_weights = {
            "Low": 5,
            "Medium": 10,
            "High": 20,
            "Critical": 30
        }

        total_weight = sum(
            severity_weights.get(
                item["severity"],
                10
            )
            for item in findings
        )

        score = max(
            0,
            100 - total_weight
        )

        st.session_state["visual_findings"] = findings
        st.session_state["visual_score"] = score


# ------------------------------------------
# DISPLAY RESULTS
# ------------------------------------------

if "visual_score" in st.session_state:

    st.divider()

    st.subheader("📊 Compliance Results")

    st.metric(
        "Visual Content Compliance Score",
        f"{st.session_state['visual_score']}/100"
    )

    visual_findings = st.session_state.get(
        "visual_findings",
        []
    )

    if not visual_findings:

        st.success(
            "No potential guideline issues detected."
        )

    else:

        st.warning(
            f"{len(visual_findings)} potential issue(s) detected."
        )

        for index, finding in enumerate(
            visual_findings,
            1
        ):

            with st.expander(
                f"Issue {index}: {finding['category']} "
                f"— {finding['severity']}"
            ):

                st.write(
                    "**Matched Rule:**",
                    finding["rule"]
                )

                st.write(
                    "**Evidence:**",
                    finding["evidence"]
                )

                st.write(
                    "**Suggested Action:** Review this text "
                    "against the brand guidelines before publishing."
                )

    st.caption(
        "OCR-based text screening only. This scanner does not yet "
        "verify logos, colours, or visual design elements. "
        "Potential matches may require human verification."
    )
