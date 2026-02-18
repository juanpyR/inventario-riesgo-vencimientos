import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz

# =============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (Look & Feel Power BI)
# =============================================================================
st.set_page_config(page_title="Gestión de Riesgo de Inventario 360", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .executive-card {
        background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-top: 6px solid #1a237e;
        text-align: center; margin-bottom: 20px;
    }
    .plan-box {
        background-color: #fff9e6; padding: 25px; border-radius: 12px;
        border-left: 10px solid #f57c00; margin: 20px 0;
    }
    .metric-value { font-size: 28px; font-weight: bold; color: #1a237e; }
    .metric-label { font-size: 13px; color: #666; font-weight: 600; text-transform: uppercase; }
    .section-header { color: #1a237e; font-weight: 700; margin-top: 30px; border-bottom: 2px solid #1a237e; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 2. LÓGICA DE NEGOCIO Y FORMATOS (Extraída de inventario.py)
# =============================================================================
def clp(valor):
    if pd.isna(valor) or valor is None: return "$0"
    v = int(round(float(valor)))
    return f"${v:,}".replace(",", ".")

def clasificar_riesgo_mes(dias):
    """Lógica oficial de inventario.py"""
    if dias <= 0: return 'VENCIDO'
    elif dias <= 3: return 'CRITICO'
    elif dias <= 7: return 'URGENTE'
    elif dias <= 30: return 'PREVENTIVO'
    else: return 'NORMAL'

COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # Violeta
    'CRITICO': '#d32f2f',      # Rojo
    'URGENTE': '#f57c00',      # Naranja
    'PREVENTIVO': '#fbc02d',   # Amarillo
    'NORMAL': '#2e7d32'        # Verde
}

# =============================================================================
# 3. CARGA E IDENTIFICACIÓN RELACIONAL (Los 5 Archivos)
# =============================================================================
st.sidebar.title("📁 Carga de Inteligencia")
uploaded_files = st.sidebar.file_uploader("Sube tus 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"suc": None, "prod": None, "inv": None, "lotes": None, "geo": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Reconocimiento por ADN de columnas
        if "Latitud" in cols and "ID_Ciudad" in cols and "Stock_Teorico_Unidades" not in cols:
            data["suc"] = df_temp
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["prod"] = df_temp
        elif "Tipo_Movimiento" in cols and "Lote_ID" in cols:
            data["inv"] = df_temp
        elif "Fecha_Creacion_Lote" in cols:
            data["lotes"] = df_temp
        elif "Stock_Teorico_Unidades" in cols and "Latitud" in cols:
            data["geo"] = df_temp

    # =============================================================================
    # 4. CONSOLIDACIÓN Y ANÁLISIS TÁCTICO
    # =============================================================================
    if data["inv"] is not None and data["suc"] is not None and data["prod"] is not None:
        try:
            # Relación de tablas (Merge Triple)
            df_full = data["inv"].merge(data["suc"], on='Sucursal', how='left')
            df_full = df_full.merge(data["prod"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], on='Producto_ID', how='left')
            
            # Análisis "Al día de hoy" (Chile Timezone)
            tz_cl = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
            df_full['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_full['Fecha_Vencimiento_Lote'])
            
            # Stock Actual (Snapshot)
            df_now = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            df_now['Dias_Efectivos'] = (df_now['Fecha_Vencimiento_Lote'] - fecha_hoy).dt.days
            df_now['Riesgo_BI'] = df_now['Dias_Efectivos'].apply(clasificar_riesgo_mes)
            df_now['Valor_Costo_Total'] = df_now['Stock_Teorico_Unidades'] * df_now['Valor_Unitario_CLP']

            # --- HEADER DASHBOARD ---
            st.title(f"🛡️ Gestión Estratégica al {fecha_hoy.strftime('%d/%m/%Y')}")

            # Filtros BI
            f1, f2, f3 = st.columns(3)
            with f1: sel_suc = st.multiselect("Sucursales", df_now['Sucursal'].unique(), default=df_now['Sucursal'].unique())
            with f2: sel_cat = st.multiselect("Categorías", df_now['Categoria'].unique(), default=df_now['Categoria'].unique())
            with f3: sel_risk = st.multiselect("Riesgos", list(COLOR_MAP.keys()), default=['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO'])

            df_f = df_now[(df_now['Sucursal'].isin(sel_suc)) & (df_now['Categoria'].isin(sel_cat)) & (df_now['Riesgo_BI'].isin(sel_risk))]

            # =============================================================================
            # 5. RESUMEN EJECUTIVO (BI)
            # =============================================================================
            st.subheader("📊 Indicadores Críticos del Negocio")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Valor en Riesgo Total</span><br><span class="metric-value">{clp(df_f["Valor_Costo_Total"].sum())}</span></div>', unsafe_allow_html=True)
            with k2:
                venc_val = df_f[df_f['Riesgo_BI'] == 'VENCIDO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Crédito Fiscal (Donación 27%)</span><br><span class="metric-value" style="color:#9c27b0">{clp(venc_val * 0.27)}</span></div>', unsafe_allow_html=True)
            with k3:
                crit_val = df_f[df_f['Riesgo_BI'] == 'CRITICO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Monto Crítico (<3d)</span><br><span class="metric-value" style="color:#d32f2f">{clp(crit_val)}</span></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Unidades en Alerta</span><br><span class="metric-value">{int(df_f["Stock_Teorico_Unidades"].sum()):,}</span></div>', unsafe_allow_html=True)

            # =============================================================================
            # 6. MAPA BI INTERACTIVO (ZOOM HABILITADO)
            # =============================================================================
            st.subheader("🌐 Análisis Geográfico de Riesgo")
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Costo_Total", color="Riesgo_BI",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", hover_data=["Producto", "Stock_Teorico_Unidades", "Dias_Efectivos"],
                zoom=10, height=550, mapbox_style="carto-positron"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True})

            # =============================================================================
            # 7. PLAN DE ACCIÓN EJECUTIVO
            # =============================================================================
            st.markdown(f"""
                <div class="plan-box">
                    <h3 style="margin-top:0;">📝 Resumen Plan de Acción Táctico</h3>
                    <p>Acciones inmediatas para el parque de inventario filtrado:</p>
                    <ul>
                        <li><b>Donaciones:</b> Ejecutar baja de {clp(venc_val)} para recuperación tributaria inmediata.</li>
                        <li><b>Liquidación FEFO:</b> Descuento del 40-60% en productos críticos en <b>{df_f[df_f['Riesgo_BI']=='CRITICO']['Sucursal'].nunique()} sucursales</b>.</li>
                        <li><b>Control de Mermas:</b> Riesgo de pérdida por caducidad en el mes: {clp(df_f[df_f['Riesgo_BI'].isin(['CRITICO','URGENTE'])]['Valor_Costo_Total'].sum())}.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # =============================================================================
            # 8. ANÁLISIS DETALLADO (LOS 5 GRÁFICOS DE PYTHON)
            # =============================================================================
            st.markdown('<h2 class="section-header">🔍 Análisis de Profundidad (Python Insights)</h2>', unsafe_allow_html=True)
            
            tabs = st.tabs(["Concentración", "Distribución", "Tendencias", "Riesgo por Sede", "Audit de Lotes"])
            
            with tabs[0]:
                st.write("### 1. Valor de Inventario por Categoría y Riesgo")
                fig1 = px.bar(df_f, x="Categoria", y="Valor_Costo_Total", color="Riesgo_BI", color_discrete_map=COLOR_MAP, barmode="group")
                st.plotly_chart(fig1, use_container_width=True)

            with tabs[1]:
                st.write("### 2. Composición del Inventario (Unidades)")
                fig2 = px.sunburst(df_f, path=['Riesgo_BI', 'Categoria'], values='Stock_Teorico_Unidades', color='Riesgo_BI', color_discrete_map=COLOR_MAP)
                st.plotly_chart(fig2, use_container_width=True)

            with tabs[2]:
                st.write("### 3. Perfil de Rotación vs Riesgo")
                fig3 = px.scatter(df_f, x="Dias_Efectivos", y="Stock_Teorico_Unidades", size="Valor_Costo_Total", color="Categoria_Rotacion", hover_name="Producto", title="Días para Vencer vs Stock (Tamaño = Valor)")
                st.plotly_chart(fig3, use_container_width=True)

            with tabs[3]:
                st.write("### 4. Top 10 Sucursales con Mayor Monto Crítico")
                df_top_suc = df_f[df_f['Riesgo_BI'].isin(['CRITICO', 'VENCIDO'])].groupby('Sucursal')['Valor_Costo_Total'].sum().sort_values(ascending=False).head(10).reset_index()
                fig4 = px.bar(df_top_suc, x='Sucursal', y='Valor_Costo_Total', color='Valor_Costo_Total', color_continuous_scale='Reds')
                st.plotly_chart(fig4, use_container_width=True)

            with tabs[4]:
                st.write("### 5. Auditoría Extensa de Lotes")
                st.dataframe(df_f[['Riesgo_BI', 'Producto', 'Sucursal', 'Dias_Efectivos', 'Stock_Teorico_Unidades', 'Valor_Costo_Total']].sort_values('Dias_Efectivos'), 
                             column_config={"Valor_Costo_Total": st.column_config.NumberColumn("Valor CLP", format="$%d")},
                             use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error en la relación técnica de los archivos: {e}")
    else:
        st.info("👋 Por favor, carga los 5 archivos maestros para activar el Dashboard BI y el Análisis Táctico.")
