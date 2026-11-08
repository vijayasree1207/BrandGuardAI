
import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(
    page_title="BrandGuard Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 BrandGuard AI Dashboard")
st.write("Monitor brand compliance and content review activity.")

conn = get_connection()

# Fetch dashboard metrics
total_content = conn.execute(
    "SELECT COUNT(*) FROM content_history"
).fetchone()[0]

average_score = conn.execute(
    "SELECT AVG(score) FROM content_history"
).fetchone()[0]

pending_reviews = conn.execute(
    "SELECT COUNT(*) FROM content_reviews WHERE review_status = 'Pending'"
).fetchone()[0]

approved_content = conn.execute(
    "SELECT COUNT(*) FROM content_reviews WHERE review_status = 'Approved'"
).fetchone()[0]

rejected_content = conn.execute(
    "SELECT COUNT(*) FROM content_reviews WHERE review_status = 'Rejected'"
).fetchone()[0]

recent_activity = conn.execute("""
    SELECT
        content_history.id,
        brands.brand_name,
        content_history.score,
        content_reviews.review_status,
        content_history.created_at
    FROM content_history
    LEFT JOIN brands
        ON content_history.brand_id = brands.id
    LEFT JOIN content_reviews
        ON content_history.id = content_reviews.content_id
    ORDER BY content_history.id DESC
    LIMIT 10
""").fetchall()

conn.close()

# Metric cards
col1, col2, col3 = st.columns(3)

col1.metric("Total Content Analysed", total_content)

col2.metric(
    "Average Compliance Score",
    f"{average_score:.1f}/100" if average_score is not None else "N/A"
)

col3.metric("Pending Reviews", pending_reviews)

col4, col5 = st.columns(2)

col4.metric("Approved Content", approved_content)
col5.metric("Rejected Content", rejected_content)

st.divider()

# Compliance overview
st.subheader("📈 Compliance Overview")

if total_content > 0:
    score = average_score or 0

    st.progress(
        int(max(0, min(100, score))) / 100
    )

    st.write(f"Average compliance score: **{score:.1f}/100**")

    if score >= 80:
        st.success("Overall compliance performance is strong.")
    elif score >= 50:
        st.warning("Some content needs improvement.")
    else:
        st.error("Several content items need attention.")
else:
    st.info("Analyse and save content to see compliance insights.")

st.divider()

# Compliance score analytics
st.subheader("📈 Content Compliance Analytics")

conn = get_connection()

score_data = conn.execute("""
    SELECT id, score
    FROM content_history
    ORDER BY id ASC
""").fetchall()

conn.close()

if score_data:
    chart_df = pd.DataFrame(
        score_data,
        columns=["Content ID", "Compliance Score"]
    )

    st.line_chart(
        chart_df.set_index("Content ID")
    )
else:
    st.info("Save analysed content to view the compliance trend.")


# Recent activity
st.subheader("🕒 Recent Review Activity")

if recent_activity:
    activity_df = pd.DataFrame(
        recent_activity,
        columns=[
            "Content ID",
            "Brand",
            "Score",
            "Review Status",
            "Created At"
        ]
    )

    activity_df["Review Status"] = (
        activity_df["Review Status"].fillna("Not submitted")
    )

    st.dataframe(
        activity_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No review activity available yet.")

st.divider()

st.caption("BrandGuard AI | Brand Governance and Content Compliance")
