import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
import calendar
import textwrap
import warnings
import io
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pytz
warnings.filterwarnings('ignore')

# =============================================================================
# FORMATO CHILENO
# =============================================================================
def clp(valor):
    """Formatea número con estilo chileno: 1.234.567"""
    if isinstance(valor, str):
        return valor
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "$0"
    try:
        valor_int = int(round(float(valor)))
        return f"${valor_int:,}".replace(",", ".")
    except:
        return str(valor)

def pct(valor):
    """Formatea porcentaje"""
    if valor is None or pd.isna(valor):
        return "0%"
    return f"{valor:.1f}%"

pd.options.display.float_format = lambda x: f'{x:,.0f}'.replace(',', '.')

# =============================================================================
# COLORES SEMÁFORO COHERENTES
# =============================================================================
COLOR_MAP = {
    'VENCIDO': '#9c27b0',
    'CRITICO': '#d32f2f',
    'URGENTE': '#f57c00',
    'PREVENTIVO': '#fbc02d',
    'NORMAL': '#2e7d32'
}

# =============================================================================
# CSS PERSONALIZADO - ESTILO BI PREMIUM
# =============================================================================
def cargar_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    .main { background: linear-gradient(135deg, #f8f9fb 0%, #eef2f7 100%); }
    
    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border-top: 5px solid #1a237e;
        transition: all 0.3s ease;
    }
    .kpi-card:hover { transform: translateY(-5px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }
    
    .kpi-value { font-size: 2.5rem; font-weight: 800; color: #1a237e; line-height: 1.1; }
    .kpi-label { font-size: 0.9rem; color: #666; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-delta { font-size: 0.85rem; margin-top: 8px; font-weight: 600; }
    .delta-positive { color: #2e7d32; }
    .delta-negative { color: #c62828; }
    
    .section-header {
        color: #1a237e;
        font-weight: 800;
        font-size: 1.6rem;
        margin: 40px 0 20px 0;
        padding-bottom: 12px;
        border-bottom: 3px solid #1a237e;
    }
    
    .classification-item {
        padding: 18px;
        margin: 12px 0;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .vencido { background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%); color: #7b1fa2; border-left: 5px solid #9c27b0; }
    .critico { background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); color: #c62828; border-left: 5px solid #d32f2f; }
    .urgente { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); color: #e65100; border-left: 5px solid #f57c00; }
    .preventivo { background: linear-gradient(135deg, #fffde7 0%, #fff9c4 100%); color: #f9a825; border-left: 5px solid #fbc02d; }
    .normal { background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); color: #2e7d32; border-left: 5px solid #2e7d32; }
    
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        font-size: 0.9rem;
    }
    .dataframe thead th {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        font-weight: 700;
        padding: 15px;
    }
    
    .insight-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        border-left: 5px solid #1976d2;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        border-left: 5px solid #f57c00;
    }
    
    .success-box {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        border-left: 5px solid #2e7d32;
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# FUNCIONES DE CARGA DE ARCHIVOS
# =============================================================================
@st.cache_data(ttl=300)
def cargar_archivo(archivo):
    """Carga un archivo CSV"""
    try:
        df = pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error al cargar {archivo.name}: {str(e)}")
        return None

def mapear_columnas(df):
    """Mapea columnas con nombres alternativos"""
    columnas_esperadas = {
        'Días_para_Vencimiento': ['Dias_Para_Vencer', 'Días_para_Vencimiento', 'Días para Vencimiento', 'Dias_Vencimiento'],
        'Stock_Inicial': ['Stock_Teorico_Unidades', 'Stock_Inicial', 'Stock Sala', 'Stock_Sala', 'Stock', 'Cantidad_Stock'],
        'Costo_Unitario_Neto': ['Valor_Unitario_CLP', 'Costo_Unitario_Neto', 'Costo Unitario Neto', 'costo_unitario_neto', 'Costo', 'Precio_Costo'],
        'Precio_Venta_Bruto': ['Precio_Venta_CLP', 'Precio_Venta_Bruto', 'Precio Venta Bruto', 'precio_venta_bruto', 'Precio'],
        'Producto': ['Producto', 'producto', 'SKU_Descripcion'],
        'Sucursal': ['Sucursal', 'sucursal', 'Tienda', 'Store'],
        'Categoria': ['Categoria', 'Categoría', 'Category'],
        'Lote_ID': ['Lote_ID', 'ID_Lote', 'Lote'],
        'Producto_ID': ['Producto_ID', 'ID_Producto', 'Producto'],
        'Latitud': ['Latitud', 'lat', 'Latitude', 'Lat'],
        'Longitud': ['Longitud', 'lon', 'Longitude', 'Lng', 'Long'],
        'Fecha_Movimiento': ['Fecha_Movimiento', 'Fecha', 'Fecha_Transaccion'],
        'Fecha_Vencimiento_Lote': ['Fecha_Vencimiento_Lote', 'Fecha_Vencimiento'],
        'Tipo_Movimiento': ['Tipo_Movimiento', 'Tipo', 'Movimiento'],
        'Cantidad_Entrada': ['Cantidad_Entrada', 'Entrada', 'Cantidad'],
        'Cantidad_Salida': ['Cantidad_Salida', 'Salida']
    }
    
    for col_destino, col_posibles in columnas_esperadas.items():
        for col_posible in col_posibles:
            if col_posible in df.columns and col_destino not in df.columns:
                df.rename(columns={col_posible: col_destino}, inplace=True)
                break
    return df

# =============================================================================
# FUNCIONES DE CLASIFICACIÓN Y CÁLCULO
# =============================================================================
def clasificar_riesgo(dias):
    """Clasifica el nivel de riesgo según días para vencimiento"""
    if pd.isna(dias):
        return 'SIN_DATO'
    elif dias < 0:
        return 'VENCIDO'
    elif dias <= 3:
        return 'CRITICO'
    elif dias <= 7:
        return 'URGENTE'
    elif dias <= 10:
        return 'PREVENTIVO'
    else:
        return 'NORMAL'

def calcular_valor_stock(df):
    """Calcula el valor del stock"""
    if 'Stock_Inicial' in df.columns:
        if 'Costo_Unitario_Neto' in df.columns:
            df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
        elif 'Precio_Venta_Bruto' in df.columns:
            df['Costo_Unitario_Neto'] = df['Precio_Venta_Bruto'] * 0.70
            df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
        else:
            df['Valor_Stock_Costo'] = df['Stock_Inicial'] * 1000
    return df

def aplicar_clasificacion(df):
    """Aplica clasificación de riesgo"""
    if 'Días_para_Vencimiento' in df.columns:
        df['Nivel_Riesgo'] = df['Días_para_Vencimiento'].apply(clasificar_riesgo)
    return df

# =============================================================================
# FUNCIONES DE ANÁLISIS BI
# =============================================================================
def calcular_kpis(df_riesgo):
    """Calcula KPIs principales para el dashboard"""
    kpis = {}
    
    # Total por nivel de riesgo
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO', 'NORMAL']:
        df_nivel = df_riesgo[df_riesgo['Nivel_Riesgo'] == nivel]
        kpis[f'{nivel}_productos'] = len(df_nivel)
        kpis[f'{nivel}_unidades'] = int(df_nivel['Stock_Inicial'].sum()) if 'Stock_Inicial' in df_nivel.columns else 0
        kpis[f'{nivel}_valor'] = df_nivel['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_nivel.columns else 0
    
    # Totales generales
    kpis['total_productos'] = len(df_riesgo)
    kpis['total_unidades'] = int(df_riesgo['Stock_Inicial'].sum()) if 'Stock_Inicial' in df_riesgo.columns else 0
    kpis['total_valor'] = df_riesgo['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
    
    # Porcentajes
    kpis['pct_vencido'] = (kpis['VENCIDO_productos'] / kpis['total_productos'] * 100) if kpis['total_productos'] > 0 else 0
    kpis['pct_critico'] = (kpis['CRITICO_productos'] / kpis['total_productos'] * 100) if kpis['total_productos'] > 0 else 0
    kpis['pct_recuperable'] = ((kpis['CRITICO_productos'] + kpis['URGENTE_productos'] + kpis['PREVENTIVO_productos']) / kpis['total_productos'] * 100) if kpis['total_productos'] > 0 else 0
    
    # Impacto financiero
    kpis['credito_tributario'] = kpis['VENCIDO_valor'] * 0.27
    kpis['perdida_potencial'] = kpis['VENCIDO_valor']
    kpis['recuperacion_potencial'] = (kpis['CRITICO_valor'] * 0.50) + (kpis['URGENTE_valor'] * 0.40)
    
    return kpis

def analizar_por_categoria(df_riesgo):
    """Analiza riesgo por categoría de producto"""
    if 'Categoria' not in df_riesgo.columns:
        return None
    
    analisis = df_riesgo.groupby('Categoria').agg({
        'Producto': 'count',
        'Stock_Inicial': 'sum',
        'Valor_Stock_Costo': 'sum'
    }).reset_index()
    analisis.rename(columns={'Producto': 'Cantidad_Productos'}, inplace=True)
    return analisis

def analizar_por_sucursal(df_riesgo):
    """Analiza riesgo por sucursal"""
    if 'Sucursal' not in df_riesgo.columns:
        return None
    
    analisis = df_riesgo.groupby('Sucursal').agg({
        'Producto': 'count',
        'Stock_Inicial': 'sum',
        'Valor_Stock_Costo': 'sum'
    }).reset_index()
    analisis.rename(columns={'Producto': 'Cantidad_Productos'}, inplace=True)
    return analisis

def analizar_tendencia_mensual(df_inventario):
    """Analiza tendencia de vencimientos por mes"""
    if 'Fecha_Movimiento' not in df_inventario.columns:
        return None
    
    df_inventario['Mes'] = pd.to_datetime(df_inventario['Fecha_Movimiento']).dt.to_period('M')
    tendencia = df_inventario.groupby('Mes').agg({
        'Stock_Inicial': 'sum',
        'Valor_Stock_Costo': 'sum'
    }).reset_index()
    return tendencia

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN
# =============================================================================
def mostrar_kpi_card(label, value, delta=None, delta_type='neutral'):
    """Muestra una tarjeta KPI"""
    delta_class = 'delta-positive' if delta_type == 'positive' else 'delta-negative' if delta_type == 'negative' else ''
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ''
    
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def crear_mapa_calor_riesgo(df_riesgo):
    """Crea mapa de calor de riesgo por sucursal"""
    if 'Sucursal' not in df_riesgo.columns or 'Latitud' not in df_riesgo.columns:
        return None
    
    # Agrupar por sucursal
    mapa_data = df_riesgo.groupby(['Sucursal', 'Latitud', 'Longitud']).agg({
        'Valor_Stock_Costo': 'sum',
        'Nivel_Riesgo': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'NORMAL'
    }).reset_index()
    
    # Crear mapa
    fig = px.scatter_mapbox(
        mapa_data,
        lat="Latitud",
        lon="Longitud",
        size="Valor_Stock_Costo",
        color="Nivel_Riesgo",
        color_discrete_map=COLOR_MAP,
        hover_name="Sucursal",
        hover_data={
            'Valor_Stock_Costo': ':$.0f',
            'Latitud': False,
            'Longitud': False
        },
        zoom=9,
        height=500,
        mapbox_style="carto-positron",
        center={"lat": -33.45, "lon": -70.65}
    )
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=True,
        legend_title="Nivel de Riesgo"
    )
    
    return fig

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal de la aplicación Streamlit"""
    st.set_page_config(
        page_title="BI - Gestión de Vencimientos",
        page_icon="📊",
        layout="wide"
    )
    cargar_css()
    
    # Título principal
    st.title("📊 BUSINESS INTELLIGENCE - Gestión de Vencimientos")
    st.markdown("### Dashboard Ejecutivo de Análisis de Inventario y Vencimientos")
    st.markdown("---")
    
    # =============================================================================
    # SIDEBAR - CARGA DE ARCHIVOS
    # =============================================================================
    with st.sidebar:
        st.header("📁 Carga de Datos")
        st.markdown("---")
        
        st.markdown("**Archivos del Sistema:**")
        
        archivo_sucursales = st.file_uploader(
            "1️⃣ Sucursales (1_SUCURSALES_MASTER.csv)",
            type=['csv'],
            help="Ubicaciones de tiendas con coordenadas GPS",
            key="uploader_sucursales"
        )
        
        archivo_productos = st.file_uploader(
            "2️⃣ Productos Master (2_PRODUCTOS_MASTER.csv)",
            type=['csv'],
            help="Catálogo maestro de productos con categorías",
            key="uploader_productos"
        )
        
        archivo_lotes = st.file_uploader(
            "3️⃣ Lotes (3_LOTES_PRODUCTOS.csv)",
            type=['csv'],
            help="Información de lotes y caducidad",
            key="uploader_lotes"
        )
        
        archivo_inventario = st.file_uploader(
            "4️⃣ Inventario Completo (4_INVENTARIO_COMPLETO_LOTES.csv)",
            type=['csv'],
            help="Histórico completo de movimientos de inventario",
            key="uploader_inventario"
        )
        
        archivo_stock = st.file_uploader(
            "5️⃣ Stock Actual (5_STOCK_ACTUAL_GEO_POWERBI.csv)",
            type=['csv'],
            help="Stock actual con ubicación geográfica",
            key="uploader_stock"
        )
        
        st.markdown("---")
        
        # Contador de archivos cargados
        archivos_cargados = sum([
            archivo_sucursales is not None,
            archivo_productos is not None,
            archivo_lotes is not None,
            archivo_inventario is not None,
            archivo_stock is not None
        ])
        
        st.progress(archivos_cargados / 5)
        st.caption(f"{archivos_cargados}/5 archivos cargados")
        
        # Filtros adicionales
        st.markdown("---")
        st.markdown("**Filtros de Análisis:**")
        
        mostrar_mapa = st.checkbox("🗺️ Mostrar Mapa Geográfico", value=True)
        mostrar_tendencias = st.checkbox("📈 Mostrar Tendencias", value=True)
        
        # Botón de ejecutar
        archivos_esenciales = archivo_stock is not None or archivo_inventario is not None
        
        if archivos_esenciales:
            boton_ejecutar = st.button("✅ Ejecutar Análisis BI", type="primary", use_container_width=True)
        else:
            st.warning("⚠️ Cargue al menos **Stock Actual** o **Inventario Completo**")
            boton_ejecutar = False
        
        st.markdown("---")
        
        # Información de ayuda
        with st.expander("ℹ️ Información de Archivos"):
            st.markdown("""
            **Estructura Esperada:**
            
            1. **Sucursales**: Sucursal, Latitud, Longitud, Direccion
            2. **Productos**: Producto_ID, Producto, Categoria
            3. **Lotes**: Lote_ID, Producto_ID, Fecha_Vencimiento
            4. **Inventario**: Lote_ID, Sucursal, Stock, Fecha_Movimiento
            5. **Stock**: Lote_ID, Sucursal, Stock_Teorico_Unidades, Dias_Para_Vencer
            
            **Nota:** El sistema mapea automáticamente columnas con nombres similares.
            """)
    
    # =============================================================================
    # SESSION STATE
    # =============================================================================
    if 'ejecutar' not in st.session_state:
        st.session_state['ejecutar'] = False
    if 'datos_procesados' not in st.session_state:
        st.session_state['datos_procesados'] = None
    if 'kpis' not in st.session_state:
        st.session_state['kpis'] = {}
    
    # =============================================================================
    # EJECUCIÓN DEL ANÁLISIS
    # =============================================================================
    if boton_ejecutar or st.session_state['ejecutar']:
        
        if archivo_stock is None and archivo_inventario is None:
            st.warning("⚠️ Por favor cargue al menos Stock Actual o Inventario Completo")
            st.stop()
        
        try:
            with st.spinner("🔄 Procesando datos y calculando métricas..."):
                
                # Cargar archivo principal
                if archivo_stock:
                    df_principal = pd.read_csv(archivo_stock)
                else:
                    df_principal = pd.read_csv(archivo_inventario)
                
                df_principal.columns = df_principal.columns.str.strip()
                df_principal = mapear_columnas(df_principal)
                
                # Parsear fechas
                fecha_col = 'Fecha' if 'Fecha' in df_principal.columns else 'Fecha_Movimiento' if 'Fecha_Movimiento' in df_principal.columns else None
                if fecha_col and df_principal[fecha_col].dtype == 'object':
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            df_principal[fecha_col] = pd.to_datetime(df_principal[fecha_col], format=fmt, errors='coerce')
                            if df_principal[fecha_col].notna().sum() > len(df_principal) * 0.8:
                                break
                        except:
                            continue
                    if df_principal[fecha_col].isna().sum() > len(df_principal) * 0.2:
                        df_principal[fecha_col] = pd.to_datetime(df_principal[fecha_col], errors='coerce', dayfirst=True)
                
                # Fecha de referencia
                if fecha_col and df_principal[fecha_col].notna().any():
                    fecha_hoy = df_principal[fecha_col].max()
                else:
                    fecha_hoy = datetime.now()
                
                # Calcular valor de stock
                df_principal = calcular_valor_stock(df_principal)
                
                # Aplicar clasificación
                df_principal = aplicar_clasificacion(df_principal)
                
                # Filtrar productos con stock
                df_riesgo = df_principal[df_principal['Stock_Inicial'] > 0].copy() if 'Stock_Inicial' in df_principal.columns else df_principal.copy()
                
                # Cargar sucursales para enriquecimiento
                df_sucursales = None
                if archivo_sucursales:
                    df_sucursales = pd.read_csv(archivo_sucursales)
                    df_sucursales.columns = df_sucursales.columns.str.strip()
                    df_sucursales = mapear_columnas(df_sucursales)
                    
                    # Merge con sucursales
                    if 'Sucursal' in df_riesgo.columns and 'Sucursal' in df_sucursales.columns:
                        df_riesgo = df_riesgo.merge(
                            df_sucursales[['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']],
                            on='Sucursal',
                            how='left'
                        )
                
                # Cargar productos para categorías
                if archivo_productos:
                    df_productos = pd.read_csv(archivo_productos)
                    df_productos.columns = df_productos.columns.str.strip()
                    df_productos = mapear_columnas(df_productos)
                    
                    if 'Producto_ID' in df_riesgo.columns and 'Producto_ID' in df_productos.columns:
                        df_riesgo = df_riesgo.merge(
                            df_productos[['Producto_ID', 'Producto', 'Categoria']],
                            on='Producto_ID',
                            how='left'
                        )
                
                # Calcular KPIs
                kpis = calcular_kpis(df_riesgo)
                
                # Análisis por categoría
                analisis_categoria = analizar_por_categoria(df_riesgo)
                
                # Análisis por sucursal
                analisis_sucursal = analizar_por_sucursal(df_riesgo)
                
                # Análisis de tendencias (si hay inventario histórico)
                analisis_tendencia = None
                if archivo_inventario:
                    df_inventario = pd.read_csv(archivo_inventario)
                    df_inventario.columns = df_inventario.columns.str.strip()
                    df_inventario = mapear_columnas(df_inventario)
                    analisis_tendencia = analizar_tendencia_mensual(df_inventario)
                
                st.success("✅ Datos procesados exitosamente!")
                st.info(f"📅 Fecha de análisis: {fecha_hoy.strftime('%d/%m/%Y')} | {len(df_riesgo)} productos analizados")
                
                # Verificar antigüedad
                dias_sin_actualizar = (datetime.now() - fecha_hoy).days if isinstance(fecha_hoy, (datetime, pd.Timestamp)) else 0
                if dias_sin_actualizar > 0:
                    st.warning(f"""
                    ⚠️ **Datos con {dias_sin_actualizar} día(s) de antigüedad**
                    
                    Última actualización: {fecha_hoy.strftime('%d/%m/%Y')}
                    
                    Para análisis preciso, se recomienda actualizar diariamente.
                    """)
            
            # =============================================================================
            # DASHBOARD PRINCIPAL - KPIs
            # =============================================================================
            st.markdown("## 📊 KPIs Principales")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                mostrar_kpi_card(
                    "Total Productos",
                    f"{kpis['total_productos']:,}",
                    delta=f"{pct(kpis['pct_vencido'])} vencidos",
                    delta_type='negative' if kpis['pct_vencido'] > 10 else 'neutral'
                )
            
            with col2:
                mostrar_kpi_card(
                    "Valor Total Inventario",
                    clp(kpis['total_valor']),
                    delta=None
                )
            
            with col3:
                mostrar_kpi_card(
                    "En Riesgo (≤10 días)",
                    f"{kpis['VENCIDO_productos'] + kpis['CRITICO_productos'] + kpis['URGENTE_productos'] + kpis['PREVENTIVO_productos']:,}",
                    delta=f"{pct(100 - kpis['pct_recuperable'])} del total",
                    delta_type='negative'
                )
            
            with col4:
                mostrar_kpi_card(
                    "Recuperación Potencial",
                    clp(kpis['recuperacion_potencial'] + kpis['credito_tributario']),
                    delta="27% crédito + descuentos",
                    delta_type='positive'
                )
            
            st.markdown("---")
            
            # =============================================================================
            # CLASIFICACIÓN POR NIVEL DE RIESGO
            # =============================================================================
            st.markdown("## 🎯 Clasificación por Nivel de Riesgo")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="classification-item vencido">
                    <div>
                        <div style="font-size: 1.1rem;">🟣 VENCIDO</div>
                        <div style="font-size: 0.9rem; margin-top: 5px;">{kpis['VENCIDO_productos']} productos | {clp(kpis['VENCIDO_valor'])}</div>
                    </div>
                    <div style="font-size: 2rem; font-weight: 800;">{pct(kpis['pct_vencido'])}</div>
                </div>
                
                <div class="classification-item critico">
                    <div>
                        <div style="font-size: 1.1rem;">🔴 CRÍTICO</div>
                        <div style="font-size: 0.9rem; margin-top: 5px;">{kpis['CRITICO_productos']} productos | {clp(kpis['CRITICO_valor'])}</div>
                    </div>
                    <div style="font-size: 2rem; font-weight: 800;">{pct(kpis['pct_critico'])}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="classification-item urgente">
                    <div>
                        <div style="font-size: 1.1rem;">🟠 URGENTE</div>
                        <div style="font-size: 0.9rem; margin-top: 5px;">{kpis['URGENTE_productos']} productos | {clp(kpis['URGENTE_valor'])}</div>
                    </div>
                    <div style="font-size: 2rem; font-weight: 800;">{pct((kpis['URGENTE_productos'] / kpis['total_productos'] * 100) if kpis['total_productos'] > 0 else 0)}</div>
                </div>
                
                <div class="classification-item preventivo">
                    <div>
                        <div style="font-size: 1.1rem;">🟡 PREVENTIVO</div>
                        <div style="font-size: 0.9rem; margin-top: 5px;">{kpis['PREVENTIVO_productos']} productos | {clp(kpis['PREVENTIVO_valor'])}</div>
                    </div>
                    <div style="font-size: 2rem; font-weight: 800;">{pct((kpis['PREVENTIVO_productos'] / kpis['total_productos'] * 100) if kpis['total_productos'] > 0 else 0)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # =============================================================================
            # MAPA GEOGRÁFICO
            # =============================================================================
            if mostrar_mapa and 'Latitud' in df_riesgo.columns and 'Longitud' in df_riesgo.columns:
                st.markdown("## 🗺️ Distribución Geográfica del Riesgo")
                
                fig_mapa = crear_mapa_calor_riesgo(df_riesgo)
                
                if fig_mapa:
                    st.plotly_chart(fig_mapa, use_container_width=True)
                    
                    # Resumen por sucursal
                    if analisis_sucursal is not None:
                        with st.expander("📊 Ver Detalle por Sucursal"):
                            st.dataframe(
                                analisis_sucursal.sort_values('Valor_Stock_Costo', ascending=False),
                                use_container_width=True,
                                hide_index=True
                            )
                
                st.markdown("---")
            
            # =============================================================================
            # ANÁLISIS POR CATEGORÍA
            # =============================================================================
            if analisis_categoria is not None:
                st.markdown("## 📦 Análisis por Categoría de Producto")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_cat = px.bar(
                        analisis_categoria.sort_values('Valor_Stock_Costo', ascending=False).head(10),
                        x='Valor_Stock_Costo',
                        y='Categoria',
                        orientation='h',
                        title='Top 10 Categorías por Valor en Riesgo',
                        color='Valor_Stock_Costo',
                        color_continuous_scale='Reds'
                    )
                    fig_cat.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_cat, use_container_width=True)
                
                with col2:
                    fig_cat_pie = px.pie(
                        analisis_categoria,
                        values='Valor_Stock_Costo',
                        names='Categoria',
                        title='Distribución por Categoría',
                        hole=0.4
                    )
                    fig_cat_pie.update_layout(height=400)
                    st.plotly_chart(fig_cat_pie, use_container_width=True)
                
                st.markdown("---")
            
            # =============================================================================
            # TENDENCIAS TEMPORALES
            # =============================================================================
            if mostrar_tendencias and analisis_tendencia is not None:
                st.markdown("## 📈 Tendencias Temporales")
                
                fig_tendencia = px.line(
                    analisis_tendencia,
                    x='Mes',
                    y='Valor_Stock_Costo',
                    title='Evolución del Valor en Riesgo por Mes',
                    markers=True
                )
                fig_tendencia.update_layout(height=400)
                st.plotly_chart(fig_tendencia, use_container_width=True)
                
                st.markdown("---")
            
            # =============================================================================
            # INSIGHTS Y RECOMENDACIONES
            # =============================================================================
            st.markdown("## 💡 Insights y Recomendaciones")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="warning-box">
                    <strong>⚠️ Atención Inmediata</strong><br>
                    {kpis['VENCIDO_productos']} productos vencidos representan 
                    <strong>{clp(kpis['perdida_potencial'])}</strong> en pérdida potencial.
                    <br><br>
                    <strong>Acción:</strong> Gestionar donación para recuperar 27% vía crédito tributario.
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="insight-box">
                    <strong>💰 Oportunidad de Recuperación</strong><br>
                    Productos críticos y urgentes representan 
                    <strong>{clp(kpis['recuperacion_potencial'])}</strong> en recuperación potencial.
                    <br><br>
                    <strong>Acción:</strong> Aplicar descuentos escalonados (40%, 25%).
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="success-box">
                    <strong>✅ Impacto Total</strong><br>
                    Recuperación total potencial (crédito + descuentos):
                    <strong>{clp(kpis['recuperacion_potencial'] + kpis['credito_tributario'])}</strong>
                    <br><br>
                    <strong>ROI:</strong> {pct((kpis['recuperacion_potencial'] + kpis['credito_tributario']) / kpis['total_valor'] * 100) if kpis['total_valor'] > 0 else '0%'} del inventario
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # =============================================================================
            # TABLA DETALLADA
            # =============================================================================
            st.markdown("## 📋 Detalle de Productos en Riesgo")
            
            with st.expander("Ver tabla completa de productos", expanded=False):
                cols_tabla = [c for c in ['Producto', 'Sucursal', 'Categoria', 'Stock_Inicial', 
                                         'Días_para_Vencimiento', 'Valor_Stock_Costo', 'Nivel_Riesgo'] 
                             if c in df_riesgo.columns]
                
                if cols_tabla:
                    st.dataframe(
                        df_riesgo[cols_tabla]
                        .sort_values(['Nivel_Riesgo', 'Valor_Stock_Costo'], ascending=[False, False])
                        .head(100),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Botón de descarga
                    csv = df_riesgo[cols_tabla].to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Descargar Datos Completos (CSV)",
                        data=csv,
                        file_name=f"analisis_vencimientos_{fecha_hoy.strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            # Guardar estado
            st.session_state['ejecutar'] = True
            st.session_state['datos_procesados'] = {
                'fecha': fecha_hoy,
                'kpis': kpis,
                'total_productos': len(df_riesgo)
            }
            
        except Exception as e:
            st.error(f"❌ Error en el análisis: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Ver detalles técnicos"):
                st.exception(e)
    
    else:
        # Pantalla de bienvenida
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px;">
            <h1 style="color: #1a237e; margin-bottom: 20px;">📊 Dashboard BI de Vencimientos</h1>
            <p style="font-size: 1.2rem; color: #666; max-width: 700px; margin: 0 auto 30px;">
                Sistema integral de Business Intelligence para gestión proactiva de vencimientos de inventario.
                Análisis en tiempo real, KPIs ejecutivos y recomendaciones accionables.
            </p>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 900px; margin: 40px auto;">
                <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    <div style="font-size: 2.5rem; margin-bottom: 10px;">📊</div>
                    <h3 style="color: #1a237e; margin-bottom: 10px;">KPIs Ejecutivos</h3>
                    <p style="color: #666; font-size: 0.9rem;">Métricas clave de rendimiento y impacto financiero</p>
                </div>
                
                <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    <div style="font-size: 2.5rem; margin-bottom: 10px;">🗺️</div>
                    <h3 style="color: #1a237e; margin-bottom: 10px;">Mapa Geográfico</h3>
                    <p style="color: #666; font-size: 0.9rem;">Distribución espacial del riesgo por sucursal</p>
                </div>
                
                <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    <div style="font-size: 2.5rem; margin-bottom: 10px;">💡</div>
                    <h3 style="color: #1a237e; margin-bottom: 10px;">Insights IA</h3>
                    <p style="color: #666; font-size: 0.9rem;">Recomendaciones accionables basadas en datos</p>
                </div>
            </div>
            
            <p style="margin-top: 40px; color: #888; font-size: 1rem;">
                ← Cargue los archivos en el panel lateral para comenzar el análisis
            </p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
