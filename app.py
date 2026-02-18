import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Sistema de Gestión de Riesgo", layout="wide")

# Inyectamos el CSS para ese look de "Resumen Ejecutivo" profesional
st.markdown("""
    <style>
    .report-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #1f77b4; }
    .metric-label { font-size: 14px; color: #666; }
    .status-critico { color: #d32f2f; font-weight: bold; }
    .status-urgente { color: #f57c00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA DE NEGOCIO (Basadas en inventario.py) ---
def clasificar_riesgo(dias):
    if dias <= 0: return 'VENCIDO'
    elif dias <= 15: return 'CRITICO'
    elif dias <= 30: return 'URGENTE'
    elif dias <= 60: return 'PREVENTIVO'
    else: return 'NORMAL'

def get_color(riesgo):
    colors = {'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32'}
    return colors.get(riesgo, '#666')

# --- CARGA Y PROCESAMIENTO ---
uploaded_files = st.sidebar.file_uploader("Sube los 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "inventario": None, "productos": None}

if uploaded_files:
    for file in uploaded_files:
        df_t = pd.read_csv(file)
        df_t.columns = df_t.columns.str.strip()
        if "Latitud" in df_t.columns and "ID_Ciudad" in df_t.columns: data["sucursales"] = df_t
        elif "Tipo_Movimiento" in df_t.columns: data["inventario"] = df_t
        elif "Categoria" in df_t.columns and "Producto_ID" in df_t.columns: data["productos"] = df_t

    if data["inventario"] is not None and data["sucursales"] is not None:
        # Consolidación Inteligente
        df = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
        if data["productos"] is not None:
            df = df.merge(data["productos"][['Producto_ID', 'Categoria']], on='Producto_ID', how='left')

        # Snapshot de Stock Actual
        df_hoy = df.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
        df_hoy['Riesgo'] = df_hoy['Dias_Para_Vencer'].apply(clasificar_riesgo)
        df_hoy['Valor_Stock'] = df_hoy['Stock_Teorico_Unidades'] * df_hoy['Precio_Venta_CLP']

        # --- TÍTULO Y FILTROS ---
        st.title("🛡️ Dashboard de Control de Riesgo y Plan de Acción")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            suc_sel = st.multiselect("Filtrar Sucursales", df_hoy['Sucursal'].unique(), default=df_hoy['Sucursal'].unique())
        with col_f2:
            riesgo_sel = st.multiselect("Niveles de Riesgo", ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO', 'NORMAL'], default=['CRITICO', 'URGENTE', 'PREVENTIVO'])

        df_f = df_hoy[(df_hoy['Sucursal'].isin(suc_sel)) & (df_hoy['Riesgo'].isin(riesgo_sel))]

        # --- BLOQUE 1: MAPA ESTRATÉGICO BI ---
        st.subheader("📍 Mapa de Calor de Riesgo Operativo")
        
        # Tamaño = Valor Stock, Color = Riesgo
        fig_map = px.scatter_mapbox(
            df_f, lat="Latitud", lon="Longitud",
            size="Valor_Stock", color="Riesgo",
            color_discrete_map={'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32'},
            hover_name="Sucursal", hover_data=["Producto", "Stock_Teorico_Unidades", "Dias_Para_Vencer"],
            zoom=10, height=500, mapbox_style="carto-positron"
        )
        st.plotly_chart(fig_map, use_container_width=True)

        # --- BLOQUE 2: RESUMEN EJECUTIVO (Plan de Acción) ---
        st.markdown("### 📋 Resumen Ejecutivo y Plan de Acción")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            val_critico = df_f[df_f['Riesgo'] == 'CRITICO']['Valor_Stock'].sum()
            st.markdown(f'<div class="report-card"><span class="metric-label">Monto en Riesgo Crítico</span><br><span class="metric-value" style="color:#d32f2f">${val_critico:,.0f}</span></div>', unsafe_allow_html=True)
        with c2:
            unid_urgente = df_f[df_f['Riesgo'] == 'URGENTE']['Stock_Teorico_Unidades'].sum()
            st.markdown(f'<div class="report-card"><span class="metric-label">Unidades Urgentes</span><br><span class="metric-value" style="color:#f57c00">{unid_urgente:,.0f}</span></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="report-card"><span class="metric-label">Sucursal más Afectada</span><br><span class="metric-value">{df_f.groupby("Sucursal")["Valor_Stock"].sum().idxmax()}</span></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="report-card"><span class="metric-label">Categoría Crítica</span><br><span class="metric-value">{df_f[df_f["Riesgo"].isin(["CRITICO", "URGENTE"])].groupby("Categoria")["Stock_Teorico_Unidades"].sum().idxmax()}</span></div>', unsafe_allow_html=True)

        # --- BLOQUE 3: DETALLE EXTENSO ---
        with st.expander("🔍 Ver Análisis Detallado por Lote y Plan de Salida"):
            tab1, tab2 = st.tabs(["Detalle de Inventario", "Análisis por Categoría"])
            
            with tab1:
                st.write("Listado priorizado para gestión de mermas:")
                st.dataframe(df_f.sort_values('Dias_Para_Vencer')[['Riesgo', 'Producto', 'Sucursal', 'Stock_Teorico_Unidades', 'Dias_Para_Vencer', 'Valor_Stock']], 
                             column_config={"Riesgo": st.column_config.TextColumn("Estado", help="Clasificación de riesgo")},
                             use_container_width=True, hide_index=True)
            
            with tab2:
                fig_bar = px.bar(df_f, x="Categoria", y="Valor_Stock", color="Riesgo", 
                                 title="Valorización de Riesgo por Categoría",
                                 color_discrete_map={'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32'})
                st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("👋 Bienvenida/o. Por favor, carga los archivos maestros para iniciar el análisis de riesgo.")
