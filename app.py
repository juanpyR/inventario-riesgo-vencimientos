import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="Centro Analítico de Inventario",
    layout="wide"
)

# =============================================================================
# UTILIDADES
# =============================================================================

def clp(x):
    if pd.isna(x):
        return "$0"
    return f"${int(x):,}".replace(",", ".")

def to_numeric_safe(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

# =============================================================================
# ETL CENTRAL
# =============================================================================

@st.cache_data
def cargar_datos():

    suc = pd.read_csv("1_SUCURSALES_MASTER.csv")
    prod = pd.read_csv("2_PRODUCTOS_MASTER.csv")
    lotes = pd.read_csv("3_LOTES_PRODUCTOS.csv")
    inv = pd.read_csv("4_INVENTARIO_COMPLETO_LOTES.csv")

    # Limpieza columnas
    for df in [suc, prod, lotes, inv]:
        df.columns = df.columns.str.strip()

    # Normalización numérica
    inv = to_numeric_safe(inv, [
        "Cantidad_Entrada",
        "Cantidad_Salida",
        "Valor_Unitario_CLP",
        "Precio_Venta_CLP",
        "Stock_Teorico_Unidades",
        "Dias_Para_Vencer"
    ])

    # Merge dimensiones
    df = inv.merge(prod, on="Producto_ID", how="left")
    df = df.merge(suc, on="Sucursal", how="left")

    # Capital
    df["Capital_Inmovilizado"] = (
        df["Stock_Teorico_Unidades"] *
        df["Valor_Unitario_CLP"]
    )

    # Margen unitario
    df["Margen_Unitario"] = (
        df["Precio_Venta_CLP"] -
        df["Valor_Unitario_CLP"]
    )

    # Rotación promedio por producto
    rotacion = (
        df.groupby("Producto_ID")["Cantidad_Salida"]
        .mean()
        .reset_index()
        .rename(columns={"Cantidad_Salida": "Venta_Promedio"})
    )

    df = df.merge(rotacion, on="Producto_ID", how="left")

    df["Venta_Promedio"] = df["Venta_Promedio"].replace(0, 1)

    # Cobertura
    df["Cobertura_Dias"] = (
        df["Stock_Teorico_Unidades"] /
        df["Venta_Promedio"]
    )

    return df

# =============================================================================
# MOTOR DE RIESGO
# =============================================================================

def calcular_riesgo(df):

    # Score vencimiento
    df["Score_Vencimiento"] = np.where(
        df["Dias_Para_Vencer"] <= 0, 5,
        np.where(df["Dias_Para_Vencer"] <= 3, 4,
        np.where(df["Dias_Para_Vencer"] <= 7, 3,
        np.where(df["Dias_Para_Vencer"] <= 15, 2, 1)))
    )

    # Score capital (quintiles)
    df["Score_Capital"] = pd.qcut(
        df["Capital_Inmovilizado"].rank(method="first"),
        5,
        labels=False
    ) + 1

    # Score cobertura
    df["Score_Sobrestock"] = np.where(
        df["Cobertura_Dias"] > 60, 4,
        np.where(df["Cobertura_Dias"] > 30, 3,
        np.where(df["Cobertura_Dias"] > 15, 2, 1))
    )

    df["Score_Total"] = (
        df["Score_Vencimiento"] * 0.5 +
        df["Score_Capital"] * 0.3 +
        df["Score_Sobrestock"] * 0.2
    )

    return df

# =============================================================================
# MÉTRICAS EJECUTIVAS
# =============================================================================

def calcular_kpis(df):

    capital_total = df["Capital_Inmovilizado"].sum()

    df_riesgo = df[df["Score_Total"] >= 3]

    capital_riesgo = df_riesgo["Capital_Inmovilizado"].sum()

    perdida_proyectada = capital_riesgo * 0.5

    indice_salud = 100 - (
        df["Score_Total"].mean() - 1
    ) / 4 * 100

    pct_riesgo = (
        capital_riesgo / capital_total * 100
        if capital_total > 0 else 0
    )

    return {
        "capital_total": capital_total,
        "capital_riesgo": capital_riesgo,
        "perdida_proyectada": perdida_proyectada,
        "indice_salud": max(0, min(100, indice_salud)),
        "pct_riesgo": pct_riesgo
    }

# =============================================================================
# DASHBOARD
# =============================================================================

df = cargar_datos()
df = calcular_riesgo(df)
kpis = calcular_kpis(df)

st.title("🛡️ Centro Analítico de Inventario")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Capital Total", clp(kpis["capital_total"]))
c2.metric("Capital en Riesgo", clp(kpis["capital_riesgo"]))
c3.metric("% Capital Riesgo", f"{kpis['pct_riesgo']:.1f}%")
c4.metric("Pérdida Proyectada", clp(kpis["perdida_proyectada"]))
c5.metric("Índice Salud", f"{kpis['indice_salud']:.1f}/100")

st.divider()

# =============================================================================
# TOP PRODUCTOS RIESGO
# =============================================================================

st.subheader("🔥 Top 20 Productos Más Críticos")

df_top = df.sort_values(
    by="Score_Total",
    ascending=False
).head(20)

st.dataframe(
    df_top[[
        "Producto_ID",
        "Sucursal",
        "Capital_Inmovilizado",
        "Dias_Para_Vencer",
        "Cobertura_Dias",
        "Score_Total"
    ]],
    use_container_width=True,
    hide_index=True
)

# =============================================================================
# RIESGO POR SUCURSAL
# =============================================================================

st.subheader("🏬 Riesgo por Sucursal")

riesgo_sucursal = (
    df.groupby("Sucursal")
    .agg({
        "Capital_Inmovilizado": "sum",
        "Score_Total": "mean"
    })
    .reset_index()
)

st.dataframe(riesgo_sucursal, use_container_width=True)

# =============================================================================
# MAPA GEO
# =============================================================================

if {"Latitud", "Longitud"}.issubset(df.columns):

    st.subheader("📍 Concentración Geográfica")

    df_geo = (
        df.groupby(["Latitud", "Longitud"], as_index=False)
        .agg({"Capital_Inmovilizado": "sum"})
        .rename(columns={
            "Latitud": "lat",
            "Longitud": "lon"
        })
    )

    st.map(df_geo)

# =============================================================================
# DESCARGA
# =============================================================================

csv = df.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    "⬇ Descargar análisis completo",
    data=csv,
    file_name="inventario_enterprise_analizado.csv",
    mime="text/csv"
)
