
import streamlit as st
from database import get_connection

st.set_page_config(
    page_title="Brand Guidelines",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Brand Guidelines Manager")

st.write(
    "Create, manage and update your company's brand identity and compliance rules."
)

CATEGORIES = [
    "Approved Term",
    "Restricted Phrase",
    "Tone of Voice",
    "Factual Claim"
]

SEVERITIES = ["Low", "Medium", "High", "Critical"]


# ==========================================
# CREATE BRAND
# ==========================================

st.divider()
st.subheader("🏢 Create Your Brand")

brand_name = st.text_input(
    "Company / Brand Name",
    key="brand_name_input"
)

description = st.text_area(
    "Brand Description",
    placeholder="Describe your company and its identity...",
    key="brand_description_input"
)

brand_voice = st.selectbox(
    "🎨 Select Brand Voice",
    [
        "Professional",
        "Friendly",
        "Innovative",
        "Luxury",
        "Minimalist",
        "Persuasive",
        "Technical"
    ],
    key="brand_voice_input"
)

if st.button("💾 Save Brand", key="save_brand"):

    if not brand_name.strip():

        st.warning("Please enter a brand name.")

    else:

        conn = get_connection()

        try:

            existing = conn.execute(
                """
                SELECT id FROM brands
                WHERE LOWER(TRIM(brand_name)) = LOWER(TRIM(?))
                """,
                (brand_name.strip(),)
            ).fetchone()

            if existing:

                st.warning(
                    "This brand already exists. "
                    "Please select it from the existing brands."
                )

            else:

                conn.execute(
                    """
                    INSERT INTO brands (brand_name, description)
                    VALUES (?, ?)
                    """,
                    (
                     brand_name.strip(),
                    f"Brand Voice: {brand_voice}. {description.strip()}"
)                               
                )

                conn.commit()

                st.success("Brand saved successfully!")

        except Exception as error:

            st.error(f"Unable to save brand: {error}")

        finally:
            conn.close()


# ==========================================
# LOAD BRANDS
# ==========================================

conn = get_connection()

try:

    brands = conn.execute(
        """
        SELECT id, brand_name
        FROM brands
        ORDER BY id
        """
    ).fetchall()

except Exception as error:

    st.error(f"Unable to load brands: {error}")
    brands = []

finally:
    conn.close()


# ==========================================
# ADD GUIDELINES
# ==========================================

st.divider()
st.subheader("➕ Add Brand Guidelines")

if brands:

    brand_options = {
        brand_id: name
        for brand_id, name in brands
    }

    selected_brand_id = st.selectbox(
        "Select Brand",
        list(brand_options.keys()),
        format_func=lambda x: brand_options[x],
        key="add_brand"
    )

    category = st.selectbox(
        "Guideline Category",
        CATEGORIES,
        key="new_category"
    )

    rule = st.text_area(
        "Enter Guideline",
        placeholder="Enter the brand rule...",
        key="new_rule"
    )

    severity = st.selectbox(
        "Severity",
        SEVERITIES,
        key="new_severity"
    )

    if st.button("💾 Save Guideline", key="save_guideline"):

        if not rule.strip():

            st.warning("Please enter a guideline.")

        else:

            conn = get_connection()

            try:

                existing_rule = conn.execute(
                    """
                    SELECT id FROM guidelines
                    WHERE brand_id = ?
                    AND LOWER(category) = LOWER(?)
                    AND LOWER(TRIM(rule)) = LOWER(TRIM(?))
                    """,
                    (selected_brand_id, category, rule.strip())
                ).fetchone()

                if existing_rule:

                    st.warning(
                        "This guideline already exists for this brand."
                    )

                else:

                    conn.execute(
                        """
                        INSERT INTO guidelines
                        (brand_id, category, rule, severity)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            selected_brand_id,
                            category,
                            rule.strip(),
                            severity
                        )
                    )

                    conn.commit()

                    st.success("Guideline saved successfully!")

            except Exception as error:

                st.error(f"Unable to save guideline: {error}")

            finally:
                conn.close()

else:

    st.info("Create a brand first to add its guidelines.")


# ==========================================
# MANAGE EXISTING GUIDELINES
# ==========================================

st.divider()
st.subheader("📝 Manage Existing Guidelines")

conn = get_connection()

try:

    guidelines = conn.execute(
        """
        SELECT
            guidelines.id,
            brands.brand_name,
            guidelines.category,
            guidelines.rule,
            guidelines.severity
        FROM guidelines
        JOIN brands ON brands.id = guidelines.brand_id
        ORDER BY guidelines.id DESC
        """
    ).fetchall()

except Exception as error:

    st.error(f"Unable to load guidelines: {error}")
    guidelines = []

finally:
    conn.close()


# ==========================================
# EDIT AND DELETE
# ==========================================

if guidelines:

    for item in guidelines:

        guideline_id, brand, old_category, old_rule, old_severity = item

        with st.expander(
            f"{brand} | {old_category} | {old_severity}"
        ):

            st.write("**Current Rule:**", old_rule)

            st.divider()
            st.write("### ✏️ Edit Guideline")

            with st.form(key=f"edit_form_{guideline_id}"):

                new_category = st.selectbox(
                    "Category",
                    CATEGORIES,
                    index=(
                        CATEGORIES.index(old_category)
                        if old_category in CATEGORIES else 0
                    )
                )

                new_rule = st.text_area(
                    "Rule",
                    value=old_rule
                )

                new_severity = st.selectbox(
                    "Severity",
                    SEVERITIES,
                    index=(
                        SEVERITIES.index(old_severity)
                        if old_severity in SEVERITIES else 1
                    )
                )

                update_clicked = st.form_submit_button(
                    "💾 Update Guideline"
                )

            if update_clicked:

                if not new_rule.strip():

                    st.warning("Rule cannot be empty.")

                else:

                    conn = get_connection()

                    try:

                        conn.execute(
                            """
                            UPDATE guidelines
                            SET category = ?, rule = ?, severity = ?
                            WHERE id = ?
                            """,
                            (
                                new_category,
                                new_rule.strip(),
                                new_severity,
                                guideline_id
                            )
                        )

                        conn.commit()

                        st.success("Guideline updated successfully!")

                    except Exception as error:

                        st.error(f"Unable to update guideline: {error}")

                    finally:
                        conn.close()

            st.divider()
            st.write("### 🗑️ Delete Guideline")

            with st.form(key=f"delete_form_{guideline_id}"):

                confirm = st.checkbox(
                    "I confirm that I want to delete this guideline."
                )

                delete_clicked = st.form_submit_button(
                    "🗑️ Delete Guideline"
                )

            if delete_clicked:

                if not confirm:

                    st.warning("Please confirm before deleting.")

                else:

                    conn = get_connection()

                    try:

                        conn.execute(
                            "DELETE FROM guidelines WHERE id = ?",
                            (guideline_id,)
                        )

                        conn.commit()

                        st.success("Guideline deleted successfully!")

                    except Exception as error:

                        st.error(f"Unable to delete guideline: {error}")

                    finally:
                        conn.close()

else:

    st.info("No guidelines have been added yet.")


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "BrandGuard AI | Evidence-Based Brand Compliance "
    "and Governance Platform"
)
