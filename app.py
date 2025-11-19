import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(
    page_title="Energy Consumption Dashboard",
    page_icon="⚡",
    layout="wide"
)

# Title and Description
st.title("⚡ Energy Consumption Dashboard")
st.markdown("Analyze energy consumption data across different sectors.")

# --- Data Loading Function ---
@st.cache_data
def load_data(file):
    try:
        # Read CSV, assuming header is on the first row (index 0)
        # We will handle the unit row (index 1 in the file, index 0 in df after header) separately
        df = pd.read_csv(file)
        
        # The dataset structure based on your file:
        # Row 0 (header): Date/Time, ..., Polishing
        # Row 1 (index 0 in df): Units (e.g., Electricity ENERGY (kWh))
        # We need to drop the unit row for analysis
        
        # clean column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        # Drop the first row which contains units
        df = df.drop(index=0)
        
        # Convert Date/Time to datetime objects
        # Adjusting 'Date/Time' column name if needed based on exact file structure
        if 'Date/Time' in df.columns:
            df['Date/Time'] = pd.to_datetime(df['Date/Time'])
        else:
            st.error("Column 'Date/Time' not found. Please check your CSV headers.")
            return None

        # Identify consumption columns (excluding time columns)
        # We exclude 'Date/Time' and 'Date/Time.1'
        cols_to_exclude = ['Date/Time', 'Date/Time.1']
        consumption_cols = [c for c in df.columns if c not in cols_to_exclude]
        
        # Convert consumption columns to numeric, coercing errors to NaN
        for col in consumption_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        return df, consumption_cols

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

# --- Sidebar ---
st.sidebar.header("Configuration")

# File Uploader
uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=['csv'])

# Try to load local file if no file is uploaded (for demo purposes)
DEFAULT_FILE = "LoadProfile Final ENLIT.xlsx - mySheet.csv"

df = None
consumption_cols = []

if uploaded_file is not None:
    df, consumption_cols = load_data(uploaded_file)
else:
    # Check if default file exists locally
    import os
    if os.path.exists(DEFAULT_FILE):
        st.sidebar.info(f"Using local file: {DEFAULT_FILE}")
        df, consumption_cols = load_data(DEFAULT_FILE)
    else:
        st.info("Please upload a CSV file to begin.")
        st.stop()

if df is not None:
    # --- Sidebar Filters ---
    
    # Date Range Filter
    min_date = df['Date/Time'].min().date()
    max_date = df['Date/Time'].max().date()
    
    start_date, end_date = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Filter data by date
    mask = (df['Date/Time'].dt.date >= start_date) & (df['Date/Time'].dt.date <= end_date)
    filtered_df = df.loc[mask]
    
    # Resampling Option
    # Raw data is 15-min intervals. Over a year, that's too much for a bar chart.
    # Resampling aggregates the data.
    st.sidebar.subheader("Data Aggregation")
    resample_map = {
        "15 Minutes (Raw)": None,
        "Hourly": "h",
        "Daily": "D",
        "Weekly": "W",
        "Monthly": "M"
    }
    selected_freq_label = st.sidebar.selectbox("Select Time Frequency", list(resample_map.keys()), index=2) # Default to Daily
    selected_freq = resample_map[selected_freq_label]
    
    # Column Selector
    st.sidebar.subheader("Select Sectors")
    # Default to selecting all valid numeric columns if manageable, or just a few
    default_cols = consumption_cols[:3] if len(consumption_cols) > 3 else consumption_cols
    selected_columns = st.sidebar.multiselect("Choose columns to visualize", consumption_cols, default=default_cols)

    # --- Main Content ---
    
    if not selected_columns:
        st.warning("Please select at least one column to visualize.")
    else:
        # Prepare data for plotting
        plot_df = filtered_df[['Date/Time'] + selected_columns].copy()
        plot_df.set_index('Date/Time', inplace=True)
        
        # Resample if selected
        if selected_freq:
            # We use sum() for energy (kWh) when resampling (e.g., sum of 15-min intervals = total hourly energy)
            plot_df = plot_df.resample(selected_freq).sum()
        
        plot_df = plot_df.reset_index()

        # --- Plotting ---
        st.subheader(f"Energy Consumption ({selected_freq_label})")
        
        # Melt for Plotly (Long format is better for multi-bar charts)
        melted_df = plot_df.melt(id_vars=['Date/Time'], value_vars=selected_columns, var_name='Sector', value_name='Energy (kWh)')
        
        fig = px.bar(
            melted_df,
            x='Date/Time',
            y='Energy (kWh)',
            color='Sector',
            title=f"Energy Consumption Over Time ({start_date} to {end_date})",
            barmode='group' if len(selected_columns) < 5 else 'stack', # Stack if too many columns
            height=600
        )
        
        fig.update_layout(xaxis_title="Time", yaxis_title="Energy (kWh)")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- Statistics ---
        st.subheader("Summary Statistics")
        st.dataframe(plot_df[selected_columns].describe())

        # --- Raw Data View ---
        with st.expander("View Raw Data"):
            st.dataframe(filtered_df)
