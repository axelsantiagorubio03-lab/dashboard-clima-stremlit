import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ─── Configuración de la página ────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Meteorológico",
    page_icon="🌤️",
    layout="wide"
)

# ─── Paleta del curso ──────────────────────────────────────────────────
GRIS = "#B9C3D1"
AZUL = "#1C4C9A"
ROJO = "#B2182B"
NARANJA = "#E69F00"
sns.set_theme(style="whitegrid")

# ─── Título y descripción ──────────────────────────────────────────────
st.title("🌤️ Dashboard Meteorológico Histórico")
st.markdown("Análisis interactivo de variables climáticas mediante la API de **Open-Meteo**.")

# ─── Barra lateral (Controles interactivos) ────────────────────────────
st.sidebar.header("⚙️ Filtros de Consulta")

CIUDADES = {
    "Morelia":   (19.7008, -101.1844),
    "Querétaro": (20.5888, -100.3899),
}
ciudad_seleccionada = st.sidebar.selectbox("Selecciona una ciudad:", list(CIUDADES.keys()))

anios_disponibles = [2021, 2022, 2023, 2024, 2025]
anio_banda = st.sidebar.selectbox(
    "Año para Gráfica 1 (Banda térmica):", 
    anios_disponibles, 
    index=len(anios_disponibles)-1
)

# ─── Función con caché para consultar la API ───────────────────────────
@st.cache_data
def cargar_datos(ciudad):
    latitud, longitud = CIUDADES[ciudad]
    variables = [
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "apparent_temperature_max",
        "precipitation_sum",
        "precipitation_hours",
        "windspeed_10m_max",
        "shortwave_radiation_sum",
    ]
    respuesta = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": latitud,
            "longitude": longitud,
            "start_date": "2021-01-01",
            "end_date": "2025-12-31",
            "daily": ",".join(variables),
            "timezone": "America/Mexico_City",
        },
        timeout=60,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    unidades = datos["daily_units"]

    df = pd.DataFrame(datos["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.rename(columns={
        "time": "Fecha",
        "temperature_2m_max": "TempMax",
        "temperature_2m_min": "TempMin",
        "temperature_2m_mean": "TempMedia",
        "apparent_temperature_max": "Sensacion",
        "precipitation_sum": "Lluvia",
        "precipitation_hours": "HorasLluvia",
        "windspeed_10m_max": "Viento",
        "shortwave_radiation_sum": "Radiacion",
    })
    df["Anio"] = df["Fecha"].dt.year
    df["Mes"] = df["Fecha"].dt.month
    df["Amplitud"] = df["TempMax"] - df["TempMin"]
    df["Temporada"] = df["Mes"].apply(lambda m: "Lluvias" if 6 <= m <= 10 else "Secas")
    
    return df, unidades

# Carga de datos
with st.spinner(f"Descargando datos históricos de {ciudad_seleccionada}..."):
    df, unidades = cargar_datos(ciudad_seleccionada)

# ─── KPIs / Métricas Principales ───────────────────────────────────────
st.subheader(f"Resumen General · {ciudad_seleccionada} (2021 - 2025)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Temp. Máxima Histórica", f"{df['TempMax'].max():.1f} {unidades['temperature_2m_max']}")
col2.metric("Temp. Mínima Histórica", f"{df['TempMin'].min():.1f} {unidades['temperature_2m_min']}")
col3.metric("Lluvia Anual Promedio", f"{df.groupby('Anio')['Lluvia'].sum().mean():.0f} {unidades['precipitation_sum']}")
col4.metric("Radiación Media Diaria", f"{df['Radiacion'].mean():.1f} {unidades['shortwave_radiation_sum']}")

st.divider()

# ─── Gráfica 1 ─────────────────────────────────────────────────────────
st.subheader(f"1. Banda de temperatura en {anio_banda}")
ultimo = df[df["Anio"] == anio_banda]

