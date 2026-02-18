import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import pytz

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILO (Look & Feel BI)
# =============================================================================
st.set_page_config(page_title="Centro de Mando de Inventario", layout="wide")

# Colores Semáforo Coherentes con inventario.py
COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # Violeta
    'CRITICO': '#d32f2f',      # Rojo
    'URGENTE': '#f57c00',      # Naranja
    'PREVENTIVO': '#fbc02d',   # Amarillo
    'NORMAL': '#2e7d32'        # Verde
}

st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .executive-card {
        background-color: #ffffff; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-top: 6px solid #1a237e;
        text-align: center; margin-bottom: 20px;
    }
    .plan-box {
        background: linear-gradient(135deg, #fff9e6 0%, #fff4e5 100%);
        padding: 25px; border-radius: 12px; border-left: 10px solid #f57c00;
        margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .metric-value { font-size: 32px; font-weight: 700; color: #1a237e; }
    .metric-label { font-size: 14px; color: #666; font-weight: 600; text-transform: uppercase; }
    .badge-vencido { color: #9c27b0; font-weight: bold; }
    .badge-critico { color: #d32f2f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 2. LÓGICA DE NEGOCIO (Sincronizada con inventario.py)
# =============================================================================
def clp(valor):
    if pd.isna(valor): return "$0"
    v = int(round(float(valor)))
    return f"${v:,}".replace(",", ".")

def clasificar_riesgo(dias):
    if dias <= 0: return 'VENCIDO'
    elif dias <= 3: return 'CRITICO'
    elif dias <= 7: return 'URGENTE'
    elif dias <= 30: return 'PREVENTIVO'
    else: return 'NORMAL'

# =============================================================================
# 3. CARGA E IDENTIFICACIÓN ROBUSTA DE ARCHIVOS
# =============================================================================
st.sidebar.title("📁 Carga de Inteligencia")
uploaded_files = st.sidebar.file_uploader("Arrastra los 5 archivos maestros", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "productos": None, "inventario": None, "lotes": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Identificación automática por columnas únicas
        if "Latitud" in cols and "ID_Ciudad" in cols and "Stock_Teorico_Unidades" not in cols:
            data["sucursales"] = df_temp
            st.sidebar.success(f"✅ Sucursales vinculadas")
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
            st.sidebar.success(f"✅ Maestro de Productos vinculado")
        elif "Tipo_Movimiento" in cols and "Lote_ID" in cols:
            data["inventario"] = df_temp
            st.sidebar.success(f"✅ Histórico de Movimientos vinculado")
        elif "Fecha_Creacion_Lote" in cols:
            data["lotes"] = df_temp
            st.sidebar.success(f"✅ Maestro de Lotes vinculado")

    # =============================================================================
    # 4. PROCESO DE RELACIÓN Y CONSOLIDACIÓN (EL "CORAZÓN")
    # =============================================================================
    if data["inventario"] is not None and data["sucursales"] is not None and data["productos"] is not None:
        try:
            # Relación de Tablas (Merges)
            df_full = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
            df_full = df_full.merge(data["productos"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], on='Producto_ID', how='left')
            
            # Análisis Dinámico "Al día de hoy"
            tz_cl = pytz.timezone('America/Santiago')
            fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
            
            # Snapshot: Stock actual (último registro por Lote/Sucursal)
            df_snapshot = df_full.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
            
            # Clasificación de Riesgo basada en HOY
            df_snapshot['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_snapshot['Fecha_Vencimiento_Lote'])
            df_snapshot['Dias_Hoy'] = (df_snapshot['Fecha_Vencimiento_Lote'] - fecha_hoy).dt.days
            df_snapshot['Nivel_Riesgo'] = df_snapshot['Dias_Hoy'].apply(clasificar_riesgo)
            df_snapshot['Valor_Costo_Total'] = df_snapshot['Stock_Teorico_Unidades'] * df_snapshot['Valor_Unitario_CLP']

            # =============================================================================
            # 5. DASHBOARD BI - VISTA RESUMEN
            # =============================================================================
            st.title(f"🛡️ Gestión de Riesgo de Inventario")
            st.markdown(f"**Análisis Estratégico Realizado al {fecha_hoy.strftime('%d/%m/%Y')}**")

            # Filtros BI
            f1, f2 = st.columns(2)
            with f1:
                sel_suc = st.multiselect("Filtrar Sucursales", df_snapshot['Sucursal'].unique(), default=df_snapshot['Sucursal'].unique())
            with f2:
                sel_riesgo = st.multiselect("Niveles de Riesgo", list(COLOR_MAP.keys()), default=['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO'])

            df_f = df_snapshot[(df_snapshot['Sucursal'].isin(sel_suc)) & (df_snapshot['Nivel_Riesgo'].isin(sel_riesgo))]

            # --- SECCIÓN KPIs EJECUTIVOS ---
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Valor en Riesgo Total</span><br><span class="metric-value">{clp(df_f["Valor_Costo_Total"].sum())}</span></div>', unsafe_allow_html=True)
            with k2:
                # Lógica Contable: Recuperación Crédito Fiscal por Donación de Vencidos (27%)
                vencidos_val = df_f[df_f['Nivel_Riesgo'] == 'VENCIDO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Crédito Fiscal (Donación)</span><br><span class="metric-value" style="color:#9c27b0">{clp(vencidos_val * 0.27)}</span></div>', unsafe_allow_html=True)
            with k3:
                criticos_val = df_f[df_f['Nivel_Riesgo'] == 'CRITICO']['Valor_Costo_Total'].sum()
                st.markdown(f'<div class="executive-card"><span class="metric-label">Monto Crítico (3d)</span><br><span class="metric-value" style="color:#d32f2f">{clp(criticos_val)}</span></div>', unsafe_allow_html=True)
            with k4:
                st.markdown(f'<div class="executive-card"><span class="metric-label">Productos en Riesgo</span><br><span class="metric-value">{len(df_f)}</span></div>', unsafe_allow_html=True)

            # --- MAPA GEOGRÁFICO BI ---
            st.subheader("🌐 Mapa de Riesgo Operativo")
            fig_map = px.scatter_mapbox(
                df_f, lat="Latitud", lon="Longitud",
                size="Valor_Costo_Total", color="Nivel_Riesgo",
                color_discrete_map=COLOR_MAP,
                hover_name="Sucursal", hover_data=["Producto", "Stock_Teorico_Unidades", "Dias_Hoy"],
                zoom=10, height=550, mapbox_style="carto-positron"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)

            # --- RESUMEN PLAN DE ACCIÓN ---
            st.markdown(f"""
                <div class="plan-box">
                    <h3 style="margin-top:0;">📝 Resumen del Plan de Acción y Decisiones</h3>
                    <p>Basado en el análisis del mes actual, se requiere intervención inmediata en <b>{df_f['Sucursal'].nunique()} sucursales</b>:</p>
                    <ul>
                        <li><b>Donación Estratégica:</b> Procesar {clp(vencidos_val)} de productos vencidos para asegurar el crédito fiscal del 27%.</li>
                        <li><b>Liquidación Crítica:</b> Aplicar descuento FEFO de hasta el 50% en productos con riesgo <b>CRITICO (1-3 días)</b>.</li>
                        <li><b>Gestión de Mermas:</b> El potencial de pérdida sin acción es de {clp(df_f[df_f['Nivel_Riesgo'].isin(['CRITICO','URGENTE'])]['Valor_Costo_Total'].sum())}.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

            # =============================================================================
            # 6. ANÁLISIS EXTENSO (TABLA Y DETALLE)
            # =============================================================================
            st.markdown("---")
            with st.expander("🔍 Ver Análisis de Inventario Extenso (Detalle por Lote)"):
                col_d1, col_d2 = st.columns([7, 3])
                with col_d1:
                    st.write("### Auditoría de Lotes")
                    st.dataframe(
                        df_f[['Nivel_Riesgo', 'Producto', 'Sucursal', 'Dias_Hoy', 'Stock_Teorico_Unidades', 'Valor_Costo_Total']].sort_values('Dias_Hoy'),
                        column_config={"Valor_Costo_Total": st.column_config.NumberColumn("Valor Costo", format="$%d")},
                        use_container_width=True, hide_index=True
                    )
                with col_d2:
                    st.write("### Riesgo por Categoría ($)")
                    cat_risk = df_f.groupby('Categoria')['Valor_Costo_Total'].sum().reset_index()
                    fig_cat = px.bar(cat_risk, x='Categoria', y='Valor_Costo_Total', color_discrete_sequence=['#1a237e'])
                    st.plotly_chart(fig_cat, use_container_width=True)

        except Exception as e:
            st.error(f"Error en la relación de datos: {e}")
            st.info("Asegúrate de que los archivos contengan las columnas 'Producto_ID' y 'Sucursal' para establecer la relación.")
    else:
        st.info("👋 Por favor, carga los 5 archivos (Sucursales, Productos, Lotes, Inventario y Stock Geo) para activar el Dashboard BI.")
