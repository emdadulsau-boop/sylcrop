import streamlit as st
import pandas as pd
from fpdf import FPDF
import io

# --- 1. PDF GENERATOR ---
def generate_report(d_name, crop_results):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Agricultural Suitability Analysis: {d_name}", ln=True, align='C')
    pdf.ln(5)

    for res in crop_results:
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, f"Crop: {res['crop']} | Score: {res['score']}%", ln=True, fill=True)
        pdf.set_font("Helvetica", '', 11)
        pdf.ln(2)
        pdf.multi_cell(0, 7, txt=res['insight'])
        pdf.ln(5)

        # Table Setup
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_fill_color(245, 245, 245)
        w_param, w_dist, w_req, w_score = 45, 45, 65, 35
        pdf.cell(w_param, 8, "Parameter", border=1, fill=True)
        pdf.cell(w_dist, 8, "District Value", border=1, fill=True)
        pdf.cell(w_req, 8, "Requirement", border=1, fill=True)
        pdf.cell(w_score, 8, "Score", border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", '', 8)
        for row in res['table_data']:
            pdf.cell(w_param, 7, str(row.get('Parameter', 'N/A')), border=1)
            pdf.cell(w_dist, 7, str(row.get('District Value', 'N/A')), border=1)
            pdf.cell(w_req, 7, str(row.get('Requirement', 'N/A')), border=1)
            pdf.cell(w_score, 7, str(row.get('Score', 'N/A')), border=1)
            pdf.ln()
        pdf.ln(10)
    return bytes(pdf.output())

# --- 2. AI INSIGHTS ENGINE ---
def run_ai_insights(d_row, crop_name, total, aez_match, temp_score, texture_score, sal_score, season):
    st.markdown(f'<p style="color: #00d2ff; font-weight: bold;">✨ AI Agronomist Analysis: {crop_name}</p>', unsafe_allow_html=True)
    ans_key = f"ai_answer_{crop_name}"
    
    if ans_key not in st.session_state:
        st.session_state[ans_key] = "Select an analysis button above for expert advice."

    col1, col2, col3 = st.columns(3)

    if col1.button(f"🔍 Why {int(total)}%?", key=f"why_{crop_name}"):
        reasons = []
        if not aez_match: reasons.append("outside primary AEZ zones")
        if temp_score < 15: reasons.append("temp outside metabolic optimum")
        if texture_score < 0: reasons.append(f"mechanical barrier ({d_row.get('Soil Texture')})")
        if sal_score <= 0: reasons.append("salinity exceeds safety threshold")
        st.session_state[ans_key] = f"**Analysis:** {int(total)}% because it is " + (" and ".join(reasons) if reasons else "optimized!")

    if col2.button("🧪 Soil Remedy", key=f"remedy_{crop_name}"):
        ph = d_row.get('pH avg', 7.0)
        if ph > 7.5: st.session_state[ans_key] = f"**Alkaline (pH {ph}):** Use Ammonium Sulfate & organic mulch."
        elif ph < 5.5: st.session_state[ans_key] = f"**Acidic (pH {ph}):** Apply Dolomite or Lime."
        else: st.session_state[ans_key] = f"**Optimal (pH {ph}):** Maintain organic matter."

    if col3.button("🌡️ Varieties", key=f"var_{crop_name}"):
        if sal_score <= 0: st.session_state[ans_key] = "**Salt Strategy:** Use BINA/BRRI salt-tolerant lines."
        elif season == "Summer": st.session_state[ans_key] = "**Heat Strategy:** Use thermotolerant varieties."
        else: st.session_state[ans_key] = "**Standard:** HYV varieties will perform well."

    if st.session_state[ans_key] != "Select an analysis button above for expert advice.":
        st.success(st.session_state[ans_key])

# --- 3. DATA LOADING & MATH ---
@st.cache_data
def load_data():
    try:
        districts = pd.read_csv(r'C:\Users\Tc\Desktop\District_64_Verified_Final.csv', encoding='latin1')
        crops = pd.read_csv(r'C:\Users\Tc\Desktop\Crop_Master_KS_Updated.csv', encoding='latin1')
        districts.columns = districts.columns.str.strip()
        crops.columns = crops.columns.str.strip()
        return districts, crops
    except: return None, None

def get_salinity_val(sal_str):
    sal_map = {'Non-saline': 0.5, 'Slightly saline': 2.5, 'Slight to moderate': 4.0, 'Moderately saline': 8.0, 'Strong saline': 12.0, 'Very strong': 16.0}
    for key, val in sal_map.items():
        if key.lower() in str(sal_str).lower(): return val
    return 1.0

def calculate_suitability_v3(d_row, c_row, season):
    raw_comparison = []
    
    # AEZ (30%)
    dist_aezs = set(str(d_row.get('AEZ', '')).replace(',', ' ').split())
    crop_aezs = set(str(c_row.get('Target AEZ', '')).replace(',', ' ').split())
    aez_match = any(a in crop_aezs for a in dist_aezs)
    aez_score = 30 if aez_match else 0
    raw_comparison.append({"Parameter": "AEZ Map", "District Value": str(d_row.get('AEZ')), "Requirement": str(c_row.get('Target AEZ')), "Score": f"{aez_score}/30"})

    # Temp/Rain
    temp_h = d_row.get('Temp H (C avg)', 30)
    temp_l = d_row.get('Temp L (C avg)', 15)
    avg_t = (temp_h + temp_l) / 2
    temp_score = 15 if (c_row.get('Opt_TempL', 15) <= avg_t <= c_row.get('Opt_TempH', 30)) else 7.5
    raw_comparison.append({"Parameter": "Avg Temp", "District Value": f"{round(avg_t,1)}°C", "Requirement": f"{c_row.get('Opt_TempL')}-{c_row.get('Opt_TempH')}°C", "Score": f"{temp_score}/15"})

    d_ph = d_row.get('pH avg', 7.0)
    ph_score = 15 if (c_row.get('KS3_MinPH', 5) <= d_ph <= c_row.get('KS4_MaxPH', 8)) else 5
    raw_comparison.append({"Parameter": "Soil pH", "District Value": f"{d_ph}", "Requirement": f"{c_row.get('KS3_MinPH', 5.5)}-{c_row.get('KS4_MaxPH', 7.5)}", "Score": f"{ph_score}/15"})

    # Salinity
    d_sal = get_salinity_val(d_row.get('Soil Salinity', 'Non-saline'))
    c_sal_limit = c_row.get('Salt_Tolerance_dS_m', 2.0)
    sal_score = 10 if d_sal <= c_sal_limit else max(-20.0, round(10 - ((d_sal/c_sal_limit - 1) * 7.5), 2))
    raw_comparison.append({"Parameter": "Salinity", "District Value": f"{d_sal} dS/m", "Requirement": f"Max {c_sal_limit}", "Score": f"{sal_score}/10"})

    # Texture
    texture_score = 10 
    raw_comparison.append({"Parameter": "Root Zone", "District Value": d_row.get('Soil Texture'), "Requirement": "Deep Expansion", "Score": f"{texture_score}/10"})

    # Kill Switches
    term_reasons = []
    if season == "Summer" and c_row.get('Summer_Tolerant', 1) == 0:
        if temp_h > (c_row.get('KS1_MaxTemp', 35) + 1): term_reasons.append(f"Heat ({temp_h}°C)")
    if d_sal > (c_sal_limit * 5): term_reasons.append(f"Salt ({d_sal} dS/m)")
    
    final_reason = " & ".join(term_reasons) if term_reasons else None
    final_score = 0.0 if final_reason else max(0, min(aez_score + temp_score + ph_score + 10 + sal_score + texture_score, 100))

    return round(final_score, 2), final_reason, aez_match, d_sal, c_sal_limit, raw_comparison

# --- 4. MAIN UI ---
def main():
    st.set_page_config(page_title="Technical Analysis", layout="wide")
    dist_df, crop_df = load_data()
    
    # Check if we have a district from Page 1
    if 'selected_district' not in st.session_state:
        st.warning("Please select a district on the Dashboard first.")
        st.stop()
    
    sel_dist = st.session_state['selected_district']
    d_data = dist_df[dist_df['District'] == sel_dist].iloc[0]

    st.title(f"📊 Technical Analysis: {sel_dist}")

    # Top Selection
    top1, top2 = st.columns([2, 1])
    with top1:
        sel_crops = st.multiselect("🌱 SELECT CROPS", options=sorted(crop_df['Crop Name'].unique()))
    with top2:
        sel_season = st.radio("🗓️ SEASON", ["Rabi", "Summer"], horizontal=True)

    report_data = []

    if sel_crops:
        for crop in sel_crops:
            c_data = crop_df[crop_df['Crop Name'] == crop].iloc[0]
            score, final_reason, aez_match, d_sal, c_sal_limit, raw_list = calculate_suitability_v3(d_data, c_data, sel_season)
            
            # Extract scores for AI
            t_score = 15 # Simplified for demo
            tex_score = 10
            s_score = 10

            st.markdown(f'### 🌱 {crop} - {score}%')
            st.progress(score/100)

            if final_reason:
                st.error(f"🛑 TERMINATED: {final_reason}")
            else:
                st.success("✅ survival thresholds maintained.")

            with st.expander(f"🔍 {crop} Technical Details"):
                st.table(pd.DataFrame(raw_list))
                run_ai_insights(d_data, crop, score, aez_match, t_score, tex_score, s_score, sel_season)
            
            report_data.append({"crop": crop, "score": score, "insight": f"Analysis for {crop}", "table_data": raw_list})

        # PDF Download
        if report_data:
            pdf_bytes = generate_report(sel_dist, report_data)
            st.download_button("📥 Download PDF Report", pdf_bytes, f"{sel_dist}_Report.pdf", "application/pdf")

if __name__ == "__main__":
    main()