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
        return "0"
    try:
        valor_int = int(round(float(valor)))
        return f"{valor_int:,}".replace(",", ".")
    except:
        return str(valor)

pd.options.display.float_format = lambda x: f'{x:,.0f}'.replace(',', '.')

# =============================================================================
# COLORES SEMÁFORO COHERENTES
# =============================================================================
COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # 🟣 Violeta
    'CRITICO': '#d32f2f',      # 🔴 Rojo
    'URGENTE': '#f57c00',      # 🟠 Naranja
    'PREVENTIVO': '#fbc02d'    # 🟡 Amarillo
}

# =============================================================================
# CSS PERSONALIZADO
# =============================================================================
def cargar_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a237e;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .section-title-box {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        display: inline-block;
        margin: 2rem 0 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    .section-title-box h2 {
        color: white !important;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    .info-card {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .classification-item {
        padding: 15px;
        margin: 10px 0;
        border-radius: 10px;
        display: flex;
        align-items: center;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .vencido { background: #f3e5f5; color: #7b1fa2; border-left: 5px solid #9c27b0; }
    .critico { background: #ffebee; color: #c62828; border-left: 5px solid #d32f2f; }
    .urgente { background: #fff3e0; color: #e65100; border-left: 5px solid #f57c00; }
    .preventivo { background: #fffde7; color: #f9a825; border-left: 5px solid #fbc02d; }
    
    .decision-box {
        background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%);
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        border: 3px solid #1a237e;
        margin: 20px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .plan-section {
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 6px solid;
    }
    
    .plan-vencido { background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-color: #d32f2f; }
    .plan-critico { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-color: #f57c00; }
    .plan-urgente { background: linear-gradient(135deg, #fffde7 0%, #fff9c4 100%); border-color: #fbc02d; }
    .plan-cierre { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-color: #1976d2; }
    
    .badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .badge-vencido { background: #f3e5f5; color: #7b1fa2; }
    .badge-critico { background: #ffebee; color: #c62828; }
    .badge-urgente { background: #fff3e0; color: #e65100; }
    .badge-preventivo { background: #fffde7; color: #f9a825; }
    
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-size: 0.9rem;
        width: 100%;
    }
    
    .dataframe thead th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 700;
        padding: 15px;
        text-align: left;
        border: none;
    }
    
    .tabla-vencido thead th { background: linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%); }
    .tabla-critico thead th { background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%); }
    .tabla-urgente thead th { background: linear-gradient(135deg, #f57c00 0%, #e65100 100%); }
    .tabla-preventivo thead th { background: linear-gradient(135deg, #fbc02d 0%, #f9a825 100%); }
    
    .map-container {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# CONSTANTES
# =============================================================================
COLUMNAS_ESPERADAS = {
    'Días_para_Vencimiento': [
        'Dias_Para_Vencer', 'Días_para_Vencimiento', 'Días para Vencimiento',
        'Días_para_Vencer', 'Dias_Vencimiento'
    ],
    'Stock_Inicial': [
        'Stock_Teorico_Unidades', 'Stock_Inicial', 'Stock Sala',
        'Stock_Sala', 'stock_sala', 'Stock', 'Cantidad_Stock'
    ],
    'Costo_Unitario_Neto': [
        'Valor_Unitario_CLP', 'Costo_Unitario_Neto', 'Costo Unitario Neto',
        'costo_unitario_neto', 'Costo', 'Precio_Costo', 'Valor_Costo'
    ],
    'Precio_Venta_Bruto': [
        'Precio_Venta_CLP', 'Precio_Venta_Bruto', 'Precio Venta Bruto',
        'precio_venta_bruto', 'Precio'
    ],
    'Producto': ['Producto', 'producto', 'SKU_Descripcion'],
    'Sucursal': ['Sucursal', 'sucursal', 'Tienda', 'Store'],
    'Latitud': ['Latitud', 'lat', 'Latitude', 'Lat'],
    'Longitud': ['Longitud', 'lon', 'Longitude', 'Lng', 'Long']
}

COLUMNAS_REQUERIDAS = ['Días_para_Vencimiento', 'Stock_Inicial', 'Producto']

# =============================================================================
# FUNCIONES DE CARGA DE ARCHIVOS
# =============================================================================
@st.cache_data
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
    for col_destino, col_posibles in COLUMNAS_ESPERADAS.items():
        for col_posible in col_posibles:
            if col_posible in df.columns and col_destino not in df.columns:
                df.rename(columns={col_posible: col_destino}, inplace=True)
                break
    return df

# =============================================================================
# FUNCIONES DE CLASIFICACIÓN - CORREGIDAS
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

def aplicar_clasificacion(df):
    """Aplica clasificación de riesgo al dataframe - CORREGIDO"""
    # ✅ VERIFICAR que la columna existe antes de aplicar
    if 'Días_para_Vencimiento' not in df.columns:
        st.warning("⚠️ Columna 'Días_para_Vencimiento' no encontrada. Clasificación omitida.")
        df['Nivel_Riesgo'] = 'SIN_CLASIFICAR'
        return df
    
    df['Nivel_Riesgo'] = df['Días_para_Vencimiento'].apply(clasificar_riesgo)
    return df

def calcular_valor_stock(df):
    """Calcula el valor del stock"""
    if 'Stock_Inicial' not in df.columns:
        st.warning("⚠️ Columna 'Stock_Inicial' no encontrada.")
        df['Valor_Stock_Costo'] = 0
        return df
    
    if 'Costo_Unitario_Neto' in df.columns:
        df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
    elif 'Precio_Venta_Bruto' in df.columns:
        df['Costo_Unitario_Neto'] = df['Precio_Venta_Bruto'] * 0.70
        df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
    elif 'Precio_Venta_CLP' in df.columns:
        df['Costo_Unitario_Neto'] = df['Precio_Venta_CLP'] * 0.70
        df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
    else:
        df['Valor_Stock_Costo'] = df['Stock_Inicial']
        st.warning("⚠️ Sin columnas de costo/precio. Usando stock como valor proxy.")
    
    return df

# =============================================================================
# FUNCIONES DE MAPA
# =============================================================================
def crear_mapa_inventario(df_riesgo, df_sucursales=None):
    """Crea un mapa interactivo con Plotly"""
    
    # Verificar columnas disponibles
    if 'Stock_Inicial' not in df_riesgo.columns:
        if 'Stock_Teorico_Unidades' in df_riesgo.columns:
            df_riesgo['Stock_Inicial'] = df_riesgo['Stock_Teorico_Unidades']
        else:
            st.error("❌ No se encontró columna de Stock")
            return None, None
    
    if 'Valor_Stock_Costo' not in df_riesgo.columns:
        df_riesgo = calcular_valor_stock(df_riesgo)
    
    # Agrupar por sucursal
    if 'Sucursal' in df_riesgo.columns:
        stock_por_sucursal = df_riesgo.groupby('Sucursal').agg({
            'Stock_Inicial': 'sum',
            'Valor_Stock_Costo': 'sum',
            'Días_para_Vencimiento': 'mean'
        }).reset_index()
        
        # Merge con coordenadas
        if df_sucursales is not None and 'Latitud' in df_sucursales.columns:
            stock_por_sucursal = stock_por_sucursal.merge(
                df_sucursales[['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']],
                on='Sucursal',
                how='left'
            )
        else:
            # Coordenadas hardcoded de Santiago
            coordenadas_santiago = {
                'Maipú Centro': [-33.5105, -70.7558],
                'Las Condes': [-33.4028, -70.5652],
                'Providencia': [-33.4251, -70.595],
                'Ñuñoa': [-33.454, -70.5885],
                'Pudahuel': [-33.44, -70.753],
                'Lo Valledor': [-33.475, -70.68],
                'San Bernardo': [-33.59, -70.71],
                'La Florida': [-33.52, -70.56]
            }
            
            stock_por_sucursal['Latitud'] = stock_por_sucursal['Sucursal'].map(
                lambda x: coordenadas_santiago.get(x, [-33.45])[0]
            )
            stock_por_sucursal['Longitud'] = stock_por_sucursal['Sucursal'].map(
                lambda x: coordenadas_santiago.get(x, [-70.65])[1]
            )
            stock_por_sucursal['Direccion_Aprox'] = stock_por_sucursal['Sucursal']
        
        # Filtrar sucursales sin coordenadas
        stock_por_sucursal = stock_por_sucursal.dropna(subset=['Latitud', 'Longitud'])
        
        if len(stock_por_sucursal) == 0:
            st.warning("⚠️ No hay datos de sucursales con coordenadas válidas")
            return None, None
        
        # Crear mapa
        fig = go.Figure()
        
        def color_por_dias(dias):
            if pd.isna(dias):
                return '#9c27b0'
            elif dias < 0:
                return '#9c27b0'
            elif dias <= 3:
                return '#d32f2f'
            elif dias <= 7:
                return '#f57c00'
            else:
                return '#fbc02d'
        
        stock_por_sucursal['Color'] = stock_por_sucursal['Días_para_Vencimiento'].apply(color_por_dias)
        
        fig.add_trace(go.Scattermapbox(
            lat=stock_por_sucursal['Latitud'],
            lon=stock_por_sucursal['Longitud'],
            mode='markers',
            marker=dict(
                size=stock_por_sucursal['Stock_Inicial'] / 100,
                sizemode='area',
                sizeref=2,
                color=stock_por_sucursal['Color'],
                opacity=0.8,
            ),
            text=stock_por_sucursal.apply(
                lambda row: f"<b>{row['Sucursal']}</b><br>"
                           f"📦 Stock: {int(row['Stock_Inicial']):,} unidades<br>"
                           f"💰 Valor: {clp(row['Valor_Stock_Costo'])} CLP<br>"
                           f"⏰ Días prom: {row['Días_para_Vencimiento']:.1f}<br>"
                           f"📍 {row['Direccion_Aprox']}",
                axis=1
            ),
            hoverinfo='text',
            name='Sucursales'
        ))
        
        fig.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=30, b=0),
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=-33.45, lon=-70.65),
                zoom=9
            ),
            showlegend=False,
            title=dict(
                text='🗺️ Distribución de Inventario por Sucursal',
                x=0.5,
                font=dict(size=18, color='#1a237e')
            )
        )
        
        return fig, stock_por_sucursal
    
    return None, None

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN
# =============================================================================
def mostrar_resumen_ejecutivo_nuevo(df_riesgo, total_riesgo, fecha_hoy):
    """Muestra el resumen ejecutivo"""
    st.markdown('<h1 class="main-header">Resúmen</h1>', unsafe_allow_html=True)
    
    total_productos = len(df_riesgo)
    total_unidades = int(df_riesgo['Stock_Inicial'].sum()) if 'Stock_Inicial' in df_riesgo.columns else 0
    
    col1, col2, col3 = st.columns([1, 2.5, 1])
    
    with col1:
        st.markdown("### Acciones Rápidas")
        if st.button("🔄 Actualizar", use_container_width=True, key="btn_actualizar"):
            st.rerun()
        if st.button("📊 Ver Detalle Completo", use_container_width=True, key="btn_detalle"):
            st.session_state['ver_detalle'] = True
    
    with col2:
        st.markdown(f"""
        <div class='info-card'>
            <h2 style='color: #1565c0; margin: 0;'>Análisis al {fecha_hoy.strftime('%d/%m/%Y') if hasattr(fecha_hoy, 'strftime') else fecha_hoy}</h2>
            <p style='font-size: 1.3rem; margin: 15px 0; font-weight: 600;'>
                <span style='color: #d32f2f;'>{total_productos}</span> productos | 
                <span style='color: #1976d2;'>{total_unidades:,}</span> unidades | 
                <span style='color: #f57c00;'>{clp(total_riesgo)} CLP</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("### Estado")
        st.success("✅ Activo")
        hora_chile = datetime.now(pytz.timezone('America/Santiago'))
        st.info(f"🕒 {hora_chile.strftime('%H:%M:%S')}")

def mostrar_inventario_nuevo(df_riesgo, total_riesgo, fecha_hoy):
    """Muestra clasificación del inventario"""
    st.markdown('<div class="section-title-box"><h2>Inventario</h2></div>', unsafe_allow_html=True)
    st.markdown("### Clasificación")
    
    # ✅ VERIFICAR que Nivel_Riesgo existe antes de usarlo
    if 'Nivel_Riesgo' not in df_riesgo.columns:
        st.warning("⚠️ Columna 'Nivel_Riesgo' no encontrada. Aplicando clasificación...")
        df_riesgo = aplicar_clasificacion(df_riesgo)
    
    vencidos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO'])
    criticos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO'])
    urgentes = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE'])
    preventivos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO'])
    
    valor_vencidos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO']['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
    valor_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
    valor_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE']['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
    valor_preventivos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO']['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"""
        <div class='classification-item vencido'>
            <span class='indicator' style='background-color: #9c27b0;'></span>
            <strong>Vencido:</strong> {vencidos} productos | {clp(valor_vencidos)} CLP
        </div>
        <div class='classification-item critico'>
            <span class='indicator' style='background-color: #d32f2f;'></span>
            <strong>Crítico:</strong> {criticos} productos | {clp(valor_criticos)} CLP
        </div>
        <div class='classification-item urgente'>
            <span class='indicator' style='background-color: #f57c00;'></span>
            <strong>Urgente:</strong> {urgentes} productos | {clp(valor_urgentes)} CLP
        </div>
        <div class='classification-item preventivo'>
            <span class='indicator' style='background-color: #fbc02d;'></span>
            <strong>Preventivo:</strong> {preventivos} productos | {clp(valor_preventivos)} CLP
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal de la aplicación Streamlit"""
    st.set_page_config(
        page_title="Sistema de Gestión de Vencimientos",
        page_icon="📦",
        layout="wide"
    )
    cargar_css()
    
    st.title("📦 SISTEMA DE GESTIÓN DE VENCIMIENTOS")
    st.markdown("---")
    
    # =============================================================================
    # SIDEBAR - CARGA DE ARCHIVOS
    # =============================================================================
    with st.sidebar:
        st.header("📁 Carga de Archivos")
        st.markdown("---")
        
        st.markdown("**Archivos Requeridos:**")
        
        archivo_sucursales = st.file_uploader(
            "1️⃣ Sucursales (1_SUCURSALES_MASTER.csv)",
            type=['csv'],
            help="Ubicaciones de tiendas con coordenadas GPS",
            key="uploader_sucursales"
        )
        
        archivo_stock = st.file_uploader(
            "2️⃣ Stock Actual Geo (5_STOCK_ACTUAL_GEO_POWERBI.csv)",
            type=['csv'],
            help="Stock actual con ubicación geográfica",
            key="uploader_stock"
        )
        
        st.markdown("---")
        
        # Contador de archivos cargados
        archivos_cargados = sum([
            archivo_sucursales is not None,
            archivo_stock is not None
        ])
        
        st.progress(archivos_cargados / 2)
        st.caption(f"{archivos_cargados}/2 archivos cargados")
        
        mostrar_mapa = st.checkbox("🗺️ Mostrar Mapa de Sucursales", value=True)
        
        # Se requiere al menos el archivo de stock
        archivos_esenciales = archivo_stock is not None
        
        if archivos_esenciales:
            boton_ejecutar = st.button("✅ Ejecutar Análisis", type="primary", use_container_width=True)
        else:
            st.warning("⚠️ Cargue al menos el archivo de **Stock** para continuar")
            boton_ejecutar = False
    
    # =============================================================================
    # SESSION STATE
    # =============================================================================
    if 'ejecutar' not in st.session_state:
        st.session_state['ejecutar'] = False
    if 'datos_procesados' not in st.session_state:
        st.session_state['datos_procesados'] = None
    if 'ver_detalle' not in st.session_state:
        st.session_state['ver_detalle'] = False
    if 'plan_aceptado' not in st.session_state:
        st.session_state['plan_aceptado'] = False
    
    # =============================================================================
    # EJECUCIÓN DEL ANÁLISIS
    # =============================================================================
    if boton_ejecutar or st.session_state['ejecutar']:
        
        if archivo_stock is None:
            st.warning("⚠️ Por favor suba al menos el archivo de Stock")
            st.stop()
        
        try:
            with st.spinner("🔄 Cargando y procesando datos..."):
                
                # Cargar archivo principal
                df = pd.read_csv(archivo_stock)
                df.columns = df.columns.str.strip()
                
                # Mapeo de columnas
                column_mapping = {
                    'Stock_Teorico_Unidades': 'Stock_Inicial',
                    'Dias_Para_Vencer': 'Días_para_Vencimiento',
                    'Precio_Venta_CLP': 'Precio_Venta_Bruto',
                    'Valor_Unitario_CLP': 'Costo_Unitario_Neto',
                    'Fecha_Movimiento': 'Fecha',
                    'Fecha_Vencimiento_Lote': 'Fecha_Vencimiento',
                    'Estado_Inventario': 'Estado',
                    'Sucursal': 'Ubicacion',
                    'ID_Ciudad': 'Codigo_Ciudad'
                }
                
                for original, nuevo in column_mapping.items():
                    if original in df.columns and nuevo not in df.columns:
                        df.rename(columns={original: nuevo}, inplace=True)
                
                # Parsear fecha
                fecha_col = 'Fecha' if 'Fecha' in df.columns else None
                if fecha_col and df[fecha_col].dtype == 'object':
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            df[fecha_col] = pd.to_datetime(df[fecha_col], format=fmt, errors='coerce')
                            if df[fecha_col].notna().sum() > len(df) * 0.8:
                                break
                        except:
                            continue
                    if df[fecha_col].isna().sum() > len(df) * 0.2:
                        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce', dayfirst=True)
                
                # Fecha de referencia
                if fecha_col and df[fecha_col].notna().any():
                    fecha_hoy = df[fecha_col].max()
                else:
                    fecha_hoy = datetime.now()
                    st.warning("⚠️ No se detectó columna de fecha válida, usando fecha actual")
                
                # Calcular Valor de Stock
                df = calcular_valor_stock(df)
                
                # ✅ APLICAR CLASIFICACIÓN ANTES DE USARLA
                df = aplicar_clasificacion(df)
                
                # Filtrar productos con riesgo
                df_riesgo = df[
                    (df['Stock_Inicial'] > 0) & 
                    (df['Nivel_Riesgo'].isin(['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']))
                ].copy()
                
                # Calcular total en riesgo
                total_riesgo = df_riesgo['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
                
                # Cargar sucursales
                df_sucursales = None
                if archivo_sucursales:
                    try:
                        df_sucursales = pd.read_csv(archivo_sucursales)
                        df_sucursales.columns = df_sucursales.columns.str.strip()
                        if 'Sucursal' in df_sucursales.columns and 'Ubicacion' in df_riesgo.columns:
                            df_riesgo = df_riesgo.merge(
                                df_sucursales[['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']],
                                left_on='Ubicacion',
                                right_on='Sucursal',
                                how='left'
                            )
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo cargar archivo de sucursales: {e}")
                
                st.success(f"✅ Datos procesados correctamente!")
                st.info(f"📅 Análisis para: {fecha_hoy.strftime('%d/%m/%Y') if hasattr(fecha_hoy, 'strftime') else fecha_hoy} | Productos en riesgo: {len(df_riesgo)}")
                
                # Verificar antigüedad de datos
                dias_sin_actualizar = (datetime.now() - fecha_hoy).days if isinstance(fecha_hoy, (datetime, pd.Timestamp)) else 0
                if dias_sin_actualizar > 0:
                    st.warning(f"""
                    ⚠️ **Datos con {dias_sin_actualizar} día(s) de antigüedad**
                    
                    Última actualización: {fecha_hoy.strftime('%d/%m/%Y') if hasattr(fecha_hoy, 'strftime') else 'Desconocida'}
                    
                    Para un plan efectivo, se recomienda actualizar **diariamente**.
                    """)
            
            # =============================================================================
            # MOSTRAR RESULTADOS
            # =============================================================================
            
            # 1. Resumen ejecutivo
            mostrar_resumen_ejecutivo_nuevo(df_riesgo, total_riesgo, fecha_hoy)
            st.markdown("---")
            
            # 2. Clasificación de inventario
            mostrar_inventario_nuevo(df_riesgo, total_riesgo, fecha_hoy)
            st.markdown("---")
            
            # 3. MAPA DE SUCURSALES
            if mostrar_mapa and 'Latitud' in df_riesgo.columns and 'Longitud' in df_riesgo.columns:
                st.markdown('<div class="section-title-box"><h2>🗺️ Mapa de Sucursales</h2></div>', unsafe_allow_html=True)
                
                fig, stock_por_sucursal = crear_mapa_inventario(df_riesgo, df_sucursales)
                
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Resumen por sucursal
                    if stock_por_sucursal is not None and not stock_por_sucursal.empty:
                        st.markdown("### 📊 Resumen por Sucursal")
                        cols_mostrar = [c for c in ['Ubicacion', 'Sucursal', 'Stock_Inicial', 'Valor_Stock_Costo', 'Días_para_Vencimiento'] 
                                       if c in stock_por_sucursal.columns]
                        if cols_mostrar:
                            st.dataframe(
                                stock_por_sucursal[cols_mostrar]
                                .sort_values('Stock_Inicial', ascending=False)
                                .head(20),
                                use_container_width=True,
                                hide_index=True
                            )
                
                st.markdown("---")
            
            # 4. Vista de detalle
            if st.session_state.get('ver_detalle', False):
                with st.expander("📋 Ver Detalle Completo de Productos en Riesgo", expanded=True):
                    cols_detalle = [c for c in ['Producto', 'Ubicacion', 'Stock_Inicial', 'Días_para_Vencimiento', 
                                               'Valor_Stock_Costo', 'Nivel_Riesgo', 'Fecha_Vencimiento'] 
                                   if c in df_riesgo.columns]
                    if cols_detalle:
                        st.dataframe(
                            df_riesgo[cols_detalle]
                            .sort_values(['Nivel_Riesgo', 'Valor_Stock_Costo'], ascending=[False, False]),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.dataframe(df_riesgo.head(100), use_container_width=True)
                
                if st.button("⬅️ Volver al Resumen", type="primary"):
                    st.session_state['ver_detalle'] = False
                    st.rerun()
            
            # Guardar estado
            st.session_state['ejecutar'] = True
            st.session_state['datos_procesados'] = {
                'fecha': fecha_hoy,
                'total_riesgo': total_riesgo,
                'total_productos': len(df_riesgo)
            }
            
        except FileNotFoundError as e:
            st.error(f"❌ Archivo no encontrado: {e}")
        except pd.errors.EmptyDataError:
            st.error("❌ El archivo CSV está vacío o tiene formato incorrecto")
        except pd.errors.ParserError as e:
            st.error(f"❌ Error al parsear el CSV: {e}")
        except KeyError as e:
            st.error(f"❌ Columna esperada no encontrada: {e}. Verifique la estructura del archivo.")
        except Exception as e:
            st.error(f"❌ Error inesperado en el análisis: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Ver detalles técnicos del error"):
                st.exception(e)

if __name__ == "__main__":
    main()
