import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
import pytz

# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="🛡️ Centro Analítico de Inventario",
    layout="wide"
)

# =============================================================================
# UTILIDADES GENERALES
# =============================================================================

def clp(x):
    if pd.isna(x):
        return "$0"
    return f"${int(x):,}".replace(",", ".")

def normalizar_columnas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    return df

def convertir_numerico_seguro(df, columnas):
    for col in columnas:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0
    return df

def detectar_tipo_archivo(df):
    cols = df.columns.tolist()

    if "VENTA" in " ".join(cols):
        return "VENTAS"
    if "STOCK" in " ".join(cols):
        return "STOCK"
    if "PRECIO" in " ".join(cols):
        return "MAESTRO"
    return "DESCONOCIDO"

# =============================================================================
# ETL
# =============================================================================

@st.cache_data
def procesar_archivos(archivos):

    data = {
        "VENTAS": [],
        "STOCK": [],
        "MAESTRO": []
    }

    for archivo in archivos:
        df = pd.read_csv(io.BytesIO(archivo.getvalue()))
        df = normalizar_columnas(df)
        tipo = detectar_tipo_archivo(df)

        if tipo in data:
            data[tipo].append(df)

    # Concatenar
    for k in data:
        if data[k]:
            data[k] = pd.concat(data[k], ignore_index=True)
        else:
            data[k] = pd.DataFrame()

    # -----------------------
    # LIMPIEZA Y NORMALIZACIÓN
    # -----------------------

    if not data["STOCK"].empty:
        data["STOCK"] = convertir_numerico_seguro(
            data["STOCK"],
            ["STOCK_Teorico_Unidades".upper(), "STOCK"]
        )

    if not data["VENTAS"].empty:
        data["VENTAS"] = convertir_numerico_seguro(
            data["VENTAS"],
            ["VENTA", "CANTIDAD"]
        )

    if not data["MAESTRO"].empty:
        data["MAESTRO"] = convertir_numerico_seguro(
            data["MAESTRO"],
            ["PRECIO", "VALOR_UNITARIO_CLP"]
        )

    # -----------------------
    # UNIFICAR CLAVE SKU
    # -----------------------

    for k in data:
        if not data[k].empty:
            if "SKU" not in data[k].columns:
                if "CODIGO" in data[k].columns:
                    data[k]["SKU"] = data[k]["CODIGO"]

    # -----------------------
    # MERGE FINAL
    # -----------------------

    df_base = data["STOCK"]

    if not data["VENTAS"].empty:
        ventas_agg = data["VENTAS"].groupby("SKU", as_index=False).sum()
        df_base = df_base.merge(ventas_agg, on="SKU", how="left")

    if not data["MAESTRO"].empty:
        df_base = df_base.merge(data["MAESTRO"], on="SKU", how="left")

    df_base.fillna(0, inplace=True)

    return df_base

# =============================================================================
# SCORING
# =============================================================================

def score_vencimiento(dias):
    if dias <= 0: return 5
    elif dias <= 3: return 4
    elif dias <= 7: return 3
    elif dias <= 15: return 2
    else: return 1

# =============================================================================
# UI
# =============================================================================

with st.sidebar:
    st.title("📂 Carga de Archivos")
    archivos = st.file_uploader(
        "Sube archivos de Stock / Ventas / Maestro",
        type="csv",
        accept_multiple_files=True
    )

if archivos:

    df = procesar_archivos(archivos)

    # --------------------------------------------------
    # CÁLCULOS
    # --------------------------------------------------

    df = convertir_numerico_seguro(
        df,
        ["STOCK", "VALOR_UNITARIO_CLP", "VENTA"]
    )

    df["CAPITAL_INMOVILIZADO"] = df["STOCK"] * df["VALOR_UNITARIO_CLP"]

    df["COBERTURA_DIAS"] = np.where(
        df["VENTA"] > 0,
        df["STOCK"] / df["VENTA"],
        999
    )

    df["DIAS_EFECTIVOS"] = df.get("DIAS_EFECTIVOS", 30)

    df["SCORE_VENCIMIENTO"] = df["DIAS_EFECTIVOS"].apply(score_vencimiento)

    df["SCORE_SOBRESTOCK"] = np.where(
        df["COBERTURA_DIAS"] > 60, 4,
        np.where(df["COBERTURA_DIAS"] > 30, 3,
        np.where(df["COBERTURA_DIAS"] > 15, 2, 1))
    )

    df["SCORE_TOTAL"] = (
        df["SCORE_VENCIMIENTO"] * 0.6 +
        df["SCORE_SOBRESTOCK"] * 0.4
    )

    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------

    capital_total = df["CAPITAL_INMOVILIZADO"].sum()
    capital_riesgo = df[df["SCORE_TOTAL"] >= 3]["CAPITAL_INMOVILIZADO"].sum()

    indice_salud = 100 - (
        (df["SCORE_TOTAL"].mean() - 1) / 4 * 100
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Capital Total", clp(capital_total))
    c2.metric("Capital en Riesgo", clp(capital_riesgo))
    c3.metric("Índice Salud", f"{indice_salud:.1f}/100")

    # --------------------------------------------------
    # RANKING
    # --------------------------------------------------

    st.subheader("🔥 Top Riesgo")

    df_top = df.sort_values("SCORE_TOTAL", ascending=False).head(20)

    st.dataframe(df_top, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # DESCARGA
    # --------------------------------------------------

    csv = df.to_csv(index=False, encoding="utf-8-sig")

    st.download_button(
        "Descargar análisis completo",
        data=csv,
        file_name="inventario_full_etl.csv",
        mime="text/csv"
    )

else:
    st.info("Sube archivos para iniciar el ETL.")
