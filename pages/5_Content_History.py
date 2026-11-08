
import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(
    page_title="Content History",
    page_icon="📜",
    layout="wide"
)

st.title("📜 Content History")
st.write(
    "View previously analysed content and its compliance status."
)

# Fetch saved content history
conn = get_connection()

history = conn.execute("""
    SELECT
        content_history.id,
        brands.brand_name,
        content_history.content,
        content_history.score,
        content_history.status,
        content_reviews.review_status,
        content_history.created_at
    FROM content_history
    LEFT JOIN brands
        ON content_history.brand_id = brands.id
    LEFT JOIN content_reviews
        ON content_history.id = content_reviews.content_id
    ORDER BY content_history.id DESC
""").fetchall()

conn.close()

if not history:
    st.info(
        "No content history available yet. "
        "Analyse content and save it for review first."
    )

else:
    df = pd.DataFrame(
        history,
        columns=[
            "Content ID",
            "Brand",
            "Content",
            "Compliance Score",
            "Submission Status",
            "Review Status",
            "Created At"
        ]
    )

    # History table
    st.subheader("Previous Analyses")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # Download report
    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download Compliance Report",
        data=csv_data,
        file_name="BrandGuard_Compliance_Report.csv",
        mime="text/csv"
    )

    st.divider()

    # View individual content
    st.subheader("View Content Details")

    selected_id = st.selectbox(
        "Select Content ID",
        df["Content ID"].tolist()
    )

    selected = df[
        df["Content ID"] == selected_id
    ].iloc[0]

    st.write("**Brand:**", selected["Brand"])
    st.write(
        "**Compliance Score:**",
        selected["Compliance Score"]
    )
    st.write(
        "**Review Status:**",
        selected["Review Status"] or "Not submitted"
    )
    st.write("**Submitted At:**", selected["Created At"])

    st.write("**Original Content:**")
    st.write(selected["Content"])

    # Fetch detected issues
    conn = get_connection()

    violations = conn.execute(
        "SELECT violations FROM content_history WHERE id = ?",
        (int(selected_id),)
    ).fetchone()

    conn.close()

    st.write("**Detected Issues:**")

    st.code(
        violations[0]
        if violations and violations[0]
        else "No issues recorded."
    )

st.divider()

st.caption(
    "BrandGuard AI | Content audit and review history"
)

