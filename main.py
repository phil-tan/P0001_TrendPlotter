import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import StringIO
import warnings
warnings.filterwarnings('ignore')

from utils import detect_date_format, is_valid_time_series

# Page configuration
st.set_page_config(page_title="Trend Plotter", layout="wide")
st.title("📊 Trend Plotter")

# Initialize session state
if "dataframes" not in st.session_state:
    st.session_state.dataframes = {}

# Sidebar for data upload
st.sidebar.header("📁 Data Management")

# Manual date format override
st.sidebar.subheader("📅 Date Format")
force_dayfirst = st.sidebar.checkbox("Force Day-first format (DD/MM/YYYY)", value=False)

# File uploader
uploaded_files = st.sidebar.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# Process uploaded files
if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state.dataframes:
            try:
                # Read file based on extension
                if file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file)
                else:  # CSV
                    df = pd.read_csv(file)
                
                # Try to convert first column to datetime
                try:
                    # Validate that first column is actually time series data
                    if not is_valid_time_series(df.iloc[:, 0]):
                        st.sidebar.error(f"❌ {file.name}: First column must contain datetime values. File rejected.")
                        continue
                    
                    # Use forced format or auto-detect
                    if force_dayfirst:
                        detected_dayfirst = True
                        format_msg = "📅 Day-first (forced)"
                    else:
                        detected_dayfirst = detect_date_format(df.iloc[:, 0])
                        format_msg = "🔍 Day-first detected" if detected_dayfirst else "🔍 Month-first detected"
                    
                    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], dayfirst=detected_dayfirst)
                    
                    st.session_state.dataframes[file.name] = df
                    st.sidebar.success(f"✓ {file.name} loaded ({format_msg})")
                except Exception as e:
                    st.sidebar.error(f"❌ {file.name}: First column is not datetime format. File rejected.")
            except Exception as e:
                st.sidebar.error(f"❌ Error reading {file.name}: {str(e)}")

# Display uploaded files
if st.session_state.dataframes:
    st.sidebar.subheader("Loaded Files:")
    for file_name in st.session_state.dataframes.keys():
        st.sidebar.text(f"✓ {file_name}")

# Clear data button
if st.sidebar.button("🗑️ Clear Data", use_container_width=True):
    st.session_state.dataframes = {}
    st.rerun()

# Main content area

if not st.session_state.dataframes:
    st.info("📤 Upload CSV or Excel files to get started. The first column should be a timestamp.")
else:
    # Combine all dataframes
    combined_df = pd.concat(
        st.session_state.dataframes.values(),
        ignore_index=False,
        sort=False
    )
    
    # Get all available columns (excluding timestamp)
    timestamp_col = combined_df.columns[0]
    available_cols = list(combined_df.columns[1:])
    
    # Resample interval selection
    st.sidebar.subheader("⏱️ Resample Data")
    resample_map = {
        "Original": None,
        "10 min": "10min",
        "15 min": "15min",
        "30 min": "30min",
        "1 hr": "1h",
        "3 hr": "3h",
        "6 hr": "6h",
        "12 hr": "12h",
        "1 day": "1d",
        "1 week": "1w",
        "1 month": "1MS"
    }
    
    resample_option = st.sidebar.selectbox(
        "Time Interval:",
        list(resample_map.keys()),
        index=0
    )
    
    # Apply resampling if selected
    if resample_map[resample_option]:
        # Set timestamp as index for resampling
        df_resampled = combined_df.set_index(timestamp_col)
        df_resampled = df_resampled.resample(resample_map[resample_option]).mean()
        df_resampled = df_resampled.reset_index()
        display_df = df_resampled
    else:
        display_df = combined_df


    # Show data summary
    with st.expander("📊 Data Summary"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", len(display_df))
        with col2:
            st.metric("Columns", len(display_df.columns))
        with col3:
            st.metric("Files Loaded", len(st.session_state.dataframes))
        with col4:
            st.metric("Resampling", resample_option)
        
        # Date range
        col5, col6 = st.columns(2)
        min_date = display_df[timestamp_col].min()
        max_date = display_df[timestamp_col].max()
        with col5:
            st.metric("Start Date", min_date.strftime("%Y-%m-%d %H:%M"))
        with col6:
            st.metric("End Date", max_date.strftime("%Y-%m-%d %H:%M"))

    
    # Two-column layout for selections
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Primary Axis")
        primary_cols = st.multiselect(
            "Select columns for primary Y-axis:",
            available_cols,
            key="primary"
        )
    
    with col2:
        st.subheader("📉 Secondary Axis")
        secondary_cols = st.multiselect(
            "Select columns for secondary Y-axis:",
            available_cols,
            key="secondary"
        )
    
    # Create plot if columns are selected
    if primary_cols or secondary_cols:
        fig = go.Figure()
        
        # Add primary axis traces
        for col in primary_cols:
            fig.add_trace(
                go.Scatter(
                    x=display_df[timestamp_col],
                    y=display_df[col],
                    name=col,
                    yaxis="y1"
                )
            )
        
        # Add secondary axis traces
        for col in secondary_cols:
            fig.add_trace(
                go.Scatter(
                    x=display_df[timestamp_col],
                    y=display_df[col],
                    name=col,
                    yaxis="y2"
                )
            )
        
        # Update layout with secondary axis
        fig.update_layout(
            title="Trend Plot",
            xaxis_title=timestamp_col,
            yaxis=dict(title="Primary Axis", side="left"),
            yaxis2=dict(title="Secondary Axis", side="right", overlaying="y"),
            hovermode="x unified",
            height=500,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("👆 Select at least one column to display a chart")
    
    # Display combined dataframe
    st.subheader("📋 Combined Data")
    st.dataframe(display_df, use_container_width=True)


