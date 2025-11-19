import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Energy SCADA & Financial Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING (SCADA LOOK) ---
st.markdown("""
    <style>
    .scada-box {
        border: 2px solid #444;
        padding: 10px;
        border-radius: 5px;
        background-color: #1e1e1e;
        text-align: center;
        margin-bottom: 10px;
    }
    .scada-title { font-size: 14px; color: #aaa; }
    .scada-value { font-size: 24px; font-weight: bold; color: #00FF00; font-family: 'Courier New', monospace; }
    .scada-alert { 
        border: 2px solid #FF0000 !important; 
        box-shadow: 0 0 15px #FF0000;
        animation: blink 1s infinite;
    }
    @keyframes blink { 50% { border-color: transparent; box-shadow: none; } }
    </style>
""", unsafe_allow_html=True)

# --- MOCK DATA GENERATOR ---
# (In production, this replaces the Excel upload if no file is provided)
@st.cache_data
def generate_mock_data():
    # Historical Data (Last 30 days)
    dates = pd.date_range(end=datetime.now(), periods=24*30, freq='H')
    
    # Processes
    processes = ['Chillers', 'Compressor 1', 'Compressor 2', 'Trafo 1', 'Trafo 2', 
                 'Extraction', 'Supply Air 1', 'Supply Air 2', 'Filing', 'Polishing', 'LPDC']
    
    data = {'Timestamp': dates}
    
    # Generate consumption data with some randomness
    for p in processes:
        base = np.random.uniform(50, 200)
        data[p] = np.random.normal(base, base*0.1, len(dates))
    
    # L1 Site (Total)
    df_hist = pd.DataFrame(data)
    df_hist['L1 Site'] = df_hist[processes].sum(axis=1)
    
    # Financial Data (Regions)
    regions = ['Mainland', 'Balearic', 'Canary', 'Ceuta', 'Melilla']
    for r in regions:
        df_hist[f'{r}_Amount'] = df_hist['L1 Site'] * np.random.uniform(0.15, 0.25) # Cost
        # Pass through mock
        df_hist[f'{r}_PassThrough_PMD'] = df_hist[f'{r}_Amount'] * 0.1
        df_hist[f'{r}_PassThrough_Ai'] = df_hist[f'{r}_Amount'] * 0.05
    
    # Forecast Data (Next 7 days)
    future_dates = pd.date_range(start=dates[-1], periods=24*7, freq='H')
    forecast_data = {'Timestamp': future_dates}
    forecast_data['Predicted_Energy'] = np.random.normal(1500, 200, len(future_dates))
    
    for r in regions:
        forecast_data[f'{r}_cost_safe'] = forecast_data['Predicted_Energy'] * np.random.uniform(0.18, 0.28)
        
    df_forecast = pd.DataFrame(forecast_data)
    
    return df_hist, df_forecast

# --- MAIN APP LOGIC ---

