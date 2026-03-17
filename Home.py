import streamlit as st
import pandas as pd
import requests
import os

# --- 1. SHARED LOADING LOGIC ---
@st.cache_data
def load_data():
    try:
        d_path = 'District_64_Verified_Final.csv'
        c_path = 'Crop_Master_KS_Updated.csv'
        
        districts = pd.read_csv(d_path, encoding='latin1')
        crops = pd.read_csv(c_path, encoding='latin1')
        
        districts.columns = districts.columns.str.strip()
        crops.columns = crops.columns.str.strip()
        return districts, crops
    except Exception as e:
        st.error(f"Error loading files: {e}")
        return None, None

# --- 2. UPDATED WEATHER LOGIC (Includes Max Temp, Rain, and Humidity) ---
def get_weather_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_mean", "precipitation_sum"],
        "hourly": ["relative_humidity_2m"],
        "timezone": "Asia/Dhaka",
        "forecast_days": 7
    }
    try:
        response = requests.get(url, params=params).json()
        daily = response['daily']
        hourly = response['hourly']
        
        # 7-Day Stats
        avg_max_7d = sum(daily['temperature_2m_max']) / 7
        total_rain_7d = sum(daily['precipitation_sum'])
        avg_rh_7d = sum(hourly['relative_humidity_2m']) / len(hourly['relative_humidity_2m'])
        
        # 48-Hour Specifics
        weather_48h = {
            "today_temp": daily['temperature_2m_max'][0],
            "today_rain": daily['precipitation_sum'][0],
            "tomorrow_temp": daily['temperature_2m_max'][1],
            "tomorrow_rain": daily['precipitation_sum'][1]
        }
        
        return round(avg_max_7d, 1), round(total_rain_7d, 1), round(avg_rh_7d, 1), weather_48h
    except:
        return "N/A", "N/A", "N/A", None

