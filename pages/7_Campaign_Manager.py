
import streamlit as st
import re
import json
from database import get_connection


# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Campaign Manager",
    page_icon="📁",
    layout="wide"
)

st.title("📁 Campaign Manager")

st.write(
    "Create marketing campaigns, organize campaign assets, "
    "analyse compliance and track content versions."
)


# ==================================================
# 2. COMPLIANCE ANALYSIS ENGINE
# ==================================================

def normalize_text(value):
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return " ".join(value.split())


def phrase_matches(rule, content, max_gap=4):

    rule_words = normalize_text(rule).split()
    content_words = normalize_text(content).split()

    if not rule_words or not content_words:
        return False

    for start in range(len(content_words)):

        if content_words[start] != rule_words[0]:
            continue

        position = start
        matched = True

        for word in rule_words[1:]:

            found = False

            for next_position in range(
                position + 1,
                min(position + max_gap + 2, len(content_words))
            ):

                if content_words[next_position] == word:
                    position = next_position
                    found = True
                    break

            if not found:
                matched = False
                break

        if matched:
            return True

    return False


def analyse_campaign_content(content, brand_id):

    conn = get_connection()

    guidelines = conn.execute(
        """
        SELECT category, rule, severity
        FROM guidelines
        WHERE brand_id = ?
        """,
        (brand_id,)
    ).fetchall()

    conn.close()

    findings = []

    severity_weights = {
        "low": 5,
        "medium": 10,
        "high": 20,
        "critical": 30
    }

    for category, rule, severity in guidelines:

        category_lower = str(category or "").lower()
        rule_text = str(rule or "").strip()
        severity_text = str(severity or "Medium").strip()

        if not rule_text:
            continue

        restricted_category = any(
            word in category_lower
            for word in [
                "restricted",
                "prohibited",
                "forbidden",
                "claim risk",
                "claim"
            ]
        )

        required_category = "required term" in category_lower

        if restricted_category and phrase_matches(
            rule_text, content
        ):

            findings.append({
                "category": category,
                "rule": rule_text,
                "severity": severity_text,
                "reason": (
                    "Potentially restricted wording was detected "
                    "in the campaign content."
                )
            })

        elif required_category and not phrase_matches(
            rule_text, content
        ):

            findings.append({
                "category": category,
                "rule": rule_text,
                "severity": severity_text,
                "reason": (
                    "A required term was not found "
                    "in the campaign content."
                )
            })

    total_deduction = sum(
        severity_weights.get(
            item["severity"].lower(), 10
        )
        for item in findings
    )

    score = max(0, 100 - total_deduction)

    status = "Compliant" if not findings else "Needs Review"

    return score, status, findings


def save_version_analysis(version_id, content, brand_id):

    score, status, findings = analyse_campaign_content(
        content,
        brand_id
    )

    conn = get_connection()

    conn.execute(
        """
        UPDATE asset_versions
        SET score = ?,
            compliance_status = ?,
            violations = ?
        WHERE id = ?
        """,
        (
            score,
            status,
            json.dumps(findings),
            version_id
        )
    )

    conn.commit()
    conn.close()

    return score, status, findings


# ==================================================
# 3. LOAD BRANDS
# ==================================================

conn = get_connection()

brands = conn.execute(
    """
    SELECT id, brand_name
    FROM brands
    ORDER BY brand_name
    """
).fetchall()

conn.close()

if not brands:
    st.warning("Create a brand before starting a campaign.")
    st.stop()

brand_options = {
    row[0]: row[1]
    for row in brands
}


# ==================================================
# 4. CREATE CAMPAIGN
# ==================================================

st.header("➕ Create New Campaign")

with st.form("create_campaign_form"):

    selected_brand_id = st.selectbox(
        "Select Brand",
        list(brand_options.keys()),
        format_func=lambda x: (
            f"{brand_options[x]} (ID: {x})"
        )
    )

    campaign_name = st.text_input(
        "Campaign Name",
        placeholder="Example: CodeX Product Launch 2026"
    )

    campaign_description = st.text_area(
        "Campaign Description",
        placeholder="Describe the purpose of this campaign..."
    )

    create_campaign = st.form_submit_button(
        "Create Campaign",
        type="primary"
    )

    if create_campaign:

        if not campaign_name.strip():

            st.error("Please enter a campaign name.")

        else:

            conn = get_connection()

            existing = conn.execute(
                """
                SELECT id FROM campaigns
                WHERE brand_id = ? AND campaign_name = ?
                """,
                (
                    selected_brand_id,
                    campaign_name.strip()
                )
            ).fetchone()

            if existing:

                st.warning(
                    "A campaign with this name already exists "
                    "for the selected brand."
                )

            else:

                conn.execute(
                    """
                    INSERT INTO campaigns
                    (brand_id, campaign_name, description)
                    VALUES (?, ?, ?)
                    """,
                    (
                        selected_brand_id,
                        campaign_name.strip(),
                        campaign_description.strip()
                    )
                )

                conn.commit()

                st.success("Campaign created successfully!")

            conn.close()


