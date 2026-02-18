import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import calendar
import pytz
import io
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# 1. CONFIGURACIÓN PREMIUM + CSS
# =============================================================================
st.set_page_config(page_title="🛡️ Command Center: Riesgo de Inventario", layout="wide", page_icon="📊")

def cargar_css_premium():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main { background: linear-gradient(135deg, #f8f9fb 0%, #eef2f7 100%); }
    .executive-card {
        background: white; padding: 25px; border-radius: 16px;
        box-shadow: 0 4px 20px rgba(26,35,126,0.12); border-top: 5px solid #1a237e;
        text-align: center; margin: 10px 0; transition: all 0.3s ease;
        border: 1px solid rgba(26,35,126,0.08);
    }
    .executive-card:hover { transform: translateY(-4px); box-shadow: 0 8px 30px rgba(26,35,126,0.2); }
    .metric-value { font-size: 34px; font-weight: 800; color: #1a237e; letter-spacing: -1px; line-height: 1.1; }
    .metric-label { font-size: 12px; color: #666; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
    .metric-sub { font-size: 11px; color: #888; margin-top: 4px; font-weight: 500; }
    .plan-box {
        background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
        padding: 30px; border-radius: 16px; border-left: 8px solid #f57c00;
        box-shadow: 0 4px 20px rgba(245,124,0,0.15); margin: 25px 0;
        border: 1px solid rgba(245,124,0,0.2);
    }
    .risk-badge {
        display: inline-flex; align-items: center; padding: 6px 16px;
        border-radius: 20px; font-size: 12px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.5px; margin: 3px;
    }
    .risk-vencido { background: #f3e5f5; color: #7b1fa2; border: 2px solid #9c27b0; }
    .risk-critico { background: #ffebee; color: #c62828; border: 2px solid #d32f2f; }
    .risk-urgente { background: #fff3e0; color: #e65100; border: 2px solid #f57c00; }
    .risk-preventivo { background: #fffde7; color: #f9a825; border: 2px solid #fbc02d; }
    .risk-normal { background: #e8f5e9; color: #2e7d32; border: 2px solid #4caf50; }
    .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    .section-header { color: #1a237e; font-weight: 800; font-size: 1.6rem; margin: 40px 0 20px 0; padding-bottom: 12px; border-bottom: 3px solid #1a237e; display: flex; align-items: center; gap: 12px; }
    .dataframe { border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); font-size: 0.9rem; }
    .dataframe thead th { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; font-weight: 700; padding: 14px; border: none; }
    .stButton>button { border-radius: 10px; font-weight: 600; transition: all 0.2s; border: 2px solid #1a237e; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(26,35,126,0.3); }
    .timeline { display: flex; justify-content: space-between; margin: 20px 0; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .timeline-item { text-align: center; flex: 1; position: relative; padding: 0 10px; }
    .timeline-item:not(:last-child)::after { content: ''; position: absolute; top: 25px; right: -50%; width: 100%; height: 2px; background: #e0e0e0; z-index: 0; }
    .timeline-dot { width: 14px; height: 14px; border-radius: 50%; margin: 0 auto 8px; background: #667eea; position: relative; z-index: 1; }
    .timeline-time { font-size: 12px; font-weight: 700; color: #1a237e; }
    .timeline-action { font-size: 11px; color: #666; }
    </style>
    """, unsafe_allow_html=True)

cargar_css_premium()

# =============================================================================
# 2. FORMATO Y CONSTANTES (Chile Standard)
# =============================================================================
def clp(valor):
    """Formatea a moneda chilena: $1.234.567"""
    if pd.isna(valor) or valor is None: return "$0"
    try:
        v = int(round(float(valor)))
        return f"${v:,}".replace(",", ".")
    except: return "$0"

# =============================================================================
# 3. LÓGICA DE CLASIFICACIÓN - VENTANA MENSUAL INTELIGENTE
# =============================================================================
def clasificar_riesgo_mensual(dias, fecha_hoy, fecha_inicio_mes, fecha_fin_mes):
    """
    Clasificación de riesgo con lógica de ventana mensual CORREGIDA:
    
    ✅ CASO BASE: Si hoy es 15-Feb → ventana = 01-Feb al 28-Feb
    ✅ CASO ESPECIAL: Si hoy es 28-Feb → ventana = 01-Feb al 28-Feb (NO incluye marzo)
    ✅ PRODUCTOS FUERA DE VENTANA: Se excluyen del análisis de riesgo inmediato
    
    Mantiene distancias originales ancladas a HOY:
    - VENCIDO: ≤0 días desde hoy (vence hoy o antes)
    - CRÍTICO: 1-3 días desde hoy
    - URGENTE: 4-7 días desde hoy  
    - PREVENTIVO: 8-30 días desde hoy (pero SOLO si vence dentro del mes)
    """
    if pd.isna(dias): return 'SIN_DATO'
    
    # Calcular fecha real de vencimiento
    fecha_vencimiento = fecha_hoy + timedelta(days=int(dias))
    
    # ✅ FILTRO CLAVE: Solo analizar productos que vencen DENTRO del mes actual
    if not (fecha_inicio_mes <= fecha_vencimiento <= fecha_fin_mes):
        return 'FUERA_VENTANA'
    
    # Clasificación manteniendo distancias originales ancladas a HOY
    if dias <= 0: return 'VENCIDO'           # 🟣 Hoy o antes
    elif dias <= 3: return 'CRITICO'          # 🔴 1-3 días desde hoy
    elif dias <= 7: return 'URGENTE'          # 🟠 4-7 días desde hoy
    elif dias <= 30: return 'PREVENTIVO'      # 🟡 8-30 días desde hoy (dentro del mes)
    else: return 'NORMAL'                     # 🟢 Más de 30 días

COLOR_MAP = {
    'VENCIDO': '#9c27b0', 'CRITICO': '#d32f2f', 'URGENTE': '#f57c00',
    'PREVENTIVO': '#fbc02d', 'NORMAL': '#2e7d32', 'SIN_DATO': '#9e9e9e', 'FUERA_VENTANA': '#bdbdbd'
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
    'Fecha_Movimiento': ['Fecha_Movimiento', 'Fecha', 'Fecha_Transaccion'],
    'Producto_ID': ['Producto_ID', 'ID_Producto'],
    'Lote_ID': ['Lote_ID', 'ID_Lote'],
    'Categoria': ['Categoria', 'Categoría', 'Category'],
    'Categoria_Rotacion': ['Categoria_Rotacion', 'Rotacion', 'Categoria_Rotación']
}

# =============================================================================
# 4. MOTOR ETL INTELIGENTE
# =============================================================================
@st.cache_data(ttl=300)
def cargar_archivo_inteligente(archivo):
    try:
        df = pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Error cargando {archivo.name}: {str(e)}")
        return None

def detectar_tipo_archivo(df):
    cols = set(df.columns)
    if {'Latitud', 'Longitud', 'ID_Ciudad'}.issubset(cols) and 'Stock_Teorico_Unidades' not in cols:
        return 'sucursales'
    elif {'Categoria', 'Producto_ID', 'Dias_Caducidad_Base'}.issubset(cols) and 'Lote_ID' not in cols:
        return 'productos'
    elif {'Tipo_Movimiento', 'Lote_ID', 'Fecha_Movimiento'}.issubset(cols):
        return 'inventario_movimientos'
    elif {'Fecha_Creacion_Lote', 'Lote_ID', 'Dias_Caducidad_Base'}.issubset(cols):
        return 'lotes'
    elif {'Stock_Teorico_Unidades', 'Latitud', 'Lote_ID'}.issubset(cols) or {'Dias_Para_Vencer', 'Stock_Teorico_Unidades'}.issubset(cols):
        return 'stock_geo'
    return 'desconocido'

def mapear_columnas(df):
    """Mapeo inteligente de columnas según diccionario"""
    for col_destino, col_posibles in COLUMNAS_ESPERADAS.items():
        for col_posible in col_posibles:
            if col_posible in df.columns and col_destino not in df.columns:
                df.rename(columns={col_posible: col_destino}, inplace=True)
                break
    return df

# =============================================================================
# 5. LÓGICA DE VENTANA MENSUAL CORREGIDA (Core Request)
# =============================================================================
def obtener_ventana_mensual(fecha_referencia):
    """
    Calcula la ventana de análisis mensual CORREGIDA:
    
    ✅ Si hoy es 15-Feb-2026 → ventana = 01-Feb-2026 a 28-Feb-2026
    ✅ Si hoy es 28-Feb-2026 → ventana = 01-Feb-2026 a 28-Feb-2026 (NO marzo)
    ✅ Si hoy es 01-Mar-2026 → ventana = 01-Mar-2026 a 31-Mar-2026
    
    La ventana SIEMPRE es: [1 del mes actual] hasta [último día del mes actual]
    """
    inicio_mes = fecha_referencia.replace(day=1)
    ultimo_dia = calendar.monthrange(fecha_referencia.year, fecha_referencia.month)[1]
    fin_mes = fecha_referencia.replace(day=ultimo_dia)
    return inicio_mes, fin_mes

def filtrar_por_ventana_mensual(df, fecha_hoy, columna_fecha_venc):
    """
    Filtra productos cuya fecha de vencimiento cae DENTRO del mes actual,
    manteniendo la clasificación por días relativos a hoy.
    """
    inicio_mes, fin_mes = obtener_ventana_mensual(fecha_hoy)
    
    # Convertir a datetime si es string
    if df[columna_fecha_venc].dtype == 'object':
        df[columna_fecha_venc] = pd.to_datetime(df[columna_fecha_venc], errors='coerce')
    
    # Filtrar por ventana mensual: productos que vencen entre inicio_mes y fin_mes
    mask_ventana = (df[columna_fecha_venc] >= inicio_mes) & (df[columna_fecha_venc] <= fin_mes)
    df_filtrado = df[mask_ventana].copy()
    
    # Calcular días efectivos desde hoy para clasificación (pueden ser negativos si ya venció)
    df_filtrado['Dias_Efectivos'] = (df_filtrado[columna_fecha_venc] - fecha_hoy).dt.days
    
    return df_filtrado, inicio_mes, fin_mes

# =============================================================================
# 6. SIDEBAR: PANEL DE CONTROL
# =============================================================================
with st.sidebar:
    st.title("🎛️ Panel de Control")
    st.markdown("---")
    
    st.subheader("📁 Archivos Maestros")
    uploaded_files = st.file_uploader(
        "Arrastra los 5 archivos CSV", type="csv", accept_multiple_files=True,
        help="• 1_SUCURSALES_MASTER.csv\n• 2_PRODUCTOS_MASTER.csv\n• 3_LOTES_PRODUCTOS.csv\n• 4_INVENTARIO_COMPLETO.csv\n• 5_STOCK_ACTUAL_GEO.csv"
    )
    
    if uploaded_files:
        progreso = min(len(uploaded_files) / 5, 1.0)
        st.progress(progreso)
        st.caption(f"✅ {len(uploaded_files)}/5 archivos cargados")
    
    st.markdown("---")
    st.subheader("⚙️ Configuración de Ventana")
    
    # Mostrar fecha de referencia y ventana calculada
    tz_cl = pytz.timezone('America/Santiago')
    fecha_hoy_ui = datetime.now(tz_cl).replace(tzinfo=None)
    inicio_mes_ui, fin_mes_ui = obtener_ventana_mensual(fecha_hoy_ui)
    
    st.info(f"""
    📅 **Ventana de Análisis Mensual**
    
    • Hoy: {fecha_hoy_ui.strftime('%d/%m/%Y')}
    • Inicio mes: {inicio_mes_ui.strftime('%d/%m/%Y')}
    • Fin mes: {fin_mes_ui.strftime('%d/%m/%Y')}
    
    ✅ Solo productos que vencen DENTRO de esta ventana serán clasificados como riesgo.
    ✅ La clasificación (Vencido/Crítico/Urgente) se calcula RELATIVO a HOY.
    """)
    
    incluir_fuera_ventana = st.checkbox(
        "🔍 Mostrar productos fuera de ventana (referencia)", value=False,
        help="Incluir productos que vencen fuera del mes actual como contexto adicional"
    )
    
    st.markdown("---")
    st.subheader("⚡ Acciones")
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# =============================================================================
# 7. PROCESAMIENTO PRINCIPAL CON LÓGICA MENSUAL CORREGIDA
# =============================================================================
if uploaded_files:
    data = {}
    
    # Cargar y clasificar archivos
    for file in uploaded_files:
        df_temp = cargar_archivo_inteligente(file)
        if df_temp is not None:
            df_temp = mapear_columnas(df_temp)
            tipo = detectar_tipo_archivo(df_temp)
            data[tipo] = df_temp
            st.sidebar.success(f"✅ {tipo}: {len(df_temp)} registros")
    
    # Validar archivos esenciales
    if 'stock_geo' in data or 'inventario_movimientos' in data:
        try:
            with st.spinner("🔄 Procesando inteligencia de inventario con ventana mensual..."):
                
                # ========================================
                # CONSOLIDACIÓN ETL
                # ========================================
                df_base = data.get('stock_geo')
                if df_base is None or (hasattr(df_base, 'empty') and df_base.empty):
                    df_base = data.get('inventario_movimientos')
                
                if df_base is None or df_base.empty:
                    st.error("❌ No se encontró archivo de stock o inventario válido")
                    st.stop()
                
                # Merge con sucursales
                if 'sucursales' in data and 'Sucursal' in df_base.columns:
                    df_base = df_base.merge(
                        data['sucursales'][['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']],
                        on='Sucursal', how='left'
                    )
                
                # Merge con productos
                if 'productos' in data and 'Producto_ID' in df_base.columns:
                    df_base = df_base.merge(
                        data['productos'][['Producto_ID', 'Categoria', 'Categoria_Rotacion']],
                        on='Producto_ID', how='left'
                    )
                
                # ========================================
                # 🎯 LÓGICA DE VENTANA MENSUAL (Core Corregido)
                # ========================================
                tz_cl = pytz.timezone('America/Santiago')
                fecha_hoy = datetime.now(tz_cl).replace(tzinfo=None)
                
                # Determinar columna de fecha de vencimiento disponible
                col_fecha_venc = None
                if 'Fecha_Vencimiento_Lote' in df_base.columns:
                    col_fecha_venc = 'Fecha_Vencimiento_Lote'
                elif 'Fecha_Vencimiento' in df_base.columns:
                    col_fecha_venc = 'Fecha_Vencimiento'
                
                if col_fecha_venc:
                    # Aplicar filtro de ventana mensual + cálculo de días efectivos
                    df_base, inicio_mes, fin_mes = filtrar_por_ventana_mensual(
                        df_base, fecha_hoy, col_fecha_venc
                    )
                    
                    # Clasificación de riesgo con lógica mensual CORREGIDA
                    df_base['Riesgo_BI'] = df_base['Dias_Efectivos'].apply(
                        lambda d: clasificar_riesgo_mensual(d, fecha_hoy, inicio_mes, fin_mes)
                    )
                    
                elif 'Dias_Para_Vencer' in df_base.columns:
                    # Fallback: usar días directos con filtro de ventana
                    df_base['Dias_Efectivos'] = pd.to_numeric(df_base['Dias_Para_Vencer'], errors='coerce').fillna(0)
                    
                    # Calcular fecha de vencimiento para filtro mensual
                    df_base['Fecha_Venc_Calc'] = fecha_hoy + pd.to_timedelta(df_base['Dias_Efectivos'], unit='D')
                    inicio_mes, fin_mes = obtener_ventana_mensual(fecha_hoy)
                    
                    # Filtrar por ventana mensual
                    mask_ventana = (df_base['Fecha_Venc_Calc'] >= inicio_mes) & (df_base['Fecha_Venc_Calc'] <= fin_mes)
                    if not incluir_fuera_ventana:
                        df_base = df_base[mask_ventana].copy()
                    
                    # Clasificación
                    df_base['Riesgo_BI'] = df_base['Dias_Efectivos'].apply(
                        lambda d: clasificar_riesgo_mensual(d, fecha_hoy, inicio_mes, fin_mes)
                    )
                else:
                    st.warning("⚠️ No se encontró columna de fecha de vencimiento. Usando clasificación básica.")
                    df_base['Dias_Efectivos'] = 0
                    df_base['Riesgo_BI'] = 'SIN_DATO'
                    inicio_mes, fin_mes = obtener_ventana_mensual(fecha_hoy)
                
                # ========================================
                # CÁLCULO DE VALOR MONETARIO
                # ========================================
                if 'Valor_Unitario_CLP' in df_base.columns and 'Stock_Teorico_Unidades' in df_base.columns:
                    df_base['Valor_Costo_Total'] = (
                        df_base['Stock_Teorico_Unidades'].fillna(0) * 
                        df_base['Valor_Unitario_CLP'].fillna(0)
                    )
                elif 'Precio_Venta_CLP' in df_base.columns:
                    df_base['Valor_Costo_Total'] = (
                        df_base['Stock_Teorico_Unidades'].fillna(0) * 
                        df_base['Precio_Venta_CLP'].fillna(0) * 0.70
                    )
                else:
                    df_base['Valor_Costo_Total'] = df_base['Stock_Teorico_Unidades'].fillna(0) * 1000  # Estimado
                
                # ========================================
                # FILTROS INTERACTIVOS
                # ========================================
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    sucursales_disp = df_base['Sucursal'].dropna().unique() if 'Sucursal' in df_base.columns else []
                    sel_suc = st.multiselect("🏪 Sucursales", sucursales_disp, default=sucursales_disp[:3] if len(sucursales_disp)>0 else [], key="filter_suc")
                
                with col_f2:
                    categorias_disp = df_base['Categoria'].dropna().unique() if 'Categoria' in df_base.columns else []
                    sel_cat = st.multiselect("📦 Categorías", categorias_disp, default=categorias_disp, key="filter_cat")
                
                with col_f3:
                    riesgos_disp = [r for r in COLOR_MAP.keys() if r in df_base['Riesgo_BI'].values and r not in ['FUERA_VENTANA', 'SIN_DATO']]
                    sel_risk = st.multiselect("⚠️ Nivel de Riesgo", riesgos_disp, default=['VENCIDO', 'CRITICO', 'URGENTE'], key="filter_risk")
                
                # Aplicar filtros
                df_f = df_base.copy()
                if sel_suc and 'Sucursal' in df_f.columns: df_f = df_f[df_f['Sucursal'].isin(sel_suc)]
                if sel_cat and 'Categoria' in df_f.columns: df_f = df_f[df_f['Categoria'].isin(sel_cat)]
                if sel_risk: df_f = df_f[df_f['Riesgo_BI'].isin(sel_risk)]
                
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
                            <h2 style="margin: 0; font-size: 1.8rem;">📊 Inteligencia Mensual</h2>
                            <p style="margin: 5px 0 0 0; opacity: 0.9;">
                                🕒 Actualizado: {datetime.now(tz_cl).strftime('%d/%m/%Y %H:%M')} CLT | 
                                📅 Ventana: {inicio_mes.strftime('%d/%m')} al {fin_mes.strftime('%d/%m/%Y')}
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
                # KPIs EJECUTIVOS (Solo ventana mensual)
                # ========================================
                # Excluir FUERA_VENTANA y SIN_DATO de cálculos principales
                df_riesgo = df_f[df_f['Riesgo_BI'].isin(['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO'])].copy()
                
                val_total = df_riesgo["Valor_Costo_Total"].sum()
                venc_val = df_riesgo[df_riesgo['Riesgo_BI'] == 'VENCIDO']['Valor_Costo_Total'].sum()
                crit_val = df_riesgo[df_riesgo['Riesgo_BI'] == 'CRITICO']['Valor_Costo_Total'].sum()
                urg_val = df_riesgo[df_riesgo['Riesgo_BI'] == 'URGENTE']['Valor_Costo_Total'].sum()
                unid_alerta = int(df_riesgo["Stock_Teorico_Unidades"].sum())
                
                # Cálculos de recuperación (Ley 19.885 Chile)
                credito_fiscal = venc_val * 0.27
                recuperacion_crit = crit_val * 0.50
                recuperacion_urg = urg_val * 0.40
                total_recuperable = credito_fiscal + recuperacion_crit + recuperacion_urg
                
                k1, k2, k3, k4 = st.columns(4)
                
                with k1:
                    st.markdown(f'''
                    <div class="executive-card">
                        <span class="metric-label">💰 Monto Total en Riesgo (Mes)</span>
                        <div class="metric-value">{clp(val_total)}</div>
                        <div class="metric-sub">{len(df_riesgo)} productos • {unid_alerta:,} unidades</div>
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
                    pct_rec = (total_recuperable/val_total*100) if val_total>0 else 0
                    st.markdown(f'''
                    <div class="executive-card" style="border-top-color: #4caf50;">
                        <span class="metric-label">✅ Total Recuperable</span>
                        <div class="metric-value" style="color:#2e7d32;">{clp(total_recuperable)}</div>
                        <div class="metric-sub">{pct_rec:.1f}% del riesgo mensual</div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # ========================================
                # MAPA GEOGRÁFICO CON FILTRO MENSUAL
                # ========================================
                st.markdown('<h2 class="section-header">🌐 Riesgo por Sucursal (Ventana Mensual)</h2>', unsafe_allow_html=True)
                
                if 'Latitud' in df_riesgo.columns and 'Longitud' in df_riesgo.columns and df_riesgo['Latitud'].notna().any():
                    df_map = df_riesgo.groupby(['Sucursal', 'Latitud', 'Longitud']).agg({
                        'Valor_Costo_Total': 'sum', 'Stock_Teorico_Unidades': 'sum',
                        'Riesgo_BI': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'NORMAL',
                        'Dias_Efectivos': 'mean'
                    }).reset_index()
                    
                    fig_map = px.scatter_mapbox(
                        df_map, lat="Latitud", lon="Longitud", size="Valor_Costo_Total", size_max=40,
                        color="Riesgo_BI", color_discrete_map=COLOR_MAP, hover_name="Sucursal",
                        hover_data={"Valor_Costo_Total": ":$.0f", "Stock_Teorico_Unidades": ":,.0f", "Dias_Efectivos": ":.1f"},
                        zoom=9, height=500, mapbox_style="carto-positron", center={"lat": -33.45, "lon": -70.65}
                    )
                    fig_map.update_layout(margin={"r":0,"t":10,"l":0,"b":0}, legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99))
                    st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True})
                    
                    with st.expander("📋 Detalle por Sucursal", expanded=False):
                        resumen_suc = df_riesgo.groupby('Sucursal').agg({
                            'Valor_Costo_Total': 'sum', 'Stock_Teorico_Unidades': 'sum',
                            'Producto': 'count' if 'Producto' in df_riesgo.columns else 'first',
                            'Dias_Efectivos': 'mean'
                        }).round(0).sort_values('Valor_Costo_Total', ascending=False)
                        st.dataframe(resumen_suc.style.format({'Valor_Costo_Total': clp, 'Stock_Teorico_Unidades': '{:,.0f}', 'Dias_Efectivos': '{:.1f}'}), use_container_width=True)
                else:
                    st.info("📍 Coordenadas no disponibles. Verifica archivos de sucursales/stock.")
                
                # ========================================
                # PLAN DE ACCIÓN ESTRATÉGICO
                # ========================================
                st.markdown(f'''
                <div class="plan-box">
                    <h3 style="margin-top:0; color:#1a237e; display:flex; align-items:center; gap:10px;">
                        📋 Plan de Acción - Ventana Mensual ({inicio_mes.strftime('%b')} {inicio_mes.year})
                    </h3>
                    <p style="margin-bottom:20px;">
                        Acciones prioritarias para mitigar pérdida de <b>{clp(val_total)}</b> en riesgo <b>dentro del mes actual</b>:
                    </p>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px;">
                        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #9c27b0;">
                            <strong style="color:#7b1fa2;">🟣 VENCIDOS ({int(df_riesgo[df_riesgo['Riesgo_BI']=='VENCIDO']['Producto'].nunique() if 'Producto' in df_riesgo.columns else 0)})</strong><br>
                            <small>→ Donación inmediata para crédito fiscal 27% (Ley 19.885)</small>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #d32f2f;">
                            <strong style="color:#c62828;">🔴 CRÍTICOS ({int(df_riesgo[df_riesgo['Riesgo_BI']=='CRITICO']['Producto'].nunique() if 'Producto' in df_riesgo.columns else 0)})</strong><br>
                            <small>→ Liquidación FEFO con 40-60% descuento (1-3 días)</small>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #f57c00;">
                            <strong style="color:#e65100;">🟠 URGENTES ({int(df_riesgo[df_riesgo['Riesgo_BI']=='URGENTE']['Producto'].nunique() if 'Producto' in df_riesgo.columns else 0)})</strong><br>
                            <small>→ Transferencia a sedes de alto tráfico (4-7 días)</small>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #fbc02d;">
                            <strong style="color:#f9a825;">🟡 PREVENTIVOS ({int(df_riesgo[df_riesgo['Riesgo_BI']=='PREVENTIVO']['Producto'].nunique() if 'Producto' in df_riesgo.columns else 0)})</strong><br>
                            <small>→ Monitoreo diario y promoción temprana (8-30 días)</small>
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
                            <div class="timeline-action">Activar descuentos críticos</div>
                        </div>
                        <div class="timeline-item">
                            <div class="timeline-dot" style="background:#fbc02d;"></div>
                            <div class="timeline-time">MAÑANA</div>
                            <div class="timeline-action">Revisar preventivos</div>
                        </div>
                        <div class="timeline-item">
                            <div class="timeline-dot" style="background:#2e7d32;"></div>
                            <div class="timeline-time">FIN MES</div>
                            <div class="timeline-action">Cierre y reporte</div>
                        </div>
                    </div>
                    
                    <div style="background: #e8f5e9; padding: 15px; border-radius: 10px; text-align: center;">
                        <strong style="color: #2e7d32; font-size: 1.2rem;">
                            💰 Proyección de Recuperación Mensual: {clp(total_recuperable)} CLP
                        </strong>
                        <br><small style="color: #666;">Incluye crédito fiscal + liquidación estimada • Ventana: {inicio_mes.strftime('%d/%m')} al {fin_mes.strftime('%d/%m')}</small>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                # ========================================
                # GRÁFICOS DE PROFUNDIDAD
                # ========================================
                st.markdown('<h2 class="section-header">🔍 Análisis de Profundidad (Ventana Mensual)</h2>', unsafe_allow_html=True)
                
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Valor por Categoría", "📉 Días vs Stock", "📍 Top Sucursales", "📑 Auditoría"])
                
                with tab1:
                    if len(df_riesgo) > 0 and 'Categoria' in df_riesgo.columns:
                        fig1 = px.bar(df_riesgo, x="Categoria", y="Valor_Costo_Total", color="Riesgo_BI", 
                                     color_discrete_map=COLOR_MAP, barmode="group", text_auto='.2s',
                                     title=f"Distribución del valor en riesgo - {inicio_mes.strftime('%B %Y')}")
                        fig1.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig1, use_container_width=True)
                    else:
                        st.info("📊 Sin datos para visualizar")
                
                with tab2:
                    if len(df_riesgo) > 0 and 'Dias_Efectivos' in df_riesgo.columns:
                        fig2 = px.scatter(df_riesgo, x="Dias_Efectivos", y="Stock_Teorico_Unidades", 
                                         size="Valor_Costo_Total", color="Riesgo_BI", color_discrete_map=COLOR_MAP,
                                         hover_name="Producto" if 'Producto' in df_riesgo.columns else None,
                                         title="Tamaño = Valor Monetario • Línea roja = Hoy")
                        fig2.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="HOY")
                        fig2.update_layout(height=400)
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("📊 Sin datos para visualizar")
                
                with tab3:
                    if 'Sucursal' in df_riesgo.columns and len(df_riesgo) > 0:
                        top_suc = df_riesgo.groupby('Sucursal')['Valor_Costo_Total'].sum().sort_values(ascending=False).head(10).reset_index()
                        fig3 = px.bar(top_suc, x='Sucursal', y='Valor_Costo_Total', color='Valor_Costo_Total', 
                                     color_continuous_scale='YlOrRd', text_auto='.3s',
                                     title="Top 10 Sucursales con Mayor Exposición Mensual")
                        fig3.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig3, use_container_width=True)
                    else:
                        st.info("📊 Sin datos de sucursales disponibles")
                
                with tab4:
                    if len(df_riesgo) > 0:
                        cols_show = [c for c in ['Riesgo_BI', 'Producto', 'Sucursal', 'Dias_Efectivos', 
                                                'Stock_Teorico_Unidades', 'Valor_Costo_Total', 'Categoria'] 
                                   if c in df_riesgo.columns]
                        
                        def badge_riesgo(val):
                            color_class = f"risk-{val.lower()}" if val in COLOR_MAP else "risk-normal"
                            return f'<span class="risk-badge {color_class}">{val}</span>'
                        
                        df_display = df_riesgo[cols_show].sort_values('Dias_Efectivos' if 'Dias_Efectivos' in cols_show else cols_show[0])
                        
                       
                        estilos_riesgo = {
                            'VENCIDO': {'background-color': '#f3e5f5', 'color': '#7b1fa2', 'font-weight': '600'},
                            'CRITICO': {'background-color': '#ffebee', 'color': '#c62828', 'font-weight': '600'},
                            'URGENTE': {'background-color': '#fff3e0', 'color': '#e65100', 'font-weight': '600'},
                            'PREVENTIVO': {'background-color': '#fffde7', 'color': '#f9a825', 'font-weight': '600'}
                        }
                        
                        # Aplicar estilos dinámicamente
                        styled_df = df_display.copy()
                        for nivel, estilo in estilos_riesgo.items():
                            mask = df_display['Nivel_Riesgo'] == nivel
                            for col in df_display.columns:
                                styled_df.loc[mask, col] = styled_df.loc[mask, col].apply(
                                    lambda x: f'<span style="{"; ".join(f"{k}: {v}" for k, v in estilo.items())}">{x}</span>' if pd.notna(x) else x
                                )
                        
                        st.dataframe(
                            styled_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        csv = df_display.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 Descargar Auditoría Mensual (CSV)",
                            data=csv,
                            file_name=f"auditoria_riesgo_{fecha_hoy.strftime('%Y%m')}.csv",
                            mime="text/csv"  # ✅ Quité use_container_width=True
                        )
                        
                    else:
                        st.info("📊 Sin datos para auditar")
                
                # ========================================
                # FOOTER
                # ========================================
                st.markdown("---")
                st.caption(f"""
                🛡️ **Command Center v2.2** • Generado: {datetime.now(tz_cl).strftime('%d/%m/%Y %H:%M:%S')} CLT  
                📅 Ventana de análisis: {inicio_mes.strftime('%d/%m/%Y')} al {fin_mes.strftime('%d/%m/%Y')}  
                📁 Fuentes: {', '.join([f.name for f in uploaded_files])} • Registros en ventana: {len(df_riesgo):,}
                """)
                
        except Exception as e:
            st.error(f"❌ Error en procesamiento: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Detalles técnicos del error"):
                st.exception(e)
    
    else:
        st.info("👋 **Bienvenido al Command Center**\n\nPor favor, carga al menos el archivo de **Stock Actual** o **Inventario Completo** para activar el análisis de inteligencia.")

else:
    # Pantalla de bienvenida
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <h1 style="color: #1a237e; margin-bottom: 20px;">🛡️ Command Center: Riesgo de Inventario</h1>
        <p style="font-size: 1.2rem; color: #666; max-width: 600px; margin: 0 auto 30px;">
            Plataforma de inteligencia estratégica para gestión proactiva de caducidad de inventario con análisis mensual.
        </p>
        <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
            <span class="risk-badge risk-vencido">🟣 Vencido (≤0 días)</span>
            <span class="risk-badge risk-critico">🔴 Crítico (1-3 días)</span>
            <span class="risk-badge risk-urgente">🟠 Urgente (4-7 días)</span>
            <span class="risk-badge risk-preventivo">🟡 Preventivo (8-30 días)</span>
        </div>
        <p style="margin-top: 40px; color: #888; font-weight: 500;">
            ✨ <b>Nuevo:</b> Análisis acotado al mes actual • Ej: Si hoy es 15/Feb → ventana 01/Feb al 28/Feb
        </p>
        <p style="margin-top: 20px; color: #888;">← Sube tus archivos en el panel lateral para comenzar</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📋 Estructura esperada de archivos"):
        st.markdown("""
        | Archivo | Columnas Clave | Propósito |
        |---------|---------------|-----------|
        | `1_SUCURSALES_MASTER.csv` | Sucursal, Latitud, Longitud, ID_Ciudad | Geolocalización de sedes |
        | `2_PRODUCTOS_MASTER.csv` | Producto_ID, Categoria, Categoria_Rotacion | Catálogo maestro |
        | `3_LOTES_PRODUCTOS.csv` | Lote_ID, Producto_ID, Fecha_Creacion_Lote | Trazabilidad de lotes |
        | `4_INVENTARIO_COMPLETO.csv` | Lote_ID, Sucursal, Tipo_Movimiento, Fecha_Movimiento | Historial de movimientos |
        | `5_STOCK_ACTUAL_GEO.csv` | Lote_ID, Stock_Teorico_Unidades, Valor_Unitario_CLP, Latitud | Snapshot actual con geo |
        
        > 💡 **Lógica de Ventana Mensual Corregida**: 
        > - Si hoy es **15 de febrero 2026**, el análisis incluye productos que vencen entre **01/02/2026 y 28/02/2026**
        > - Si hoy es **28 de febrero 2026**, el análisis incluye productos que vencen entre **01/02/2026 y 28/02/2026** (NO marzo)
        > - Dentro de esa ventana, se mantiene la clasificación original ANCLADA A HOY: 
        >   - 🟣 **VENCIDO**: ≤0 días desde hoy (vence hoy o antes)
        >   - 🔴 **CRÍTICO**: 1-3 días desde hoy  
        >   - 🟠 **URGENTE**: 4-7 días desde hoy
        >   - 🟡 **PREVENTIVO**: 8-30 días desde hoy (pero SOLO si vence dentro del mes)
        > - Productos que vencen fuera del mes se excluyen del análisis de riesgo inmediato
        """)