def main():
    st.set_page_config(page_title="District Dashboard", layout="wide")
    
    dist_df, _ = load_data()
    if dist_df is None:
        st.stop()

    st.title("🌍 District Climate Dashboard")

    # --- DISTRICT SELECTION ---
    sel_dist = st.selectbox(
        "📍 CHOOSE DISTRICT TO SYNC", 
        options=["Select a District"] + sorted(dist_df['District'].unique())
    )

    if sel_dist == "Select a District":
        st.info("Please select a district to view live weather and soil data.")
    else:
        d_data = dist_df[dist_df['District'] == sel_dist].iloc[0]
        st.session_state['selected_district'] = sel_dist
        
        lat, lon = d_data.get('lat', 23.68), d_data.get('lon', 90.35) 
        avg_max_7d, total_rain_7d, avg_rh_7d, w_48 = get_weather_forecast(lat, lon)

        # --- UI LAYOUT ---
        col1, col2 = st.columns([2, 1])

        with col1:
            # --- 1. TOP PRIORITY: 48-HOUR WINDOW ---
            st.subheader("📅 Immediate 48-Hour Outlook")
            if w_48:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    <div style="background-color: #0f172a; padding: 15px; border-radius: 12px; border-top: 5px solid #38bdf8; color: white;">
                        <p style="color: #94a3b8; font-size: 0.8rem; margin:0;">TODAY'S PEAK</p>
                        <h2 style="margin: 5px 0;">{w_48['today_temp']}°C</h2>
                        <p style="color: #38bdf8; margin:0; font-size: 1.3rem;">💧 {w_48['today_rain']} mm rain</p>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div style="background-color: #0f172a; padding: 15px; border-radius: 12px; border-top: 5px solid #fbbf24; color: white;">
                        <p style="color: #94a3b8; font-size: 0.8rem; margin:0;">TOMORROW'S PEAK</p>
                        <h2 style="margin: 5px 0;">{w_48['tomorrow_temp']}°C</h2>
                        <p style="color: #fbbf24; margin:0; font-size: 1.3rem;">💧 {w_48['tomorrow_rain']} mm rain</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.write("") 

            # --- 2. 7-DAY TREND CARD (Now with Humidity) ---
            st.markdown(f"""
            <div style="background-color: #1e293b; padding: 25px; border-radius: 15px; border-left: 8px solid #38bdf8; color: white; margin-bottom: 20px;">
                <h3 style="margin:0;">{sel_dist} - 7 Day Overview</h3>
                <div style="display: flex; justify-content: space-between; gap: 10px; margin-top:15px;">
                    <div style="background: #334155; padding: 15px; border-radius: 10px; flex: 1; text-align: center;">
                        <span style="color: #38bdf8; font-size: 0.8rem;">AVG MAX TEMP</span>
                        <h2 style="margin:5px 0;">{avg_max_7d}°C</h2>
                    </div>
                    <div style="background: #334155; padding: 15px; border-radius: 10px; flex: 1; text-align: center;">
                        <span style="color: #38bdf8; font-size: 0.8rem;">TOTAL RAINFALL</span>
                        <h2 style="margin:5px 0;">{total_rain_7d}mm</h2>
                    </div>
                    <div style="background: #334155; padding: 15px; border-radius: 10px; flex: 1; text-align: center;">
                        <span style="color: #38bdf8; font-size: 0.8rem;">AVG HUMIDITY</span>
                        <h2 style="margin:5px 0;">{avg_rh_7d}%</h2>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Proceed to Technical Crop Analysis ➡️", use_container_width=True):
                         st.switch_page("pages/2_Technical_Analysis.py")

        with col2:
            st.subheader("Field Metadata")
            st.info(f"**AEZ Zone:** {d_data.get('AEZ')}")
            st.info(f"**Soil Texture:** {d_data.get('Soil Texture')}")
            st.info(f"**Soil pH (Avg):** {d_data.get('pH avg')}")
            st.info(f"**Salinity:** {d_data.get('Soil Salinity')} dS/m")
            
            # --- 3. SMART INSIGHTS (Multi-Stress Logic) ---
            st.subheader("Smart Insights")
            
            # 1. Pull the raw numbers from your diction
            today_r = w_48['today_rain']
            tomorrow_r = w_48['tomorrow_rain']
            today_t = w_48['today_temp']
            tomorrow_t = w_48['tomorrow_temp']

		 # 2. Define your 48-hour Thresholds
            is_high_rain = (today_r + tomorrow_r) > 20.0  # Sum of 2 days
            is_high_temp = (today_t > 32.0) or (tomorrow_t > 32.0) # If either day is a peak
            is_low_temp  = (today_t < 18.0) and (tomorrow_t < 18.0) # Sustained chill
            
            
            
            # Define "High" thresholds
            is_high_humid = avg_rh_7d > 80.0
            
            high_count = sum([is_high_temp, is_high_rain, is_high_humid])
            is_low_rain = (today_r+tomorrow_r) < 20.0
            
            
                # Combined stress scenarios
            if is_low_temp and is_low_rain:
                st.warning("❄️ **Dormancy Risk:** Low Temp + Low Rainfall. Metabolic rates will drop. Phosphorus uptake is usually limited in cold, dry soils—consider foliar feeding.")
                if high_count >= 2:
                   if is_high_temp and is_high_humid:
                       st.warning("🚨 **Disease Alert:** High Heat + High Humidity detected. This is a primary trigger for fungal outbreaks like Downy Mildew or Late Blight.")
                elif is_high_rain and is_high_humid:
                    st.warning("⚠️ **Saturation Risk:** High Rain + High Humidity. Soil aeration might be compromised; monitor for root-zone hypoxia.")
                elif is_high_temp and is_high_rain:
                    st.info("🌡️ **Rapid Growth/Stress:** High Heat + Rain. Expect rapid vegetative growth but watch for 'steaming' effects in low-canopy crops.")
            else:
                # Single or No stress
                if is_high_temp:
                    st.warning("🔥 Ensure adequate mulch to prevent soil moisture evaporation during afternoon peaks.")
                elif is_high_rain:
                    st.info("🌧️ Postpone scheduled irrigation; the soil moisture levels are being replenished naturally.")
                    
                elif is_low_temp:
                  st.info("🌡️ **Growth Slowdown:** Temperatures are below the optimum for tropical crops. Expect delayed flowering.")
                elif is_low_rain:
                  st.warning("🌵 **Moisture Stress:** Negligible rainfall. Supplement with light irrigation to maintain root zone turgidity.")
                else:
                    st.success("✅ Favorable conditions for most standard agricultural operations.")

if __name__ == "__main__":
    main()
