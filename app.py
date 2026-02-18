import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import pytz

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="BI - Gestión de Inventario Crítico", layout="wide")

# =============================================================================
# LÓGICA DE NEGOCIO (Sincronizada con inventario.py)
# =============================================================================
def clp(valor):
    """Formatea número con estilo chileno: $1.234.567"""
    if pd.isna(valor): return "$0"
    try:
        v = int(round(float(valor)))
        return f"${v:,}".replace(",", ".")
    except:
        return "$0"

def clasificar_riesgo_mes(dias):
    """Lógica de semáforo basada en el análisis del mes actual"""
    if dias <= 0:
        return 'VENCIDO'
    elif dias <= 15: # Vence en la quincena (Crítico)
        return 'CRITICO'
    elif dias <= 30: # Vence este mes (Urgente)
        return 'URGENTE'
    elif dias <= 60: # Vence próximo mes (Preventivo)
        return 'PREVENTIVO'
    else:
        return 'NORMAL'

COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # Violeta
    'CRITICO': '#d32f2f',      # Rojo
    'URGENTE': '#f57c00',      # Naranja
    'PREVENTIVO': '#fbc02d',   # Amarillo
    'NORMAL': '#2e7d32'        # Verde
}

# --- ESTILOS CSS (Dashboard Corporativo BI) ---
st.markdown("""
    <style>
    .executive-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border-top: 5px solid #1a237e; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
    .plan-action-box { background-color: #f8f9fa; border-left: 10px solid #1a237e; padding: 20px; border-radius: 10px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .metric-val { font-size: 32px; font-weight: 700; color: #1a237e; margin-bottom: 5px; }
    .metric-label { font-size: 14px; color: #666; font-weight: 600; text-transform: uppercase; }
    .status-tag { padding: 4px 12px; border-radius: 20px; color: white; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. CARGA E IDENTIFICACIÓN (SIN ORDEN DE SUBIDA) ---
st.sidebar.title("📁 Carga de Inteligencia")
uploaded_files = st.sidebar.file_uploader("Sube los 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "productos": None, "inventario": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Identificación inteligente por ADN de columnas
        if "Latitud" in cols and "ID_Ciudad" in cols and "Stock_Teorico_Unidades" not in cols:
            data["sucursales"] = df_temp
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
        elif "Tipo_Movimiento" in cols and "Lote_ID" in cols:
            data["inventario"] = df_temp

    # --- 2. RELACIÓN DE TABLAS (EL CORAZÓN DEL ANÁLISIS) ---
    if data["inventario"] is not None and data["sucursales"] is not None and data["productos"] is not None:
        try:
            # UNIÓN ROBUSTA: Garantizamos que la data se relacione antes de calcular
            df_full = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
            df_full = df_full.merge(data["productos"][['Producto_ID', 'Categoria']], on='Producto_ID', how='left')
            
            # --- 3. ANÁLISIS TEMPORAL AL DÍA DE HOY ---
            tz_cl = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
            
            # Convertir fechas para cálculo matemático
            df_full['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_full['Fecha_Vencimiento_Lote'])
            
            # Snapshot: Stock actual por lote y sucursal
            df_actual = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            
            # Cálculo de Días para Vencer basado en HOY (Lógica inventario.py)
            df_actual['Dias_Efectivos'] = (df_actual['Fecha_Vencimiento_Lote'] - fecha_hoy).dt.days
            df_actual['Riesgo_BI'] = df_actual['Dias_Efectivos'].apply(clasificar_riesgo_mes)
            df_actual['Valor_Stock_CLP'] = df_actual['Stock_Teorico_Unidades'] * df_actual['Precio_Venta_CLP']

            # --- 4. PANEL DE CONTROL (BI) ---
            st.title(f"🛡️ Gestión de Riesgo de Inventario")
            st.markdown(f"**Análisis Estratégico al {fecha_hoy.strftime('%d/%m/%Y')}**")

            # Filtros dinámicos
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                sel_suc = st.multiselect("Sucursales", df_actual['Sucursal'].unique(), default=df_actual['Sucursal'].unique())
            with col_f2:
                sel_riesgo = st.multiselect("Filtro de Riesgo", list(COLOR_MAP.keys()), default=['VENCIDO', 'CRITICO', 'URGENTE'])

            df_f = df_actual[(df_actual['Sucursal'].isin(sel_suc)) & (df_actual['Riesgo_BI'].isin(sel_riesgo))]

            # --- 5. RESUMEN EJECUTIVO (Cards Financieras) ---
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                v_venc = df_f[df_f['Riesgo_BI'] == 'VENCIDO']['Valor_Stock_CLP'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Pérdida Vencida</span><br><span class="metric-val" style="color:{COLOR_MAP["VENCIDO"]}">{clp(v_venc)}</span></div>', unsafe_allow_html=True)
            with k2:
                v_crit = df_f[df_f['Riesgo_BI'] == 'CRITICO']['Valor_Stock_CLP'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Monto Crítico</span><br><span class="metric-val" style="color:{COLOR_MAP["CRITICO"]}">{clp(v_crit)}</span></div>', unsafe_allow_html=True)
            with k3:
                v_total = df_f['Valor_Stock_CLP'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Valor en Observación</span><br><span class="metric-val">{clp(v_total)}</span></div>', unsafe_allow_html=True)
            with k4:
                u_total = int(df_f['Stock_Teorico_Unidades'].sum())
                st.markdown(f'<div class="executive-card"><span class="metric-label">Unidades Totales</span><br><span class="metric-val">{u_total:,}</span></div>', unsafe_allow_html=True)

            # --- 6. MAPA GEOGRÁFICO BI (Limpio y Profesional) ---
            st.subheader("🌐 Visualización Geográfica de Alerta")
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Stock_CLP", color="Riesgo_BI",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", hover_data={"Producto": True, "Dias_Efectivos": True, "Valor_Stock_CLP": False},
                zoom=10, height=550, mapbox_style="carto-positron"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)

            # --- 7. PLAN DE ACCIÓN TÁCTICO ---
            st.markdown(f"""
                <div class="plan-action-box">
                    <h3>📢 Plan de Acción Ejecutivo</h3>
                    <p>Para mitigar el riesgo de <b>{clp(v_total)}</b> detectado en el mes:</p>
                    <ul>
                        <li><b>Vencidos:</b> Gestión inmediata de merma y donación para recuperación de crédito fiscal (27%).</li>
                        <li><b>Críticos:</b> Venta asistida (FEFO) con descuento del 30-50% en las cabeceras de góndola.</li>
                        <li><b>Urgentes:</b> Monitorear velocidad de venta; si no hay movimiento en 7 días, transferir a sucursales de mayor tráfico.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # --- 8. ANÁLISIS EXTENSO (Desplegable) ---
            with st.expander("🔍 Ver Análisis Detallado (Extenso)"):
                col_d1, col_d2 = st.columns([6, 4])
                with col_d1:
                    st.write("### Desglose por Lote")
                    st.dataframe(df_f[['Riesgo_BI', 'Producto', 'Sucursal', 'Dias_Efectivos', 'Stock_Teorico_Unidades', 'Valor_Stock_CLP']].sort_values('Dias_Efectivos'), use_container_width=True, hide_index=True)
                with col_d2:
                    st.write("### Concentración por Categoría")
                    fig_cat = px.bar(df_f.groupby('Categoria')['Valor_Stock_CLP'].sum().reset_index(), x='Categoria', y='Valor_Stock_CLP', color_discrete_sequence=['#1a237e'])
                    st.plotly_chart(fig_cat, use_container_width=True)

        except Exception as e:
            st.error(f"Error de Integración: {e}")
    else:
        st.info("👋 Por favor, carga los archivos (Sucursales, Productos e Inventario) para activar el Dashboard BI.")
