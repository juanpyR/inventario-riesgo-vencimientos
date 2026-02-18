import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import io

# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="🛡️ Centro Analítico de Inventario",
    layout="wide"
)

# =============================================================================
# UTILIDADES
# =============================================================================

def clp(x):
    if pd.isna(x):
        return "$0"
    return f"${int(x):,}".replace(",", ".")

def safe_numeric(df, col):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    else:
        df[col] = 0
    return df

# =============================================================================
# CARGA
# =============================================================================

@st.cache_data
def cargar(archivo):
    df = pd.read_csv(io.BytesIO(archivo.getvalue()))
    df.columns = df.columns.str.strip()
    return df

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("⚙️ Configuración")
    file = st.file_uploader("Sube inventario", type="csv")

# =============================================================================
# MAIN
# =============================================================================

if file:

    df = cargar(file)

    # --------------------------------------------------
    # NORMALIZACIÓN
    # --------------------------------------------------

    columnas_clave = [
        "Stock_Teorico_Unidades",
        "Valor_Unitario_CLP",
        "Dias_Para_Vencer",
        "Venta_Promedio_Diaria"
    ]

    for col in columnas_clave:
        df = safe_numeric(df, col)

    # --------------------------------------------------
    # CÁLCULOS CORE
    # --------------------------------------------------

    df["Capital_Inmovilizado"] = (
        df["Stock_Teorico_Unidades"] *
        df["Valor_Unitario_CLP"]
    )

    df["Cobertura_Dias"] = np.where(
        df["Venta_Promedio_Diaria"] > 0,
        df["Stock_Teorico_Unidades"] / df["Venta_Promedio_Diaria"],
        999
    )

    df["Riesgo_Vencimiento"] = np.where(
        df["Dias_Para_Vencer"] <= 0, 5,
        np.where(df["Dias_Para_Vencer"] <= 3, 4,
        np.where(df["Dias_Para_Vencer"] <= 7, 3,
        np.where(df["Dias_Para_Vencer"] <= 15, 2, 1)))
    )

    df["Riesgo_Sobrestock"] = np.where(
        df["Cobertura_Dias"] > 60, 4,
        np.where(df["Cobertura_Dias"] > 30, 3,
        np.where(df["Cobertura_Dias"] > 15, 2, 1))
    )

    # Score ejecutivo ponderado
    df["Score_Riesgo_Total"] = (
        df["Riesgo_Vencimiento"] * 0.6 +
        df["Riesgo_Sobrestock"] * 0.4
    )

    # Pérdida proyectada
    df["Perdida_Proyectada"] = np.where(
        df["Dias_Para_Vencer"] <= df["Cobertura_Dias"],
        df["Capital_Inmovilizado"] * 0.6,
        df["Capital_Inmovilizado"] * 0.2
    )

    # --------------------------------------------------
    # KPIs EJECUTIVOS
    # --------------------------------------------------

    capital_total = df["Capital_Inmovilizado"].sum()
    capital_riesgo = df[df["Score_Riesgo_Total"] >= 3]["Capital_Inmovilizado"].sum()
    perdida_estimada = df["Perdida_Proyectada"].sum()
    productos_criticos = len(df[df["Score_Riesgo_Total"] >= 4])

    st.title("🛡️ Centro Analítico de Inventario")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Capital Total", clp(capital_total))
    c2.metric("Capital en Riesgo Alto", clp(capital_riesgo))
    c3.metric("Pérdida Proyectada", clp(perdida_estimada))
    c4.metric("Productos Críticos", productos_criticos)

    # --------------------------------------------------
    # RANKING INTELIGENTE
    # --------------------------------------------------

    st.subheader("🔥 Top 20 Productos Más Riesgosos")

    df_top = df.sort_values(
        by="Score_Riesgo_Total",
        ascending=False
    ).head(20)

    st.dataframe(
        df_top[[
            "Score_Riesgo_Total",
            "Capital_Inmovilizado",
            "Perdida_Proyectada",
            "Cobertura_Dias",
            "Dias_Para_Vencer"
        ]],
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------
    # DESCARGA
    # --------------------------------------------------

    csv = df.to_csv(index=False, encoding="utf-8-sig")

    st.download_button(
        "Descargar análisis completo",
        data=csv,
        file_name="inventario_analizado.csv",
        mime="text/csv"
    )

else:
    st.info("Sube un archivo CSV para iniciar el análisis.")
