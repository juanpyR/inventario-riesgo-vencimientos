import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="BI - Gestión de Riesgo de Inventario", layout="wide")

# =============================================================================
# LÓGICA DE NEGOCIO Y FORMATO (Basada en inventario.py)
# =============================================================================
def clp(valor):
    """Formatea número con estilo chileno: $1.234.567"""
    if pd.isna(valor): return "$0"
    return f"${int(round(float(valor))):,}".replace(",", ".")

def clasificar_riesgo_hoy(fecha_venc, fecha_hoy):
    """Clasificación semáforo según lógica de inventario.py"""
    dias = (fecha_venc - fecha_hoy).days
    if dias <= 0: return 'VENCIDO'
    elif dias <= 15: return 'CRITICO'
    elif dias <= 30: return 'URGENTE'
    elif dias <= 60: return 'PREVENTIVO'
    else: return 'NORMAL'

COLOR_MAP = {
    'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 
    'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32'
}

# --- ESTILOS CSS (Dashboard BI) ---
st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 20px; border-radius: 12px; border-top: 6px solid #1f77b4; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 25px; }
    .plan-box { background-color: #fef9e7; border-left: 8px solid #f39c12; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .metric-val { font-size: 30px; font-weight: bold; color: #1f77b4; }
    .metric-label { font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA Y RELACIÓN DE TABLAS ---
st.sidebar.title("📁 Carga de Datos")
uploaded_files = st.sidebar.file_uploader("Subir archivos maestros y transaccionales", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "productos": None, "inventario": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Identificación de tablas por columnas clave
        if "Latitud" in cols and "ID_Ciudad" in cols:
            data["sucursales"] = df_temp
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
        elif "Tipo_Movimiento" in cols and "Lote_ID" in cols:
            data["inventario"] = df_temp

    # --- PROCESO DE INTEGRACIÓN Y ANÁLISIS ---
    if all(v is not None for v in [data["sucursales"], data["productos"], data["inventario"]]):
        try:
            # 1. Relación de Tablas (Merge)
            df_full = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
            df_full = df_full.merge(data["productos"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], on='Producto_ID', how='left')
            
            # 2. Análisis al día de hoy
            tz_cl = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
            
            df_full['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_full['Fecha_Vencimiento_Lote'])
            
            # Snapshot actual: último movimiento por lote en cada sucursal
            df_actual = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            
            # Recalcular Riesgo basado en HOY
            df_actual['Dias_Restantes'] = (df_actual['Fecha_Vencimiento_Lote'] - fecha_hoy).dt.days
            df_actual['Riesgo_Hoy'] = df_actual['Dias_Restantes'].apply(lambda x: clasificar_riesgo_hoy(datetime.now(), datetime.now() + pd.Timedelta(days=x)))
            df_actual['Valor_Stock'] = df_actual['Stock_Teorico_Unidades'] * df_actual['Precio_Venta_CLP']

            # --- VISTA BI PRINCIPAL ---
            st.title(f"🛡️ Panel de Riesgo al {fecha_hoy.strftime('%d/%m/%Y')}")
            
            # Filtros de Dashboard
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                sel_suc = st.multiselect("Filtrar por Sucursal", df_actual['Sucursal'].unique(), default=df_actual['Sucursal'].unique())
            with c_f2:
                sel_riesgo = st.multiselect("Niveles de Riesgo", list(COLOR_MAP.keys()), default=['VENCIDO', 'CRITICO', 'URGENTE'])

            df_final = df_actual[(df_actual['Sucursal'].isin(sel_suc)) & (df_actual['Riesgo_Hoy'].isin(sel_riesgo))]

            # --- RESUMEN EJECUTIVO ---
            st.subheader("📊 Resumen Ejecutivo")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                val_vencido = df_final[df_final['Riesgo_Hoy']=='VENCIDO']['Valor_Stock'].sum()
                st.markdown(f'<div class="report-container"><span class="metric-label">Pérdida Vencida</span><br><span class="metric-val" style="color:{COLOR_MAP["VENCIDO"]}">{clp(val_vencido)}</span></div>', unsafe_allow_html=True)
            with k2:
                val_critico = df_final[df_final['Riesgo_Hoy']=='CRITICO']['Valor_Stock'].sum()
                st.markdown(f'<div class="report-container"><span class="metric-label">Riesgo Crítico (15d)</span><br><span class="metric-val" style="color:{COLOR_MAP["CRITICO"]}">{clp(val_critico)}</span></div>', unsafe_allow_html=True)
            with k3:
                val_urgente = df_final[df_final['Riesgo_Hoy']=='URGENTE']['Valor_Stock'].sum()
                st.markdown(f'<div class="report-container"><span class="metric-label">Riesgo Urgente (30d)</span><br><span class="metric-val" style="color:{COLOR_MAP["URGENTE"]}">{clp(val_urgente)}</span></div>', unsafe_allow_html=True)
            with k4:
                val_total = df_final['Valor_Stock'].sum()
                st.markdown(f'<div class="report-container"><span class="metric-label">Total en Observación</span><br><span class="metric-val">{clp(val_total)}</span></div>', unsafe_allow_html=True)

            # --- MAPA GEOGRÁFICO BI ---
            st.subheader("🌐 Análisis Geográfico de Riesgo")
            [Image of a professional business intelligence dashboard map of Chile with colored inventory risk bubbles]
            fig_map = px.scatter_mapbox(
                df_final, lat="Latitud", lon="Longitud",
                size="Valor_Stock", color="Riesgo_Hoy",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", 
                hover_data={"Producto": True, "Stock_Teorico_Unidades": True, "Dias_Restantes": True, "Latitud": False, "Longitud": False},
                zoom=10, height=500, mapbox_style="carto-positron"
            )
            st.plotly_chart(fig_map, use_container_width=True)

            # --- PLAN DE ACCIÓN ---
            st.markdown(f"""
                <div class="plan-box">
                    <h3 style="margin-top:0;">📝 Plan de Acción Estratégico</h3>
                    <ul>
                        <li><b>Manejo de Vencidos:</b> Retirar de inmediato {clp(val_vencido)} de sala para proceso de merma/devolución.</li>
                        <li><b>Acción Crítica:</b> Aplicar descuento FEFO del 40-50% en productos con riesgo Crítico.</li>
                        <li><b>Estrategia Urgente:</b> Realizar transferencias cruzadas desde {len(sel_suc)} sucursales a puntos de mayor venta.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # --- DETALLE EXTENSO ---
            st.markdown("---")
            with st.expander("🔍 Análisis Detallado por Lote y Categoría (Vista Completa)"):
                t1, t2 = st.tabs(["Detalle Lotes", "Valor por Categoría"])
                with t1:
                    st.dataframe(df_final[['Riesgo_Hoy', 'Producto', 'Sucursal', 'Dias_Restantes', 'Stock_Teorico_Unidades', 'Valor_Stock']].sort_values('Dias_Restantes'), 
                                 use_container_width=True, hide_index=True)
                with t2:
                    fig_bar = px.bar(df_final, x="Categoria", y="Valor_Stock", color="Riesgo_Hoy", 
                                     color_discrete_map=COLOR_MAP, title="Valorización de Riesgo por Categoría")
                    st.plotly_chart(fig_bar, use_container_width=True)

        except Exception as e:
            st.error(f"Error en la relación de datos: {e}")
    else:
        st.info("👋 Por favor, carga los archivos (Sucursales, Productos e Inventario) para iniciar el análisis en tiempo real.")
