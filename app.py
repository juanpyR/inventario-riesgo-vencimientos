import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pytz
import io
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# 1. CONFIGURACIÓN PREMIUM + CSS AVANZADO
# =============================================================================
st.set_page_config(
    page_title="🛡️ Command Center: Riesgo de Inventario", 
    layout="wide",
    page_icon="📊"
)

def cargar_css_premium():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    /* Fondo y estructura */
    .main { background: linear-gradient(135deg, #f8f9fb 0%, #eef2f7 100%); }
    .stApp { background-color: #f8f9fb; }
    
    /* Tarjetas Ejecutivas con efecto hover */
    .executive-card {
        background: white; 
        padding: 25px; 
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(26,35,126,0.12); 
        border-top: 5px solid #1a237e;
        text-align: center; 
        margin: 10px 0;
        transition: all 0.3s ease;
        border: 1px solid rgba(26,35,126,0.08);
    }
    .executive-card:hover { 
        transform: translateY(-4px); 
        box-shadow: 0 8px 30px rgba(26,35,126,0.2);
    }
    
    /* Métricas */
    .metric-value { 
        font-size: 34px; 
        font-weight: 800; 
        color: #1a237e; 
        letter-spacing: -1px;
        line-height: 1.1;
    }
    .metric-label { 
        font-size: 12px; 
        color: #666; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.8px;
        margin-bottom: 8px;
    }
    .metric-sub { 
        font-size: 11px; 
        color: #888; 
        margin-top: 4px;
        font-weight: 500;
    }
    
    /* Plan de Acción Premium */
    .plan-box {
        background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
        padding: 30px; 
        border-radius: 16px; 
        border-left: 8px solid #f57c00;
        box-shadow: 0 4px 20px rgba(245,124,0,0.15); 
        margin: 25px 0;
        border: 1px solid rgba(245,124,0,0.2);
    }
    
    /* Semáforo de Riesgo */
    .risk-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 3px;
    }
    .risk-vencido { background: #f3e5f5; color: #7b1fa2; border: 2px solid #9c27b0; }
    .risk-critico { background: #ffebee; color: #c62828; border: 2px solid #d32f2f; }
    .risk-urgente { background: #fff3e0; color: #e65100; border: 2px solid #f57c00; }
    .risk-preventivo { background: #fffde7; color: #f9a825; border: 2px solid #fbc02d; }
    .risk-normal { background: #e8f5e9; color: #2e7d32; border: 2px solid #4caf50; }
    
    /* Indicador de estado */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Títulos de sección */
    .section-header { 
        color: #1a237e; 
        font-weight: 800; 
        font-size: 1.6rem;
        margin: 40px 0 20px 0; 
        padding-bottom: 12px;
        border-bottom: 3px solid #1a237e;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    /* Tablas premium */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        font-size: 0.9rem;
    }
    .dataframe thead th {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        font-weight: 700;
        padding: 14px;
        border: none;
    }
    
    /* Botones personalizados */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s;
        border: 2px solid #1a237e;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(26,35,126,0.3);
    }
    
    /* Timeline de acciones */
    .timeline {
        display: flex;
        justify-content: space-between;
        margin: 20px 0;
        padding: 20px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .timeline-item {
        text-align: center;
        flex: 1;
        position: relative;
        padding: 0 10px;
    }
    .timeline-item:not(:last-child)::after {
        content: '';
        position: absolute;
        top: 25px;
        right: -50%;
        width: 100%;
        height: 2px;
        background: #e0e0e0;
        z-index: 0;
    }
    .timeline-dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        margin: 0 auto 8px;
        background: #667eea;
        position: relative;
        z-index: 1;
    }
    .timeline-time { font-size: 12px; font-weight: 700; color: #1a237e; }
    .timeline-action { font-size: 11px; color: #666; }
    </style>
    """, unsafe_allow_html=True)

cargar_css_premium()

# =============================================================================
# 2. CONSTANTES Y LÓGICA DE NEGOCIO (Chile BI Standard)
# =============================================================================
def clp(valor):
    """Formatea a moneda chilena: $1.234.567"""
    if pd.isna(valor) or valor is None: 
        return "$0"
    try:
        v = int(round(float(valor)))
        return f"${v:,}".replace(",", ".")
    except:
        return "$0"

def clasificar_riesgo_bi(dias):
    """Lógica oficial con semáforo de 5 niveles"""
    if pd.isna(dias): return 'SIN_DATO'
    if dias <= 0: return 'VENCIDO'
    elif dias <= 3: return 'CRITICO'
    elif dias <= 7: return 'URGENTE'
    elif dias <= 30: return 'PREVENTIVO'
    else: return 'NORMAL'

COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # 🟣 Violeta - Pérdida total
    'CRITICO': '#d32f2f',      # 🔴 Rojo - Acción inmediata
    'URGENTE': '#f57c00',      # 🟠 Naranja - Alta prioridad
    'PREVENTIVO': '#fbc02d',   # 🟡 Amarillo - Monitoreo
    'NORMAL': '#2e7d32',       # 🟢 Verde - Sin riesgo
    'SIN_DATO': '#9e9e9e'      # ⚪ Gris - Sin información
}

COLUMNAS_ESPERADAS = {
    'Dias_Para_Vencer': ['Dias_Para_Vencer', 'Días_para_Vencimiento', 'Días para Vencimiento'],
    'Stock_Teorico_Unidades': ['Stock_Teorico_Unidades', 'Stock_Inicial', 'Cantidad_Stock'],
    'Valor_Unitario_CLP': ['Valor_Unitario_CLP', 'Costo_Unitario_Neto', 'Precio_Costo'],
    'Precio_Venta_CLP': ['Precio_Venta_CLP', 'Precio_Venta_Bruto'],
    'Producto': ['Producto', 'producto', 'SKU_Descripcion'],
    'Sucursal': ['Sucursal', 'sucursal', 'Tienda'],
    'Latitud': ['Latitud', 'lat', 'Latitude'],
    'Longitud': ['Longitud', 'lon', 'Longitude'],
    'Fecha_Vencimiento_Lote': ['Fecha_Vencimiento_Lote', 'Fecha_Vencimiento'],
    'Fecha_Movimiento': ['Fecha_Movimiento', 'Fecha', 'Fecha_Transaccion']
}

# =============================================================================
# 3. MOTOR DE CARGA INTELIGENTE (Auto-Detect 5 Archivos)
# =============================================================================
@st.cache_data(ttl=300)
def cargar_archivo_inteligente(archivo):
    """Carga CSV con limpieza automática de columnas"""
    try:
        df = pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        # Limpieza de valores
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip() if hasattr(df[col].iloc[0] if len(df) > 0 else '', 'strip') else df[col]
        return df
    except Exception as e:
        st.error(f"❌ Error cargando {archivo.name}: {str(e)}")
        return None

def detectar_tipo_archivo(df):
    """Detecta automáticamente el tipo de archivo por su estructura"""
    cols = set(df.columns)
    
    if {'Latitud', 'Longitud', 'ID_Ciudad'}.issubset(cols) and 'Stock_Teorico_Unidades' not in cols:
        return 'sucursales'
    elif {'Categoria', 'Producto_ID', 'Dias_Caducidad_Base'}.issubset(cols) and 'Lote_ID' not in cols:
        return 'productos'
    elif {'Tipo_Movimiento', 'Lote_ID', 'Fecha_Movimiento'}.issubset(cols):
        return 'inventario_movimientos'
    elif {'Fecha_Creacion_Lote', 'Lote_ID', 'Dias_Caducidad_Base'}.issubset(cols):
        return 'lotes'
    elif {'Stock_Teorico_Unidades', 'Latitud', 'Lote_ID'}.issubset(cols):
        return 'stock_geo'
    return 'desconocido'

# =============================================================================
# 4. SIDEBAR: PANEL DE CONTROL
# =============================================================================
with st.sidebar:
    st.title("🎛️ Panel de Control")
    st.markdown("---")
    
    # Carga de archivos con progreso visual
    st.subheader("📁 Archivos Maestros")
    uploaded_files = st.file_uploader(
        "Arrastra los 5 archivos CSV", 
        type="csv", 
        accept_multiple_files=True,
        help="• 1_SUCURSALES_MASTER.csv\n• 2_PRODUCTOS_MASTER.csv\n• 3_LOTES_PRODUCTOS.csv\n• 4_INVENTARIO_COMPLETO.csv\n• 5_STOCK_ACTUAL_GEO.csv"
    )
    
    if uploaded_files:
        progreso = min(len(uploaded_files) / 5, 1.0)
        st.progress(progreso)
        st.caption(f"✅ {len(uploaded_files)}/5 archivos cargados")
    
    st.markdown("---")
    
    # Configuración de análisis
    st.subheader("⚙️ Configuración")
    
    dias_ventana = st.slider(
        "Ventana de análisis (días)", 
        min_value=7, max_value=90, value=30,
        help="Productos que vencen en los próximos X días"
    )
    
    incluir_normales = st.checkbox(
        "Incluir productos normales", 
        value=False,
        help="Mostrar también productos sin riesgo inminente"
    )
    
    st.markdown("---")
    
    # Acciones rápidas
    st.subheader("⚡ Acciones")
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    if st.button("📥 Exportar Reporte", use_container_width=True):
        st.info("📊 Generando archivo Excel... (próximamente)")

# =============================================================================
# 5. PROCESAMIENTO PRINCIPAL
# =============================================================================
if uploaded_files:
    # Diccionario para almacenar dataframes por tipo
    data = {}
    
    # Clasificar y cargar archivos
    for file in uploaded_files:
        df_temp = cargar_archivo_inteligente(file)
        if df_temp is not None:
            tipo = detectar_tipo_archivo(df_temp)
            data[tipo] = df_temp
            st.sidebar.success(f"✅ {tipo}: {len(df_temp)} registros")
    
    # Validar archivos esenciales
    if 'stock_geo' in data or 'inventario_movimientos' in data:
        try:
            with st.spinner("🔄 Procesando inteligencia de inventario..."):
                
                # ========================================
                # CONSOLIDACIÓN DE DATOS
                # ========================================
                df_base = data.get('stock_geo') or data.get('inventario_movimientos')
                
                # Merge con sucursales para coordenadas
                if 'sucursales' in data and 'Sucursal' in df_base.columns:
                    df_base = df_base.merge(
                        data['sucursales'][['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']],
                        on='Sucursal', how='left'
                    )
                
                # Merge con productos para categoría
                if 'productos' in data and 'Producto_ID' in df_base.columns:
                    df_base = df_base.merge(
                        data['productos'][['Producto_ID', 'Categoria', 'Categoria_Rotacion']],
                        on='Producto_ID', how='left'
                    )
                
                # ========================================
                # CÁLCULOS TEMPORALES (Chile Timezone)
                # ========================================
                tz_cl = pytz.timezone('America/Santiago')
                fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
                
                # Parsear fechas de vencimiento
                if 'Fecha_Vencimiento_Lote' in df_base.columns:
                    df_base['Fecha_Vencimiento_Lote'] = pd.to_datetime(
                        df_base['Fecha_Vencimiento_Lote'], errors='coerce'
                    )
                    df_base['Dias_Efectivos'] = (
                        df_base['Fecha_Vencimiento_Lote'] - fecha_hoy
                    ).dt.days
                elif 'Dias_Para_Vencer' in df_base.columns:
                    df_base['Dias_Efectivos'] = df_base['Dias_Para_Vencer'].astype(float)
                
                # Clasificación de riesgo
                df_base['Riesgo_BI'] = df_base['Dias_Efectivos'].apply(clasificar_riesgo_bi)
                
                # Cálculo de valor monetario
                if 'Valor_Unitario_CLP' in df_base.columns and 'Stock_Teorico_Unidades' in df_base.columns:
                    df_base['Valor_Costo_Total'] = (
                        df_base['Stock_Teorico_Unidades'].fillna(0) * 
                        df_base['Valor_Unitario_CLP'].fillna(0)
                    )
                elif 'Precio_Venta_CLP' in df_base.columns:
                    # Estimación: costo = 70% del precio de venta
                    df_base['Valor_Costo_Total'] = (
                        df_base['Stock_Teorico_Unidades'].fillna(0) * 
                        df_base['Precio_Venta_CLP'].fillna(0) * 0.70
                    )
                else:
                    df_base['Valor_Costo_Total'] = df_base['Stock_Teorico_Unidades'].fillna(0)
                
                # ========================================
                # FILTROS INTERACTIVOS
                # ========================================
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                
                with col_f1:
                    sucursales_disp = df_base['Sucursal'].dropna().unique() if 'Sucursal' in df_base.columns else []
                    sel_suc = st.multiselect(
                        "🏪 Sucursales", 
                        sucursales_disp, 
                        default=sucursales_disp[:3] if len(sucursales_disp) > 0 else [],
                        key="filter_suc"
                    )
                
                with col_f2:
                    categorias_disp = df_base['Categoria'].dropna().unique() if 'Categoria' in df_base.columns else []
                    sel_cat = st.multiselect(
                        "📦 Categorías", 
                        categorias_disp,
                        default=categorias_disp,
                        key="filter_cat"
                    )
                
                with col_f3:
                    riesgos_disp = [r for r in COLOR_MAP.keys() if r in df_base['Riesgo_BI'].values]
                    sel_risk = st.multiselect(
                        "⚠️ Nivel de Riesgo", 
                        riesgos_disp,
                        default=['VENCIDO', 'CRITICO', 'URGENTE'],
                        key="filter_risk"
                    )
                
                with col_f4:
                    rotacion_disp = df_base['Categoria_Rotacion'].dropna().unique() if 'Categoria_Rotacion' in df_base.columns else []
                    sel_rot = st.multiselect(
                        "🔄 Rotación", 
                        rotacion_disp,
                        default=rotacion_disp,
                        key="filter_rot"
                    )
                
                # Aplicar filtros
                df_f = df_base.copy()
                if sel_suc and 'Sucursal' in df_f.columns:
                    df_f = df_f[df_f['Sucursal'].isin(sel_suc)]
                if sel_cat and 'Categoria' in df_f.columns:
                    df_f = df_f[df_f['Categoria'].isin(sel_cat)]
                if sel_risk:
                    df_f = df_f[df_f['Riesgo_BI'].isin(sel_risk)]
                if sel_rot and 'Categoria_Rotacion' in df_f.columns:
                    df_f = df_f[df_f['Categoria_Rotacion'].isin(sel_rot)]
                if not incluir_normales:
                    df_f = df_f[df_f['Riesgo_BI'] != 'NORMAL']
                
                # ========================================
                # CABECERA EJECUTIVA
                # ========================================
                st.title(f"🛡️ Command Center: Riesgo de Inventario")
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a237e 0%, #283593 100%); 
                           color: white; padding: 20px 30px; border-radius: 16px; 
                           margin: 10px 0 30px 0; box-shadow: 0 4px 20px rgba(26,35,126,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h2 style="margin: 0; font-size: 1.8rem;">📊 Inteligencia en Tiempo Real</h2>
                            <p style="margin: 5px 0 0 0; opacity: 0.9;">
                                🕒 Actualizado: {datetime.now(tz_cl).strftime('%d/%m/%Y %H:%M')} CLT
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <span style="display: inline-flex; align-items: center; background: rgba(255,255,255,0.2); 
                                   padding: 8px 16px; border-radius: 20px; font-weight: 600;">
                                <span class="status-dot" style="background: #4caf50;"></span>
                                Sistema Activo
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # ========================================
                # KPIs EJECUTIVOS (4 Columnas)
                # ========================================
                val_total = df_f["Valor_Costo_Total"].sum()
                venc_val = df_f[df_f['Riesgo_BI'] == 'VENCIDO']['Valor_Costo_Total'].sum()
                crit_val = df_f[df_f['Riesgo_BI'] == 'CRITICO']['Valor_Costo_Total'].sum()
                urg_val = df_f[df_f['Riesgo_BI'] == 'URGENTE']['Valor_Costo_Total'].sum()
                unid_alerta = int(df_f["Stock_Teorico_Unidades"].sum())
                
                # Cálculos de recuperación
                credito_fiscal = venc_val * 0.27  # Ley 19.885 Chile
                recuperacion_crit = crit_val * 0.50  # Estimado liquidación 40-60%
                recuperacion_urg = urg_val * 0.40
                total_recuperable = credito_fiscal + recuperacion_crit + recuperacion_urg
                
                k1, k2, k3, k4 = st.columns(4)
                
                with k1:
                    st.markdown(f'''
                    <div class="executive-card">
                        <span class="metric-label">💰 Monto Total en Riesgo</span>
                        <div class="metric-value">{clp(val_total)}</div>
                        <div class="metric-sub">{len(df_f)} productos • {unid_alerta:,} unidades</div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with k2:
                    st.markdown(f'''
                    <div class="executive-card" style="border-top-color: #9c27b0;">
                        <span class="metric-label">🏛️ Crédito Fiscal (Donación)</span>
                        <div class="metric-value" style="color:#9c27b0;">{clp(credito_fiscal)}</div>
                        <div class="metric-sub">27% sobre ${int(venc_val):,} vencidos</div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with k3:
                    st.markdown(f'''
                    <div class="executive-card" style="border-top-color: #d32f2f;">
                        <span class="metric-label">🔥 Recuperación Crítica</span>
                        <div class="metric-value" style="color:#d32f2f;">{clp(recuperacion_crit)}</div>
                        <div class="metric-sub">50% estimado liquidación</div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with k4:
                    st.markdown(f'''
                    <div class="executive-card" style="border-top-color: #4caf50;">
                        <span class="metric-label">✅ Total Recuperable</span>
                        <div class="metric-value" style="color:#2e7d32;">{clp(total_recuperable)}</div>
                        <div class="metric-sub">{(total_recuperable/val_total*100) if val_total>0 else 0:.1f}% del riesgo</div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # ========================================
                # MAPA GEOGRÁFICO INTERACTIVO (Plotly Mapbox)
                # ========================================
                st.markdown('<h2 class="section-header">🌐 Análisis Espacial de Caducidad</h2>', unsafe_allow_html=True)
                
                if 'Latitud' in df_f.columns and 'Longitud' in df_f.columns and df_f['Latitud'].notna().any():
                    # Preparar datos para mapa
                    df_map = df_f.groupby(['Sucursal', 'Latitud', 'Longitud']).agg({
                        'Valor_Costo_Total': 'sum',
                        'Stock_Teorico_Unidades': 'sum',
                        'Riesgo_BI': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'NORMAL',
                        'Dias_Efectivos': 'mean'
                    }).reset_index()
                    
                    fig_map = px.scatter_mapbox(
                        df_map, 
                        lat="Latitud", lon="Longitud",
                        size="Valor_Costo_Total", 
                        size_max=40,
                        color="Riesgo_BI",
                        color_discrete_map=COLOR_MAP,
                        hover_name="Sucursal", 
                        hover_data={
                            "Valor_Costo_Total": ":$.0f",
                            "Stock_Teorico_Unidades": ":,.0f",
                            "Dias_Efectivos": ":.1f",
                            "Latitud": False, 
                            "Longitud": False
                        },
                        zoom=9, 
                        height=500, 
                        mapbox_style="carto-positron",
                        center={"lat": -33.45, "lon": -70.65}  # Santiago centro
                    )
                    
                    fig_map.update_layout(
                        margin={"r":0,"t":10,"l":0,"b":0},
                        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99)
                    )
                    
                    st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})
                    
                    # Resumen por sucursal debajo del mapa
                    with st.expander("📋 Detalle por Sucursal", expanded=False):
                        resumen_suc = df_f.groupby('Sucursal').agg({
                            'Valor_Costo_Total': 'sum',
                            'Stock_Teorico_Unidades': 'sum',
                            'Producto': 'count',
                            'Dias_Efectivos': 'mean'
                        }).round(0).sort_values('Valor_Costo_Total', ascending=False)
                        
                        st.dataframe(
                            resumen_suc.style.format({
                                'Valor_Costo_Total': clp,
                                'Stock_Teorico_Unidades': '{:,.0f}',
                                'Dias_Efectivos': '{:.1f}'
                            }),
                            use_container_width=True
                        )
                else:
                    st.info("📍 Coordenadas no disponibles. Verifica que los archivos de sucursales/stock incluyan Latitud y Longitud.")
                
                # ========================================
                # PLAN DE ACCIÓN ESTRATÉGICO
                # ========================================
                st.markdown(f'''
                <div class="plan-box">
                    <h3 style="margin-top:0; color:#1a237e; display:flex; align-items:center; gap:10px;">
                        📋 Plan de Acción Inmediato
                    </h3>
                    <p style="margin-bottom:20px;">
                        Acciones prioritarias para mitigar pérdida de <b>{clp(val_total)}</b> en riesgo:
                    </p>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px;">
                        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #9c27b0;">
                            <strong style="color:#7b1fa2;">🟣 VENCIDOS ({int(df_f[df_f['Riesgo_BI']=='VENCIDO']['Producto'].nunique() if 'Producto' in df_f.columns else 0)})</strong><br>
                            <small>→ Donación inmediata para crédito fiscal 27%</small>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #d32f2f;">
                            <strong style="color:#c62828;">🔴 CRÍTICOS ({int(df_f[df_f['Riesgo_BI']=='CRITICO']['Producto'].nunique() if 'Producto' in df_f.columns else 0)})</strong><br>
                            <small>→ Liquidación FEFO con 40-60% descuento</small>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #f57c00;">
                            <strong style="color:#e65100;">🟠 URGENTES ({int(df_f[df_f['Riesgo_BI']=='URGENTE']['Producto'].nunique() if 'Producto' in df_f.columns else 0)})</strong><br>
                            <small>→ Transferencia a sedes de alto tráfico</small>
                        </div>
                    </div>
                    
                    <div class="timeline">
                        <div class="timeline-item">
                            <div class="timeline-dot" style="background:#d32f2f;"></div>
                            <div class="timeline-time">HOY 08:00</div>
                            <div class="timeline-action">Retirar vencidos</div>
                        </div>
                        <div class="timeline-item">
                            <div class="timeline-dot" style="background:#f57c00;"></div>
                            <div class="timeline-time">HOY 14:00</div>
                            <div class="timeline-action">Activar descuentos</div>
                        </div>
                        <div class="timeline-item">
                            <div class="timeline-dot" style="background:#fbc02d;"></div>
                            <div class="timeline-time">MAÑANA</div>
                            <div class="timeline-action">Revisar preventivos</div>
                        </div>
                        <div class="timeline-item">
                            <div class="timeline-dot" style="background:#2e7d32;"></div>
                            <div class="timeline-time">48H</div>
                            <div class="timeline-action">Reporte final</div>
                        </div>
                    </div>
                    
                    <div style="background: #e8f5e9; padding: 15px; border-radius: 10px; text-align: center;">
                        <strong style="color: #2e7d32; font-size: 1.2rem;">
                            💰 Proyección de Recuperación: {clp(total_recuperable)} CLP
                        </strong>
                        <br><small style="color: #666;">Incluye crédito fiscal + liquidación estimada</small>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                # ========================================
                # GRÁFICOS DE PROFUNDIDAD (Tabs)
                # ========================================
                st.markdown('<h2 class="section-header">🔍 Análisis de Profundidad</h2>', unsafe_allow_html=True)
                
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📊 Concentración Financiera", 
                    "🏗️ Composición Stock", 
                    "📉 Rotación vs Caducidad", 
                    "📍 Riesgo por Sede",
                    "📑 Auditoría Detallada"
                ])
                
                with tab1:
                    st.write("### Valor de Inventario por Categoría y Nivel de Riesgo")
                    if len(df_f) > 0 and 'Categoria' in df_f.columns:
                        fig1 = px.bar(
                            df_f, 
                            x="Categoria", 
                            y="Valor_Costo_Total", 
                            color="Riesgo_BI", 
                            color_discrete_map=COLOR_MAP, 
                            barmode="group", 
                            text_auto='.2s',
                            title="Distribución del valor en riesgo por categoría"
                        )
                        fig1.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig1, use_container_width=True)
                    else:
                        st.info("📊 Sin datos para visualizar")
                
                with tab2:
                    st.write("### Composición Jerárquica del Inventario")
                    if len(df_f) > 0:
                        fig2 = px.sunburst(
                            df_f, 
                            path=['Riesgo_BI', 'Categoria'] if 'Categoria' in df_f.columns else ['Riesgo_BI'], 
                            values='Stock_Teorico_Unidades',
                            color='Riesgo_BI', 
                            color_discrete_map=COLOR_MAP,
                            title="Navega por niveles: Riesgo → Categoría → Producto"
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("📊 Sin datos para visualizar")
                
                with tab3:
                    st.write("### Correlación: Días para Vencer vs Unidades")
                    if len(df_f) > 0 and 'Dias_Efectivos' in df_f.columns:
                        fig3 = px.scatter(
                            df_f, 
                            x="Dias_Efectivos", 
                            y="Stock_Teorico_Unidades", 
                            size="Valor_Costo_Total", 
                            color="Categoria_Rotacion" if 'Categoria_Rotacion' in df_f.columns else None,
                            hover_name="Producto" if 'Producto' in df_f.columns else None,
                            color_discrete_map=COLOR_MAP if 'Categoria_Rotacion' not in df_f.columns else None,
                            title="Tamaño de burbuja = Valor Monetario • Línea roja = Hoy"
                        )
                        fig3.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="HOY")
                        fig3.update_layout(height=400)
                        st.plotly_chart(fig3, use_container_width=True)
                    else:
                        st.info("📊 Sin datos para visualizar")
                
                with tab4:
                    st.write("### Top 10 Sucursales con Mayor Inversión en Riesgo")
                    if 'Sucursal' in df_f.columns and len(df_f) > 0:
                        top_suc = df_f.groupby('Sucursal')['Valor_Costo_Total'].sum().sort_values(ascending=False).head(10).reset_index()
                        fig4 = px.bar(
                            top_suc, 
                            x='Sucursal', 
                            y='Valor_Costo_Total', 
                            color='Valor_Costo_Total', 
                            color_continuous_scale='YlOrRd', 
                            text_auto='.3s',
                            title="Foco en sedes con mayor exposición financiera"
                        )
                        fig4.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig4, use_container_width=True)
                    else:
                        st.info("📊 Sin datos de sucursales disponibles")
                
                with tab5:
                    st.write("### 📑 Listado Maestro de Auditoría")
                    if len(df_f) > 0:
                        # Columnas a mostrar
                        cols_show = [c for c in ['Riesgo_BI', 'Producto', 'Sucursal', 'Dias_Efectivos', 
                                                'Stock_Teorico_Unidades', 'Valor_Costo_Total', 'Categoria'] 
                                   if c in df_f.columns]
                        
                        # Badge de riesgo en la tabla
                        def badge_riesgo(val):
                            color_class = f"risk-{val.lower()}" if val in COLOR_MAP else "risk-normal"
                            return f'<span class="risk-badge {color_class}">{val}</span>'
                        
                        # Formatear tabla
                        df_display = df_f[cols_show].sort_values('Dias_Efectivos' if 'Dias_Efectivos' in cols_show else cols_show[0])
                        
                        st.dataframe(
                            df_display.style.format({
                                'Valor_Costo_Total': clp if 'Valor_Costo_Total' in df_display.columns else None,
                                'Stock_Teorico_Unidades': '{:,.0f}' if 'Stock_Teorico_Unidades' in df_display.columns else None,
                                'Dias_Efectivos': '{:.0f}' if 'Dias_Efectivos' in df_display.columns else None
                            }).map(badge_riesgo, subset=['Riesgo_BI']) if 'Riesgo_BI' in df_display.columns else None,
                            use_container_width=True, 
                            hide_index=True
                        )
                        
                        # Botón de descarga
                        csv = df_display.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 Descargar Auditoría (CSV)",
                            data=csv,
                            file_name=f"auditoria_riesgo_{fecha_hoy.strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.info("📊 Sin datos para auditar")
                
                # ========================================
                # FOOTER CON METADATOS
                # ========================================
                st.markdown("---")
                st.caption(f"""
                🛡️ **Command Center v2.0** • Generado: {datetime.now(tz_cl).strftime('%d/%m/%Y %H:%M:%S')} CLT  
                📁 Fuentes: {', '.join([f.name for f in uploaded_files])} • Registros procesados: {len(df_base):,}
                """)
                
        except Exception as e:
            st.error(f"❌ Error en procesamiento: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Detalles técnicos del error"):
                st.exception(e)
                st.code("""
                💡 Soluciones comunes:
                1. Verifica que los archivos tengan las columnas esperadas
                2. Asegura que Producto_ID y Sucursal coincidan entre archivos
                3. Revisa que las fechas estén en formato válido (YYYY-MM-DD)
                """)
    
    else:
        st.info("👋 **Bienvenido al Command Center**\n\nPor favor, carga al menos el archivo de **Stock Actual** o **Inventario Completo** para activar el análisis de inteligencia.")

else:
    # Pantalla de bienvenida cuando no hay archivos
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <h1 style="color: #1a237e; margin-bottom: 20px;">🛡️ Command Center: Riesgo de Inventario</h1>
        <p style="font-size: 1.2rem; color: #666; max-width: 600px; margin: 0 auto 30px;">
            Plataforma de inteligencia estratégica para gestión proactiva de caducidad de inventario.
        </p>
        <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
            <span class="risk-badge risk-vencido">🟣 Vencido</span>
            <span class="risk-badge risk-critico">🔴 Crítico</span>
            <span class="risk-badge risk-urgente">🟠 Urgente</span>
            <span class="risk-badge risk-preventivo">🟡 Preventivo</span>
            <span class="risk-badge risk-normal">🟢 Normal</span>
        </div>
        <p style="margin-top: 40px; color: #888;">
            ← Sube tus archivos en el panel lateral para comenzar
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar ejemplos de estructura esperada
    with st.expander("📋 Estructura esperada de archivos"):
        st.markdown("""
        | Archivo | Columnas Clave | Propósito |
        |---------|---------------|-----------|
        | `1_SUCURSALES_MASTER.csv` | Sucursal, Latitud, Longitud, ID_Ciudad | Geolocalización de sedes |
        | `2_PRODUCTOS_MASTER.csv` | Producto_ID, Categoria, Categoria_Rotacion | Catálogo maestro |
        | `3_LOTES_PRODUCTOS.csv` | Lote_ID, Producto_ID, Fecha_Creacion_Lote | Trazabilidad de lotes |
        | `4_INVENTARIO_COMPLETO.csv` | Lote_ID, Sucursal, Tipo_Movimiento, Fecha_Movimiento | Historial de movimientos |
        | `5_STOCK_ACTUAL_GEO.csv` | Lote_ID, Stock_Teorico_Unidades, Valor_Unitario_CLP, Latitud | Snapshot actual con geo |
        
        > 💡 **Tip**: Los archivos se relacionan automáticamente por `Producto_ID`, `Lote_ID` y `Sucursal`.
        """)
