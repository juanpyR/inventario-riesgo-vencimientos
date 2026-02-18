import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
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

def clasificar_riesgo_hoy(dias):
    """Lógica de semáforo de inventario.py: Vencido (0), Crítico (3), Urgente (7)"""
    if dias == 0: return 'VENCIDO'
    elif dias <= 3: return 'CRITICO'
    elif dias <= 7: return 'URGENTE'
    else: return 'PREVENTIVO'

COLOR_MAP = {
    'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 
    'URGENTE': '#f57c00', 'PREVENTIVO': '#fbc02d'
}

# --- ESTILOS CSS (Look BI Corporativo) ---
st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 20px; border-radius: 12px; border-top: 6px solid #1a237e; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 25px; }
    .plan-box { background-color: #fef9e7; border-left: 8px solid #f39c12; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .metric-val { font-size: 30px; font-weight: bold; color: #1a237e; }
    .metric-label { font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 1. CARGA Y RELACIÓN DE TABLAS (PASO FUNDAMENTAL)
# =============================================================================
st.sidebar.title("📁 Carga de Inteligencia")
uploaded_files = st.sidebar.file_uploader("Sube los 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "productos": None, "inventario": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Identificación automática por ADN de columnas
        if "Latitud" in cols and "ID_Ciudad" in cols:
            data["sucursales"] = df_temp
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
        elif "Tipo_Movimiento" in cols and "Lote_ID" in cols:
            data["inventario"] = df_temp

    # =============================================================================
    # 2. PROCESO DE INTEGRACIÓN Y ANÁLISIS AL DÍA DE HOY
    # =============================================================================
    if all(v is not None for v in [data["sucursales"], data["productos"], data["inventario"]]):
        try:
            # Relación de Tablas Primero
            df_full = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
            df_full = df_full.merge(data["productos"][['Producto_ID', 'Categoria']], on='Producto_ID', how='left')
            
            # Análisis Temporal
            tz_cl = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
            df_full['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_full['Fecha_Vencimiento_Lote'])
            
            # Snapshot actual
            df_actual = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            df_actual['Dias_Restantes'] = (df_actual['Fecha_Vencimiento_Lote'] - fecha_hoy).dt.days
            df_actual['Riesgo_Hoy'] = df_actual['Dias_Restantes'].apply(clasificar_riesgo_hoy)
            df_actual['Valor_Costo'] = df_actual['Stock_Teorico_Unidades'] * df_actual['Valor_Unitario_CLP']

            # --- VISTA BI ---
            st.title(f"🛡️ Centro de Mando: Riesgo al {fecha_hoy.strftime('%d/%m/%Y')}")

            # Filtros
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                sel_suc = st.multiselect("Sucursales", df_actual['Sucursal'].unique(), default=df_actual['Sucursal'].unique())
            with c_f2:
                sel_riesgo = st.multiselect("Niveles de Riesgo", list(COLOR_MAP.keys()), default=['CRITICO', 'URGENTE'])

            df_f = df_actual[(df_actual['Sucursal'].isin(sel_suc)) & (df_actual['Riesgo_Hoy'].isin(sel_riesgo))]

            # --- RESUMEN EJECUTIVO ---
            st.subheader("📊 Resumen Ejecutivo")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                val_critico = df_f[df_f['Riesgo_Hoy']=='CRITICO']['Valor_Costo'].sum()
                st.markdown(f'<div class="report-container"><span class="metric-label">Riesgo Crítico</span><br><span class="metric-val" style="color:#d32f2f">{clp(val_critico)}</span></div>', unsafe_allow_html=True)
            with k2:
                recup = df_f[df_f['Riesgo_Hoy'] == 'VENCIDO']['Valor_Costo'].sum() * 0.27
                st.markdown(f'<div class="report-container"><span class="metric-label">Crédito Fiscal Est.</span><br><span class="metric-val" style="color:#9c27b0">{clp(recup)}</span></div>', unsafe_allow_html=True)
            with k3:
                val_tot = df_f['Valor_Costo'].sum()
                st.markdown(f'<div class="report-container"><span class="metric-label">Monto en Riesgo</span><br><span class="metric-val">{clp(val_tot)}</span></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="report-container"><span class="metric-label">Días Promedio</span><br><span class="metric-val">{int(df_f["Dias_Restantes"].mean()) if not df_f.empty else 0} d</span></div>', unsafe_allow_html=True)

            # --- MAPA GEOGRÁFICO INTERACTIVO (ZOOM HABILITADO) ---
            st.subheader("🌐 Análisis Geográfico Dinámico")
            
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Costo", color="Riesgo_Hoy",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", hover_data=["Producto", "Stock_Teorico_Unidades", "Dias_Restantes"],
                zoom=10, height=550, mapbox_style="carto-positron"
            )
            
            # ACTUALIZACIÓN DE INTERACTIVIDAD (ZOOM CON RUEDA)
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True})

            # --- PLAN DE ACCIÓN ---
            st.markdown(f"""
                <div class="plan-box">
                    <h3>📝 Plan de Acción Ejecutivo</h3>
                    <ul>
                        <li><b>Donaciones:</b> Gestionar {clp(df_f[df_f['Riesgo_Hoy']=='VENCIDO']['Valor_Costo'].sum())} para asegurar el beneficio tributario del 27%.</li>
                        <li><b>Descuento Crítico:</b> Aplicar FEFO inmediato en productos con riesgo Crítico (1-3 días).</li>
                        <li><b>Logística:</b> Coordinar transferencias desde las sucursales con mayor concentración de riesgo Urgente.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error en la relación de datos: {e}")
    else:
        st.info("👋 Por favor, carga los archivos maestros para activar el Dashboard BI.")
