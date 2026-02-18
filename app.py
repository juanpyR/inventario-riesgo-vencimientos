import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

st.set_page_config(
    page_title="Centro Analítico de Riesgo de Inventario",
    layout="wide"
)

# =============================================================================
# UTILIDADES
# =============================================================================

def clp(x):
    if pd.isna(x):
        return "$0"
    return f"${int(x):,}".replace(",", ".")

def safe_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

# =============================================================================
# ETL PRINCIPAL
# =============================================================================

@st.cache_data
def cargar_y_procesar(archivos):

    suc = pd.read_csv(archivos["1_SUCURSALES_MASTER"])
    prod = pd.read_csv(archivos["2_PRODUCTOS_MASTER"])
    lotes = pd.read_csv(archivos["3_LOTES_PRODUCTOS"])
    inv = pd.read_csv(archivos["4_INVENTARIO_COMPLETO_LOTES"])
    geo = pd.read_csv(archivos["5_STOCK_ACTUAL_GEO_POWERBI"])

    # Limpieza columnas
    for df in [suc, prod, lotes, inv, geo]:
        df.columns = df.columns.str.strip()

    inv = safe_numeric(inv, [
        "Cantidad_Entrada",
        "Cantidad_Salida",
        "Valor_Unitario_CLP",
        "Precio_Venta_CLP",
        "Stock_Teorico_Unidades",
        "Dias_Para_Vencer"
    ])

    # =============================
    # MERGES
    # =============================

    df = inv.merge(prod, on="Producto_ID", how="left")
    df = df.merge(suc, on="Sucursal", how="left")

    # =============================
    # MÉTRICAS BASE
    # =============================

    df["Capital_Inmovilizado"] = (
        df["Stock_Teorico_Unidades"] *
        df["Valor_Unitario_CLP"]
    )

    df["Ingresos_Potenciales"] = (
        df["Stock_Teorico_Unidades"] *
        df["Precio_Venta_CLP"]
    )

    df["Margen_Unitario"] = (
        df["Precio_Venta_CLP"] -
        df["Valor_Unitario_CLP"]
    )

    df["Margen_Total_Potencial"] = (
        df["Margen_Unitario"] *
        df["Stock_Teorico_Unidades"]
    )

    # =============================
    # ROTACIÓN
    # =============================

    rot = (
        df.groupby("Producto_ID")["Cantidad_Salida"]
        .mean()
        .reset_index()
        .rename(columns={"Cantidad_Salida": "Venta_Promedio"})
    )

    df = df.merge(rot, on="Producto_ID", how="left")
    df["Venta_Promedio"] = df["Venta_Promedio"].replace(0, 1)

    df["Cobertura_Dias"] = (
        df["Stock_Teorico_Unidades"] /
        df["Venta_Promedio"]
    )

    # =============================
    # MOTOR DE RIESGO
    # =============================

    df["Score_Vencimiento"] = np.select(
        [
            df["Dias_Para_Vencer"] <= 0,
            df["Dias_Para_Vencer"] <= 3,
            df["Dias_Para_Vencer"] <= 7,
            df["Dias_Para_Vencer"] <= 15
        ],
        [5,4,3,2],
        default=1
    )

    df["Score_Sobrestock"] = np.select(
        [
            df["Cobertura_Dias"] > 90,
            df["Cobertura_Dias"] > 60,
            df["Cobertura_Dias"] > 30
        ],
        [4,3,2],
        default=1
    )

    df["Score_Capital"] = pd.qcut(
        df["Capital_Inmovilizado"].rank(method="first"),
        5,
        labels=False,
        duplicates="drop"
    ) + 1

    df["Score_Total"] = (
        df["Score_Vencimiento"] * 0.5 +
        df["Score_Capital"] * 0.3 +
        df["Score_Sobrestock"] * 0.2
    )

    # Clasificación estratégica
    df["Nivel_Riesgo"] = np.select(
        [
            df["Score_Total"] >= 4,
            df["Score_Total"] >= 3
        ],
        ["CRÍTICO", "ALTO"],
        default="CONTROLADO"
    )

    # =============================
    # SIMULACIÓN DE LIQUIDACIÓN
    # =============================

    df["Ingreso_Liquidacion_30"] = df["Ingresos_Potenciales"] * 0.7
    df["Ingreso_Liquidacion_50"] = df["Ingresos_Potenciales"] * 0.5
    df["Ingreso_Liquidacion_70"] = df["Ingresos_Potenciales"] * 0.3

    df["Perdida_Proyectada"] = np.where(
        df["Dias_Para_Vencer"] <= 0,
        df["Capital_Inmovilizado"],
        np.where(
            df["Dias_Para_Vencer"] <= 7,
            df["Capital_Inmovilizado"] * 0.5,
            df["Capital_Inmovilizado"] * 0.2
        )
    )

    # =============================
    # MOTOR DE DONACIÓN
    # =============================

    df["Sugerencia_Donacion"] = np.where(
        (df["Dias_Para_Vencer"] <= 3) &
        (df["Cobertura_Dias"] > 60),
        "DONAR",
        "NO"
    )

    return df

