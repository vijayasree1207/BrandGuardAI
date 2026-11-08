
import streamlit as st
from database import get_connection

st.set_page_config(page_title="Review & Approval", page_icon="✅", layout="wide")

st.title("Review & Approval")
st.write("Review analysed content and record your decision.")

conn = get_connection()

reviews = conn.execute("""
    SELECT id, content_id, review_status, reviewer_notes, reviewed_at
    FROM content_reviews
    ORDER BY id DESC
""").fetchall()

conn.close()

if not reviews:
    st.info("No reviews available yet.")
else:
    for review in reviews:
        review_id, content_id, status, notes, reviewed_at = review

        with st.container(border=True):
            st.subheader(f"Review #{review_id}")
            st.write(f"Content ID: {content_id}")
            st.write(f"Current Status: **{status}**")
            st.write(f"Reviewer Notes: {notes or 'No notes'}")
            st.caption(f"Created: {reviewed_at}")

            decision = st.radio(
                "Your decision",
                ["Pending", "Approved", "Rejected"],
                index=["Pending", "Approved", "Rejected"].index(status),
                key=f"decision_{review_id}",
                horizontal=True
            )

            reviewer_notes = st.text_area(
                "Reviewer comments",
                value=notes or "",
                key=f"notes_{review_id}"
            )

            if st.button("Save Decision", key=f"save_{review_id}"):
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

                st.success("Review decision saved!")
                st.rerun()
