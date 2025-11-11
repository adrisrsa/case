# streamlit_app.py

import streamlit as st
import pandas as pd
import datetime


# ==========================================================
# 🔧 HELPER: Format numeric columns for display
# ==========================================================
def format_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Format numeric columns consistently for dashboard display."""
    df_fmt = df.copy()

    thousand_cols = [
        "Spend ($)", "Installs", "Impressions",
        "Revenue D7", "Payers D7", "Total Budget ($)"
    ]
    percent_cols = ["Attribution %", "Payers %"]
    decimal_cols = ["CPI", "IPM", "CPM", "ARPI", "ARPP"]

    for col in df_fmt.columns:
        if col in thousand_cols and col in df_fmt:
            df_fmt[col] = df_fmt[col].apply(
                lambda x: f"{x:,.0f}".replace(",", ".") if pd.notna(x) and isinstance(x, (int, float)) else x
            )
        elif col in percent_cols and col in df_fmt:
            df_fmt[col] = df_fmt[col].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) and isinstance(x, (int, float)) else x
            )
        elif col in decimal_cols and col in df_fmt:
            df_fmt[col] = df_fmt[col].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
            )

    return df_fmt



# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="CTV Campaign Dashboard",
    layout="wide"
)

# --- DATA LOADING FUNCTION ---
@st.cache_data
def load_data():
    df = pd.read_csv("Dataset.csv")

    # --- CLEAN DATA ---
    df["Impressions"] = df["Impressions"].astype(str).str.replace(",", "").astype(int)
    df["Attribution %"] = df["Attribution %"].astype(str).str.replace("%", "").astype(float) / 100
    df["ROAS D7"] = df["ROAS D7"].astype(str).str.replace("%", "").astype(float) / 100
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%y")

    # --- ROW-LEVEL CALCULATED FIELDS ---
    df["CPI"] = df["Spend ($)"] / df["Installs"]
    df["IPM"] = df["Installs"] / (df["Impressions"] / 1000)
    df["CPM"] = df["Spend ($)"] / (df["Impressions"] / 1000)
    df["ROAS D7_calc"] = df["Revenue D7"] / df["Spend ($)"]
    df["Payers %"] = df["Payers D7"] / df["Installs"]
    df["ARPI"] = df["Revenue D7"] / df["Installs"]
    df["ARPP"] = df["Revenue D7"] / df["Payers D7"]

    # Replace division errors
    df.replace([float("inf"), -float("inf")], pd.NA, inplace=True)
    df.fillna(0, inplace=True)

    return df

df = load_data()

# --- AGGREGATION FUNCTION ---
def aggregate_data(df, group_cols):
    agg = df.groupby(group_cols, as_index=False).agg({
        "Spend ($)": "sum",
        "Installs": "sum",
        "Impressions": "sum",
        "Payers D7": "sum",
        "Revenue D7": "sum",
        "Attribution %": "mean"
    })

    # --- RECALCULATE KPIs ---
    agg["CPI"] = agg["Spend ($)"] / agg["Installs"]
    agg["IPM"] = agg["Installs"] / (agg["Impressions"] / 1000)
    agg["CPM"] = agg["Spend ($)"] / (agg["Impressions"] / 1000)
    agg["ROAS D7"] = agg["Revenue D7"] / agg["Spend ($)"]
    agg["Payers %"] = agg["Payers D7"] / agg["Installs"]
    agg["ARPI"] = agg["Revenue D7"] / agg["Installs"]
    agg["ARPP"] = agg["Revenue D7"] / agg["Payers D7"]

    agg.replace([float("inf"), -float("inf")], pd.NA, inplace=True)
    agg.fillna(0, inplace=True)

    return agg

# ==========================================================
# 🧭 SIDEBAR FILTERS (clean + stable version)
# ==========================================================
st.sidebar.header("Filters")

# --- APP FILTER ---
apps = df["App Name"].unique().tolist()
selected_apps = st.sidebar.multiselect(
    "Select App(s)",
    options=apps,
    default=apps  # All selected by default
)

filtered_df = df[df["App Name"].isin(selected_apps)]

# --- CAMPAIGN FILTER ---
campaigns = filtered_df["Campaign Id"].unique().tolist()
selected_campaigns = st.sidebar.multiselect(
    "Select Campaign(s)",
    options=campaigns,
    default=campaigns
)
filtered_df = filtered_df[filtered_df["Campaign Id"].isin(selected_campaigns)]

# --- CREATIVE FILTER ---
creatives = filtered_df["Creative Id"].unique().tolist()
selected_creatives = st.sidebar.multiselect(
    "Select Creative(s)",
    options=creatives,
    default=creatives
)
filtered_df = filtered_df[filtered_df["Creative Id"].isin(selected_creatives)]

# --- SAFE DATE RANGE SELECTOR ---
import datetime

if not filtered_df.empty and filtered_df["Date"].notna().any():
    min_date = pd.to_datetime(filtered_df["Date"].min()).date()
    max_date = pd.to_datetime(filtered_df["Date"].max()).date()
else:
    # fallback defaults if dataset empty
    min_date = datetime.date(2025, 1, 1)
    max_date = datetime.date.today()

selected_dates = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# --- APPLY DATE FILTER ---
if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    filtered_df = filtered_df[
        (filtered_df["Date"] >= pd.to_datetime(start_date)) &
        (filtered_df["Date"] <= pd.to_datetime(end_date))
    ]

# --- OPTIONAL WARNING ---
if filtered_df.empty:
    st.sidebar.warning("⚠️ No data available for the selected filters.")


#DEFINING BUDGETS

# --- Daily budgets per app ---
daily_budget = {
    "MaxiBingo": 4000,
    # Default for all other apps
    "default": 2000
}



# --- MAIN DASHBOARD STRUCTURE ---

# Create only two tabs now
tab_general, tab_app = st.tabs(["📊 General", "📱 App Analysis"])

# ==========================================================
# 🟢 TAB 1: GENERAL
# ==========================================================
with tab_general:
    st.markdown("## 📊 General Overview")

    # --- KPI Section ---
    total_spend = filtered_df["Spend ($)"].sum()
    total_revenue = filtered_df["Revenue D7"].sum()
    roas = (total_revenue / total_spend * 100) if total_spend > 0 else 0

    col1, col2 = st.columns(2)
    col1.metric("Total Spend ($)", f"{total_spend:,.0f}")
    col2.metric("ROAS D7 (%)", f"{roas:.1f}%")

    st.divider()

    # ==========================================================
    # 💵 VISUAL BUDGET USAGE (progress bars only)
    # ==========================================================
    st.markdown("### Visual Budget Usage")

    # --- Calculate number of days in selected range ---
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = filtered_df["Date"].min()
        end_date = filtered_df["Date"].max()
    num_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1

    # --- Aggregate spend per app ---
    spend_by_app = aggregate_data(filtered_df, ["App Name"])[["App Name", "Spend ($)"]]

    for _, row in spend_by_app.iterrows():
        app_name = row["App Name"]
        spend = row["Spend ($)"]

        # Look up daily budget
        daily_cap = daily_budget.get(str(app_name).strip(), daily_budget["default"])
        total_budget = daily_cap * num_days
        pct_used = (spend / total_budget) * 100 if total_budget > 0 else 0

        # Progress visualization
        pct_display = min(pct_used / 100, 1.0)
        st.write(f"**{app_name}** — {pct_used:.1f}% of budget used (${spend:,.0f} / ${total_budget:,.0f})")
        st.progress(pct_display)

    st.divider()

    # ==========================================================
    # 🧮 PERFORMANCE BY APP
    # ==========================================================
    st.markdown("### Performance by App")

    app_level_df = aggregate_data(filtered_df, ["App Name"]).reset_index(drop=True)

    # Add % of budget used column
    app_level_df["Total Budget ($)"] = app_level_df["App Name"].apply(
        lambda x: daily_budget.get(str(x).strip(), daily_budget["default"]) * num_days
    )
    app_level_df["% of Budget Used"] = (
        app_level_df["Spend ($)"] / app_level_df["Total Budget ($)"] * 100
    )

    # Format % column
    app_level_df["ROAS D7"] = (app_level_df["ROAS D7"] * 100).round(1).astype(str) + "%"
    app_level_df["% of Budget Used"] = pd.to_numeric(
        app_level_df["% of Budget Used"], errors="coerce"
    ).round(1).astype(str) + "%"

    # --- Display (formatted) ---
    st.dataframe(format_metrics(app_level_df), use_container_width=True, hide_index=True)

    st.divider()

    # ==========================================================
    # 📅 PERFORMANCE BY DAY
    # ==========================================================
    st.markdown("### Performance by Day")

    day_level_df = aggregate_data(filtered_df, ["Date"])
    day_level_df["Date"] = pd.to_datetime(day_level_df["Date"]).dt.date
    day_level_df = day_level_df.sort_values("Date").reset_index(drop=True)

    # --- Calculate % of total budget used per day ---
    selected_app_names = filtered_df["App Name"].unique().tolist()
    day_total_budget = sum(
        daily_budget.get(str(app).strip(), daily_budget["default"]) for app in selected_app_names
    )

    day_level_df["Total Budget ($)"] = day_total_budget
    day_level_df["% of Budget Used"] = (
        day_level_df["Spend ($)"] / day_level_df["Total Budget ($)"] * 100
    )

    # Format % column
    day_level_df["ROAS D7"] = (day_level_df["ROAS D7"] * 100).round(1).astype(str) + "%"
    day_level_df["% of Budget Used"] = pd.to_numeric(
        day_level_df["% of Budget Used"], errors="coerce"
    ).round(1).astype(str) + "%"

    # --- Display (formatted) ---
    st.dataframe(format_metrics(day_level_df), use_container_width=True, hide_index=True)


# ==========================================================
# 🔵 TAB 2: APP ANALYSIS
# ==========================================================
with tab_app:
    st.markdown("## 📱 App Analysis")

    # --- Select one app ---
    apps = df["App Name"].unique().tolist()
    selected_app = st.selectbox("Select App", options=apps, index=0)

    app_df = df[df["App Name"] == selected_app]

    # --- App-level KPIs ---
    total_spend = app_df["Spend ($)"].sum()
    total_revenue = app_df["Revenue D7"].sum()
    total_installs = app_df["Installs"].sum()
    roas = (total_revenue / total_spend * 100) if total_spend > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Spend ($)", f"{total_spend:,.0f}")
    col2.metric("Revenue D7 ($)", f"{total_revenue:,.0f}")
    col3.metric("Installs", f"{total_installs:,}")
    col4.metric("ROAS D7 (%)", f"{roas:.1f}%")

    st.divider()

    # ==========================================================
    # 🎯 CAMPAIGN SUMMARY
    # ==========================================================
    st.markdown("### Campaign Summary")

    campaign_df = aggregate_data(app_df, ["App Name", "Campaign Id"])
    campaign_df = campaign_df.reset_index(drop=True)

    campaign_df["ROAS D7"] = (campaign_df["ROAS D7"] * 100).round(1).astype(str) + "%"
    campaign_df["% of Budget Used"] = (
        campaign_df["Spend ($)"] / (
            daily_budget.get(str(selected_app).strip(), daily_budget["default"]) * len(app_df["Date"].unique())
        ) * 100
    )
    campaign_df["% of Budget Used"] = pd.to_numeric(
        campaign_df["% of Budget Used"], errors="coerce"
    ).round(1).astype(str) + "%"

    st.dataframe(
        format_metrics(campaign_df[[
            "Campaign Id", "Spend ($)", "Revenue D7", "Installs", "Payers D7",
            "CPI", "CPM", "IPM", "ROAS D7", "Payers %", "ARPI", "ARPP", "% of Budget Used"
        ]]),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # ==========================================================
    # 🎨 CREATIVE SUMMARY
    # ==========================================================
    st.markdown("### Aggregated Creative Performance")

    creative_summary_df = aggregate_data(app_df, ["App Name", "Creative Id"])
    creative_summary_df = creative_summary_df.reset_index(drop=True)
    creative_summary_df["ROAS D7"] = (creative_summary_df["ROAS D7"] * 100).round(1).astype(str) + "%"

    st.dataframe(
        format_metrics(creative_summary_df[[
            "Creative Id", "Spend ($)", "Revenue D7", "Installs", "Payers D7",
            "CPI", "CPM", "IPM", "ROAS D7", "Payers %", "ARPI", "ARPP"
        ]]),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # ==========================================================
    # 📊 CAMPAIGN DETAILS
    # ==========================================================
    st.markdown("### 📊 Campaign Details")

    for campaign_id, campaign_df_sub in app_df.groupby("Campaign Id"):
        spend_camp = campaign_df_sub["Spend ($)"].sum()
        rev_camp = campaign_df_sub["Revenue D7"].sum()
        roas_camp = (rev_camp / spend_camp * 100) if spend_camp > 0 else 0

        with st.expander(f"🎯 Campaign {campaign_id} — Spend: ${spend_camp:,.0f} | ROAS: {roas_camp:.1f}%"):
            creative_df = aggregate_data(campaign_df_sub, ["App Name", "Campaign Id", "Creative Id"])
            creative_df = creative_df.reset_index(drop=True)
            creative_df["ROAS D7"] = (creative_df["ROAS D7"] * 100).round(1).astype(str) + "%"

            st.dataframe(
                format_metrics(creative_df[[
                    "Creative Id", "Spend ($)", "Revenue D7", "Installs", "Payers D7",
                    "CPI", "CPM", "IPM", "ROAS D7", "Payers %", "ARPI", "ARPP"
                ]]),
                use_container_width=True,
                hide_index=True
            )
