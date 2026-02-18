import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import pytz
import io
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="🛡️ Command Center: Riesgo de Inventario",
    layout="wide",
    page_icon="📊"
)

# =============================================================================
# UTILIDADES
# =============================================================================

def clp(valor):
    if pd.isna(valor) or valor is None:
        return "$0"
    try:
        v = int(round(float(valor)))
        return f"${v:,}".replace(",", ".")
    except:
        return "$0"


def clasificar_riesgo_mensual(dias):
    if pd.isna(dias):
        return 'SIN_DATO'
    if dias <= 0:
        return 'VENCIDO'
    elif dias <= 3:
        return 'CRITICO'
    elif dias <= 7:
        return 'URGENTE'
    elif dias <= 30:
        return 'PREVENTIVO'
    else:
        return 'NORMAL'


COLOR_MAP = {
    'VENCIDO': '#9c27b0',
    'CRITICO': '#d32f2f',
    'URGENTE': '#f57c00',
    'PREVENTIVO': '#fbc02d',
    'NORMAL': '#2e7d32',
    'SIN_DATO': '#9e9e9e'
}

# =============================================================================
# CACHE CARGA
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def cargar_archivo_inteligente(archivo):
    try:
        df = pd.read_csv(io.BytesIO(archivo.getvalue()))
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error cargando {archivo.name}: {str(e)}")
        return None

# =============================================================================
# VENTANA MENSUAL
# =============================================================================

def obtener_ventana_mensual(fecha):
    inicio = fecha.replace(day=1)
    ultimo = calendar.monthrange(fecha.year, fecha.month)[1]
    fin = fecha.replace(day=ultimo)
    return inicio, fin

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("🎛️ Panel")

    uploaded_files = st.file_uploader(
        "Sube CSV",
        type="csv",
        accept_multiple_files=True
    )

    incluir_fuera_ventana = st.checkbox(
        "Mostrar fuera de ventana",
        value=False
    )

# =============================================================================
# MAIN
# =============================================================================

if uploaded_files:

    dataframes = []

    for file in uploaded_files:
        df = cargar_archivo_inteligente(file)
        if df is not None:
            dataframes.append(df)

    if not dataframes:
        st.stop()

    df_base = pd.concat(dataframes, ignore_index=True)

    tz_cl = pytz.timezone("America/Santiago")
    fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
    inicio_mes, fin_mes = obtener_ventana_mensual(fecha_hoy)

    # ---------------------------------------------
    # FECHA VENCIMIENTO
    # ---------------------------------------------

    if "Fecha_Vencimiento_Lote" in df_base.columns:
        df_base["Fecha_Vencimiento_Lote"] = pd.to_datetime(
            df_base["Fecha_Vencimiento_Lote"], errors="coerce"
        )

        df_base["Dias_Efectivos"] = (
            df_base["Fecha_Vencimiento_Lote"] - fecha_hoy
        ).dt.days

        if not incluir_fuera_ventana:
            df_base = df_base[
                (df_base["Fecha_Vencimiento_Lote"] >= inicio_mes) &
                (df_base["Fecha_Vencimiento_Lote"] <= fin_mes)
            ]

    elif "Dias_Para_Vencer" in df_base.columns:
        df_base["Dias_Efectivos"] = pd.to_numeric(
            df_base["Dias_Para_Vencer"], errors="coerce"
        ).fillna(0)

        if not incluir_fuera_ventana:
            df_base["Fecha_Venc_Calc"] = fecha_hoy + pd.to_timedelta(
                df_base["Dias_Efectivos"], unit="D"
            )
            df_base = df_base[
                (df_base["Fecha_Venc_Calc"] >= inicio_mes) &
                (df_base["Fecha_Venc_Calc"] <= fin_mes)
            ]
    else:
        df_base["Dias_Efectivos"] = np.nan

    # ---------------------------------------------
    # CLASIFICACIÓN
    # ---------------------------------------------

    df_base["Riesgo_BI"] = df_base["Dias_Efectivos"].apply(
        clasificar_riesgo_mensual
    )

    # ---------------------------------------------
    # NUMÉRICOS SEGUROS
    # ---------------------------------------------

    df_base["Stock_Teorico_Unidades"] = pd.to_numeric(
        df_base.get("Stock_Teorico_Unidades", 0),
        errors="coerce"
    ).fillna(0)

    df_base["Valor_Unitario_CLP"] = pd.to_numeric(
        df_base.get("Valor_Unitario_CLP", 0),
        errors="coerce"
    ).fillna(0)

    df_base["Valor_Costo_Total"] = (
        df_base["Stock_Teorico_Unidades"] *
        df_base["Valor_Unitario_CLP"]
    )

    # ---------------------------------------------
    # KPI
    # ---------------------------------------------

    df_riesgo = df_base[
        df_base["Riesgo_BI"].isin(
            ["VENCIDO", "CRITICO", "URGENTE", "PREVENTIVO"]
        )
    ]

    val_total = df_riesgo["Valor_Costo_Total"].sum()

    if "Stock_Teorico_Unidades" in df_riesgo.columns:
        unid_alerta = int(df_riesgo["Stock_Teorico_Unidades"].sum())
    else:
        unid_alerta = 0

    st.title("🛡️ Command Center")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Monto en Riesgo (Mes)", clp(val_total))

    with col2:
        st.metric("Unidades en Riesgo", f"{unid_alerta:,}")

    # ---------------------------------------------
    # TABLA SEGURA
    # ---------------------------------------------

    st.subheader("Auditoría")

    if len(df_riesgo) > 0:

        df_display = df_riesgo.copy()

        style_obj = df_display.style

        formatos = {}

        if "Valor_Costo_Total" in df_display.columns:
            formatos["Valor_Costo_Total"] = clp

        if "Stock_Teorico_Unidades" in df_display.columns:
            formatos["Stock_Teorico_Unidades"] = "{:,.0f}"

        if "Dias_Efectivos" in df_display.columns:
            formatos["Dias_Efectivos"] = "{:.0f}"

        if formatos:
            style_obj = style_obj.format(formatos)

        st.dataframe(style_obj, use_container_width=True, hide_index=True)

        csv = df_display.to_csv(index=False, encoding="utf-8-sig")

        st.download_button(
            "Descargar CSV",
            data=csv,
            file_name=f"auditoria_{fecha_hoy.strftime('%Y%m')}.csv",
            mime="text/csv"
        )

    else:
        st.info("Sin registros en ventana mensual")

else:
    st.info("Sube archivos CSV para comenzar")
