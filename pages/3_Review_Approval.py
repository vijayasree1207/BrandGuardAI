
import streamlit as st
import json
from database import get_connection

st.set_page_config(
    page_title="Review & Approval",
    page_icon="✅",
    layout="wide"
)

st.title("✅ Review & Approval")
st.write("Review analysed content and campaign asset versions.")

# ==================================================
# FETCH BOTH TYPES OF REVIEWS
# ==================================================

conn = get_connection()

content_reviews = conn.execute("""
    SELECT id, content_id, review_status, reviewer_notes, reviewed_at
    FROM content_reviews
    ORDER BY id DESC
""").fetchall()

campaign_reviews = conn.execute("""
    SELECT
        av.id,
        c.campaign_name,
        ca.asset_name,
        ca.channel,
        av.version_number,
        av.content,
        av.score,
        av.compliance_status,
        av.violations,
        av.version_note,
        av.review_status,
        av.reviewer_notes,
        av.created_at,
        av.reviewed_at,
        b.brand_name
    FROM asset_versions av
    JOIN campaign_assets ca
        ON av.asset_id = ca.id
    JOIN campaigns c
        ON ca.campaign_id = c.id
    JOIN brands b
        ON c.brand_id = b.id
    ORDER BY av.id DESC
""").fetchall()

conn.close()

# ==================================================
# SECTION 1: EXISTING CONTENT REVIEWS
# ==================================================

st.header("📄 Content Reviews")

if not content_reviews:
    st.info("No content reviews available yet.")

else:
    for review in content_reviews:

        review_id, content_id, status, notes, reviewed_at = review

        with st.container(border=True):

            st.subheader(f"Content Review #{review_id}")

            st.write(f"Content ID: {content_id}")
            st.write(f"Current Status: **{status or 'Pending'}**")
            st.write(f"Reviewer Notes: {notes or 'No notes'}")

            st.caption(f"Last reviewed: {reviewed_at or 'Not reviewed yet'}")

            status_options = ["Pending", "Approved", "Rejected"]
            current_status = status if status in status_options else "Pending"

            with st.form(key=f"content_review_form_{review_id}"):

                decision = st.radio(
                    "Your decision",
                    status_options,
                    index=status_options.index(current_status),
                    key=f"content_decision_{review_id}",
                    horizontal=True
                )

                reviewer_notes = st.text_area(
                    "Reviewer comments",
                    value=notes or "",
                    key=f"content_notes_{review_id}"
                )

                save_content = st.form_submit_button("Save Content Decision")

            if save_content:

                conn = get_connection()

                conn.execute("""
                    UPDATE content_reviews
                    SET review_status = ?,
                        reviewer_notes = ?,
                        reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (decision, reviewer_notes, review_id))

                conn.commit()
                conn.close()

                st.success("Content review decision saved!")
                st.rerun()


# ==================================================
# SECTION 2: CAMPAIGN ASSET VERSION REVIEWS
# ==================================================

st.divider()

st.header("🚀 Campaign Asset Version Reviews")

st.write(
    "Review individual campaign asset versions, "
    "check their compliance scores and record approval decisions."
)

if not campaign_reviews:

    st.info(
        "No campaign asset versions available yet. "
        "Create a campaign and add an asset in Campaign Manager."
    )

else:

    for review in campaign_reviews:

        (
            version_id,
            campaign_name,
            asset_name,
            channel,
            version_number,
            content,
            score,
            compliance_status,
            violations,
            version_note,
            review_status,
            reviewer_notes,
            created_at,
            reviewed_at,
            brand_name
        ) = review

        with st.container(border=True):

            st.subheader(
                f"{campaign_name} — {asset_name}"
            )

            st.write(f"**Brand:** {brand_name}")
            st.write(f"**Channel:** {channel}")
            st.write(f"**Version:** {version_number}")
            st.write(f"**Version Note:** {version_note or 'No note'}")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Compliance Score",
                f"{score}/100" if score is not None else "N/A"
            )

            col2.write("**Compliance Status**")
            col2.write(compliance_status or "Not analysed")

            col3.write("**Review Status**")
            col3.write(review_status or "Pending")

            st.caption(f"Created: {created_at}")
            st.caption(f"Last reviewed: {reviewed_at or 'Not reviewed yet'}")

            with st.expander("View Campaign Content"):
                st.write(content)

            with st.expander("View Compliance Findings"):

                if violations:

                    try:
                        parsed_violations = json.loads(violations)
                        st.json(parsed_violations)

                    except (json.JSONDecodeError, TypeError):
                        st.write(violations)

                else:
                    st.success("No recorded compliance findings.")

            status_options = ["Pending", "Approved", "Rejected"]

            current_status = (
                review_status
                if review_status in status_options
                else "Pending"
            )

            with st.form(key=f"campaign_review_form_{version_id}"):

                decision = st.radio(
                    "Campaign version decision",
                    status_options,
                    index=status_options.index(current_status),
                    horizontal=True,
                    key=f"campaign_decision_{version_id}"
                )

                reviewer_notes = st.text_area(
                    "Reviewer comments",
                    value=reviewer_notes or "",
                    key=f"campaign_notes_{version_id}"
                )

                save_campaign = st.form_submit_button(
                    "Save Campaign Review Decision"
                )

            if save_campaign:

                conn = get_connection()

                conn.execute("""
                    UPDATE asset_versions
                    SET review_status = ?,
                        reviewer_notes = ?,
                        reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (decision, reviewer_notes, version_id))

                conn.commit()
                conn.close()

                st.success(
                    f"Campaign version {version_number} review decision saved!"
                )

                st.rerun()


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "BrandGuard AI | Human-in-the-loop Brand Governance"
)
