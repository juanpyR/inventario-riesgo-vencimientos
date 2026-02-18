import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz

# =============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (Look & Feel BI Premium)
# =============================================================================
st.set_page_config(page_title="Command Center: Riesgo de Inventario", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fb; }
    .executive-card {
        background-color: #ffffff; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-top: 6px solid #1a237e;
        text-align: center; margin-bottom: 20px; transition: transform 0.3s;
    }
    .executive-card:hover { transform: translateY(-5px); }
    .plan-box {
        background: linear-gradient(135deg, #fffcf0 0%, #fff4e5 100%);
        padding: 30px; border-radius: 15px; border-left: 10px solid #f57c00;
        box-shadow: 0 4px 15px rgba(245, 124, 0, 0.1); margin: 25px 0;
    }
    .metric-value { font-size: 32px; font-weight: 800; color: #1a237e; letter-spacing: -1px; }
    .metric-label { font-size: 13px; color: #666; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    .section-header { 
        color: #1a237e; font-weight: 800; font-size: 1.8rem;
        margin-top: 40px; border-bottom: 3px solid #1a237e; padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 2. LÓGICA DE NEGOCIO Y FORMATOS (Lógica Chile)
# =============================================================================
def clp(valor):
    """Formatea a moneda chilena: $1.234.567"""
    if pd.isna(valor) or valor is None: return "$0"
    v = int(round(float(valor)))
    return f"${v:,}".replace(",", ".")

def clasificar_riesgo_bi(dias):
    """Lógica oficial: Vencido(0), Crítico(3), Urgente(7), Preventivo(30)"""
    if dias <= 0: return 'VENCIDO'
    elif dias <= 3: return 'CRITICO'
    elif dias <= 7: return 'URGENTE'
    elif dias <= 30: return 'PREVENTIVO'
    else: return 'NORMAL'

COLOR_MAP = {
    'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 
    'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32'
}

# =============================================================================
# 3. MOTOR DE CARGA Y RELACIÓN AUTOMÁTICA (Los 5 Archivos)
# =============================================================================
st.sidebar.title("📁 Carga de Inteligencia")
uploaded_files = st.sidebar.file_uploader("Sube los 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"suc": None, "prod": None, "inv": None, "lotes": None, "geo": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip() # Limpieza de espacios
        cols = df_temp.columns
        
        # Reconocimiento inteligente por ADN de columnas
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
    # 4. CONSOLIDACIÓN RELACIONAL Y SNAPSHOT TEMPORAL
    # =============================================================================
    if data["inv"] is not None and data["suc"] is not None and data["prod"] is not None:
        try:
            # Relación de Tablas (Merge Blindado)
            df_full = data["inv"].merge(data["suc"], on='Sucursal', how='left')
            df_full = df_full.merge(data["prod"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], on='Producto_ID', how='left')
            
            # Cálculo al día de hoy (Chile Timezone)
            tz_cl = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
            df_full['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_full['Fecha_Vencimiento_Lote'])
            
            # Stock Actual (Snapshot de último movimiento)
            df_now = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            df_now['Dias_Efectivos'] = (df_now['Fecha_Vencimiento_Lote'] - fecha_hoy).dt.days
            df_now['Riesgo_BI'] = df_now['Dias_Efectivos'].apply(clasificar_riesgo_bi)
            df_now['Valor_Costo_Total'] = df_now['Stock_Teorico_Unidades'] * df_now['Valor_Unitario_CLP']

            # --- CABECERA ---
            st.title(f"🛡️ Gestión Estratégica al {fecha_hoy.strftime('%d/%m/%Y')}")

            # Filtros BI de Alta Velocidad
            f1, f2, f3 = st.columns(3)
            with f1: sel_suc = st.multiselect("Filtrar Sucursales", df_now['Sucursal'].unique(), default=df_now['Sucursal'].unique())
            with f2: sel_cat = st.multiselect("Filtrar Categorías", df_now['Categoria'].unique(), default=df_now['Categoria'].unique())
            with f3: sel_risk = st.multiselect("Filtro de Riesgo", list(COLOR_MAP.keys()), default=['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO'])

            df_f = df_now[(df_now['Sucursal'].isin(sel_suc)) & (df_now['Categoria'].isin(sel_cat)) & (df_now['Riesgo_BI'].isin(sel_risk))]

            # =============================================================================
            # 5. RESUMEN EJECUTIVO FINANCIERO (BI)
            # =============================================================================
            st.subheader("📊 Indicadores Críticos de Gestión")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                val_total = df_f["Valor_Costo_Total"].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Monto Total en Riesgo</span><br><span class="metric-value">{clp(val_total)}</span></div>', unsafe_allow_html=True)
            with k2:
                # Lógica Contable: Recuperación del 27% por Donación de Vencidos
                venc_val = df_f[df_f['Riesgo_BI'] == 'VENCIDO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Crédito Fiscal (Donación)</span><br><span class="metric-value" style="color:#9c27b0">{clp(venc_val * 0.27)}</span></div>', unsafe_allow_html=True)
            with k3:
                # Recuperación por Liquidación Crítica (Estimado 50%)
                crit_val = df_f[df_f['Riesgo_BI'] == 'CRITICO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Recuperación Crítica</span><br><span class="metric-value" style="color:#d32f2f">{clp(crit_val * 0.5)}</span></div>', unsafe_allow_html=True)
            with k4:
                unid_alerta = int(df_f["Stock_Teorico_Unidades"].sum())
                st.markdown(f'<div class="executive-card"><span class="metric-label">Unidades en Alerta</span><br><span class="metric-value">{unid_alerta:,}</span></div>', unsafe_allow_html=True)

            # =============================================================================
            # 6. MAPA GEOGRÁFICO INTERACTIVO (ZOOM DINÁMICO)
            # =============================================================================
            st.subheader("🌐 Análisis Espacial de Caducidad")
            
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Costo_Total", color="Riesgo_BI",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", 
                hover_data={"Producto": True, "Stock_Teorico_Unidades": True, "Dias_Efectivos": True, "Latitud": False, "Longitud": False},
                zoom=10, height=600, mapbox_style="carto-positron"
            )
            # Habilitar zoom con rueda de mouse y centrado
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True})

            # =============================================================================
            # 7. PLAN DE ACCIÓN Y DECISIÓN (Lógica inventario.py)
            # =============================================================================
            st.markdown(f"""
                <div class="plan-box">
                    <h3 style="margin-top:0; color:#1a237e;">📋 Resumen Plan de Acción y Decisiones</h3>
                    <p>Acciones obligatorias para mitigar la pérdida de <b>{clp(val_total)}</b>:</p>
                    <ul>
                        <li><b>Donaciones Inmediatas:</b> Gestionar retiro de {clp(venc_val)} para asegurar beneficio tributario del 27%.</li>
                        <li><b>Liquidación FEFO (First Expired, First Out):</b> Aplicar descuentos del 40-60% en productos Críticos en las <b>{df_f[df_f['Riesgo_BI']=='CRITICO']['Sucursal'].nunique()} sedes</b> afectadas.</li>
                        <li><b>Transferencias Tácticas:</b> Movilizar productos Urgentes (4-7 días) a sucursales con mayor tráfico para evitar mermas.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # =============================================================================
            # 8. BATERÍA DE 5 GRÁFICOS DE PROFUNDIDAD
            # =============================================================================
            st.markdown('<h2 class="section-header">🔍 Análisis de Profundidad (Python Insights)</h2>', unsafe_allow_html=True)
            
            tabs = st.tabs(["📊 Concentración Financiera", "🏗️ Composición de Stock", "📉 Rotación vs Caducidad", "📍 Riesgo por Sede", "📑 Auditoría Lotes"])
            
            with tabs[0]:
                st.write("### Valor de Inventario por Categoría y Riesgo")
                fig1 = px.bar(df_f, x="Categoria", y="Valor_Costo_Total", color="Riesgo_BI", 
                             color_discrete_map=COLOR_MAP, barmode="group", text_auto='.2s')
                st.plotly_chart(fig1, use_container_width=True)

            with tabs[1]:
                st.write("### Composición Jerárquica del Inventario")
                # Gráfico Sunburst para navegar entre niveles
                fig2 = px.sunburst(df_f, path=['Riesgo_BI', 'Categoria'], values='Stock_Teorico_Unidades',
                                  color='Riesgo_BI', color_discrete_map=COLOR_MAP)
                st.plotly_chart(fig2, use_container_width=True)

            with tabs[2]:
                st.write("### Correlación: Días para Vencer vs Unidades")
                fig3 = px.scatter(df_f, x="Dias_Efectivos", y="Stock_Teorico_Unidades", 
                                 size="Valor_Costo_Total", color="Categoria_Rotacion", 
                                 hover_name="Producto", title="Tamaño de burbuja = Valor Monetario")
                st.plotly_chart(fig3, use_container_width=True)

            with tabs[3]:
                st.write("### Top 10 Sucursales con Mayor Inversión en Riesgo")
                top_suc = df_f.groupby('Sucursal')['Valor_Costo_Total'].sum().sort_values(ascending=False).head(10).reset_index()
                fig4 = px.bar(top_suc, x='Sucursal', y='Valor_Costo_Total', color='Valor_Costo_Total', 
                             color_continuous_scale='Reds', text_auto='.3s')
                st.plotly_chart(fig4, use_container_width=True)

            with tabs[4]:
                st.write("### Listado Maestro de Auditoría")
                # Tabla interactiva con formato de moneda
                st.dataframe(df_f[['Riesgo_BI', 'Producto', 'Sucursal', 'Dias_Efectivos', 'Stock_Teorico_Unidades', 'Valor_Costo_Total']].sort_values('Dias_Efectivos'), 
                             column_config={"Valor_Costo_Total": st.column_config.NumberColumn("Valor Costo", format="$%d")},
                             use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error en la relación técnica de archivos: {e}")
            st.info("Valida que los archivos contengan Producto_ID, Lote_ID y Sucursal para establecer los puentes relacionales.")
    else:
        st.info("👋 Bienvenida/o. Por favor, carga los 5 archivos maestros para activar el Centro de Inteligencia.")
