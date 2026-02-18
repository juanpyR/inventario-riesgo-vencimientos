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
        return "$0"
    try:
        valor_int = int(round(float(valor)))
        return f"${valor_int:,}".replace(",", ".")
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
    
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        margin: 20px 0;
    }
    
    .metric-item {
        background: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .metric-label { font-size: 0.85rem; color: #666; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #1a237e; }
    .metric-sub { font-size: 0.75rem; color: #999; margin-top: 5px; }
    
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
    
    .map-container {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# ETL - CARGA Y PROCESAMIENTO DE LOS 5 ARCHIVOS
# =============================================================================
@st.cache_data
def cargar_y_procesar_etl(archivo_sucursales, archivo_productos, archivo_lotes, 
                          archivo_inventario, archivo_stock):
    """
    ETL Completo: Carga los 5 archivos, hace joins y crea columnas calculadas
    """
    
    # 1. Cargar todos los archivos
    df_sucursales = pd.read_csv(archivo_sucursales)
    df_productos = pd.read_csv(archivo_productos)
    df_lotes = pd.read_csv(archivo_lotes)
    df_inventario = pd.read_csv(archivo_inventario)
    df_stock = pd.read_csv(archivo_stock)
    
    # 2. Limpieza de columnas
    for df in [df_sucursales, df_productos, df_lotes, df_inventario, df_stock]:
        df.columns = df.columns.str.strip()
    
    # 3. Mapeo de columnas para estandarizar
    # Sucursales
    df_sucursales = df_sucursales.rename(columns={
        'Direccion_Aprox': 'Direccion'
    })
    
    # Productos
    df_productos = df_productos.rename(columns={
        'Dias_Caducidad_Base': 'Dias_Caducidad',
        'ETA_Proveedor_Dias': 'ETA_Proveedor',
        'Categoria_Rotacion': 'Rotacion'
    })
    
    # Lotes
    df_lotes = df_lotes.rename(columns={
        'Fecha_Creacion_Lote': 'Fecha_Creacion'
    })
    
    # Inventario
    df_inventario = df_inventario.rename(columns={
        'Fecha_Movimiento': 'Fecha',
        'Cantidad_Entrada': 'Entrada',
        'Cantidad_Salida': 'Salida',
        'Valor_Unitario_CLP': 'Costo_Unitario',
        'Precio_Venta_CLP': 'Precio_Venta',
        'Fecha_Vencimiento_Lote': 'Fecha_Vencimiento',
        'Dias_Para_Vencer': 'Dias_Vencer',
        'Estado_Inventario': 'Estado',
        'Stock_Teorico_Unidades': 'Stock'
    })
    
    # Stock Actual
    df_stock = df_stock.rename(columns={
        'Stock_Teorico_Unidades': 'Stock',
        'Precio_Venta_CLP': 'Precio_Venta',
        'Fecha_Vencimiento_Lote': 'Fecha_Vencimiento',
        'Dias_Para_Vencer': 'Dias_Vencer',
        'Estado_Inventario': 'Estado'
    })
    
    # 4. JOINS - Unir todas las tablas
    # Unir Stock con Sucursales (por Sucursal)
    df_master = df_stock.merge(
        df_sucursales[['Sucursal', 'Latitud', 'Longitud', 'Direccion']],
        on='Sucursal',
        how='left'
    )
    
    # Unir con Productos (por Producto_ID)
    df_master = df_master.merge(
        df_productos[['Producto_ID', 'Producto', 'Categoria', 'Dias_Caducidad', 'Rotacion']],
        on='Producto_ID',
        how='left'
    )
    
    # Unir con Lotes (por Lote_ID)
    df_master = df_master.merge(
        df_lotes[['Lote_ID', 'Fecha_Creacion']],
        on='Lote_ID',
        how='left'
    )
    
    # 5. CREAR COLUMNAS CALCULADAS
    # Valor del stock (costo)
    df_master['Valor_Stock_Costo'] = df_master['Stock'] * df_master['Precio_Venta'] * 0.70  # 70% del precio = costo estimado
    
    # Clasificación de riesgo
    def clasificar_riesgo(dias):
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
    
    df_master['Nivel_Riesgo'] = df_master['Dias_Vencer'].apply(clasificar_riesgo)
    
    # Fecha de análisis
    df_master['Fecha_Analisis'] = datetime.now()
    
    # Días hasta vencimiento desde hoy
    df_master['Dias_Para_Vencimiento'] = df_master['Dias_Vencer']
    
    # 6. Filtrar productos con stock > 0
    df_riesgo = df_master[df_master['Stock'] > 0].copy()
    
    return df_riesgo, df_master, {
        'sucursales': df_sucursales,
        'productos': df_productos,
        'lotes': df_lotes,
        'inventario': df_inventario,
        'stock': df_stock
    }

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN
# =============================================================================
def mostrar_resumen_ejecutivo(df_riesgo, total_riesgo, fecha_hoy):
    """Muestra el resumen ejecutivo"""
    st.markdown('<h1 class="main-header">Resumen Ejecutivo</h1>', unsafe_allow_html=True)
    
    total_productos = df_riesgo['Producto'].nunique()
    total_unidades = int(df_riesgo['Stock'].sum())
    total_sucursales = df_riesgo['Sucursal'].nunique()
    
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
            <h2 style='color: #1565c0; margin: 0;'>Análisis al {fecha_hoy.strftime('%d/%m/%Y')}</h2>
            <p style='font-size: 1.3rem; margin: 15px 0; font-weight: 600;'>
                <span style='color: #d32f2f;'>{total_productos}</span> productos | 
                <span style='color: #1976d2;'>{total_unidades:,}</span> unidades | 
                <span style='color: #f57c00;'>{clp(total_riesgo)}</span>
            </p>
            <p style='font-size: 0.9rem; color: #666;'>
                🏪 {total_sucursales} sucursales analizadas
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
    st.markdown('<div class="section-title-box"><h2>Inventario por Nivel de Riesgo</h2></div>', unsafe_allow_html=True)
    st.markdown("### Clasificación")
    
    # Calcular métricas por nivel
    metricas = {}
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
        df_nivel = df_riesgo[df_riesgo['Nivel_Riesgo'] == nivel]
        metricas[nivel] = {
            'productos': df_nivel['Producto'].nunique() if len(df_nivel) > 0 else 0,
            'unidades': int(df_nivel['Stock'].sum()) if len(df_nivel) > 0 else 0,
            'valor': df_nivel['Valor_Stock_Costo'].sum() if len(df_nivel) > 0 else 0
        }
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"""
        <div class='classification-item vencido'>
            <span class='indicator' style='background-color: #9c27b0;'></span>
            <strong>Vencido:</strong> {metricas['VENCIDO']['productos']} productos | {clp(metricas['VENCIDO']['valor'])}
        </div>
        <div class='classification-item critico'>
            <span class='indicator' style='background-color: #d32f2f;'></span>
            <strong>Crítico:</strong> {metricas['CRITICO']['productos']} productos | {clp(metricas['CRITICO']['valor'])}
        </div>
        <div class='classification-item urgente'>
            <span class='indicator' style='background-color: #f57c00;'></span>
            <strong>Urgente:</strong> {metricas['URGENTE']['productos']} productos | {clp(metricas['URGENTE']['valor'])}
        </div>
        <div class='classification-item preventivo'>
            <span class='indicator' style='background-color: #fbc02d;'></span>
            <strong>Preventivo:</strong> {metricas['PREVENTIVO']['productos']} productos | {clp(metricas['PREVENTIVO']['valor'])}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Calcular plan de acción
        credito_trib = metricas['VENCIDO']['valor'] * 0.27
        recuperacion_crit = metricas['CRITICO']['valor'] * 0.50
        recuperacion_urg = metricas['URGENTE']['valor'] * 0.40
        total_recuperado = credito_trib + recuperacion_crit + recuperacion_urg
        
        st.session_state['metricas_plan'] = {
            'credito_tributario': credito_trib,
            'recuperacion_descuentos': recuperacion_crit + recuperacion_urg,
            'total_recuperado': total_recuperado
        }
        
        st.markdown(f"""
        <div class='decision-box'>
            <h3>💰 Impacto Financiero del Plan</h3>
            <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0;'>
                <div style='background: #e8f5e9; padding: 15px; border-radius: 8px;'>
                    <div style='font-size: 0.9rem; color: #2e7d32;'>Crédito Tributario (27%)</div>
                    <div style='font-size: 1.5rem; font-weight: 700; color: #1565c0;'>{clp(credito_trib)}</div>
                </div>
                <div style='background: #fff3e0; padding: 15px; border-radius: 8px;'>
                    <div style='font-size: 0.9rem; color: #e65100;'>Recuperación Descuentos</div>
                    <div style='font-size: 1.5rem; font-weight: 700; color: #ef6c00;'>{clp(recuperacion_crit + recuperacion_urg)}</div>
                </div>
            </div>
            <div style='background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); padding: 20px; border-radius: 10px; text-align: center; color: white;'>
                <div style='font-size: 1.2rem;'>TOTAL RECUPERADO</div>
                <div style='font-size: 2.5rem; font-weight: 700;'>{clp(total_recuperado)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def crear_mapa_inventario(df_riesgo):
    """Crea un mapa interactivo con Plotly"""
    
    # Agrupar por sucursal
    stock_por_sucursal = df_riesgo.groupby('Sucursal').agg({
        'Stock': 'sum',
        'Valor_Stock_Costo': 'sum',
        'Dias_Para_Vencimiento': 'mean',
        'Latitud': 'first',
        'Longitud': 'first'
    }).reset_index()
    
    # Filtrar sucursales sin coordenadas
    stock_por_sucursal = stock_por_sucursal.dropna(subset=['Latitud', 'Longitud'])
    
    if len(stock_por_sucursal) == 0:
        return None, None
    
    # Crear mapa
    fig = go.Figure()
    
    # Colores según nivel de riesgo promedio
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
    
    stock_por_sucursal['Color'] = stock_por_sucursal['Dias_Para_Vencimiento'].apply(color_por_dias)
    
    fig.add_trace(go.Scattermapbox(
        lat=stock_por_sucursal['Latitud'],
        lon=stock_por_sucursal['Longitud'],
        mode='markers',
        marker=dict(
            size=stock_por_sucursal['Stock'] / 100,
            sizemode='area',
            sizeref=2,
            color=stock_por_sucursal['Color'],
            opacity=0.8,
        ),
        text=stock_por_sucursal.apply(
            lambda row: f"<b>{row['Sucursal']}</b><br>"
                       f"📦 Stock: {int(row['Stock']):,} unidades<br>"
                       f"💰 Valor: {clp(row['Valor_Stock_Costo'])}<br>"
                       f"⏰ Días prom: {row['Días_Para_Vencimiento']:.1f}<br>"
                       f"📍 {row.get('Direccion', 'N/A')}",
            axis=1
        ),
        hoverinfo='text',
        name='Sucursales'
    ))
    
    # Configurar layout
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
    # SIDEBAR - CARGA DE LOS 5 ARCHIVOS
    # =============================================================================
    with st.sidebar:
        st.header("📁 Carga de Archivos (ETL)")
        st.markdown("---")
        
        st.markdown("**Se requieren los 5 archivos para el ETL completo:**")
        
        archivo_sucursales = st.file_uploader(
            "1️⃣ 1_SUCURSALES_MASTER.csv",
            type=['csv'],
            help="Ubicaciones de tiendas con coordenadas GPS",
            key="uploader_sucursales"
        )
        
        archivo_productos = st.file_uploader(
            "2️⃣ 2_PRODUCTOS_MASTER.csv",
            type=['csv'],
            help="Catálogo maestro de productos",
            key="uploader_productos"
        )
        
        archivo_lotes = st.file_uploader(
            "3️⃣ 3_LOTES_PRODUCTOS.csv",
            type=['csv'],
            help="Información de lotes y caducidad",
            key="uploader_lotes"
        )
        
        archivo_inventario = st.file_uploader(
            "4️⃣ 4_INVENTARIO_COMPLETO_LOTES.csv",
            type=['csv'],
            help="Inventario completo con movimientos",
            key="uploader_inventario"
        )
        
        archivo_stock = st.file_uploader(
            "5️⃣ 5_STOCK_ACTUAL_GEO_POWERBI.csv",
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
        
        # Botón de ejecutar (solo se habilita si todos los archivos están cargados)
        todos_archivos = archivos_cargados == 5
        
        if todos_archivos:
            boton_ejecutar = st.button("✅ Ejecutar ETL y Análisis", type="primary", use_container_width=True)
        else:
            st.warning(f"⚠️ Faltan {5 - archivos_cargados} archivos. Se necesitan los 5 para el ETL completo.")
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
    if 'metricas_plan' not in st.session_state:
        st.session_state['metricas_plan'] = {}
    
    # =============================================================================
    # EJECUCIÓN DEL ETL Y ANÁLISIS
    # =============================================================================
    if boton_ejecutar or st.session_state['ejecutar']:
        
        if not todos_archivos:
            st.warning("⚠️ Por favor cargue los 5 archivos para ejecutar el ETL completo")
            st.stop()
        
        try:
            with st.spinner("🔄 Ejecutando ETL: Cargando y procesando los 5 archivos..."):
                
                # EJECUTAR ETL COMPLETO
                df_riesgo, df_master, dfs_originales = cargar_y_procesar_etl(
                    archivo_sucursales,
                    archivo_productos,
                    archivo_lotes,
                    archivo_inventario,
                    archivo_stock
                )
                
                # Fecha de referencia
                fecha_hoy = datetime.now()
                
                # Calcular total en riesgo
                total_riesgo = df_riesgo['Valor_Stock_Costo'].sum()
                
                st.success("✅ ETL completado exitosamente!")
                st.info(f"📅 Análisis para: {fecha_hoy.strftime('%d/%m/%Y')} | Productos en riesgo: {len(df_riesgo)}")
                
                # Mostrar resumen de datos cargados
                with st.expander("📊 Resumen de Datos Cargados", expanded=False):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("🏪 Sucursales", len(dfs_originales['sucursales']))
                    with col2:
                        st.metric("📦 Productos", len(dfs_originales['productos']))
                    with col3:
                        st.metric("🔢 Lotes", len(dfs_originales['lotes']))
                    with col4:
                        st.metric("📋 Movimientos", len(dfs_originales['inventario']))
                    with col5:
                        st.metric("📍 Stock Actual", len(dfs_originales['stock']))
            
            # =============================================================================
            # MOSTRAR RESULTADOS
            # =============================================================================
            
            # 1. Resumen ejecutivo
            mostrar_resumen_ejecutivo(df_riesgo, total_riesgo, fecha_hoy)
            st.markdown("---")
            
            # 2. Clasificación de inventario
            mostrar_inventario_nuevo(df_riesgo, total_riesgo, fecha_hoy)
            st.markdown("---")
            
            # 3. MAPA DE SUCURSALES
            st.markdown('<div class="section-title-box"><h2>🗺️ Mapa de Sucursales</h2></div>', unsafe_allow_html=True)
            
            fig, stock_por_sucursal = crear_mapa_inventario(df_riesgo)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # Resumen por sucursal
                if stock_por_sucursal is not None and not stock_por_sucursal.empty:
                    st.markdown("### 📊 Resumen por Sucursal")
                    st.dataframe(
                        stock_por_sucursal[['Sucursal', 'Stock', 'Valor_Stock_Costo', 'Días_Para_Vencimiento']]
                        .sort_values('Stock', ascending=False)
                        .head(20),
                        use_container_width=True,
                        hide_index=True
                    )
            
            st.markdown("---")
            
            # 4. Vista de detalle (opcional)
            if st.session_state.get('ver_detalle', False):
                with st.expander("📋 Ver Detalle Completo de Productos en Riesgo", expanded=True):
                    cols_detalle = ['Producto', 'Sucursal', 'Stock', 'Días_Para_Vencimiento', 
                                   'Valor_Stock_Costo', 'Nivel_Riesgo', 'Categoria']
                    st.dataframe(
                        df_riesgo[cols_detalle]
                        .sort_values(['Nivel_Riesgo', 'Valor_Stock_Costo'], ascending=[False, False]),
                        use_container_width=True,
                        hide_index=True
                    )
                
                if st.button("⬅️ Volver al Resumen", type="primary"):
                    st.session_state['ver_detalle'] = False
                    st.rerun()
            
            # Guardar estado de ejecución
            st.session_state['ejecutar'] = True
            st.session_state['datos_procesados'] = {
                'fecha': fecha_hoy,
                'total_riesgo': total_riesgo,
                'total_productos': len(df_riesgo),
                'total_recuperado': st.session_state.get('metricas_plan', {}).get('total_recuperado', 0)
            }
            
        except Exception as e:
            st.error(f"❌ Error en el ETL: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Ver detalles técnicos del error"):
                st.exception(e)

if __name__ == "__main__":
    main()
