
import streamlit as st
import pandas as pd
import json
from collections import Counter, defaultdict
from datetime import datetime
import numpy as np
import plotly.express as px

# Utility functions
def extract_company_name(company):
    if isinstance(company, dict):
        return company.get('name', str(company))
    return str(company)

def clean_ctc(ctc):
    # Extract value
    if isinstance(ctc, dict):
        val = ctc.get('value', None)
    elif isinstance(ctc, list):
        val = ctc[0] if ctc else None
    else:
        val = ctc
    # Normalize: convert to lakh (divide by 100000 if it's in absolute value)
    try:
        num = float(val)
        if num >= 1000:
            return num / 100000  # Convert to lakh
        else:
            return num  # Already in lakh
    except:
        return None

def clean_cutoff(cutoff):
    if isinstance(cutoff, dict):
        return cutoff.get('value', None)
    if isinstance(cutoff, list):
        return cutoff[0] if cutoff else None
    return cutoff


# Sidebar navigation for year selection
st.sidebar.title("Select Year")
year_page = st.sidebar.radio("Go to:", ["2024 Company Stats", "2025 Company Stats"])

if year_page == "2024 Company Stats":
    st.title('DTU RM Data Analysis Dashboard - 2024')
    st.markdown("""
    <span style='color:red;'>⚠️ <b>Disclaimer:</b></span> Data is estimated, unofficial, and for info only. Source: RM, 'trust me bro'. Not responsible for any use. Do not copy or redistribute.
    """, unsafe_allow_html=True)
    with open('./jobs.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)
elif year_page == "2025 Company Stats":
    st.title('DTU RM Data Analysis Dashboard - 2025')
    with open('./jobs2025.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)

# Normalize data for DataFrame
for job in jobs:
    job['company_name'] = extract_company_name(job.get('company'))
    job['ctc_clean'] = clean_ctc(job.get('ctc'))
    job['cutoff_clean'] = clean_cutoff(job.get('cutoff'))
df = pd.DataFrame(jobs)

st.markdown("""
This dashboard provides comprehensive insights into arriving companies data at DTU. Use the filters in the sidebar to customize your analysis.

**How to use this dashboard:**
- **Job Type**: Choose between FTE positions only or include internships in the analysis
- **Time Filter**: Select how you want to group data (Year/Month/Week)
- **CTC Range**: Adjust the salary range to focus on specific compensation brackets (in lakhs)
- **High CTC Threshold**: Set threshold to identify high-paying opportunities

**Understanding the visualizations:**
- Charts show trends and distributions across different time periods
- All CTC values are displayed in lakhs for better readability
- Data is filtered based on your selections to provide targeted insights
- Interactive elements allow you to drill down into specific months or companies
""")    

# Sidebar filters - removed branch and cutoff filters
st.sidebar.header("Filters")

# Job Type Filter
job_type_options = ['FTE Only', 'Include Internships']
selected_job_type = st.sidebar.selectbox('Job Type', job_type_options, index=0)

# CTC range slider (use lakh values)
ctc_numeric = pd.to_numeric(df['ctc_clean'], errors='coerce')
ctc_numeric = ctc_numeric.dropna()
if not ctc_numeric.empty:
    ctc_min, ctc_max = int(ctc_numeric.min()), int(ctc_numeric.max())
else:
    ctc_min, ctc_max = 0, 50
ctc_range = st.sidebar.slider('CTC Range (₹ Lakhs)', min_value=ctc_min, max_value=ctc_max, value=(ctc_min, ctc_max), format='%d')

# Default to Month for time filter
time_filter = st.sidebar.selectbox('Time Filter', ['Month', 'Year', 'Week'], index=0)

# Use 'applicationOpen' as the main date field for timeline analysis
date_field = 'applicationOpen' if 'applicationOpen' in df.columns else None
if date_field:
    df['date_parsed'] = pd.to_datetime(df[date_field], errors='coerce')
else:
    df['date_parsed'] = pd.NaT
if time_filter == 'Year':
    df['period'] = df['date_parsed'].dt.year
elif time_filter == 'Month':
    df['period'] = df['date_parsed'].dt.to_period('M').astype(str)
elif time_filter == 'Week':
    df['period'] = df['date_parsed'].dt.strftime('%Y-W%U')
else:
    df['period'] = None

periods = sorted(df['period'].dropna().unique())
selected_period = st.sidebar.selectbox('Select Period', ['All'] + list(periods))

# Filter data
def filter_data(df):
    filtered = df.copy()
    
    # Filter by job type
    if selected_job_type == 'FTE Only':
        filtered = filtered[filtered['jobType'] == 'fte']
    # If 'Include Internships' is selected, we include all job types
    
    # Filter by CTC range
    filtered = filtered[(pd.to_numeric(filtered['ctc_clean'], errors='coerce') >= ctc_range[0]) & (pd.to_numeric(filtered['ctc_clean'], errors='coerce') <= ctc_range[1])]
    # Filter by selected period
    if selected_period != 'All':
        filtered = filtered[filtered['period'] == selected_period]
    return filtered

filtered_df = filter_data(df)

# --- Companies per Branch Section (Commented Out) ---
# st.header('📊 Companies per Branch')
# st.markdown("""
# **What this shows:** Number of unique companies that have opened positions for each engineering branch.
# This helps identify which branches have more recruitment opportunities.
# """)
# branch_counts = defaultdict(set)
# for _, row in filtered_df.iterrows():
#     branches = row.get('branches', [])
#     if isinstance(branches, list):
#         for branch in branches:
#             branch_counts[branch].add(row.get('company_name'))
# branch_counts = {k: len(v) for k, v in branch_counts.items()}
# if branch_counts:
#     st.bar_chart(pd.Series(branch_counts))
# else:
#     st.info("No data available for the selected filters.")

# --- Top CTC Offers Section ---
st.header('🏆 Top CTC Offers')
st.markdown("""
**What this shows:** Highest compensation packages offered, showing company details, CTC amount, and the time period when the offer was made.
This helps identify the best opportunities and trends in high-paying positions.
""")

top_ctc_df = filtered_df.dropna(subset=['ctc_clean', 'company_name']).copy()
top_ctc_df['ctc_numeric'] = pd.to_numeric(top_ctc_df['ctc_clean'], errors='coerce')
top_ctc_df = top_ctc_df.dropna(subset=['ctc_numeric'])

if not top_ctc_df.empty:
    # Sort by CTC and get top 20
    top_ctc_offers = top_ctc_df.nlargest(20, 'ctc_numeric')
    
    # Create a display dataframe with relevant columns
    display_df = top_ctc_offers[['company_name', 'ctc_numeric', 'period', 'jobType', 'location']].copy()
    display_df.columns = ['Company Name', 'CTC (₹ Lakhs)', 'Period', 'Job Type', 'Location']
    display_df = display_df.reset_index(drop=True)
    display_df.index = display_df.index + 1  # Start index from 1
    
    st.dataframe(display_df, use_container_width=True)
    
    # Show summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Highest CTC", f"₹{top_ctc_offers['ctc_numeric'].max():.2f} Lakhs")
    with col2:
        st.metric("Average Top 10 CTC", f"₹{top_ctc_offers.head(10)['ctc_numeric'].mean():.2f} Lakhs")
    with col3:
        st.metric("Companies in Top 20", len(top_ctc_offers['company_name'].unique()))
else:
    st.info("No CTC data available for the selected filters.")



# --- High CTC Companies per Month (Bar Chart, Box Plot, Heatmap) ---
st.header('💰 High CTC Companies Analysis')
st.markdown("""
**What this shows:** Analysis of companies offering high compensation packages.
- **Bar Chart:** Number of companies per month offering salaries above the threshold
- **Box Plot:** Distribution of CTC values across months, showing median, quartiles, and outliers
- **Heatmap:** Average CTC offered by each company across different months

**💡 Tip:** Adjust the 'High CTC Threshold' in the sidebar to see how many companies offer packages above your desired salary level. 
A higher threshold will show fewer companies but those with premium packages, while a lower threshold will include more opportunities.
""")

# Apply job type filter to the main dataframe for this analysis
analysis_df = df.copy()
if selected_job_type == 'FTE Only':
    analysis_df = analysis_df[analysis_df['jobType'] == 'fte']

ctc_threshold = st.sidebar.number_input('High CTC Threshold (₹ Lakhs)', 
                                       min_value=ctc_min, max_value=ctc_max, 
                                       value=10, format='%d',
                                       help="Companies offering CTC above this threshold will be highlighted in the analysis")

analysis_df['ctc_num'] = pd.to_numeric(analysis_df['ctc_clean'], errors='coerce')
analysis_df['month'] = analysis_df['date_parsed'].dt.to_period('M').astype(str)
high_ctc_df = analysis_df[analysis_df['ctc_num'] >= ctc_threshold]
month_high_ctc_counts = high_ctc_df.groupby('month')['company_name'].nunique().sort_values(ascending=False)

if not month_high_ctc_counts.empty:
    st.subheader('High CTC Companies per Month')
    
    # Create interactive bar chart
    month_company_details = high_ctc_df.groupby('month').apply(
        lambda x: x[['company_name', 'ctc_num', 'name', 'location']].to_dict('records')
    ).to_dict()
    
    # Display the bar chart
    selected_month = st.selectbox(
        'Select a month to see detailed company information:',
        ['All Months'] + list(month_high_ctc_counts.index),
        key='month_selector'
    )
    
    st.bar_chart(month_high_ctc_counts)
    
    # Show detailed information for selected month
    if selected_month != 'All Months' and selected_month in month_company_details:
        st.subheader(f'Companies with High CTC in {selected_month}')
        month_data = month_company_details[selected_month]
        
        if month_data:
            # Create a detailed dataframe
            detail_df = pd.DataFrame(month_data)
            detail_df = detail_df.drop_duplicates(subset=['company_name'])
            detail_df.columns = ['Company Name', 'CTC (₹ Lakhs)', 'Job Title', 'Location']
            detail_df = detail_df.sort_values('CTC (₹ Lakhs)', ascending=False)
            detail_df = detail_df.reset_index(drop=True)
            detail_df.index = detail_df.index + 1
            
            st.dataframe(detail_df, use_container_width=True)
        else:
            st.info("No detailed data available for this month.")
else:
    st.info(f"No companies found offering CTC above {ctc_threshold} lakhs in the selected period.")

# Box plot: CTC distribution per month with hover info
box_data = analysis_df.dropna(subset=['month', 'ctc_num'])
if not box_data.empty:
    st.subheader('CTC Distribution per Month')
    fig_box = px.box(box_data, x='month', y='ctc_num', points='all', 
                     title='CTC Distribution per Month (in Lakhs)', 
                     hover_data=['company_name', 'ctc_num'],
                     labels={'ctc_num': 'CTC (₹ Lakhs)', 'month': 'Month'})
    st.plotly_chart(fig_box)
else:
    st.info("No valid data available for CTC distribution analysis.")

# Heatmap: Month vs CTC
# --- Company CTC Heatmap by Month (Commented Out) ---
# heatmap_data = analysis_df.dropna(subset=['month', 'ctc_num'])
# if not heatmap_data.empty:
#     st.subheader('Company CTC Heatmap by Month')
#     heatmap_pivot = heatmap_data.pivot_table(index='month', columns='company_name', values='ctc_num', aggfunc='mean').fillna(0)
#     if not heatmap_pivot.empty:
#         st.dataframe(heatmap_pivot.style.background_gradient(cmap='RdYlGn'))
#     else:
#         st.info("No data available for heatmap visualization.")
# else:
#     st.info("No valid data available for heatmap analysis.")

# --- Companies per period (month/year/week) ---
st.header(f'📈 Companies per {time_filter}')
st.markdown(f"""
**What this shows:** Timeline view of recruitment activity showing the number of unique companies 
that posted job opportunities in each {time_filter.lower()}. This helps identify peak recruitment periods.
""")
period_counts = filtered_df.groupby('period')['company_name'].nunique()
if not period_counts.empty:
    st.line_chart(period_counts)
else:
    st.info("No data available for the selected time period.")

# --- Average CTC per period ---
st.header(f'💵 Average CTC per {time_filter}')
st.markdown(f"""
**What this shows:** Trend of average compensation packages offered across different {time_filter.lower()}s.
Values are displayed in lakhs. This helps identify if salaries are trending upward or downward over time.
""")
avg_ctc_period = filtered_df.groupby('period')['ctc_clean'].apply(lambda x: pd.to_numeric(x, errors='coerce').mean())
if not avg_ctc_period.empty:
    st.line_chart(avg_ctc_period)
else:
    st.info("No data available for average CTC analysis.")


# Top recruiters
st.header('🏆 Top Recruiters')
st.markdown("""
**What this shows:** Companies that have posted the most job opportunities, ranked by frequency.
This identifies the most active recruiters on campus.
""")
top_recruiters = filtered_df['company_name'].value_counts().head(10)
if not top_recruiters.empty:
    st.table(top_recruiters)
else:
    st.info("No recruiter data available for the selected filters.")



# Average CTC overall
st.header('📊 Average CTC Overall')
st.markdown("""
**What this shows:** Overall average compensation package across all companies and time periods 
within your selected filters. Values are displayed in lakhs.
""")
if 'ctc_clean' in filtered_df:
    try:
        avg_ctc = pd.to_numeric(filtered_df['ctc_clean'], errors='coerce').mean()
        if not pd.isna(avg_ctc):
            st.metric('Average CTC (₹ Lakhs)', f'{avg_ctc:.2f}')
        else:
            st.info('No valid CTC data available for calculation.')
    except:
        st.info('CTC data could not be processed.')
else:
    st.info('No CTC data available.')


# --- Raw Data Section (Commented Out) ---
# st.header('📋 Raw Data')
# st.markdown("""
# **What this shows:** Complete dataset with all available information for jobs matching your selected filters.
# You can explore individual records and export this data for further analysis.
# """)
# if not filtered_df.empty:
#     st.dataframe(filtered_df)
#     st.info(f"Showing {len(filtered_df)} records out of {len(df)} total records.")
# else:
#     st.info("No data matches your current filter selections.")
