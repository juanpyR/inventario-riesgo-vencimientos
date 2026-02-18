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

.plan-metrics {
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;
    border: 2px solid #4CAF50;
}

.metric-row {
    display: flex;
    justify-content: space-between;
    padding: 10px;
    margin: 5px 0;
    background: white;
    border-radius: 5px;
    font-weight: 600;
}

.metric-label { color: #2e7d32; }
.metric-value { color: #1565c0; font-size: 1.1rem; }

.indicator {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    margin-right: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

.total-box {
    background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
    color: white;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    margin: 20px 0;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.total-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px;
}

.total-item {
    background: rgba(255,255,255,0.2);
    padding: 15px;
    border-radius: 10px;
}

.total-label { font-size: 0.9rem; opacity: 0.9; margin-bottom: 5px; }
.total-value { font-size: 1.8rem; font-weight: 700; }

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

.dataframe tbody tr:nth-child(even) { background-color: #f8f9fa; }
.dataframe tbody tr:nth-child(odd) { background-color: white; }
.dataframe tbody tr:hover { background-color: #e3f2fd; transition: all 0.3s; }
.dataframe td { padding: 12px 15px; border-bottom: 1px solid #e0e0e0; }

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

.plan-section {
    border-radius: 15px;
    padding: 25px;
    margin: 20px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    border-left: 6px solid;
}

.plan-vencido { background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%); border-color: #9c27b0; }
.plan-critico { background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-color: #d32f2f; }
.plan-urgente { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-color: #f57c00; }
.plan-cierre { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-color: #1976d2; }

.plan-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 2px solid rgba(0,0,0,0.1);
}

.plan-title { font-size: 1.3rem; font-weight: 700; color: #1a237e; margin: 0; }
.plan-badge {
    background: rgba(255,255,255,0.9);
    padding: 8px 15px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

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

.action-list { background: white; border-radius: 10px; padding: 20px; margin: 15px 0; }

.action-item {
    display: flex;
    align-items: center;
    padding: 12px;
    margin: 8px 0;
    background: #f5f5f5;
    border-radius: 8px;
    border-left: 4px solid;
}

.action-icon { font-size: 1.5rem; margin-right: 15px; }
.action-text { flex: 1; font-size: 0.95rem; }

.sensitivity-box {
    background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
    border: 2px solid #9c27b0;
}

.sensitivity-title { font-size: 1.1rem; font-weight: 700; color: #6a1b9a; margin-bottom: 15px; }

.sensitivity-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
}

.sensitivity-item {
    background: white;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
}

.sensitivity-label { font-size: 0.8rem; color: #666; margin-bottom: 5px; }
.sensitivity-value { font-size: 1.2rem; font-weight: 700; color: #6a1b9a; }

.timeline {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 20px 0;
    padding: 20px;
    background: white;
    border-radius: 12px;
}

.timeline-item { text-align: center; flex: 1; position: relative; }
.timeline-time { font-size: 0.9rem; font-weight: 700; color: #1a237e; margin-bottom: 5px; }
.timeline-action { font-size: 0.8rem; color: #666; }
.timeline-dot { width: 12px; height: 12px; border-radius: 50%; margin: 10px auto; background: #667eea; }

.resumen-final-box {
    background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
    border-radius: 15px;
    padding: 30px;
    color: white;
    margin: 20px 0;
    box-shadow: 0 4px 15px rgba(26, 35, 126, 0.4);
}

.resumen-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }

.resumen-card {
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(10px);
}

.resumen-card h4 { margin: 0 0 15px 0; font-size: 1.1rem; opacity: 0.9; }

.resumen-item {
    display: flex;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.2);
}

.resumen-item:last-child { border-bottom: none; }
.resumen-icon { font-size: 1.5rem; margin-right: 12px; }
.resumen-text { flex: 1; font-size: 0.9rem; }

.conclusion-box {
    background: white;
    border-radius: 12px;
    padding: 25px;
    margin: 20px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.conclusion-item { padding: 15px; margin: 10px 0; border-radius: 10px; border-left: 5px solid; }
.conclusion-error { background: #ffebee; border-color: #d32f2f; color: #c62828; }
.conclusion-success { background: #e8f5e9; border-color: #4caf50; color: #2e7d32; }
.conclusion-info { background: #e3f2fd; border-color: #1976d2; color: #1565c0; }

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
MESES_ESP = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

COLUMNAS_ESPERADAS = {
    'Días_para_Vencimiento': ['Dias_Para_Vencer', 'Días_para_Vencimiento', 'Días para Vencimiento', 'Días_para_Vencer', 'Dias_Vencimiento'],
    'Stock_Inicial': ['Stock_Teorico_Unidades', 'Stock_Inicial', 'Stock Sala', 'Stock_Sala', 'stock_sala', 'Stock', 'Cantidad_Stock'],
    'Costo_Unitario_Neto': ['Valor_Unitario_CLP', 'Costo_Unitario_Neto', 'Costo Unitario Neto', 'costo_unitario_neto', 'Costo', 'Precio_Costo', 'Valor_Costo'],
    'Precio_Venta_Bruto': ['Precio_Venta_CLP', 'Precio_Venta_Bruto', 'Precio Venta Bruto', 'precio_venta_bruto', 'Precio'],
    'Producto': ['Producto', 'producto', 'SKU_Descripcion'],
    'Sucursal': ['Sucursal', 'sucursal', 'Tienda', 'Store'],
    'Latitud': ['Latitud', 'lat', 'Latitude', 'Lat'],
    'Longitud': ['Longitud', 'lon', 'Longitude', 'Lng', 'Long']
}

COLUMNAS_REQUERIDAS = ['Días_para_Vencimiento', 'Stock_Inicial', 'Producto']

# =============================================================================
# FUNCIONES DE CARGA Y PREPARACIÓN
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
            if col_posible in df.columns:
                df.rename(columns={col_posible: col_destino}, inplace=True)
                break
    return df

# =============================================================================
# FUNCIONES DE CLASIFICACIÓN
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
    """Aplica clasificación de riesgo al dataframe"""
    df['Nivel_Riesgo'] = df['Días_para_Vencimiento'].apply(clasificar_riesgo)
    return df

def calcular_valor_stock(df):
    """Calcula el valor del stock"""
    if 'Costo_Unitario_Neto' in df.columns:
        df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
    elif 'Precio_Venta_Bruto' in df.columns:
        df['Costo_Unitario_Neto'] = df['Precio_Venta_Bruto'] * 0.70
        df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
    else:
        df['Valor_Stock_Costo'] = df['Stock_Inicial'] * 1000  # Valor estimado
    return df

def filtrar_productos_riesgo(df_hoy, dias_min=0, dias_max=10):
    """Filtra productos en riesgo"""
    return df_hoy[
        (df_hoy['Días_para_Vencimiento'] <= dias_max) &
        (df_hoy['Días_para_Vencimiento'] >= dias_min) &
        (df_hoy['Stock_Inicial'] > 0)
    ].copy()

# =============================================================================
# FUNCIONES DE MAPA
# =============================================================================
def crear_mapa_inventario(df_riesgo, df_sucursales=None):
    """Crea un mapa interactivo con Plotly"""
    
    # Verificar y preparar columnas requeridas
    if 'Stock_Inicial' not in df_riesgo.columns:
        if 'Stock_Teorico_Unidades' in df_riesgo.columns:
            df_riesgo['Stock_Inicial'] = df_riesgo['Stock_Teorico_Unidades']
        else:
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
        
        # Merge con coordenadas si hay dataframe de sucursales
        if df_sucursales is not None and 'Latitud' in df_sucursales.columns and 'Longitud' in df_sucursales.columns:
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
                lambda x: coordenadas_santiago.get(x, [-33.45])[0] if isinstance(coordenadas_santiago.get(x), list) else -33.45
            )
            stock_por_sucursal['Longitud'] = stock_por_sucursal['Sucursal'].map(
                lambda x: coordenadas_santiago.get(x, [-70.65])[1] if isinstance(coordenadas_santiago.get(x), list) else -70.65
            )
            stock_por_sucursal['Direccion_Aprox'] = stock_por_sucursal['Sucursal']
        
        # Filtrar sucursales sin coordenadas
        stock_por_sucursal = stock_por_sucursal.dropna(subset=['Latitud', 'Longitud'])
        
        # Crear mapa
        fig = go.Figure()
        
        def color_por_dias(dias):
            if pd.isna(dias):
                return '#9c27b0'
            elif dias < 0:
                return '#9c27b0'  # Violeta - Vencido
            elif dias <= 3:
                return '#d32f2f'  # Rojo - Crítico
            elif dias <= 7:
                return '#f57c00'  # Naranja - Urgente
            else:
                return '#fbc02d'  # Amarillo - Preventivo
        
        stock_por_sucursal['Color'] = stock_por_sucursal['Días_para_Vencimiento'].apply(color_por_dias)
        
        fig.add_trace(go.Scattermapbox(
            lat=stock_por_sucursal['Latitud'],
            lon=stock_por_sucursal['Longitud'],
            mode='markers',
            marker=dict(
                size=stock_por_sucursal['Stock_Inicial'] / 50,
                sizemode='area',
                sizeref=2,
                color=stock_por_sucursal['Color'],
                opacity=0.85,
                line=dict(width=2, color='white')
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
            height=500,
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
                font=dict(size=16, color='#1a237e')
            )
        )
        
        return fig, stock_por_sucursal
    
    return None, None

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN - RESUMEN
# =============================================================================
def mostrar_resumen_ejecutivo_nuevo(df_riesgo, total_riesgo, fecha_hoy):
    """Muestra el resumen ejecutivo"""
    st.markdown('<h1 class="main-header">Resúmen</h1>', unsafe_allow_html=True)
    
    total_productos = len(df_riesgo)
    total_unidades = int(df_riesgo['Stock_Inicial'].sum())
    
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
                <span style='color: #9c27b0;'>{total_productos}</span> productos | 
                <span style='color: #1976d2;'>{total_unidades:,}</span> unidades | 
                <span style='color: #f57c00;'>{clp(total_riesgo)} CLP</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.button("📋 Ver Reporte Detallado", use_container_width=True, type="primary", key="btn_reporte")
    
    with col3:
        st.markdown("### Estado")
        st.success("✅ Activo")
        hora_chile = datetime.now(pytz.timezone('America/Santiago'))
        st.info(f"🕒 {hora_chile.strftime('%H:%M:%S')}")

def mostrar_inventario_nuevo(df_riesgo, total_riesgo, fecha_hoy):
    """Muestra clasificación del inventario"""
    st.markdown('<div class="section-title-box"><h2>Inventario</h2></div>', unsafe_allow_html=True)
    st.markdown("### Clasificación")
    
    vencidos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO'])
    criticos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO'])
    urgentes = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE'])
    preventivos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO'])
    
    valor_vencidos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO']['Valor_Stock_Costo'].sum()
    valor_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']['Valor_Stock_Costo'].sum()
    valor_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE']['Valor_Stock_Costo'].sum()
    valor_preventivos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO']['Valor_Stock_Costo'].sum()
    
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
    
    with col2:
        acciones = []
        if vencidos > 0:
            credito = valor_vencidos * 0.27
            acciones.append(f"• <strong>{vencidos} vencidos</strong>: Donación inmediata → Crédito {clp(credito)} CLP (27%)")
        if criticos > 0:
            recuperacion = valor_criticos * 0.50
            acciones.append(f"• <strong>{criticos} críticos</strong>: Descuento 40% → Recuperación estimada {clp(recuperacion)} CLP")
        if urgentes > 0:
            recuperacion = valor_urgentes * 0.40
            acciones.append(f"• <strong>{urgentes} urgentes</strong>: Descuento 25% → Recuperación estimada {clp(recuperacion)} CLP")
        
        plan_texto = "<br>".join(acciones) if acciones else "No se requieren acciones inmediatas"
        total_credito = valor_vencidos * 0.27 if vencidos > 0 else 0
        total_recuperacion = ((valor_criticos * 0.50 if criticos > 0 else 0) + (valor_urgentes * 0.40 if urgentes > 0 else 0))
        total_recuperado = total_credito + total_recuperacion
        
        st.session_state['metricas_plan'] = {
            'credito_tributario': total_credito,
            'recuperacion_descuentos': total_recuperacion,
            'total_recuperado': total_recuperado
        }
        
        st.markdown(f"""
        <div class='decision-box'>
            <h3>Decisión Requerida</h3>
            <p style='font-size: 1.1rem; color: #424242; margin: 20px 0;'>
                Se requieren <strong>acciones inmediatas</strong> para {vencidos} productos vencidos 
                y {criticos} productos críticos.<br><br>
                <div class='plan-summary'>
                    <h4>📋 Plan de Acción Recomendado:</h4>
                    {plan_texto}
                </div>
                <div class='plan-metrics'>
                    <div class='metric-row'>
                        <span class='metric-label'>💰 Crédito Tributario (27%):</span>
                        <span class='metric-value'>{clp(total_credito)} CLP</span>
                    </div>
                    <div class='metric-row'>
                        <span class='metric-label'>📈 Recuperación por Descuentos (48h):</span>
                        <span class='metric-value'>{clp(total_recuperacion)} CLP</span>
                    </div>
                    <div class='metric-row' style='background: #c8e6c9; font-size: 1.2rem;'>
                        <span class='metric-label'>✅ Total Recuperado:</span>
                        <span class='metric-value' style='color: #2e7d32;'>{clp(total_recuperado)} CLP</span>
                    </div>
                </div>
                ¿Proceder con el plan de acción?
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✅ Aceptar Plan", use_container_width=True, type="primary", key="btn_aceptar"):
                st.session_state['plan_aceptado'] = True
                st.rerun()
        with col_btn2:
            if st.button("❌ Rechazar", use_container_width=True, key="btn_rechazar"):
                st.session_state['plan_aceptado'] = False
                st.warning("⚠️ Plan rechazado. Se requiere revisión manual.")
        
        if st.session_state.get('plan_aceptado', False):
            st.success("✅ Plan de acción aceptado - Ejecución iniciada")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Crédito Tributario", f"{clp(total_credito)} CLP", "27% s/donaciones")
            with col2:
                st.metric("📈 Recuperación Descuentos", f"{clp(total_recuperacion)} CLP", "40%, 25%, 15% dto")
            with col3:
                st.metric("✅ Total Recuperado", f"{clp(total_recuperado)} CLP", f"De {clp(total_riesgo)} en riesgo")

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN - GRÁFICOS
# =============================================================================
def mostrar_visualizacion_nueva(df_riesgo):
    """Muestra visualización con gráficos circulares"""
    st.markdown('<div class="section-title-box"><h2>Visualización de datos</h2></div>', unsafe_allow_html=True)
    
    vencidos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO'])
    criticos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO'])
    urgentes = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE'])
    preventivos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO'])
    
    valor_vencidos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO']['Valor_Stock_Costo'].sum()
    valor_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']['Valor_Stock_Costo'].sum()
    valor_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE']['Valor_Stock_Costo'].sum()
    valor_preventivos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO']['Valor_Stock_Costo'].sum()
    
    recuperables = criticos + urgentes + preventivos
    perdidos = vencidos
    
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{'type':'domain'}, {'type':'domain'}, {'type':'domain'}]],
        subplot_titles=['Distribución por Nivel', 'Distribución por Valor', 'Estado del Inventario']
    )
    
    colors_semaforo = ['#9c27b0', '#d32f2f', '#f57c00', '#fbc02d']
    
    fig.add_trace(go.Pie(
        labels=['Vencido<br>(Hoy)', 'Crítico<br>(1-3 días)', 'Urgente<br>(4-7 días)', 'Preventivo<br>(8-10 días)'],
        values=[vencidos, criticos, urgentes, preventivos],
        marker_colors=colors_semaforo,
        hole=0.4,
        textinfo='percent',
        textposition='inside',
        textfont=dict(color='white', size=12, weight='bold'),
        insidetextorientation='radial',
        name='Por Nivel'
    ), row=1, col=1)
    
    fig.add_trace(go.Pie(
        labels=['Vencido', 'Crítico', 'Urgente', 'Preventivo'],
        values=[valor_vencidos, valor_criticos, valor_urgentes, valor_preventivos],
        marker_colors=colors_semaforo,
        hole=0.4,
        textinfo='percent',
        textposition='inside',
        textfont=dict(color='white', size=12, weight='bold'),
        insidetextorientation='radial',
        name='Por Valor'
    ), row=1, col=2)
    
    fig.add_trace(go.Pie(
        labels=['Recuperables', 'Perdidos<br>(Vencidos)'],
        values=[recuperables, perdidos],
        marker_colors=['#4caf50', '#f44336'],
        hole=0.4,
        textinfo='percent',
        textposition='inside',
        textfont=dict(color='white', size=12, weight='bold'),
        insidetextorientation='radial',
        name='Estado'
    ), row=1, col=3)
    
    fig.update_layout(
        height=450,
        showlegend=False,
        title_text="<b>Distribución del Inventario en Riesgo</b>",
        title_x=0.5,
        title_font_size=22,
        title_font_color='#1a237e',
        margin=dict(t=80, b=20, l=20, r=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("### Leyenda - Distribución por Nivel")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class='legend-box' style='border-color: #9c27b0; background: #f3e5f5;'>
            <span class='indicator' style='background-color: #9c27b0;'></span>
            <strong>Vencido</strong><br>
            <small style='color: #666;'>Hoy</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='legend-box' style='border-color: #d32f2f; background: #ffebee;'>
            <span class='indicator' style='background-color: #d32f2f;'></span>
            <strong>Crítico</strong><br>
            <small style='color: #666;'>1-3 días</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='legend-box' style='border-color: #f57c00; background: #fff3e0;'>
            <span class='indicator' style='background-color: #f57c00;'></span>
            <strong>Urgente</strong><br>
            <small style='color: #666;'>4-7 días</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class='legend-box' style='border-color: #fbc02d; background: #fffde7;'>
            <span class='indicator' style='background-color: #fbc02d;'></span>
            <strong>Preventivo</strong><br>
            <small style='color: #666;'>8-10 días</small>
        </div>
        """, unsafe_allow_html=True)


def mostrar_top_productos(df_riesgo, fecha_hoy):
    """Muestra TODOS los productos por nivel con tablas formateadas"""
    st.header("📦 PRODUCTOS POR NIVEL DE RIESGO")
    
    df_filtrado = df_riesgo[df_riesgo['Días_para_Vencimiento'] >= 0].copy()
    
    # Calcular totales
    totales = {}
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
        df_nivel = df_filtrado[df_filtrado['Nivel_Riesgo'] == nivel]
        if len(df_nivel) > 0:
            totales[nivel] = {
                'productos': len(df_nivel),
                'unidades': int(df_nivel['Stock_Inicial'].sum()),
                'valor': df_nivel['Valor_Stock_Costo'].sum()
            }
    
    # Colores y badges
    config_niveles = {
        'VENCIDO': {'color': '🟣', 'badge': 'badge-vencido', 'clase': 'tabla-vencido'},
        'CRITICO': {'color': '🔴', 'badge': 'badge-critico', 'clase': 'tabla-critico'},
        'URGENTE': {'color': '🟠', 'badge': 'badge-urgente', 'clase': 'tabla-urgente'},
        'PREVENTIVO': {'color': '🟡', 'badge': 'badge-preventivo', 'clase': 'tabla-preventivo'}
    }
    
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
        df_nivel = df_filtrado[df_filtrado['Nivel_Riesgo'] == nivel].sort_values('Valor_Stock_Costo', ascending=False)
        
        if len(df_nivel) == 0:
            continue
        
        config = config_niveles[nivel]
        total_valor = totales[nivel]['valor']
        total_unidades = totales[nivel]['unidades']
        total_productos = totales[nivel]['productos']
        
        titulo = f"{config['color']} {nivel} ({total_productos} productos | {total_unidades:,} unidades | {clp(total_valor)} CLP)"
        
        with st.expander(titulo, expanded=False):
            # Preparar datos con badges
            tabla_datos = []
            for _, row in df_nivel.iterrows():
                dias = int(row['Días_para_Vencimiento'])
                unidades = int(row['Stock_Inicial'])
                valor = row['Valor_Stock_Costo']
                fecha_venc = fecha_hoy + timedelta(days=dias)
                
                if nivel == 'VENCIDO':
                    accion = '<span class="badge badge-vencido">DONAR HOY</span>'
                elif nivel == 'CRITICO':
                    accion = '<span class="badge badge-critico">40% dto</span>'
                elif nivel == 'URGENTE':
                    accion = '<span class="badge badge-urgente">25% dto</span>'
                else:
                    accion = '<span class="badge badge-preventivo">15% dto</span>'
                
                tabla_datos.append({
                    '📦 Producto': str(row['Producto'])[:35] if pd.notna(row['Producto']) else 'Sin nombre',
                    '⏰ Días': dias,
                    '📦 Unidades': f"{unidades:,}",
                    '💰 Valor Riesgo': clp(valor),
                    '📅 Fecha Venc.': fecha_venc.strftime('%d/%m/%Y'),
                    '⚡ Acción': accion
                })
            
            df_tabla = pd.DataFrame(tabla_datos)
            
            # Mostrar tabla con HTML personalizado para colores
            clase_css = config.get("clase", "") if config else ""
            
            # Fallback si no hay clase
            if not clase_css:
                clase_css = "dataframe"  # Clase por defecto
            
            tabla_html = df_tabla.to_html(index=False, escape=False)
            
            html_tabla = f'<div class="{clase_css}">{tabla_html}</div>'
            
            st.markdown(html_tabla, unsafe_allow_html=True)
            
# =============================================================================
# MATRIZ DE RIESGO
# =============================================================================
def crear_matriz_riesgo(df_riesgo, total_riesgo, fecha_hoy):
    """Crea y muestra la matriz de riesgo visual"""
    df_viz = df_riesgo.copy()
    sizes = np.clip(df_viz['Valor_Stock_Costo'] / df_viz['Valor_Stock_Costo'].max() * 600 + 40, 40, 600)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    x_map = {'VENCIDO': 0.0, 'CRITICO': 1.0, 'URGENTE': 2.0, 'PREVENTIVO': 3.0}
    df_viz['x_pos'] = df_viz['Nivel_Riesgo'].map(x_map).astype(float)
    
    df_viz = df_viz.sort_values(['Nivel_Riesgo', 'Valor_Stock_Costo'], ascending=[True, True]).reset_index(drop=True)
    df_viz['pos_y_rel'] = df_viz.groupby('Nivel_Riesgo')['Valor_Stock_Costo'].rank(pct=True, method='first')
    
    y_map_base = {'VENCIDO': 0.0, 'CRITICO': 1.0, 'URGENTE': 2.0, 'PREVENTIVO': 3.0}
    df_viz['y_pos'] = df_viz['Nivel_Riesgo'].map(y_map_base) + (df_viz['pos_y_rel'] - 0.5) * 0.8
    
    df_viz['x_jitter'] = df_viz['x_pos']
    df_viz['y_jitter'] = df_viz['y_pos']
    
    ax.scatter(df_viz['x_jitter'], df_viz['y_jitter'],
              s=sizes, c=df_viz['Nivel_Riesgo'].map(COLOR_MAP),
              alpha=0.85, edgecolors='black', linewidth=0.9, zorder=3)
    
    for pos in [0.5, 1.5, 2.5]:
        ax.axhline(pos, color='gray', linestyle='--', linewidth=1.0, alpha=0.35)
        ax.axvline(pos, color='gray', linestyle='--', linewidth=1.0, alpha=0.35)
    
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(['VENCIDO', 'CRÍTICO', 'URGENTE', 'PREVENTIVO'], fontsize=11, fontweight='bold')
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(['Hoy', '1-3 días', '4-7 días', '8-10 días'], fontsize=10)
    
    ax.set_xlabel('Nivel de Riesgo', fontsize=12, fontweight='bold')
    ax.set_ylabel('Días para Vencimiento', fontsize=12, fontweight='bold')
    ax.set_title(f'Riesgo de Vencimiento - {fecha_hoy.date()}\n{len(df_viz)} productos | {clp(total_riesgo)} CLP', fontsize=13, pad=15)
    
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='VENCIDO', markerfacecolor='#9c27b0', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='CRÍTICO', markerfacecolor='#d32f2f', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='URGENTE', markerfacecolor='#f57c00', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='PREVENTIVO', markerfacecolor='#fbc02d', markersize=14),
        plt.scatter([], [], s=80, c='gray', alpha=0.6, label='~100k CLP', edgecolors='none'),
        plt.scatter([], [], s=250, c='gray', alpha=0.6, label='~500k CLP', edgecolors='none'),
        plt.scatter([], [], s=450, c='gray', alpha=0.6, label='~1M+ CLP', edgecolors='none')
    ]
    
    ax.legend(handles=legend_elements, loc='upper left', title='Nivel | Tamaño = Valor', fontsize=10, title_fontsize=11, frameon=True, edgecolor='gray', facecolor='white', borderpad=0.8, labelspacing=1, handletextpad=0.6, columnspacing=1.2, ncol=2)
    
    ax.set_xlim(-0.7, 3.7)
    ax.set_ylim(-0.7, 3.7)
    ax.grid(False)
    plt.tight_layout()
    
    return fig

# =============================================================================
# PLAN DE ACCIÓN 48H
# =============================================================================
def mostrar_plan_accion(df_riesgo, fecha_hoy):
    """Muestra el plan de acción 48H"""
    
    productos_vencidos = df_riesgo[(df_riesgo['Nivel_Riesgo'] == 'VENCIDO') & (df_riesgo['Días_para_Vencimiento'] >= 0)].copy()
    valor_vencido = productos_vencidos['Valor_Stock_Costo'].sum() if len(productos_vencidos) > 0 else 0
    credito_trib = valor_vencido * 0.27
    
    productos_criticos = df_riesgo[(df_riesgo['Nivel_Riesgo'] == 'CRITICO') & (df_riesgo['Días_para_Vencimiento'].between(1, 3))].copy()
    valor_critico = productos_criticos['Valor_Stock_Costo'].sum() if len(productos_criticos) > 0 else 0
    
    productos_urgentes = df_riesgo[(df_riesgo['Nivel_Riesgo'] == 'URGENTE') & (df_riesgo['Días_para_Vencimiento'].between(4, 7))].copy()
    valor_urgente = productos_urgentes['Valor_Stock_Costo'].sum() if len(productos_urgentes) > 0 else 0
    
    valor_rescatado_descuentos = (valor_critico * 0.50) + (valor_urgente * 0.40)
    total_recuperado_base = valor_rescatado_descuentos + credito_trib
    
    if len(productos_vencidos) > 0:
        st.markdown(textwrap.dedent(f"""
        <div class="plan-section plan-vencido">
            <div class="plan-header">
                <h3 class="plan-title">🔴 HOY 08:00 - 10:00 | DONACIONES OBLIGATORIAS</h3>
                <span class="plan-badge" style="color: #d32f2f;">⚠️ PRIORIDAD MÁXIMA</span>
            </div>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">📦 Productos</div><div class="metric-value">{len(productos_vencidos)}</div></div>
                <div class="metric-item"><div class="metric-label">📊 Unidades</div><div class="metric-value">{int(productos_vencidos['Stock_Inicial'].sum()):,}</div></div>
                <div class="metric-item"><div class="metric-label">💰 Valor en Riesgo</div><div class="metric-value">{clp(valor_vencido)}</div></div>
            </div>
            <div class="action-list">
                <div class="action-item" style="border-color: #4caf50;"><span class="action-icon">📋</span><span class="action-text"><strong>Generar acta de donación</strong> - Crédito tributario Ley 19.885</span></div>
            </div>
            <div style="background: #c8e6c9; padding: 15px; border-radius: 10px; margin-top: 15px; text-align: center;">
                <span style="font-size: 1.5rem; font-weight: 700; color: #2e7d32;">💰 +{clp(credito_trib)} CLP de ahorro fiscal proyectado</span>
            </div>
        </div>
        """), unsafe_allow_html=True)
    
    if len(productos_criticos) > 0:
        st.markdown(textwrap.dedent(f"""
        <div class="plan-section plan-critico">
            <div class="plan-header">
                <h3 class="plan-title">🟠 HOY 10:00 - 12:00 | ACCIÓN CRÍTICA</h3>
                <span class="plan-badge" style="color: #f57c00;">⚡ ALTA URGENCIA</span>
            </div>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">📦 SKUs</div><div class="metric-value">{len(productos_criticos)}</div></div>
                <div class="metric-item"><div class="metric-label">📊 Unidades</div><div class="metric-value">{int(productos_criticos['Stock_Inicial'].sum()):,}</div></div>
                <div class="metric-item"><div class="metric-label">💰 Valor</div><div class="metric-value">{clp(valor_critico)}</div></div>
            </div>
            <div class="action-list">
                <div class="action-item" style="border-color: #f57c00;"><span class="action-icon">🏷️</span><span class="action-text"><strong>Markdown 40%</strong> - Reposición prioritaria en entrada principal</span></div>
            </div>
        </div>
        """), unsafe_allow_html=True)
    
    if len(productos_urgentes) > 0:
        st.markdown(textwrap.dedent(f"""
        <div class="plan-section plan-urgente">
            <div class="plan-header">
                <h3 class="plan-title">🟡 HOY 14:00 - 16:00 | ACCIÓN URGENTE</h3>
                <span class="plan-badge" style="color: #f9a825;">⏰ URGENCIA MEDIA</span>
            </div>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">📦 SKUs</div><div class="metric-value">{len(productos_urgentes)}</div></div>
                <div class="metric-item"><div class="metric-label">📊 Unidades</div><div class="metric-value">{int(productos_urgentes['Stock_Inicial'].sum()):,}</div></div>
                <div class="metric-item"><div class="metric-label">💰 Valor</div><div class="metric-value">{clp(valor_urgente)}</div></div>
            </div>
        </div>
        """), unsafe_allow_html=True)
    
    st.markdown(textwrap.dedent("""
    <div class="timeline">
        <div class="timeline-item"><div class="timeline-time">08:00</div><div class="timeline-dot"></div><div class="timeline-action">Donar Vencidos</div></div>
        <div class="timeline-item"><div class="timeline-time">10:00</div><div class="timeline-dot"></div><div class="timeline-action">Críticos (40%)</div></div>
        <div class="timeline-item"><div class="timeline-time">14:00</div><div class="timeline-dot"></div><div class="timeline-action">Urgentes (25%)</div></div>
        <div class="timeline-item"><div class="timeline-time">Mañana</div><div class="timeline-dot"></div><div class="timeline-action">Cierre 48h</div></div>
    </div>
    """), unsafe_allow_html=True)
    
    st.markdown(textwrap.dedent(f"""
    <div class="sensitivity-box">
        <div class="sensitivity-title">📊 ANÁLISIS DE SENSIBILIDAD - ¿Qué pasa si varía la venta?</div>
        <div class="sensitivity-grid">
            <div class="sensitivity-item">
                <div class="sensitivity-label">🔴 Pesimista (-30%)</div>
                <div class="sensitivity-value">{clp((valor_rescatado_descuentos * 0.7) + credito_trib)}</div>
            </div>
            <div class="sensitivity-item" style="background: #e8f5e9; border: 2px solid #4caf50;">
                <div class="sensitivity-label">✅ Escenario Base</div>
                <div class="sensitivity-value" style="color: #2e7d32;">{clp(total_recuperado_base)}</div>
            </div>
            <div class="sensitivity-item">
                <div class="sensitivity-label">🟢 Optimista (+30%)</div>
                <div class="sensitivity-value">{clp((valor_rescatado_descuentos * 1.3) + credito_trib)}</div>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)
    
    st.markdown(textwrap.dedent(f"""
    <div class="plan-section plan-cierre">
        <div class="plan-header">
            <h3 class="plan-title">🔵 MAÑANA 18:00 | CIERRE OPERATIVO 48H</h3>
            <span class="plan-badge" style="color: #1976d2;">📈 RESULTADOS</span>
        </div>
        <div class="metric-grid">
            <div class="metric-item">
                <div class="metric-label">💰 Valor Rescatado</div>
                <div class="metric-value">{clp(valor_rescatado_descuentos)}</div>
                <div class="metric-sub">Ventas proyectadas</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">🏛️ Crédito Tributario</div>
                <div class="metric-value">{clp(credito_trib)}</div>
                <div class="metric-sub">27% s/donaciones</div>
            </div>
            <div class="metric-item" style="background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);">
                <div class="metric-label" style="color: white;">✅ TOTAL RECUPERADO</div>
                <div class="metric-value" style="color: white;">{clp(total_recuperado_base)}</div>
                <div class="metric-sub" style="color: rgba(255,255,255,0.9);">Inyección de liquidez</div>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)
    
    return valor_vencido, credito_trib, valor_critico, valor_urgente, total_recuperado_base

# =============================================================================
# RESUMEN FINAL
# =============================================================================
def mostrar_resumen_final(valor_vencido, credito_trib, productos_criticos, productos_urgentes, total_recuperado):
    """Muestra el resumen final ejecutivo"""
    st.markdown('<h2 style="color: #1a237e; margin-bottom: 20px;">📊 RESUMEN FINAL</h2>', unsafe_allow_html=True)
    
    valor_critico = productos_criticos['Valor_Stock_Costo'].sum() if len(productos_criticos) > 0 else 0
    valor_urgente = productos_urgentes['Valor_Stock_Costo'].sum() if len(productos_urgentes) > 0 else 0
    
    st.markdown(f"""
    <div class="resumen-final-box">
        <h3 style="margin: 0 0 20px 0; text-align: center; color: white;">💵 Impacto Financiero del Plan</h3>
        <div class="resumen-grid">
            <div class="resumen-card">
                <h4 style="color: white;">✅ LO QUE SÍ CONTROLAMOS</h4>
                <div class="resumen-item">
                    <span class="resumen-icon">💰</span>
                    <span class="resumen-text">Crédito tributario: <strong>{clp(credito_trib)} CLP</strong></span>
                </div>
                <div class="resumen-item">
                    <span class="resumen-icon">🏷️</span>
                    <span class="resumen-text">Descuentos: <strong>40%, 25%, 15%</strong></span>
                </div>
            </div>
            <div class="resumen-card">
                <h4 style="color: white;">⚠️ LO QUE NO CONTROLAMOS</h4>
                <div class="resumen-item">
                    <span class="resumen-icon">🌧️</span>
                    <span class="resumen-text">Eventos externos: <strong>Impredecible</strong></span>
                </div>
                <div class="resumen-item">
                    <span class="resumen-icon">📦</span>
                    <span class="resumen-text">Stock residual: <strong>20-30%</strong></span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    conclusion_html = textwrap.dedent(f"""
    <div class="conclusion-box">
        <div class="conclusion-item conclusion-error">
            <strong>❌ Si no donamos:</strong> Pérdida total de <strong>{clp(valor_vencido)} CLP</strong> hoy
        </div>
        <div class="conclusion-item conclusion-success">
            <strong>✅ Con donación:</strong> Recuperamos <strong>{clp(credito_trib)} CLP</strong> en crédito tributario (27%)
        </div>
        <div class="conclusion-item conclusion-info">
            <strong>📈 En 48h:</strong> Rescatamos entre <strong>{clp(valor_critico*0.4 + valor_urgente*0.3)}</strong> y <strong>{clp(valor_critico*0.6 + valor_urgente*0.5)}</strong>
        </div>
        <div style="background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); padding: 25px; border-radius: 12px; text-align: center; color: white; margin-top: 20px;">
            <div style="font-size: 1.2rem; margin-bottom: 10px;">💵 TOTAL RECUPERADO ESPERADO</div>
            <div style="font-size: 3rem; font-weight: 700;">{clp(total_recuperado)} CLP</div>
        </div>
    </div>
    """)
    st.markdown(conclusion_html, unsafe_allow_html=True)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal de la aplicación Streamlit"""
    st.set_page_config(page_title="Sistema de Gestión de Vencimientos", page_icon="📦", layout="wide")
    cargar_css()
    
    st.title("📦 SISTEMA DE GESTIÓN DE VENCIMIENTOS")
    st.markdown("---")
    
    # SIDEBAR - CARGA DE ARCHIVOS
    with st.sidebar:
        st.header("📁 Carga de Archivos")
        st.markdown("---")
        
        archivo_sucursales = st.file_uploader("1️⃣ Sucursales (1_SUCURSALES_MASTER.csv)", type=['csv'], help="Ubicaciones de tiendas con coordenadas GPS", key="uploader_sucursales")
        archivo_productos = st.file_uploader("2️⃣ Productos Master (2_PRODUCTOS_MASTER.csv)", type=['csv'], help="Catálogo maestro de productos", key="uploader_productos")
        archivo_lotes = st.file_uploader("3️⃣ Lotes (3_LOTES_PRODUCTOS.csv)", type=['csv'], help="Información de lotes y caducidad", key="uploader_lotes")
        archivo_inventario = st.file_uploader("4️⃣ Inventario Completo (4_INVENTARIO_COMPLETO_LOTES.csv)", type=['csv'], help="Inventario completo con lotes", key="uploader_inventario")
        archivo_stock = st.file_uploader("5️⃣ Stock Actual Geo (5_STOCK_ACTUAL_GEO_POWERBI.csv)", type=['csv'], help="Stock actual con ubicación geográfica", key="uploader_stock")
        
        st.markdown("---")
        
        archivos_cargados = sum([archivo_sucursales is not None, archivo_productos is not None, archivo_lotes is not None, archivo_inventario is not None, archivo_stock is not None])
        st.progress(archivos_cargados / 5)
        st.caption(f"{archivos_cargados}/5 archivos cargados")
        
        mostrar_mapa = st.checkbox("🗺️ Mostrar Mapa de Sucursales", value=True)
        archivos_esenciales = archivo_stock is not None or archivo_inventario is not None
        
        if archivos_esenciales:
            boton_ejecutar = st.button("✅ Ejecutar Análisis", type="primary", use_container_width=True)
        else:
            st.warning("⚠️ Cargue al menos el archivo de **Stock** o **Inventario** para continuar")
            boton_ejecutar = False
    
    # SESSION STATE
    if 'ejecutar' not in st.session_state:
        st.session_state['ejecutar'] = False
    if 'datos_procesados' not in st.session_state:
        st.session_state['datos_procesados'] = None
    if 'ver_detalle' not in st.session_state:
        st.session_state['ver_detalle'] = False
    if 'plan_aceptado' not in st.session_state:
        st.session_state['plan_aceptado'] = False
    if 'metricas_inventario' not in st.session_state:
        st.session_state['metricas_inventario'] = {}
    if 'metricas_plan' not in st.session_state:
        st.session_state['metricas_plan'] = {}
    
    # EJECUCIÓN DEL ANÁLISIS
    if boton_ejecutar or st.session_state['ejecutar']:
        if archivo_stock is None and archivo_inventario is None:
            st.warning("⚠️ Por favor suba al menos el archivo de Stock o Inventario")
            st.stop()
        
        try:
            with st.spinner("🔄 Cargando y procesando datos..."):
                # Cargar archivo principal
                if archivo_stock:
                    df = pd.read_csv(archivo_stock)
                else:
                    df = pd.read_csv(archivo_inventario)
                
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
                    'Producto_ID': 'ID_Producto',
                    'Lote_ID': 'ID_Lote',
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
                
                if fecha_col and df[fecha_col].notna().any():
                    fecha_hoy = df[fecha_col].max()
                else:
                    fecha_hoy = datetime.now()
                    st.warning("⚠️ No se detectó columna de fecha válida, usando fecha actual")
                
                # Calcular Valor de Stock
                df = calcular_valor_stock(df)
                
                # Aplicar clasificación de riesgo
                if 'Días_para_Vencimiento' in df.columns:
                    df = aplicar_clasificacion(df)
                    df_riesgo = df[(df['Stock_Inicial'] > 0) & (df['Nivel_Riesgo'].isin(['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']))].copy()
                else:
                    df_riesgo = df[df['Stock_Inicial'] > 0].copy()
                    df_riesgo['Nivel_Riesgo'] = 'PREVENTIVO'
                    st.warning("⚠️ No se encontró columna de días para vencimiento")
                
                total_riesgo = df_riesgo['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
                
                # Cargar sucursales
                df_sucursales = None
                if archivo_sucursales:
                    try:
                        df_sucursales = pd.read_csv(archivo_sucursales)
                        df_sucursales.columns = df_sucursales.columns.str.strip()
                        if 'Sucursal' in df_sucursales.columns and 'Ubicacion' in df_riesgo.columns:
                            df_riesgo = df_riesgo.merge(df_sucursales[['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']], left_on='Ubicacion', right_on='Sucursal', how='left')
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo cargar archivo de sucursales: {e}")
                
                st.success(f"✅ Datos procesados correctamente!")
                st.info(f"📅 Análisis para: {fecha_hoy.strftime('%d/%m/%Y')} | Productos en riesgo: {len(df_riesgo)}")
                
                # Verificar antigüedad de datos
                dias_sin_actualizar = (datetime.now() - fecha_hoy).days if isinstance(fecha_hoy, (datetime, pd.Timestamp)) else 0
                if dias_sin_actualizar > 0:
                    st.warning(f"⚠️ **Datos con {dias_sin_actualizar} día(s) de antigüedad**\n\nÚltima actualización: {fecha_hoy.strftime('%d/%m/%Y') if isinstance(fecha_hoy, (datetime, pd.Timestamp)) else 'Desconocida'}\n\nPara un plan efectivo, se recomienda actualizar **diariamente**.")
            
            # MOSTRAR RESULTADOS
            mostrar_resumen_ejecutivo_nuevo(df_riesgo, total_riesgo, fecha_hoy)
            st.markdown("---")
            mostrar_inventario_nuevo(df_riesgo, total_riesgo, fecha_hoy)
            st.markdown("---")
            
            # MAPA DE SUCURSALES
            if mostrar_mapa and 'Latitud' in df_riesgo.columns and 'Longitud' in df_riesgo.columns:
                st.markdown('<div class="section-title-box"><h2>🗺️ Mapa de Sucursales</h2></div>', unsafe_allow_html=True)
                fig, stock_por_sucursal = crear_mapa_inventario(df_riesgo, df_sucursales)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    if stock_por_sucursal is not None and not stock_por_sucursal.empty:
                        st.markdown("### 📊 Resumen por Sucursal")
                        cols_mostrar = [c for c in ['Ubicacion', 'Sucursal', 'Stock_Inicial', 'Valor_Stock_Costo', 'Días_para_Vencimiento'] if c in stock_por_sucursal.columns]
                        if cols_mostrar:
                            st.dataframe(stock_por_sucursal[cols_mostrar].sort_values('Stock_Inicial', ascending=False).head(20), use_container_width=True, hide_index=True)
                st.markdown("---")
            
            # VISUALIZACIÓN
            mostrar_visualizacion_nueva(df_riesgo)
            st.markdown("---")
            
            # VISTA DE DETALLE
            if st.session_state.get('ver_detalle', False):
                with st.expander("📈 MATRIZ DE RIESGO", expanded=True):
                    fig = crear_matriz_riesgo(df_riesgo, total_riesgo, fecha_hoy)
                    st.pyplot(fig)
                    buf = io.BytesIO()
                    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(label="📥 Descargar Matriz (PNG)", data=buf, file_name="matriz_riesgo.png", mime="image/png")
                
                mostrar_top_productos(df_riesgo, fecha_hoy)
                st.markdown("---")
                
                valor_vencido, credito_trib, valor_critico, valor_urgente, total_recuperado = mostrar_plan_accion(df_riesgo, fecha_hoy)
                st.markdown("---")
                
                productos_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']
                productos_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE']
                mostrar_resumen_final(valor_vencido, credito_trib, productos_criticos, productos_urgentes, total_recuperado)
                
                if st.button("⬅️ Volver al Resumen", type="primary"):
                    st.session_state['ver_detalle'] = False
                    st.rerun()
            
            st.session_state['ejecutar'] = True
            st.session_state['datos_procesados'] = {
                'fecha': fecha_hoy,
                'total_riesgo': total_riesgo,
                'total_productos': len(df_riesgo),
                'total_recuperado': st.session_state.get('metricas_plan', {}).get('total_recuperado', 0)
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
