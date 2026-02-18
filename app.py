import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
import pytz

# =============================================================================
# CONFIGURACIÓN
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

def asegurar_columna(df, col, default=0):
    if col not in df.columns:
        df[col] = default
    return df

def convertir_numerico_seguro(df, columnas):
    for col in columnas:
        df = asegurar_columna(df, col)
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

def score_vencimiento(dias):
    if pd.isna(dias): return 1
    if dias <= 0: return 5
    elif dias <= 3: return 4
    elif dias <= 7: return 3
    elif dias <= 15: return 2
    else: return 1

# =============================================================================
# CARGA
# =============================================================================

@st.cache_data
def cargar_archivo(archivo):
    df = pd.read_csv(io.BytesIO(archivo.getvalue()))
    df.columns = df.columns.str.strip()
    return df

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("⚙️ Configuración")
    archivo = st.file_uploader("Sube archivo CSV de inventario", type="csv")

# =============================================================================
# MAIN
# =============================================================================

if archivo:

    df = cargar_archivo(archivo)

    # --------------------------------------------------
    # NORMALIZACIÓN
    # --------------------------------------------------

    columnas_numericas = [
        "Stock_Teorico_Unidades",
        "Valor_Unitario_CLP",
        "Dias_Efectivos",
        "Venta_Promedio_Diaria"
    ]

    df = convertir_numerico_seguro(df, columnas_numericas)

    # --------------------------------------------------
    # CÁLCULOS PRINCIPALES
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

    df["Score_Vencimiento"] = df["Dias_Efectivos"].apply(score_vencimiento)

    df["Score_Sobrestock"] = np.where(
        df["Cobertura_Dias"] > 60, 4,
        np.where(df["Cobertura_Dias"] > 30, 3,
        np.where(df["Cobertura_Dias"] > 15, 2, 1))
    )

    df["Score_Total"] = (
        df["Score_Vencimiento"] * 0.6 +
        df["Score_Sobrestock"] * 0.4
    )

    # --------------------------------------------------
    # ÍNDICE SALUD
    # --------------------------------------------------

    score_promedio = df["Score_Total"].mean()
    indice_salud = 100 - ((score_promedio - 1) / 4 * 100)
    indice_salud = max(0, min(100, indice_salud))

    # --------------------------------------------------
    # KPIs EJECUTIVOS
    # --------------------------------------------------

    capital_total = df["Capital_Inmovilizado"].sum()

    capital_riesgo = df[
        df["Score_Total"] >= 3
    ]["Capital_Inmovilizado"].sum()

    perdida_proyectada = df[
        df["Score_Total"] >= 3
    ]["Capital_Inmovilizado"].sum() * 0.5

    productos_criticos = len(df[df["Score_Total"] >= 4])

    pct_riesgo = 0
    if capital_total > 0:
        pct_riesgo = capital_riesgo / capital_total * 100

    # --------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------

    st.title("🛡️ Centro Analítico de Inventario")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Capital Total", clp(capital_total))
    c2.metric("Capital en Riesgo", clp(capital_riesgo))
    c3.metric("% Capital Riesgo", f"{pct_riesgo:.1f}%")
    c4.metric("Pérdida Proyectada", clp(perdida_proyectada))
    c5.metric("Índice Salud", f"{indice_salud:.1f}/100")

    st.divider()

    # --------------------------------------------------
    # RANKING ESTRATÉGICO
    # --------------------------------------------------

    st.subheader("🔥 Top 20 Productos Más Riesgosos")

    df_top = df.sort_values(
        by="Score_Total",
        ascending=False
    ).head(20)

    columnas_mostrar = [
        col for col in [
            "Score_Total",
            "Capital_Inmovilizado",
            "Cobertura_Dias",
            "Dias_Efectivos",
            "Stock_Teorico_Unidades",
            "Valor_Unitario_CLP"
        ] if col in df_top.columns
    ]

    st.dataframe(
        df_top[columnas_mostrar],
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # --------------------------------------------------
    # MAPA PONDERADO (SI EXISTE GEO)
    # --------------------------------------------------

    if {"Latitud", "Longitud"}.issubset(df.columns):

        st.subheader("📍 Concentración de Capital en Riesgo por Ubicación")

        df_geo = df.groupby(
            ["Latitud", "Longitud"],
            as_index=False
        ).agg({
            "Capital_Inmovilizado": "sum"
        })

        df_geo = df_geo.rename(columns={
            "Latitud": "lat",
            "Longitud": "lon"
        })

        st.map(df_geo)

    # --------------------------------------------------
    # DESCARGA
    # --------------------------------------------------

    csv = df.to_csv(index=False, encoding="utf-8-sig")

    st.download_button(
        "⬇ Descargar análisis completo",
        data=csv,
        file_name="inventario_analizado_full.csv",
        mime="text/csv"
    )

else:
    st.info("Sube un archivo CSV para iniciar el análisis.")