# =============================================================================
# SIDEBAR - CARGA
# =============================================================================

st.sidebar.title("📂 Cargar Archivos Base")

uploaded = st.sidebar.file_uploader(
    "Sube los 5 archivos CSV",
    type="csv",
    accept_multiple_files=True
)

if not uploaded:
    st.warning("Debes subir los 5 archivos.")
    st.stop()

archivos = {f.name.replace(".csv",""): f for f in uploaded}

requeridos = [
    "1_SUCURSALES_MASTER",
    "2_PRODUCTOS_MASTER",
    "3_LOTES_PRODUCTOS",
    "4_INVENTARIO_COMPLETO_LOTES",
    "5_STOCK_ACTUAL_GEO_POWERBI"
]

faltan = [r for r in requeridos if r not in archivos]

if faltan:
    st.error(f"Faltan archivos: {', '.join(faltan)}")
    st.stop()

df = cargar_y_procesar(archivos)

# =============================================================================
# KPIs EJECUTIVOS
# =============================================================================

capital_total = df["Capital_Inmovilizado"].sum()
capital_riesgo = df[df["Nivel_Riesgo"] != "CONTROLADO"]["Capital_Inmovilizado"].sum()
perdida_total = df["Perdida_Proyectada"].sum()
margen_total = df["Margen_Total_Potencial"].sum()
indice_salud = 100 - ((df["Score_Total"].mean() - 1)/4*100)

# =============================================================================
# DASHBOARD
# =============================================================================

st.title("🛡️ Centro Analítico de Riesgo de Inventario")

c1,c2,c3,c4,c5 = st.columns(5)

c1.metric("Capital Total", clp(capital_total))
c2.metric("Capital en Riesgo", clp(capital_riesgo))
c3.metric("Pérdida Proyectada", clp(perdida_total))
c4.metric("Margen Potencial", clp(margen_total))
c5.metric("Índice Salud", f"{indice_salud:.1f}/100")

st.divider()

# =============================================================================
# ANÁLISIS POR SUCURSAL
# =============================================================================

st.subheader("🏪 Riesgo por Sucursal")

suc_riesgo = (
    df.groupby("Sucursal")
    .agg({
        "Capital_Inmovilizado":"sum",
        "Perdida_Proyectada":"sum"
    })
    .reset_index()
)

st.dataframe(suc_riesgo, use_container_width=True)

# =============================================================================
# TOP CRÍTICOS
# =============================================================================

st.subheader("🔥 Top 25 Productos Críticos")

top = df.sort_values("Score_Total", ascending=False).head(25)

st.dataframe(
    top[[
        "Producto_ID",
        "Sucursal",
        "Capital_Inmovilizado",
        "Dias_Para_Vencer",
        "Cobertura_Dias",
        "Nivel_Riesgo"
    ]],
    use_container_width=True
)

# =============================================================================
# SIMULADOR GLOBAL
# =============================================================================

st.subheader("🎯 Simulador de Liquidación Global")

rec30 = df["Ingreso_Liquidacion_30"].sum()
rec50 = df["Ingreso_Liquidacion_50"].sum()
rec70 = df["Ingreso_Liquidacion_70"].sum()

col1,col2,col3 = st.columns(3)
col1.metric("Escenario -30%", clp(rec30))
col2.metric("Escenario -50%", clp(rec50))
col3.metric("Escenario -70%", clp(rec70))

# =============================================================================
# MAPA
# =============================================================================

if {"Latitud","Longitud"}.issubset(df.columns):
    st.subheader("📍 Concentración Geográfica")
    geo_df = (
        df.groupby(["Latitud","Longitud"], as_index=False)
        .agg({"Capital_Inmovilizado":"sum"})
        .rename(columns={"Latitud":"lat","Longitud":"lon"})
    )
    st.map(geo_df)

# =============================================================================
# DESCARGA
# =============================================================================

csv = df.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    "⬇ Descargar Dataset Analizado Completo",
    data=csv,
    file_name="inventario_riesgo_full_enterprise.csv",
    mime="text/csv"
)