st.divider()


# ==================================================
# 5. LOAD CAMPAIGNS
# ==================================================

st.header("📋 Your Campaigns")

conn = get_connection()

campaigns = conn.execute(
    """
    SELECT
        campaigns.id,
        campaigns.campaign_name,
        campaigns.description,
        campaigns.status,
        campaigns.created_at,
        brands.brand_name,
        campaigns.brand_id
    FROM campaigns
    JOIN brands
        ON campaigns.brand_id = brands.id
    ORDER BY campaigns.id DESC
    """
).fetchall()

conn.close()


if not campaigns:

    st.info("No campaigns created yet.")

else:

    for campaign in campaigns:

        (
            campaign_id,
            name,
            description,
            status,
            created_at,
            brand_name,
            brand_id
        ) = campaign

        with st.expander(
            f"📁 {name} — {brand_name}"
        ):

            st.write(
                "**Description:**",
                description or "No description"
            )

            st.write("**Status:**", status)

            st.caption(f"Created: {created_at}")


            # ======================================
            # 6. ADD CAMPAIGN ASSET
            # ======================================

            st.subheader("➕ Add Campaign Asset")

            with st.form(f"asset_form_{campaign_id}"):

                asset_name = st.text_input(
                    "Asset Name",
                    placeholder="Example: Instagram Launch Poster"
                )

                channel = st.selectbox(
                    "Content Channel",
                    [
                        "Instagram Post",
                        "Facebook Post",
                        "Facebook Advertisement",
                        "LinkedIn Post",
                        "Website Content",
                        "Email Campaign",
                        "General Document"
                    ]
                )

                initial_content = st.text_area(
                    "Initial Content",
                    placeholder="Enter the original campaign content...",
                    height=150
                )

                add_asset = st.form_submit_button(
                    "Add Asset",
                    type="primary"
                )

                if add_asset:

                    if (
                        not asset_name.strip()
                        or not initial_content.strip()
                    ):

                        st.error(
                            "Please provide both asset name "
                            "and initial content."
                        )

                    else:

                        conn = get_connection()

                        cursor = conn.cursor()

                        cursor.execute(
                            """
                            INSERT INTO campaign_assets
                            (campaign_id, asset_name, channel)
                            VALUES (?, ?, ?)
                            """,
                            (
                                campaign_id,
                                asset_name.strip(),
                                channel
                            )
                        )

                        asset_id = cursor.lastrowid

                        cursor.execute(
                            """
                            INSERT INTO asset_versions
                            (
                                asset_id,
                                version_number,
                                content,
                                version_note
                            )
                            VALUES (?, 1, ?, ?)
                            """,
                            (
                                asset_id,
                                initial_content.strip(),
                                "Original version"
                            )
                        )

                        version_id = cursor.lastrowid

                        conn.commit()
                        conn.close()

                        score, result_status, findings = (
                            save_version_analysis(
                                version_id,
                                initial_content.strip(),
                                brand_id
                            )
                        )

                        st.success(
                            "Campaign asset and Version 1 saved!"
                        )

                        st.info(
                            f"Version 1 analysis: "
                            f"{score}/100 — {result_status}"
                        )


            # ======================================
            # 7. LOAD CAMPAIGN ASSETS
            # ======================================

            conn = get_connection()

            assets = conn.execute(
                """
                SELECT id, asset_name, channel, created_at
                FROM campaign_assets
                WHERE campaign_id = ?
                ORDER BY id DESC
                """,
                (campaign_id,)
            ).fetchall()

            conn.close()

            st.subheader("📄 Campaign Assets")

            if not assets:

                st.info(
                    "No assets added to this campaign yet."
                )

            else:

                for asset in assets:

                    (
                        asset_id,
                        asset_name,
                        asset_channel,
                        asset_created
                    ) = asset

                    st.markdown(f"### {asset_name}")

                    st.caption(
                        f"{asset_channel} | Created: {asset_created}"
                    )


                    # ==================================
                    # LOAD VERSIONS
                    # ==================================

                    conn = get_connection()

                    versions = conn.execute(
                        """
                        SELECT
                            id,
                            version_number,
                            content,
                            score,
                            compliance_status,
                            review_status,
                            version_note,
                            created_at,
                            violations
                        FROM asset_versions
                        WHERE asset_id = ?
                        ORDER BY version_number DESC
                        """,
                        (asset_id,)
                    ).fetchall()

                    conn.close()


                    # ==================================
                    # 8. CREATE NEW VERSION
                    # ==================================

                    latest_content = (
                        versions[0][2] if versions else ""
                    )

                    latest_number = max(
                        (version[1] for version in versions),
                        default=0
                    )

                    next_version = latest_number + 1

                    st.subheader("✏️ Create New Version")

                    with st.form(
                        f"new_version_form_{asset_id}"
                    ):

                        updated_content = st.text_area(
                            f"Content for Version {next_version}",
                            value=latest_content,
                            height=150
                        )

                        version_note_input = st.text_input(
                            "What changed?",
                            placeholder="Example: Removed restricted claims"
                        )

                        save_new_version = st.form_submit_button(
                            f"Save Version {next_version}",
                            type="primary"
                        )

                        if save_new_version:

                            if not updated_content.strip():

                                st.error("Content cannot be empty.")

                            else:

                                conn = get_connection()

                                cursor = conn.cursor()

                                cursor.execute(
                                    """
                                    INSERT INTO asset_versions
                                    (
                                        asset_id,
                                        version_number,
                                        content,
                                        version_note
                                    )
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (
                                        asset_id,
                                        next_version,
                                        updated_content.strip(),
                                        version_note_input.strip()
                                        or f"Version {next_version}"
                                    )
                                )

                                new_version_id = cursor.lastrowid

                                conn.commit()
                                conn.close()

                                score, result_status, findings = (
                                    save_version_analysis(
                                        new_version_id,
                                        updated_content.strip(),
                                        brand_id
                                    )
                                )

                                st.success(
                                    f"Version {next_version} saved "
                                    f"and analysed: {score}/100"
                                )

                                st.rerun()


                    # ==================================
                    # 9. VERSION COMPARISON
                    # ==================================

                    if len(versions) >= 2:

                        st.subheader("📊 Version Comparison")

                        latest = versions[0]
                        previous = versions[1]

                        col1, col2 = st.columns(2)

                        with col1:

                            st.markdown(
                                f"**Version {previous[1]}**"
                            )

                            if previous[3] is not None:

                                st.metric(
                                    "Compliance Score",
                                    f"{previous[3]}/100"
                                )

                            else:

                                st.warning("Not analysed yet.")

                            st.text_area(
                                "Previous content",
                                value=previous[2],
                                height=140,
                                disabled=True,
                                key=f"previous_{asset_id}"
                            )

                        with col2:

                            st.markdown(
                                f"**Version {latest[1]}**"
                            )

                            if latest[3] is not None:

                                st.metric(
                                    "Compliance Score",
                                    f"{latest[3]}/100"
                                )

                            else:

                                st.warning("Not analysed yet.")

                            st.text_area(
                                "Latest content",
                                value=latest[2],
                                height=140,
                                disabled=True,
                                key=f"latest_{asset_id}"
                            )

                        if (
                            latest[3] is not None
                            and previous[3] is not None
                        ):

                            difference = latest[3] - previous[3]

                            if difference > 0:

                                st.success(
                                    f"Compliance improved by "
                                    f"{difference} points."
                                )

                            elif difference < 0:

                                st.warning(
                                    f"Compliance decreased by "
                                    f"{abs(difference)} points."
                                )

                            else:

                                st.info(
                                    "Compliance score unchanged."
                                )


                    # ==================================
                    # 10. VERSION HISTORY
                    # ==================================

                    st.subheader("🕘 Version History")

                    for version in versions:

                        (
                            version_id,
                            version_number,
                            content,
                            score,
                            compliance_status,
                            review_status,
                            version_note,
                            version_created,
                            violations
                        ) = version

                        with st.expander(
                            f"Version {version_number} — "
                            f"{compliance_status or 'Not analysed'}"
                        ):

                            st.write(content)

                            st.caption(
                                f"Note: {version_note or 'No note'}"
                            )

                            st.caption(
                                f"Created: {version_created}"
                            )

                            if score is None:

                                if st.button(
                                    "🔍 Analyse Version",
                                    key=f"analyse_{version_id}"
                                ):

                                    save_version_analysis(
                                        version_id,
                                        content,
                                        brand_id
                                    )

                                    st.success("Analysis completed!")

                                    st.rerun()

                            else:

                                st.metric(
                                    "Compliance Score",
                                    f"{score}/100"
                                )

                                st.write(
                                    "Compliance Status:",
                                    compliance_status
                                )

                                st.write(
                                    "Review Status:",
                                    review_status
                                )

                                try:

                                    findings = json.loads(
                                        violations or "[]"
                                    )

                                except (
                                    json.JSONDecodeError,
                                    TypeError
                                ):

                                    findings = []

                                if findings:

                                    st.warning(
                                        f"{len(findings)} potential "
                                        "compliance issue(s) detected."
                                    )

                                    for finding in findings:

                                        st.markdown(
                                            f"**{finding['severity']} — "
                                            f"{finding['category']}**"
                                        )

                                        st.write(
                                            "Rule:",
                                            finding["rule"]
                                        )

                                        st.caption(
                                            finding["reason"]
                                        )

                                else:

                                    st.success(
                                        "No matching guideline "
                                        "violations detected."
                                    )

                    st.divider()
