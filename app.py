import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
import pytz
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS DE ALTO IMPACTO (BI STYLE)
# =============================================================================
st.set_page_config(page_title="🛡️ Command Center: Riesgo de Inventario", layout="wide", page_icon="📊")

def aplicar_estilo_ejecutivo():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main { background-color: #f4f7f9; }
    .executive-card {
        background: white; padding: 25px; border-radius: 16px;
        box-shadow: 0 4px 20px rgba(26,35,126,0.12); border-top: 6px solid #1a237e;
        text-align: center; margin: 10px 0; transition: all 0.3s ease;
    }
    .metric-value { font-size: 34px; font-weight: 800; color: #1a237e; letter-spacing: -1px; }
    .metric-label { font-size: 12px; color: #666; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
    .plan-box {
        background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
        padding: 30px; border-radius: 16px; border-left: 10px solid #f57c00;
        box-shadow: 0 4px 20px rgba(245,124,0,0.15); margin: 25px 0;
    }
    .risk-badge {
        display: inline-flex; align-items: center; padding: 4px 12px;
        border-radius: 20px; font-size: 11px; font-weight: 700;
    }
    .status-vencido { background: #f3e5f5; color: #7b1fa2; border: 1px solid #9c27b0; }
    .status-critico { background: #ffebee; color: #c62828; border: 1px solid #d32f2f; }
    .status-urgente { background: #fff3e0; color: #e65100; border: 1px solid #f57c00; }
    .status-preventivo { background: #fffde7; color: #f9a825; border: 1px solid #fbc02d; }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_ejecutivo()

# =============================================================================
# 2. FORMATOS Y CONSTANTES
# =============================================================================
def clp(valor):
    if pd.isna(valor) or valor is None: return "$0"
    v = int(round(float(valor)))
    return f"${v:,}".replace(",", ".")

COLOR_MAP = {
    'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 'URGENTE': '#f57c00',
    'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32', 'OTRO': '#9e9e9e'
}

# =============================================================================
# 3. LÓGICA DE RIESGO (CORREGIDA: PREVENTIVO 8-10 DÍAS)
# =============================================================================
def clasificar_riesgo_estricto(dias, fecha_venc, inicio_mes, fin_mes):
    """
    Lógica de análisis acotada al mes pero con rangos tácticos específicos:
    - Vencido: <= 0 días
    - Crítico: 1-3 días
    - Urgente: 4-7 días
    - Preventivo: 8-10 días (Solicitado 7-10)
    """
    if not (inicio_mes <= fecha_venc <= fin_mes):
        return 'NORMAL_MES_SIGUIENTE'
    
    if dias <= 0: return 'VENCIDO'
    elif dias <= 3: return 'CRITICO'
    elif dias <= 7: return 'URGENTE'
    elif dias <= 10: return 'PREVENTIVO' # Rango específico solicitado
    else: return 'NORMAL'

# =============================================================================
# 4. MOTOR ETL: RELACIÓN DE LOS 5 ARCHIVOS
# =============================================================================
st.sidebar.title("📁 Carga de Inteligencia")
uploaded_files = st.sidebar.file_uploader("Sube tus 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"suc": None, "prod": None, "inv": None, "lotes": None, "geo": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Reconocimiento inteligente de la relación de tablas
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

    # --- INICIO DEL ANÁLISIS RELACIONAL ---
    if data["inv"] is not None and data["suc"] is not None and data["prod"] is not None:
        try:
            # 1. Unir Inventario con Sucursales
            df_full = data["inv"].merge(data["suc"], on='Sucursal', how='left')
            # 2. Unir con Maestro de Productos
            df_full = df_full.merge(data["prod"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], on='Producto_ID', how='left')
            
            # 3. Preparación de Fechas y Ventana Mensual
            tz_cl = pytz.timezone('America/Santiago')
            hoy = datetime.now(tz_cl).replace(tzinfo=None)
            inicio_mes = hoy.replace(day=1)
            fin_mes = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])
            
            df_full['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_full['Fecha_Vencimiento_Lote'])
            
            # 4. Snapshot de Inventario Actual
            df_now = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            df_now['Dias_Efectivos'] = (df_now['Fecha_Vencimiento_Lote'] - hoy).dt.days
            
            # 5. Aplicar Clasificación Estricta (Ventana Mensual + Rangos Tácticos)
            df_now['Riesgo_BI'] = df_now.apply(
                lambda row: clasificar_riesgo_estricto(row['Dias_Efectivos'], row['Fecha_Vencimiento_Lote'], inicio_mes, fin_mes), 
                axis=1
            )
            df_now['Valor_Costo_Total'] = df_now['Stock_Teorico_Unidades'] * df_now['Valor_Unitario_CLP']

            # =============================================================================
            # 5. DASHBOARD BI: RESUMEN EJECUTIVO
            # =============================================================================
            st.title("🛡️ Command Center: Riesgo de Inventario")
            st.markdown(f"**Análisis de Ventana Mensual: {inicio_mes.strftime('%d/%m')} al {fin_mes.strftime('%d/%m/%Y')}**")

            # Filtros BI
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                sel_suc = st.multiselect("🏪 Sucursales", df_now['Sucursal'].unique(), default=df_now['Sucursal'].unique())
            with col_f2:
                sel_risk = st.multiselect("⚠️ Niveles de Riesgo", [r for r in COLOR_MAP.keys() if r != 'OTRO'], default=['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO'])

            df_f = df_now[(df_now['Sucursal'].isin(sel_suc)) & (df_now['Riesgo_BI'].isin(sel_risk))]

            # KPIs FINANCIEROS
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Valor Total en Riesgo</span><br><span class="metric-value">{clp(df_f["Valor_Costo_Total"].sum())}</span></div>', unsafe_allow_html=True)
            with k2:
                venc_val = df_f[df_f['Riesgo_BI'] == 'VENCIDO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Crédito Fiscal Est. (27%)</span><br><span class="metric-value" style="color:#9c27b0">{clp(venc_val * 0.27)}</span></div>', unsafe_allow_html=True)
            with k3:
                crit_val = df_f[df_f['Riesgo_BI'] == 'CRITICO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Monto Crítico (0-3d)</span><br><span class="metric-value" style="color:#d32f2f">{clp(crit_val)}</span></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Unidades en Alerta</span><br><span class="metric-value">{int(df_f["Stock_Teorico_Unidades"].sum()):,}</span></div>', unsafe_allow_html=True)

            # =============================================================================
            # 6. MAPA BI INTERACTIVO (ZOOM HABILITADO)
            # =============================================================================
            st.subheader("🌐 Análisis Geográfico de Exposición")
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud", size="Valor_Costo_Total",
                color="Riesgo_BI", color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", hover_data=["Producto", "Dias_Efectivos", "Stock_Teorico_Unidades"],
                zoom=10, height=550, mapbox_style="carto-positron"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True})

            # =============================================================================
            # 7. PLAN DE ACCIÓN (Resumen Ejecutivo)
            # =============================================================================
            st.markdown(f"""
                <div class="plan-box">
                    <h3 style="margin-top:0; color:#1a237e;">📝 Plan de Acción Estratégico</h3>
                    <ul>
                        <li><b>Vencidos:</b> Donación inmediata de {clp(venc_val)} para asegurar beneficio tributario del 27%.</li>
                        <li><b>Críticos (1-3d):</b> Descuento agresivo del 50% en las <b>{df_f[df_f['Riesgo_BI']=='CRITICO']['Sucursal'].nunique()} sedes</b> afectadas.</li>
                        <li><b>Preventivos (8-10d):</b> Monitoreo de rotación para productos que entrarán a fase Crítica en 72 horas.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # =============================================================================
            # 8. ANÁLISIS DE PROFUNDIDAD (Los 5 Gráficos Clave)
            # =============================================================================
            st.markdown("---")
            tabs = st.tabs(["📊 Concentración", "🏗️ Composición", "📉 Días vs Stock", "📍 Riesgo/Sede", "📑 Auditoría"])
            
            with tabs[0]:
                st.write("### Valorización por Categoría y Riesgo")
                fig1 = px.bar(df_f, x="Categoria", y="Valor_Costo_Total", color="Riesgo_BI", color_discrete_map=COLOR_MAP, barmode="group")
                st.plotly_chart(fig1, use_container_width=True)
            
            with tabs[1]:
                st.write("### Composición de Stock por Nivel de Riesgo")
                fig2 = px.sunburst(df_f, path=['Riesgo_BI', 'Categoria'], values='Stock_Teorico_Unidades', color='Riesgo_BI', color_discrete_map=COLOR_MAP)
                st.plotly_chart(fig2, use_container_width=True)

            with tabs[2]:
                st.write("### Matriz de Exposición: Días vs Unidades")
                fig3 = px.scatter(df_f, x="Dias_Efectivos", y="Stock_Teorico_Unidades", size="Valor_Costo_Total", color="Categoria_Rotacion", hover_name="Producto")
                fig3.add_vline(x=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig3, use_container_width=True)

            with tabs[3]:
                st.write("### Top Sucursales por Monto en Riesgo")
                top_suc = df_f.groupby('Sucursal')['Valor_Costo_Total'].sum().sort_values(ascending=False).head(10).reset_index()
                fig4 = px.bar(top_suc, x='Sucursal', y='Valor_Costo_Total', color='Valor_Costo_Total', color_continuous_scale='Reds')
                st.plotly_chart(fig4, use_container_width=True)

            with tabs[4]:
                st.write("### Auditoría Detallada de Lotes")
                st.dataframe(df_f[['Riesgo_BI', 'Producto', 'Sucursal', 'Dias_Efectivos', 'Stock_Teorico_Unidades', 'Valor_Costo_Total']].sort_values('Dias_Efectivos'), 
                             column_config={"Valor_Costo_Total": st.column_config.NumberColumn("Valor CLP", format="$%d")},
                             use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error en la relación técnica de archivos: {e}")
    else:
        st.info("👋 Por favor, carga los 5 archivos para activar el Dashboard Estratégico.")
