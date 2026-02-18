import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Estratégica de Inventario", layout="wide")

# =============================================================================
# FORMATO CHILENO Y LÓGICA DE NEGOCIO (De inventario.py)
# =============================================================================
def clp(valor):
    if valor is None or pd.isna(valor): return "$0"
    return f"${int(round(float(valor))):,}".replace(",", ".")

def clasificar_riesgo(dias):
    if dias <= 0: return 'VENCIDO'
    elif dias <= 15: return 'CRITICO'
    elif dias <= 30: return 'URGENTE'
    elif dias <= 60: return 'PREVENTIVO'
    else: return 'NORMAL'

COLOR_MAP = {
    'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 
    'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32'
}

# --- ESTILOS CSS PARA DASHBOARD BI ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .resumen-card {
        background-color: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #1f77b4;
    }
    .plan-accion {
        background-color: #fff4e5; padding: 15px; border-radius: 8px;
        border-left: 5px solid #f57c00; margin-top: 10px;
    }
    .metric-title { font-size: 14px; color: #555; font-weight: bold; }
    .metric-value { font-size: 22px; color: #1f77b4; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA DE ARCHIVOS ---
st.sidebar.title("🛠️ Configuración")
uploaded_files = st.sidebar.file_uploader("Sube los 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "inventario": None, "productos": None}

if uploaded_files:
    for file in uploaded_files:
        df_t = pd.read_csv(file)
        # LIMPIEZA CRÍTICA: Eliminar espacios en nombres de columnas
        df_t.columns = df_t.columns.str.strip()
        cols = df_t.columns
        
        if "Latitud" in cols and "ID_Ciudad" in cols:
            data["sucursales"] = df_t
        elif "Tipo_Movimiento" in cols:
            data["inventario"] = df_t
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_t

    # VALIDACIÓN DE DATOS
    if data["inventario"] is not None and data["sucursales"] is not None and data["productos"] is not None:
        
        # --- CONSOLIDACIÓN ---
        try:
            df = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
            df = df.merge(data["productos"][['Producto_ID', 'Categoria']], on='Producto_ID', how='left')
            
            # SNAPSHOT ACTUAL
            df_hoy = df.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            df_hoy['Riesgo'] = df_hoy['Dias_Para_Vencer'].apply(clasificar_riesgo)
            df_hoy['Valor_Stock'] = df_hoy['Stock_Teorico_Unidades'] * df_hoy['Precio_Venta_CLP']
            
            # --- DASHBOARD PRINCIPAL ---
            st.title("🛡️ Centro de Control de Riesgo Logístico")
            
            # Filtros dinámicos
            cols_f = st.columns(3)
            with cols_f[0]:
                suc_f = st.multiselect("Sucursales", df_hoy['Sucursal'].unique(), default=df_hoy['Sucursal'].unique())
            with cols_f[1]:
                cat_f = st.multiselect("Categorías", df_hoy['Categoria'].unique(), default=df_hoy['Categoria'].unique())
            with cols_f[2]:
                riesgo_f = st.multiselect("Nivel de Riesgo", list(COLOR_MAP.keys()), default=['CRITICO', 'URGENTE', 'PREVENTIVO'])

            df_f = df_hoy[(df_hoy['Sucursal'].isin(suc_f)) & (df_hoy['Categoria'].isin(cat_f)) & (df_hoy['Riesgo'].isin(riesgo_f))]

            # --- VISTA MAPA BI ---
            st.subheader("📍 Mapa de Riesgo y Capacidad")
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Stock", color="Riesgo",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", 
                hover_data={"Producto": True, "Stock_Teorico_Unidades": True, "Dias_Para_Vencer": True, "Latitud": False, "Longitud": False},
                zoom=10, height=500, mapbox_style="carto-positron"
            )
            st.plotly_chart(fig_map, use_container_width=True)

            # --- RESUMEN EJECUTIVO (Plan de Acción) ---
            st.markdown("### 📊 Resumen Ejecutivo")
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                total_critico = df_f[df_f['Riesgo'] == 'CRITICO']['Valor_Stock'].sum()
                st.markdown(f'<div class="resumen-card"><span class="metric-title">Monto Crítico (15d)</span><br><span class="metric-value" style="color:#d32f2f">{clp(total_critico)}</span></div>', unsafe_allow_html=True)
            with c2:
                unid_urg = df_f[df_f['Riesgo'] == 'URGENTE']['Stock_Teorico_Unidades'].sum()
                st.markdown(f'<div class="resumen-card"><span class="metric-title">Unidades Urgentes</span><br><span class="metric-value" style="color:#f57c00">{unid_urg:,.0f}</span></div>', unsafe_allow_html=True)
            with c3:
                top_suc = df_f.groupby('Sucursal')['Valor_Stock'].sum().idxmax()
                st.markdown(f'<div class="resumen-card"><span class="metric-title">Sucursal Mayor Riesgo</span><br><span class="metric-value">{top_suc}</span></div>', unsafe_allow_html=True)
            with c4:
                dias_prom = df_f['Dias_Para_Vencer'].mean()
                st.markdown(f'<div class="resumen-card"><span class="metric-title">Promedio Días Venc.</span><br><span class="metric-value">{int(dias_prom)} días</span></div>', unsafe_allow_html=True)

            # --- PLAN DE ACCIÓN ---
            st.markdown("""
                <div class="plan-accion">
                    <strong>📢 Plan de Acción Inmediato:</strong><br>
                    1. <b>Críticos:</b> Priorizar para liquidación inmediata o transferencia a sucursales de alta rotación.<br>
                    2. <b>Urgentes:</b> Activar campañas de descuento (FEFO) y validar estado físico en bodega.<br>
                    3. <b>Preventivos:</b> Monitorear velocidad de venta para evitar escalamiento a Urgente.
                </div>
            """, unsafe_allow_html=True)

            # --- DETALLE EXTENSO ---
            st.markdown("---")
            with st.expander("🔍 Ver Análisis Detallado de Lotes e Inventario"):
                st.dataframe(
                    df_f[['Riesgo', 'Producto', 'Sucursal', 'Stock_Teorico_Unidades', 'Dias_Para_Vencer', 'Valor_Stock']].sort_values('Dias_Para_Vencer'),
                    column_config={
                        "Valor_Stock": st.column_config.NumberColumn("Valor CLP", format="$%d"),
                        "Stock_Teorico_Unidades": "Unidades"
                    },
                    use_container_width=True, hide_index=True
                )
                
                # Gráfico de barras de valorización
                st.subheader("Valorización de Riesgo por Categoría")
                fig_bar = px.bar(df_f, x="Categoria", y="Valor_Stock", color="Riesgo", color_discrete_map=COLOR_MAP, barmode="group")
                st.plotly_chart(fig_bar, use_container_width=True)

        except KeyError as e:
            st.error(f"Error de columna: No se encontró {e}. Revisa que los archivos CSV tengan las columnas correctas.")
            
    else:
        st.warning("⚠️ Esperando carga de archivos. Necesitas subir: Sucursales, Productos e Inventario.")
