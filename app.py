import streamlit as st
import pandas as pd
import numpy as np

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
def cargar_y_transformar(archivos_dict):

    suc = pd.read_csv(archivos_dict["1_SUCURSALES_MASTER"])
    prod = pd.read_csv(archivos_dict["2_PRODUCTOS_MASTER"])
    lotes = pd.read_csv(archivos_dict["3_LOTES_PRODUCTOS"])
    inv = pd.read_csv(archivos_dict["4_INVENTARIO_COMPLETO_LOTES"])
    stock_geo = pd.read_csv(archivos_dict["5_STOCK_ACTUAL_GEO_POWERBI"])

    # Limpieza columnas
    for df in [suc, prod, lotes, inv, stock_geo]:
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

    # Merge dimensiones principales
    df = inv.merge(prod, on="Producto_ID", how="left")
    df = df.merge(suc, on="Sucursal", how="left")

    # =============================
    # MÉTRICAS BASE
    # =============================

    df["Capital_Inmovilizado"] = (
        df["Stock_Teorico_Unidades"] *
        df["Valor_Unitario_CLP"]
    )

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

    df["Cobertura_Dias"] = (
        df["Stock_Teorico_Unidades"] /
        df["Venta_Promedio"]
    )

    # =============================
    # MOTOR DE RIESGO
    # =============================

    df["Score_Vencimiento"] = np.where(
        df["Dias_Para_Vencer"] <= 0, 5,
        np.where(df["Dias_Para_Vencer"] <= 3, 4,
        np.where(df["Dias_Para_Vencer"] <= 7, 3,
        np.where(df["Dias_Para_Vencer"] <= 15, 2, 1)))
    )

    df["Score_Capital"] = pd.qcut(
        df["Capital_Inmovilizado"].rank(method="first"),
        5,
        labels=False,
        duplicates="drop"
    ) + 1

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
# SIDEBAR - CARGA MÚLTIPLE
# =============================================================================

st.sidebar.title("📂 Cargar Archivos Base")

uploaded_files = st.sidebar.file_uploader(
    "Selecciona los 5 archivos CSV",
    type="csv",
    accept_multiple_files=True
)

if not uploaded_files:
    st.warning("⚠ Debes cargar los 5 archivos CSV.")
    st.stop()

# Convertir lista en diccionario por nombre base
archivos_dict = {}
for file in uploaded_files:
    nombre = file.name.replace(".csv", "")
    archivos_dict[nombre] = file

# Archivos requeridos
requeridos = [
    "1_SUCURSALES_MASTER",
    "2_PRODUCTOS_MASTER",
    "3_LOTES_PRODUCTOS",
    "4_INVENTARIO_COMPLETO_LOTES",
    "5_STOCK_ACTUAL_GEO_POWERBI"
]

faltantes = [r for r in requeridos if r not in archivos_dict]

if faltantes:
    st.error(f"Faltan archivos: {', '.join(faltantes)}")
    st.stop()

# =============================================================================
# EJECUCIÓN
# =============================================================================

df = cargar_y_transformar(archivos_dict)

# =============================================================================
# KPIs
# =============================================================================

capital_total = df["Capital_Inmovilizado"].sum()
df_riesgo = df[df["Score_Total"] >= 3]
capital_riesgo = df_riesgo["Capital_Inmovilizado"].sum()
perdida_proyectada = capital_riesgo * 0.5
indice_salud = 100 - ((df["Score_Total"].mean() - 1) / 4 * 100)
pct_riesgo = (capital_riesgo / capital_total * 100) if capital_total > 0 else 0

# =============================================================================
# DASHBOARD
# =============================================================================

st.title("🛡️ Centro Analítico de Inventario")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Capital Total", clp(capital_total))
c2.metric("Capital en Riesgo", clp(capital_riesgo))
c3.metric("% Capital Riesgo", f"{pct_riesgo:.1f}%")
c4.metric("Pérdida Proyectada", clp(perdida_proyectada))
c5.metric("Índice Salud", f"{indice_salud:.1f}/100")

st.divider()

st.subheader("🔥 Top 20 Productos Más Críticos")

df_top = df.sort_values("Score_Total", ascending=False).head(20)

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
# MAPA
# =============================================================================

if {"Latitud", "Longitud"}.issubset(df.columns):

    st.subheader("📍 Concentración Geográfica")

    df_geo = (
        df.groupby(["Latitud", "Longitud"], as_index=False)
        .agg({"Capital_Inmovilizado": "sum"})
        .rename(columns={"Latitud": "lat", "Longitud": "lon"})
    )

    st.map(df_geo)

# =============================================================================
# DESCARGA
# =============================================================================

csv = df.to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    "⬇ Descargar análisis completo",
    data=csv,
    file_name="inventario_analizado_enterprise.csv",
    mime="text/csv"
)
