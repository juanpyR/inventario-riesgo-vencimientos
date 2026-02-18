import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIGURACIÓN Y ESTILO (Sincronizado con inventario.py) ---
st.set_page_config(page_title="Gestión de Inventario Crítico", layout="wide")

# Mantenemos tu paleta de colores original
COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # Violeta
    'CRITICO': '#d32f2f',      # Rojo
    'URGENTE': '#f57c00',      # Naranja
    'PREVENTIVO': '#fbc02d',   # Amarillo
    'NORMAL': '#2e7d32'        # Verde
}

st.markdown("""
    <style>
    .executive-header { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .plan-section { background: #fdfefe; border-left: 6px solid #1a237e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .metric-box { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-value { font-size: 22px; font-weight: bold; color: #1a237e; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE FORMATO CHILENO (De inventario.py) ---
def clp(valor):
    if pd.isna(valor): return "$0"
    return f"${int(round(float(valor))):,}".replace(",", ".")

def clasificar_riesgo_mes(dias):
    """Tu lógica exacta de inventario.py"""
    if dias <= 0: return 'VENCIDO'
    elif dias <= 3: return 'CRITICO'
    elif dias <= 7: return 'URGENTE'
    else: return 'PREVENTIVO'

# --- 3. CARGA E IDENTIFICACIÓN AUTOMÁTICA ---
st.sidebar.title("📁 Carga de Inteligencia")
uploaded_files = st.sidebar.file_uploader("Sube los archivos (Master y Transaccional)", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "productos": None, "inventario": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Lógica de relación: Primero identificamos quién es quién
        if "Latitud" in cols and "ID_Ciudad" in cols:
            data["sucursales"] = df_temp
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
        elif "Tipo_Movimiento" in cols and "Lote_ID" in cols:
            data["inventario"] = df_temp

    # --- 4. RELACIÓN DE TABLAS Y PROCESAMIENTO ---
    if data["inventario"] is not None and data["sucursales"] is not None and data["productos"] is not None:
        try:
            # Unión relacional blindada
            df_full = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
            df_full = df_full.merge(data["productos"][['Producto_ID', 'Categoria']], on='Producto_ID', how='left')
            
            # Análisis temporal dinámico (Al día de hoy)
            tz_cl = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
            df_full['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_full['Fecha_Vencimiento_Lote'])
            
            # Snapshot actual
            df_actual = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            df_actual['Dias_Efectivos'] = (df_actual['Fecha_Vencimiento_Lote'] - fecha_hoy).dt.days
            df_actual['Riesgo'] = df_actual['Dias_Efectivos'].apply(clasificar_riesgo_mes)
            df_actual['Valor_Costo'] = df_actual['Stock_Teorico_Unidades'] * df_actual['Valor_Unitario_CLP']

            # --- 5. RESUMEN EJECUTIVO ---
            st.markdown(f'<div class="executive-header"><h1>Dashboard de Análisis al {fecha_hoy.strftime("%d/%m/%Y")}</h1></div>', unsafe_allow_html=True)
            
            # Filtros dinámicos
            c1, c2 = st.columns(2)
            with c1:
                sel_suc = st.multiselect("Sucursales en Análisis", df_actual['Sucursal'].unique(), default=df_actual['Sucursal'].unique())
            with c2:
                sel_riesgo = st.multiselect("Niveles de Riesgo", list(COLOR_MAP.keys()), default=['VENCIDO', 'CRITICO', 'URGENTE'])

            df_f = df_actual[(df_actual['Sucursal'].isin(sel_suc)) & (df_actual['Riesgo'].isin(sel_riesgo))]

            # KPIs Superiores
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="metric-box"><span class="metric-label">Productos</span><br><span class="metric-value">{len(df_f)}</span></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="metric-box"><span class="metric-label">Unidades</span><br><span class="metric-value">{int(df_f["Stock_Teorico_Unidades"].sum()):,}</span></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="metric-box"><span class="metric-label">Valor en Riesgo</span><br><span class="metric-value">{clp(df_f["Valor_Costo"].sum())}</span></div>', unsafe_allow_html=True)
            with k4:
                # Recuperación estimada (Lógica 27% Donación / 50% Recuperación)
                recup = df_f[df_f['Riesgo'] == 'VENCIDO']['Valor_Costo'].sum() * 0.27
                st.markdown(f'<div class="metric-box"><span class="metric-label">Crédito Fiscal Est.</span><br><span class="metric-value" style="color:#2e7d32">{clp(recup)}</span></div>', unsafe_allow_html=True)

            # --- 6. MAPA DE CALOR BI ---
            st.subheader("📍 Distribución Geográfica de Riesgo")
            
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Costo", color="Riesgo",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", hover_data=["Producto", "Dias_Efectivos"],
                zoom=10, height=500, mapbox_style="carto-positron"
            )
            st.plotly_chart(fig_map, use_container_width=True)

            # --- 7. PLAN DE ACCIÓN (Resumen Ejecutivo) ---
            st.markdown('<div class="plan-section"><h3>📋 Plan de Acción y Decisiones</h3>', unsafe_allow_html=True)
            pa1, pa2 = st.columns(2)
            with pa1:
                st.write("**Estrategia de Salida:**")
                st.write(f"- **Vencidos:** Gestionar donación de {clp(df_f[df_f['Riesgo']=='VENCIDO']['Valor_Costo'].sum())} para asegurar beneficio tributario.")
                st.write(f"- **Críticos/Urgentes:** Implementar descuento FEFO inmediato.")
            with pa2:
                st.write("**Análisis de Mes:**")
                mes_act = fecha_hoy.month
                st.write(f"- Concentración de riesgo detectada para el mes de {fecha_hoy.strftime('%B')}.")
            st.markdown('</div>', unsafe_allow_html=True)

            # --- 8. DETALLE EXTENSO ---
            st.markdown("---")
            with st.expander("🔍 Ver Detalle Extenso de Lotes (Auditoría)"):
                st.dataframe(df_f[['Riesgo', 'Producto', 'Sucursal', 'Dias_Efectivos', 'Stock_Teorico_Unidades', 'Valor_Costo']].sort_values('Dias_Efectivos'), 
                             use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error al relacionar tablas: {e}")
    else:
        st.info("👋 Por favor, carga los archivos maestros (Productos, Sucursales e Inventario) para activar el Dashboard.")