def main():
    # Sidebar
    st.sidebar.title("⚡ Energy Manager Pro")
    
    uploaded_file_hist = st.sidebar.file_uploader("Upload Amount_Corrected.xlsx", type=['xlsx'])
    uploaded_file_fore = st.sidebar.file_uploader("Upload Forecast_Safe.xlsx", type=['xlsx'])
    
    if uploaded_file_hist and uploaded_file_fore:
        # Real logic would go here: pd.read_excel...
        st.sidebar.success("Files Uploaded (Using Mock Data for Demo)")
        df_hist, df_forecast = generate_mock_data()
    else:
        st.sidebar.info("Awaiting Uploads... (Using Simulation Mode)")
        df_hist, df_forecast = generate_mock_data()
        
    # Global Region Selector
    region = st.sidebar.selectbox("Select Region Focus", 
                                  ["Mainland", "Balearic", "Canary", "Ceuta", "Melilla"])

    # Navigation
    tab_main, tab_scada, tab_fin, tab_fore, tab_ai = st.tabs([
        "📊 Management Dashboard", 
        "🖥️ SCADA View", 
        "💶 Financial Analysis", 
        "📈 Forecasting",
        "🧠 AI Insights"
    ])

    # --- TAB 1: MANAGEMENT DASHBOARD ---
    with tab_main:
        st.subheader("Operational Overview (L1 Site)")
        
        # Top KPIs
        latest = df_hist.iloc[-1]
        prev = df_hist.iloc[-2]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Load (kW)", f"{latest['L1 Site']:.2f}", f"{latest['L1 Site'] - prev['L1 Site']:.2f} kW")
        col2.metric("Daily Peak (kW)", f"{df_hist.tail(24)['L1 Site'].max():.2f}")
        col3.metric("Top Consumer", "Chillers") # Logic to find max col could go here
        col4.metric(f"{region} Cost (Last Hr)", f"€{latest[f'{region}_Amount']:.2f}")
        
        # Charts
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("#### Total Consumption Trend")
            fig_trend = px.line(df_hist.tail(168), x='Timestamp', y='L1 Site', title="Last 7 Days Load Profile")
            fig_trend.update_traces(line_color='#00CC96')
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with c2:
            st.markdown("#### Operating Hours Heatmap")
            # Pivot for heatmap
            df_hm = df_hist.tail(24*7).copy()
            df_hm['Hour'] = df_hm['Timestamp'].dt.hour
            df_hm['Day'] = df_hm['Timestamp'].dt.day_name()
            fig_hm = px.density_heatmap(df_hm, x='Hour', y='Day', z='L1 Site', color_continuous_scale='Viridis')
            st.plotly_chart(fig_hm, use_container_width=True)

    # --- TAB 2: SCADA VISUALIZATION ---
    with tab_scada:
        st.subheader("Real-Time Facility Digital Twin")
        st.caption("Red Glow = Consumption > Average")
        
        # Helper to render "SCADA Cards"
        def render_machine(name, value, avg_val):
            is_alert = value > (avg_val * 1.1) # Alert if 10% over average
            alert_class = "scada-alert" if is_alert else ""
            color = "#FF4B4B" if is_alert else "#00FF00"
            
            html = f"""
            <div class="scada-box {alert_class}">
                <div class="scada-title">{name}</div>
                <div class="scada-value" style="color: {color}">{value:.1f} kW</div>
                <div style="font-size:10px; color:#666">Avg: {avg_val:.1f} kW</div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

        # Layout - Manually placing items to mimic a floor plan
        c1, c2, c3, c4 = st.columns(4)
        
        avg_vals = df_hist.mean()
        
        with c1:
            st.markdown("### Power Input")
            render_machine("Trafo 1", latest['Trafo 1'], avg_vals['Trafo 1'])
            render_machine("Trafo 2", latest['Trafo 2'], avg_vals['Trafo 2'])
            render_machine("Main Bus", latest['L1 Site'], avg_vals['L1 Site'])
            
        with c2:
            st.markdown("### Utility")
            render_machine("Chillers", latest['Chillers'], avg_vals['Chillers'])
            render_machine("Compressor 1", latest['Compressor 1'], avg_vals['Compressor 1'])
            render_machine("Compressor 2", latest['Compressor 2'], avg_vals['Compressor 2'])

        with c3:
            st.markdown("### HVAC")
            render_machine("Supply Air 1", latest['Supply Air 1'], avg_vals['Supply Air 1'])
            render_machine("Supply Air 2", latest['Supply Air 2'], avg_vals['Supply Air 2'])
            render_machine("Extraction", latest['Extraction'], avg_vals['Extraction'])

        with c4:
            st.markdown("### Production")
            render_machine("LPDC", latest['LPDC'], avg_vals['LPDC'])
            render_machine("Filing", latest['Filing'], avg_vals['Filing'])
            render_machine("Polishing", latest['Polishing'], avg_vals['Polishing'])
            
        # Graphviz Flow Diagram
        st.markdown("---")
        st.subheader("System Logic Diagram")
        
        # Using Graphviz to draw the connections
        graph = graphviz.Digraph()
        graph.attr(rankdir='LR', bgcolor='transparent')
        graph.attr('node', shape='box', style='filled', fillcolor='#262730', fontcolor='white', color='white')
        graph.edge_attr.update(color='white')
        
        graph.node('Grid', 'External Grid', shape='ellipse', fillcolor='#4CAF50')
        graph.node('T1', f'Trafo 1\n{latest["Trafo 1"]:.0f}kW')
        graph.node('T2', f'Trafo 2\n{latest["Trafo 2"]:.0f}kW')
        graph.node('Bus', 'Main Bus L1')
        graph.node('Chiller', 'Chillers')
        graph.node('Comp', 'Compressors')
        graph.node('Prod', 'Production Line')
        
        graph.edges([('Grid', 'T1'), ('Grid', 'T2'), ('T1', 'Bus'), ('T2', 'Bus')])
        graph.edges([('Bus', 'Chiller'), ('Bus', 'Comp'), ('Bus', 'Prod')])
        
        st.graphviz_chart(graph)

    # --- TAB 3: FINANCIAL DASHBOARD ---
    with tab_fin:
        st.subheader(f"Financial Breakdown: {region}")
        
        fc1, fc2 = st.columns([2, 1])
        
        with fc1:
            # Stacked Area for Pass Throughs
            pt_cols = [c for c in df_hist.columns if f'{region}_PassThrough' in c]
            df_pt = df_hist[['Timestamp'] + pt_cols].tail(168) # Last 7 days
            
            fig_fin = px.area(df_pt, x='Timestamp', y=pt_cols, title="Pass-Through Cost Components (7 Days)")
            st.plotly_chart(fig_fin, use_container_width=True)
            
        with fc2:
            # Region Comparison
            total_costs = {r: df_hist[f'{r}_Amount'].sum() for r in ["Mainland", "Balearic", "Canary", "Ceuta", "Melilla"]}
            df_compare = pd.DataFrame(list(total_costs.items()), columns=['Region', 'Total Cost'])
            
            fig_bar = px.bar(df_compare, x='Region', y='Total Cost', color='Region', title="Total Cost by Region (All History)")
            st.plotly_chart(fig_bar, use_container_width=True)

    # --- TAB 4: FORECAST DASHBOARD ---
    with tab_fore:
        st.subheader("AI Prediction Model")
        
        # Merge History and Forecast for visualization
        fig_pred = go.Figure()
        
        # Historical Line
        hist_slice = df_hist.tail(48) # Last 48h
        fig_pred.add_trace(go.Scatter(x=hist_slice['Timestamp'], y=hist_slice['L1 Site'], name='Historical', line=dict(color='gray')))
        
        # Forecast Line
        fore_slice = df_forecast.head(48) # Next 48h
        fig_pred.add_trace(go.Scatter(x=fore_slice['Timestamp'], y=fore_slice['Predicted_Energy'], name='Predicted', line=dict(color='#00CC96', dash='dot')))
        
        fig_pred.update_layout(title="Energy Consumption Forecast (Next 48h)", xaxis_title="Time", yaxis_title="kWh")
        st.plotly_chart(fig_pred, use_container_width=True)
        
        # Cost Forecast Table
        st.subheader("Predicted Costs per Region (Next 24h)")
        cols_cost = [c for c in df_forecast.columns if 'cost_safe' in c]
        st.dataframe(df_forecast[['Timestamp'] + cols_cost].head(24).style.background_gradient(cmap='Reds'))

    # --- TAB 5: INTELLIGENT ADVISOR ---
    with tab_ai:
        st.subheader("🧠 Energy Advisor Chatbot")
        
        user_query = st.text_input("Ask insights about your energy data:", placeholder="e.g., Which hour is most expensive?")
        
        if user_query:
            response = ""
            q = user_query.lower()
            
            if "expensive" in q or "cost" in q:
                max_cost_row = df_hist.loc[df_hist[f'{region}_Amount'].idxmax()]
                response = f"Based on historical data, the most expensive hour was **{max_cost_row['Timestamp']}** with a cost of **€{max_cost_row[f'{region}_Amount']:.2f}** in {region}."
            
            elif "process" in q or "consume" in q:
                # Simple sum comparison
                proc_sums = df_hist[['Chillers', 'Compressor 1', 'LPDC']].sum().sort_values(ascending=False)
                response = f"The process consuming the most energy is **{proc_sums.index[0]}**."
            
            elif "optimize" in q:
                response = "Recommendation: **Chillers** are operating at 90% capacity during peak pricing hours (18:00-21:00). Consider pre-cooling during off-peak hours."
            
            else:
                response = "I am analyzing the datasets... Try asking about 'peak hours', 'expensive times', or 'process consumption'."
            
            st.info(response, icon="🤖")

if __name__ == "__main__":
    import graphviz # Import here to avoid top-level failure if not installed
    main()