fig1, ax1 = plt.subplots(figsize=(10, 4))
ax1.fill_between(ultimo["Fecha"], ultimo["TempMin"], ultimo["TempMax"], color=GRIS, label="Entre mínima y máxima")
ax1.plot(ultimo["Fecha"], ultimo["TempMedia"], color=AZUL, linewidth=1.5, label="Temperatura media")
ax1.set_title(f"El día más frío y el más caluroso de cada fecha en {ciudad_seleccionada} ({anio_banda})")
ax1.set_xlabel("Fecha")
ax1.set_ylabel(f"Temperatura ({unidades['temperature_2m_max']})")
ax1.legend(frameon=False)
st.pyplot(fig1)

# ─── Gráficas 2 y 3 en dos columnas ────────────────────────────────────
col_izq, col_der = st.columns(2)

with col_izq:
    st.subheader("2. Lluvia acumulada vs Horas de lluvia")
    mensual = df.groupby("Mes").agg(Lluvia=("Lluvia", "sum"), Horas=("HorasLluvia", "sum")) / df["Anio"].nunique()
    
    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    colores = [AZUL if v == mensual["Lluvia"].max() else GRIS for v in mensual["Lluvia"]]
    ax2.bar(mensual.index, mensual["Lluvia"], color=colores)
    ax2.set_title("Concentración mensual de lluvia")
    ax2.set_xlabel("Mes")
    ax2.set_ylabel(f"Lluvia ({unidades['precipitation_sum']})")
    ax2.set_xticks(range(1, 13))
    
    eje2 = ax2.twinx()
    eje2.plot(mensual.index, mensual["Horas"], color=ROJO, linewidth=2, marker="o", markersize=4)
    eje2.set_ylabel("Horas con lluvia", color=ROJO)
    eje2.grid(False)
    st.pyplot(fig2)

with col_der:
    st.subheader("3. Amplitud térmica diaria por mes")
    fig3, ax3 = plt.subplots(figsize=(7, 4.5))
    sns.boxplot(data=df, x="Mes", y="Amplitud", color=GRIS, ax=ax3)
    ax3.set_title("Diferencia entre máxima y mínima diaria")
    ax3.set_xlabel("Mes")
    ax3.set_ylabel(f"Amplitud ({unidades['temperature_2m_max']})")
    st.pyplot(fig3)

st.divider()

# ─── Gráficas 4 y 5 (Nuevas gráficas solicitadas) ──────────────────────
col_izq2, col_der2 = st.columns(2)

with col_izq2:
    st.subheader("4. Radiación solar contra temperatura máxima")
    fig4, ax4 = plt.subplots(figsize=(7, 4.5))
    sns.scatterplot(
        data=df, 
        x="Radiacion", 
        y="TempMax", 
        hue="Temporada", 
        palette={"Secas": NARANJA, "Lluvias": AZUL},
        alpha=0.6, 
        ax=ax4
    )
    ax4.set_title("Relación Radiación vs Temperatura Máxima")
    ax4.set_xlabel(f"Radiación Solar ({unidades['shortwave_radiation_sum']})")
    ax4.set_ylabel(f"Temp. Máxima ({unidades['temperature_2m_max']})")
    st.pyplot(fig4)

with col_der2:
    st.subheader("5. Mapa de calor: Temperatura media mes por año")
    matriz_temp = df.pivot_table(index="Anio", columns="Mes", values="TempMedia", aggfunc="mean")
    
    fig5, ax5 = plt.subplots(figsize=(7, 4.5))
    sns.heatmap(
        matriz_temp, 
        annot=True, 
        fmt=".1f", 
        cmap="YlOrRd", 
        linewidths=0.5, 
        cbar_kws={"label": f"Temp. Media ({unidades['temperature_2m_mean']})"},
        ax=ax5
    )
    ax5.set_title(f"Temperatura media mensual ({ciudad_seleccionada})")
    ax5.set_xlabel("Mes")
    ax5.set_ylabel("Año")
    st.pyplot(fig5)

# ─── Tabla de datos crudos desplegable ─────────────────────────────────
with st.expander("📋 Ver tabla de datos históricos completos"):
    st.dataframe(df, use_container_width=True)