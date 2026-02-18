import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO (Look BI & Ejecutivo) ---
st.set_page_config(page_title="Gestión de Riesgo Operativo", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .executive-card {
        background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 6px solid #1f77b4;
        text-align: center; margin-bottom: 20px;
    }
    .plan-accion-box {
        background-color: #fff9e6; padding: 20px; border-radius: 12px;
        border-left: 8px solid #f57c00; margin: 20px 0;
    }
    .metric-val { font-size: 28px; font-weight: bold; color: #1f77b4; }
    .metric-label { font-size: 14px; color: #555; text-transform: uppercase; letter-spacing: 1px; }
    .badge { padding: 4px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE LÓGICA (Formato CLP y Clasificación) ---
def clp(valor):
    if pd.isna(valor): return "$0"
    return f"${int(round(float(valor))):,}".replace(",", ".")

def asignar_categoria_riesgo(dias):
    if dias <= 0: return 'VENCIDO'
    elif dias <= 15: return 'CRITICO'
    elif dias <= 30: return 'URGENTE'
    elif dias <= 60: return 'PREVENTIVO'
    else: return 'NORMAL'

COLOR_MAP = {
    'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 
    'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32'
}

# --- 3. CARGA E IDENTIFICACIÓN DE RELACIONES ---
st.title("🛡️ Dashboard de Inteligencia de Inventario")
st.sidebar.header("📂 Carga de Datos")
files = st.sidebar.file_uploader("Sube los 5 archivos maestros", type="csv", accept_multiple_files=True)

# Contenedor de datos
data = {"suc": None, "prod": None, "inv": None, "lotes": None}

if files:
    for f in files:
        df_temp = pd.read_csv(f)
        df_temp.columns = df_temp.columns.str.strip() # Limpieza de nombres
        cols = df_temp.columns
        
        # Identificación por "ADN" de columnas
        if "Latitud" in cols and "ID_Ciudad" in cols and "Stock_Teorico_Unidades" not in cols:
            data["suc"] = df_temp
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["prod"] = df_temp
        elif "Tipo_Movimiento" in cols:
            data["inv"] = df_temp
        elif "Fecha_Creacion_Lote" in cols:
            data["lotes"] = df_temp

    # --- 4. ESTABLECER RELACIONES (MERGE) ---
    if data["inv"] is not None and data["prod"] is not None and data["suc"] is not None:
        try:
            # Relación 1: Inventario + Sucursales (Para Mapa)
            df_master = data["inv"].merge(data["suc"][['Sucursal', 'Latitud', 'Longitud', 'ID_Ciudad']], on='Sucursal', how='left')
            
            # Relación 2: Inventario + Productos (Para Categorías)
            df_master = df_master.merge(data["prod"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], on='Producto_ID', how='left')
            
            # Procesamiento de Stock Actual
            df_snapshot = df_master.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            df_snapshot['Riesgo'] = df_snapshot['Dias_Para_Vencer'].apply(asignar_categoria_riesgo)
            df_snapshot['Valor_Stock'] = df_snapshot['Stock_Teorico_Unidades'] * df_snapshot['Precio_Venta_CLP']

            # --- 5. RESUMEN EJECUTIVO (BI) ---
            st.subheader("📊 Resumen Ejecutivo de Riesgos")
            
            # Filtros Rápidos
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                sel_suc = st.multiselect("Filtrar por Sucursal", df_snapshot['Sucursal'].unique(), default=df_snapshot['Sucursal'].unique())
            with col_f2:
                sel_riesgo = st.multiselect("Ver Niveles de Riesgo", list(COLOR_MAP.keys()), default=['CRITICO', 'URGENTE', 'PREVENTIVO'])
            
            df_f = df_snapshot[(df_snapshot['Sucursal'].isin(sel_suc)) & (df_snapshot['Riesgo'].isin(sel_riesgo))]

            # KPIs Superiores
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Monto Crítico</span><br><span class="metric-val" style="color:#d32f2f">{clp(df_f[df_f["Riesgo"]=="CRITICO"]["Valor_Stock"].sum())}</span></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Unidades Urgentes</span><br><span class="metric-val" style="color:#f57c00">{int(df_f[df_f["Riesgo"]=="URGENTE"]["Stock_Teorico_Unidades"].sum()):,}</span></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Valor en Riesgo Total</span><br><span class="metric-val">{clp(df_f["Valor_Stock"].sum())}</span></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Días Promedio</span><br><span class="metric-val">{int(df_f["Dias_Para_Vencer"].mean())} d</span></div>', unsafe_allow_html=True)

            # --- 6. MAPA ESTRATÉGICO ---
            st.subheader("🌐 Distribución Geográfica del Riesgo")
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Stock", color="Riesgo",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", hover_data=["Producto", "Stock_Teorico_Unidades", "Dias_Para_Vencer"],
                zoom=10, height=500, mapbox_style="carto-positron"
            )
            st.plotly_chart(fig_map, use_container_width=True)

            # --- 7. RESUMEN PLAN DE ACCIÓN ---
            st.markdown(f"""
                <div class="plan-accion-box">
                    <h3>📢 Plan de Acción Táctico</h3>
                    <p>Basado en el análisis de <b>{len(df_f)} lotes</b> detectados:</p>
                    <ul>
                        <li><b>Prioridad Crítica:</b> Movilizar {clp(df_f[df_f["Riesgo"]=="CRITICO"]["Valor_Stock"].sum())} mediante ofertas relámpago o transferencias inmediatas.</li>
                        <li><b>Gestión Urgente:</b> Revisar exhibición de productos con menos de 30 días en <b>{df_f[df_f["Riesgo"]=="URGENTE"]["Sucursal"].nunique()} sucursales</b>.</li>
                        <li><b>Acción Preventiva:</b> Programar reposición controlada para categorías de rotación lenta.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # --- 8. DETALLES (EXTENSO) ---
            st.markdown("---")
            with st.expander("🔍 Ver Análisis Detallado de Inventario (Vista Extensa)"):
                col_det1, col_det2 = st.columns([6, 4])
                with col_det1:
                    st.write("### Listado de Lotes por Riesgo")
                    st.dataframe(
                        df_f[['Riesgo', 'Producto', 'Sucursal', 'Dias_Para_Vencer', 'Stock_Teorico_Unidades', 'Valor_Stock']].sort_values('Dias_Para_Vencer'),
                        column_config={"Valor_Stock": st.column_config.NumberColumn("Valor CLP", format="$%d")},
                        use_container_width=True, hide_index=True
                    )
                with col_det2:
                    st.write("### Concentración de Riesgo ($)")
                    fig_bar = px.bar(df_f.groupby('Categoria')['Valor_Stock'].sum().reset_index(), 
                                     x='Categoria', y='Valor_Stock', title="Riesgo por Categoría",
                                     color_discrete_sequence=['#1f77b4'])
                    st.plotly_chart(fig_bar, use_container_width=True)

        except Exception as e:
            st.error(f"Error al procesar relaciones: {e}. Asegúrate de cargar los archivos correctos.")
    else:
        st.info("👋 Por favor, carga los archivos maestros (Productos, Sucursales e Inventario) para activar el dashboard.")
