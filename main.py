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

# Create tabs
tab_analyze, tab_help = st.tabs(["Analyze", "Help"])

with tab_help:
    st.markdown("""
    ### Getting Started
    
    1. **Upload Data**
       - Click "Upload CSV or Excel files" in the sidebar
       - Select one or more CSV or Excel files containing time series data
       - The first column must contain timestamps (dates/times)
       - Files are kept in memory until you click "Clear Data"
    
    2. **Configure Date Format**
       - Use "Force Day-first format" checkbox if your dates are in DD/MM/YYYY format
       - Otherwise, the app automatically detects the format based on chronological order
    
    3. **Filter & Resample Data**
       - Use "Date Range" selector to focus on a specific time period
       - Use "Resample Data" dropdown to aggregate data (e.g., hourly → daily averages)
       - Changes update all charts and statistics instantly
    
    4. **View Statistics**
       - Expand "Data Summary" to see row count, date range, and resampling info
       - Expand "Column Statistics" to see mean, median, std dev, min, max for each column
    
    5. **Create Charts**
       - Under "Trend Plot", select columns for Primary Axis (left) and/or Secondary Axis (right)
       - The chart updates automatically with dual-axis support
    
    6. **Explore Data**
       - Expand "Data Table" to view the filtered/resampled data as a table
       - Hover over the chart to see exact values at each point
    """)

with tab_analyze:
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
        
        # Ensure timestamp column is datetime
        combined_df[timestamp_col] = pd.to_datetime(combined_df[timestamp_col])
        
        # Resample and date range in main content
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            st.subheader("⏱️ Resample Data")
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
            
            resample_option = st.selectbox(
                "Time Interval:",
                list(resample_map.keys()),
                index=0
            )
        
        with col_filter2:
            st.subheader("📅 Date Range")
            min_date = combined_df[timestamp_col].min()
            max_date = combined_df[timestamp_col].max()
            
            date_range = st.date_input(
                "Select date range:",
                value=(min_date.date(), max_date.date()),
                min_value=min_date.date(),
                max_value=max_date.date()
            )
        
        # Handle date range selection
        if len(date_range) == 2:
            start_date, end_date = date_range
            # Filter combined_df based on date range
            filtered_df = combined_df[
                (combined_df[timestamp_col].dt.date >= start_date) &
                (combined_df[timestamp_col].dt.date <= end_date)
            ].copy()
        else:
            filtered_df = combined_df.copy()
        
        # Apply resampling if selected
        if resample_map[resample_option]:
            # Set timestamp as index for resampling
            df_resampled = filtered_df.set_index(timestamp_col)
            df_resampled = df_resampled.resample(resample_map[resample_option]).mean()
            df_resampled = df_resampled.reset_index()
            display_df = df_resampled
        else:
            display_df = filtered_df


        # Show data summary
        with st.expander("📊 Data Summary"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Rows", len(display_df), label_visibility="visible")
            with col2:
                st.metric("Columns", len(display_df.columns), label_visibility="visible")
            with col3:
                st.metric("Files", len(st.session_state.dataframes), label_visibility="visible")
            with col4:
                st.metric("Resample", resample_option, label_visibility="visible")
            
            # Date range - from filtered and resampled data
            col5, col6, col7 = st.columns(3)
            if len(display_df) > 0:
                min_date_filtered = display_df[timestamp_col].min()
                max_date_filtered = display_df[timestamp_col].max()
                date_range_span = (max_date_filtered - min_date_filtered).days + 1
                with col5:
                    st.metric("Start", min_date_filtered.strftime("%Y-%m-%d"), label_visibility="visible")
                with col6:
                    st.metric("End", max_date_filtered.strftime("%Y-%m-%d"), label_visibility="visible")
                with col7:
                    st.metric("Days", date_range_span, label_visibility="visible")
            else:
                st.warning("No data available for selected date range")

        # Column statistics
        with st.expander("📈 Column Statistics"):
            stats_data = []
            numeric_cols = display_df.select_dtypes(include=['number']).columns
            
            for col in numeric_cols:
                col_data = display_df[col].dropna()
                if len(col_data) > 0:
                    # Find date range for non-null values
                    non_null_mask = display_df[col].notna()
                    non_null_dates = display_df.loc[non_null_mask, timestamp_col]
                    date_range_start = non_null_dates.min().strftime("%Y-%m-%d")
                    date_range_end = non_null_dates.max().strftime("%Y-%m-%d")
                    
                    stats_data.append({
                        "Column": col,
                        "Mean": f"{col_data.mean():.4f}",
                        "Median": f"{col_data.median():.4f}",
                        "Std Dev": f"{col_data.std():.4f}",
                        "Min": f"{col_data.min():.4f}",
                        "Max": f"{col_data.max():.4f}",
                        "Data Range": f"{date_range_start} to {date_range_end}"
                })
            
            if stats_data:
                stats_df = pd.DataFrame(stats_data)
                st.dataframe(stats_df, use_container_width=True)
            else:
                st.info("No numeric columns to display statistics for.")

        # Chart section
        st.subheader("📊 Trend Plot")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Primary Axis**")
            primary_cols = st.multiselect(
                "Select columns for primary Y-axis:",
                available_cols,
                key="primary"
            )
        
        with col2:
            st.markdown("**Secondary Axis**")
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
            # Display empty placeholder chart
            fig_placeholder = go.Figure()
            fig_placeholder.add_annotation(
                text="👆 Select columns to display chart",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig_placeholder.update_layout(
                title="Trend Plot",
                xaxis_title=timestamp_col,
                yaxis=dict(title="Primary Axis", side="left"),
                yaxis2=dict(title="Secondary Axis", side="right", overlaying="y"),
                height=500,
                template="plotly_white",
                showlegend=False
            )
            st.plotly_chart(fig_placeholder, use_container_width=True)
        
        # Display combined dataframe
        with st.expander("📋 Data Table"):
            st.dataframe(display_df, use_container_width=True)


