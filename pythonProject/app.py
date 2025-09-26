# nexus_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="Proyecciones Energía y Clima")

# -------------------------
# Datos base por región
# -------------------------
BASE_DEMANDA = {
    "Costa": 12000,
    "Sierra": 7000,
    "Selva": 4000
}

CAPACITIES = {
    "Costa": {"hydro": 15000, "solar": 8000, "thermal": 12000},
    "Sierra": {"hydro": 20000, "solar": 3000, "thermal": 8000},
    "Selva": {"hydro": 10000, "solar": 1000, "thermal": 5000}
}

EMISSION_FACTORS = {"hydro": 0.02, "solar": 0.03, "thermal": 0.8}
COSTS = {"hydro": 30, "solar": 40, "thermal": 90}

# -------------------------
# Simulación demanda y clima
# -------------------------
def project_demand(region, years=10, growth_rate=0.04):
    """Proyecta la demanda eléctrica de una región a n años."""
    base = BASE_DEMANDA[region]
    dates = pd.date_range("2025-01-01", periods=years, freq="Y")
    demand = [base * ((1 + growth_rate) ** i) for i in range(years)]
    return pd.DataFrame({"Año": dates.year, "Demanda_MWh": demand})

def apply_climate_scenario(df, scenario):
    """Ajusta generación renovable según el escenario climático."""
    factor = {"Optimista": 1.1, "Normal": 1.0, "Crítico": 0.8}[scenario]
    df["climate_factor"] = factor
    return df

def simulate_mix(region, demanda, factor):
    """Simula el mix de generación dado un escenario."""
    caps = CAPACITIES[region]
    # proporciones iniciales
    mix = {"hydro": 0.5, "solar": 0.2, "thermal": 0.3}
    gen = {k: demanda * mix[k] for k in mix}
    # aplicar límite de capacidad
    for k in ["hydro", "solar"]:
        gen[k] = min(gen[k] * factor, caps[k])
    gen["thermal"] = min(demanda - (gen["hydro"] + gen["solar"]), caps["thermal"])
    deficit = max(0, demanda - sum(gen.values()))
    emissions = sum(gen[t] * EMISSION_FACTORS[t] for t in gen)
    cost = sum(gen[t] * COSTS[t] for t in gen)
    # costo marginal promedio
    cmp = cost / demanda if demanda > 0 else 0
    return {"gen": gen, "deficit": deficit, "emissions": emissions, "cost": cost, "cmp": cmp}

# -------------------------
# UI principal
# -------------------------
st.title("🌐 Nexus: Proyecciones Energía & Clima")

st.markdown("Este simulador permite explorar cómo la **demanda energética** y los **escenarios climáticos** afectan el mix de generación en distintas regiones del país.")

# Selección de región
region = st.selectbox("🌍 Selecciona región", ["Costa", "Sierra", "Selva"])

# Selección de escenario climático
scenario = st.radio("☁️ Escenario climático", ["Optimista", "Normal", "Crítico"])

# Parámetros de proyección
years = st.slider("Horizonte de proyección (años)", 5, 20, 10)
growth_rate = st.slider("Crecimiento anual de demanda (%)", 1, 10, 4) / 100

# -------------------------
# Simulación
# -------------------------
df_proj = project_demand(region, years, growth_rate)
df_proj = apply_climate_scenario(df_proj, scenario)

results = []
for _, row in df_proj.iterrows():
    sim = simulate_mix(region, row["Demanda_MWh"], row["climate_factor"])
    results.append({
        "Año": row["Año"],
        "Demanda_MWh": row["Demanda_MWh"],
        "Hidro_MWh": sim["gen"]["hydro"],
        "Solar_MWh": sim["gen"]["solar"],
        "Térmica_MWh": sim["gen"]["thermal"],
        "Déficit": sim["deficit"],
        "Emisiones_tCO2e": sim["emissions"],
        "Costo_USD": sim["cost"],
        "CMP_USD_MWh": sim["cmp"]
    })

df_results = pd.DataFrame(results)

# -------------------------
# Dashboard
# -------------------------
st.markdown(f"## 📊 Resultados para {region} - Escenario {scenario}")

col1, col2, col3 = st.columns(3)
col1.metric("Demanda final (MWh)", f"{df_results['Demanda_MWh'].iloc[-1]:,.0f}")
col2.metric("Costo total (USD)", f"${df_results['Costo_USD'].sum():,.0f}")
col3.metric("Emisiones acumuladas (tCO2e)", f"{df_results['Emisiones_tCO2e'].sum():,.0f}")

st.subheader("Evolución de la Demanda vs Generación")
fig = px.line(df_results, x="Año", y=["Demanda_MWh", "Hidro_MWh", "Solar_MWh", "Térmica_MWh"],
              labels={"value": "MWh", "variable": "Tipo"}, markers=True)
st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Mix final (último año) con Pie chart + CMP
# -------------------------
st.subheader("Participación porcentual del mix (último año)")
last_year = df_results.iloc[-1]
mix_last = pd.DataFrame({
    "Tecnología": ["Hidro", "Solar", "Térmica"],
    "MWh": [last_year["Hidro_MWh"], last_year["Solar_MWh"], last_year["Térmica_MWh"]]
})

col_pie, col_cmp = st.columns([2, 1])
with col_pie:
    fig_pie = px.pie(mix_last, names="Tecnología", values="MWh", hole=0.3)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_cmp:
    st.markdown(
        f"""
        <div style="text-align: center; border: 2px solid #444; border-radius: 12px; padding: 25px; background-color: #fdfdfd; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
            <h3 style="margin-bottom:15px; font-size:22px; color:#000000;">⚡ <b>Costo Marginal Promedio</b></h3>
            <h1 style="color:#2E86C1; font-size:42px; margin: 5px 0;">${last_year['CMP_USD_MWh']:.0f}</h1>
            <p style="font-size:20px; color:#555;">USD/MWh</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------
# Déficit
# -------------------------
st.subheader("Déficit a lo largo de los años")
st.bar_chart(df_results.set_index("Año")["Déficit"])

st.info("✅ Este dashboard proyecta demanda, mix energético y costo marginal promedio considerando escenarios climáticos y límites de capacidad por región.")
