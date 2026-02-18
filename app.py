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
MESES_ESP = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

COLUMNAS_ESPERADAS = {
    'Días_para_Vencimiento': ['Dias_Para_Vencer', 'Días_para_Vencimiento', 'Días para Vencimiento', 'Días_para_Vencer', 'Dias_Vencimiento'],
    'Stock_Inicial': ['Stock_Teorico_Unidades', 'Stock_Inicial', 'Stock Sala', 'Stock_Sala', 'stock_sala', 'Stock', 'Cantidad_Stock'],
    'Costo_Unitario_Neto': ['Valor_Unitario_CLP', 'Costo_Unitario_Neto', 'Costo Unitario Neto', 'costo_unitario_neto', 'Costo', 'Precio_Costo'],
    'Precio_Venta_Bruto': ['Precio_Venta_CLP', 'Precio_Venta_Bruto', 'Precio Venta Bruto', 'precio_venta_bruto', 'Precio'],
    'Producto': ['Producto', 'producto', 'SKU_Descripcion'],
    'Sucursal': ['Sucursal', 'sucursal', 'Tienda', 'Store'],
    'Latitud': ['Latitud', 'lat', 'Latitude', 'Lat'],
    'Longitud': ['Longitud', 'lon', 'Longitude', 'Lng', 'Long'],
    'Fecha': ['Fecha_Movimiento', 'Fecha', 'fecha']
}

COLUMNAS_REQUERIDAS = ['Días_para_Vencimiento', 'Stock_Inicial', 'Producto']

# =============================================================================
# FUNCIONES DE CARGA Y PREPARACIÓN
# =============================================================================
@st.cache_data
def cargar_archivo(archivo):
    """Carga un archivo CSV con manejo de errores"""
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

def parsear_fecha(df, col_fecha='Fecha'):
    """Parsea fechas con múltiples formatos"""
    if col_fecha not in df.columns:
        return df
    
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
        try:
            df[col_fecha] = pd.to_datetime(df[col_fecha], format=fmt, errors='coerce')
            if df[col_fecha].notna().sum() > len(df) * 0.8:
                break
        except:
            continue
    
    # Fallback final
    if df[col_fecha].isna().sum() > len(df) * 0.2:
        df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce', dayfirst=True)
    
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

def aplicar_clasificacion(df, col_dias='Días_para_Vencimiento'):
    """Aplica clasificación de riesgo al dataframe"""
    if col_dias in df.columns:
        df['Nivel_Riesgo'] = df[col_dias].apply(clasificar_riesgo)
    return df

def calcular_valor_stock(df):
    """Calcula el valor del stock en costo"""
    if 'Valor_Stock_Costo' not in df.columns:
        if 'Stock_Inicial' in df.columns and 'Costo_Unitario_Neto' in df.columns:
            df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
        elif 'Stock_Inicial' in df.columns and 'Precio_Venta_Bruto' in df.columns:
            # Estimar costo como 70% del precio de venta
            df['Costo_Unitario_Neto'] = df['Precio_Venta_Bruto'] * 0.70
            df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
        elif 'Stock_Inicial' in df.columns and 'Precio_Venta_CLP' in df.columns:
            df['Costo_Unitario_Neto'] = df['Precio_Venta_CLP'] * 0.70
            df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
        else:
            df['Valor_Stock_Costo'] = df['Stock_Inicial'] if 'Stock_Inicial' in df.columns else 0
    return df

def filtrar_productos_riesgo(df, dias_max=10):
    """Filtra productos en riesgo de vencimiento"""
    return df[
        (df['Stock_Inicial'] > 0) & 
        (df['Nivel_Riesgo'].isin(['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']))
    ].copy()

# =============================================================================
# FUNCIONES DE MAPA
# =============================================================================
def crear_mapa_inventario(df_riesgo, df_sucursales=None):
    """Crea un mapa interactivo con Plotly"""
    
    # Verificar columnas requeridas
    if 'Stock_Inicial' not in df_riesgo.columns:
        st.error("❌ No se encontró columna de Stock_Inicial")
        return None, None
    
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
                lambda x: coordenadas_santiago.get(x, [-33.45, -70.65])[0]
            )
            stock_por_sucursal['Longitud'] = stock_por_sucursal['Sucursal'].map(
                lambda x: coordenadas_santiago.get(x, [-33.45, -70.65])[1]
            )
            stock_por_sucursal['Direccion_Aprox'] = stock_por_sucursal['Sucursal']
        
        # Filtrar sucursales sin coordenadas
        stock_por_sucursal = stock_por_sucursal.dropna(subset=['Latitud', 'Longitud'])
        
        # Función de color por días
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
        
        # Crear figura
        fig = go.Figure()
        
        fig.add_trace(go.Scattermapbox(
            lat=stock_por_sucursal['Latitud'],
            lon=stock_por_sucursal['Longitud'],
            mode='markers',
            marker=dict(
                size=np.clip(stock_por_sucursal['Stock_Inicial'] / 100, 10, 50),
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
def mostrar_resumen_ejecutivo(df_riesgo, total_riesgo, fecha_hoy):
    """Muestra el resumen ejecutivo"""
    st.markdown('<h1 class="main-header">Resúmen</h1>', unsafe_allow_html=True)
    
    total_productos = len(df_riesgo)
    total_unidades = int(df_riesgo['Stock_Inicial'].sum())
    
    col1, col2, col3 = st.columns([1, 2.5, 1])
    
    with col1:
        st.markdown("### Acciones Rápidas")
        if st.button("🔄 Actualizar", use_container_width=True, key="btn_actualizar"):
            st.rerun()
        if st.button("📊 Ver Detalle", use_container_width=True, key="btn_detalle"):
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
    
    with col3:
        st.markdown("### Estado")
        st.success("✅ Activo")
        hora_chile = datetime.now(pytz.timezone('America/Santiago'))
        st.info(f"🕒 {hora_chile.strftime('%H:%M:%S')}")

def mostrar_clasificacion_inventario(df_riesgo):
    """Muestra la clasificación del inventario por nivel de riesgo"""
    st.markdown('<div class="section-title-box"><h2>Inventario</h2></div>', unsafe_allow_html=True)
    st.markdown("### Clasificación por Nivel de Riesgo")
    
    # Calcular métricas por nivel
    metrics = {}
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
        df_nivel = df_riesgo[df_riesgo['Nivel_Riesgo'] == nivel]
        metrics[nivel] = {
            'count': len(df_nivel),
            'unidades': int(df_nivel['Stock_Inicial'].sum()) if len(df_nivel) > 0 else 0,
            'valor': df_nivel['Valor_Stock_Costo'].sum() if len(df_nivel) > 0 else 0
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class='classification-item vencido'>
            <span class='indicator' style='background-color: #9c27b0;'></span>
            <strong>🟣 Vencido:</strong> {metrics['VENCIDO']['count']} productos | 
            {metrics['VENCIDO']['unidades']:,} unidades | {clp(metrics['VENCIDO']['valor'])} CLP
        </div>
        <div class='classification-item critico'>
            <span class='indicator' style='background-color: #d32f2f;'></span>
            <strong>🔴 Crítico (1-3 días):</strong> {metrics['CRITICO']['count']} productos | 
            {metrics['CRITICO']['unidades']:,} unidades | {clp(metrics['CRITICO']['valor'])} CLP
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='classification-item urgente'>
            <span class='indicator' style='background-color: #f57c00;'></span>
            <strong>🟠 Urgente (4-7 días):</strong> {metrics['URGENTE']['count']} productos | 
            {metrics['URGENTE']['unidades']:,} unidades | {clp(metrics['URGENTE']['valor'])} CLP
        </div>
        <div class='classification-item preventivo'>
            <span class='indicator' style='background-color: #fbc02d;'></span>
            <strong>🟡 Preventivo (8-10 días):</strong> {metrics['PREVENTIVO']['count']} productos | 
            {metrics['PREVENTIVO']['unidades']:,} unidades | {clp(metrics['PREVENTIVO']['valor'])} CLP
        </div>
        """, unsafe_allow_html=True)
    
    return metrics

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN - GRÁFICOS
# =============================================================================
def mostrar_visualizacion(df_riesgo):
    """Muestra gráficos de distribución del inventario"""
    st.markdown('<div class="section-title-box"><h2>Visualización</h2></div>', unsafe_allow_html=True)
    
    # Calcular datos para gráficos
    data_nivel = [
        len(df_riesgo[df_riesgo['Nivel_Riesgo'] == n]) 
        for n in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']
    ]
    data_valor = [
        df_riesgo[df_riesgo['Nivel_Riesgo'] == n]['Valor_Stock_Costo'].sum() 
        for n in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']
    ]
    
    # Crear subplots
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{'type':'domain'}, {'type':'domain'}]],
        subplot_titles=['Distribución por Cantidad', 'Distribución por Valor (CLP)']
    )
    
    labels = ['Vencido', 'Crítico (1-3d)', 'Urgente (4-7d)', 'Preventivo (8-10d)']
    colors = ['#9c27b0', '#d32f2f', '#f57c00', '#fbc02d']
    
    # Gráfico 1 - Por cantidad
    fig.add_trace(go.Pie(
        labels=labels,
        values=data_nivel,
        marker_colors=colors,
        hole=0.4,
        textinfo='percent+label',
        textposition='inside',
        textfont=dict(color='white', size=10),
        name='Por Cantidad'
    ), row=1, col=1)
    
    # Gráfico 2 - Por valor
    fig.add_trace(go.Pie(
        labels=labels,
        values=data_valor,
        marker_colors=colors,
        hole=0.4,
        textinfo='percent',
        textposition='inside',
        textfont=dict(color='white', size=10),
        name='Por Valor'
    ), row=1, col=2)
    
    fig.update_layout(
        height=400,
        showlegend=False,
        title_text="<b>Distribución del Inventario en Riesgo</b>",
        title_x=0.5,
        title_font_size=18,
        margin=dict(t=60, b=20, l=20, r=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Leyenda
    st.markdown("### Leyenda de Colores")
    cols = st.columns(4)
    leyenda = [
        ('🟣 Vencido', '#9c27b0', 'Hoy'),
        ('🔴 Crítico', '#d32f2f', '1-3 días'),
        ('🟠 Urgente', '#f57c00', '4-7 días'),
        ('🟡 Preventivo', '#fbc02d', '8-10 días')
    ]
    for i, (texto, color, sub) in enumerate(leyenda):
        with cols[i]:
            st.markdown(f"""
            <div style='padding:10px;border-radius:8px;background:{color}20;border-left:4px solid {color};'>
                <strong style='color:{color}'>{texto}</strong><br>
                <small style='color:#666'>{sub}</small>
            </div>
            """, unsafe_allow_html=True)

# =============================================================================
# FUNCIONES DE DETALLE Y TABLAS
# =============================================================================
def mostrar_detalle_productos(df_riesgo, fecha_hoy, nivel=None):
    """Muestra tabla detallada de productos"""
    
    if nivel:
        df_filtrado = df_riesgo[df_riesgo['Nivel_Riesgo'] == nivel].copy()
        titulo = f"📦 Productos {nivel}"
        clase_css = f"tabla-{nivel.lower()}"
    else:
        df_filtrado = df_riesgo.copy()
        titulo = "📦 Todos los Productos en Riesgo"
        clase_css = "dataframe"
    
    if len(df_filtrado) == 0:
        st.info(f"No hay productos en nivel {nivel}" if nivel else "No hay productos en riesgo")
        return
    
    # Preparar datos para tabla
    tabla_datos = []
    for _, row in df_filtrado.iterrows():
        dias = int(row['Días_para_Vencimiento']) if pd.notna(row['Días_para_Vencimiento']) else 0
        fecha_venc = fecha_hoy + timedelta(days=dias) if dias >= 0 else fecha_hoy
        
        # Badge de acción según nivel
        if row['Nivel_Riesgo'] == 'VENCIDO':
            accion = '<span class="badge badge-vencido">🎁 DONAR</span>'
        elif row['Nivel_Riesgo'] == 'CRITICO':
            accion = '<span class="badge badge-critico">🏷️ -40%</span>'
        elif row['Nivel_Riesgo'] == 'URGENTE':
            accion = '<span class="badge badge-urgente">🏷️ -25%</span>'
        else:
            accion = '<span class="badge badge-preventivo">🏷️ -15%</span>'
        
        tabla_datos.append({
            '📦 Producto': str(row['Producto'])[:40] if pd.notna(row.get('Producto')) else 'Sin nombre',
            '📍 Sucursal': row.get('Sucursal', 'N/A'),
            '⏰ Días': dias,
            '📅 Vence': fecha_venc.strftime('%d/%m/%Y'),
            '📦 Unidades': f"{int(row['Stock_Inicial']):,}".replace(',', '.'),
            '💰 Valor': clp(row['Valor_Stock_Costo']),
            '⚡ Acción': accion
        })
    
    df_tabla = pd.DataFrame(tabla_datos)
    
    # Mostrar con expander si hay muchos registros
    with st.expander(f"{titulo} ({len(df_tabla)} registros)", expanded=(nivel is None)):
        st.dataframe(
            df_tabla,
            use_container_width=True,
            hide_index=True,
            column_config={
                "💰 Valor": st.column_config.NumberColumn(format="%s CLP")
            }
        )
        
        # Botón de descarga
        csv = df_tabla.to_csv(index=False, sep=';', decimal=',')
        st.download_button(
            label=f"📥 Descargar {titulo}",
            data=csv,
            file_name=f"productos_{nivel or 'riesgo'}_{fecha_hoy.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# =============================================================================
# FUNCIONES DE PLAN DE ACCIÓN
# =============================================================================
def mostrar_plan_accion(df_riesgo, fecha_hoy):
    """Muestra el plan de acción recomendado"""
    st.markdown('<div class="section-title-box"><h2>⏱️ Plan de Acción 48H</h2></div>', unsafe_allow_html=True)
    
    # Calcular valores por nivel
    productos_vencidos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO']
    productos_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']
    productos_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE']
    
    valor_vencido = productos_vencidos['Valor_Stock_Costo'].sum() if len(productos_vencidos) > 0 else 0
    valor_critico = productos_criticos['Valor_Stock_Costo'].sum() if len(productos_criticos) > 0 else 0
    valor_urgente = productos_urgentes['Valor_Stock_Costo'].sum() if len(productos_urgentes) > 0 else 0
    
    # Cálculo de recuperación estimada
    credito_tributario = valor_vencido * 0.27  # Ley 19.885 Chile
    recuperacion_criticos = valor_critico * 0.50  # 40% descuento ~ 50% recuperación
    recuperacion_urgentes = valor_urgente * 0.40  # 25% descuento ~ 40% recuperación
    total_recuperado = credito_tributario + recuperacion_criticos + recuperacion_urgentes
    
    # Sección 1: Vencidos - Donación
    if len(productos_vencidos) > 0:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#ffebee,#ffcdd2);padding:20px;border-radius:12px;border-left:5px solid #d32f2f;margin:15px 0;'>
            <h4 style='color:#c62828;margin:0 0 10px 0;'>🔴 HOY 08:00-10:00 | DONACIONES OBLIGATORIAS</h4>
            <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:15px 0;'>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Productos</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#c62828;'>{len(productos_vencidos)}</div>
                </div>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Unidades</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#c62828;'>{int(productos_vencidos["Stock_Inicial"].sum()):,}</div>
                </div>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Valor en Riesgo</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#c62828;'>{clp(valor_vencido)}</div>
                </div>
            </div>
            <div style='background:#c8e6c9;padding:12px;border-radius:8px;text-align:center;margin-top:10px;'>
                <strong style='color:#2e7d32;font-size:1.1rem;'>💰 +{clp(credito_tributario)} CLP de crédito tributario proyectado</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Sección 2: Críticos - Descuento 40%
    if len(productos_criticos) > 0:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#fff3e0,#ffe0b2);padding:20px;border-radius:12px;border-left:5px solid #f57c00;margin:15px 0;'>
            <h4 style='color:#e65100;margin:0 0 10px 0;'>🟠 HOY 10:00-12:00 | ACCIÓN CRÍTICA (-40%)</h4>
            <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:15px 0;'>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Productos</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#e65100;'>{len(productos_criticos)}</div>
                </div>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Unidades</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#e65100;'>{int(productos_criticos["Stock_Inicial"].sum()):,}</div>
                </div>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Valor</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#e65100;'>{clp(valor_critico)}</div>
                </div>
            </div>
            <div style='background:#fff9c4;padding:12px;border-radius:8px;text-align:center;margin-top:10px;'>
                <strong style='color:#f57c00;'>🎯 Recuperación estimada: {clp(recuperacion_criticos)} CLP</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Sección 3: Urgentes - Descuento 25%
    if len(productos_urgentes) > 0:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#fffde7,#fff9c4);padding:20px;border-radius:12px;border-left:5px solid #fbc02d;margin:15px 0;'>
            <h4 style='color:#f9a825;margin:0 0 10px 0;'>🟡 HOY 14:00-16:00 | ACCIÓN URGENTE (-25%)</h4>
            <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:15px 0;'>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Productos</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#f9a825;'>{len(productos_urgentes)}</div>
                </div>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Unidades</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#f9a825;'>{int(productos_urgentes["Stock_Inicial"].sum()):,}</div>
                </div>
                <div style='background:white;padding:15px;border-radius:8px;text-align:center;'>
                    <div style='font-size:0.8rem;color:#666;'>Valor</div>
                    <div style='font-size:1.5rem;font-weight:700;color:#f9a825;'>{clp(valor_urgente)}</div>
                </div>
            </div>
            <div style='background:#e8f5e9;padding:12px;border-radius:8px;text-align:center;margin-top:10px;'>
                <strong style='color:#2e7d32;'>🎯 Recuperación estimada: {clp(recuperacion_urgentes)} CLP</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Resumen financiero
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a237e,#283593);color:white;padding:25px;border-radius:15px;margin:20px 0;'>
        <h3 style='margin:0 0 20px 0;text-align:center;'>💵 Resumen Financiero del Plan</h3>
        <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:15px;'>
            <div style='background:rgba(255,255,255,0.15);padding:20px;border-radius:10px;text-align:center;'>
                <div style='font-size:0.9rem;opacity:0.9;'>Crédito Tributario (27%)</div>
                <div style='font-size:1.8rem;font-weight:700;margin:10px 0;'>{clp(credito_tributario)}</div>
                <div style='font-size:0.8rem;opacity:0.8;'>CLP proyectados</div>
            </div>
            <div style='background:rgba(255,255,255,0.15);padding:20px;border-radius:10px;text-align:center;'>
                <div style='font-size:0.9rem;opacity:0.9;'>Recuperación Descuentos</div>
                <div style='font-size:1.8rem;font-weight:700;margin:10px 0;'>{clp(recuperacion_criticos + recuperacion_urgentes)}</div>
                <div style='font-size:0.8rem;opacity:0.8;'>48 horas estimadas</div>
            </div>
            <div style='background:rgba(76,175,80,0.3);padding:20px;border-radius:10px;text-align:center;border:2px solid #4caf50;'>
                <div style='font-size:0.9rem;color:#81c784;'>✅ TOTAL RECUPERADO</div>
                <div style='font-size:2rem;font-weight:700;margin:10px 0;color:#4caf50;'>{clp(total_recuperado)}</div>
                <div style='font-size:0.8rem;color:#a5d6a7;'>Inyección de liquidez</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Timeline visual
    st.markdown("### ⏰ Timeline de Ejecución")
    cols = st.columns(4)
    timeline = [
        ("🔴 HOY 08:00", "Donaciones\n• Acta Ley 19.885\n• Contacto fundación"),
        ("🟠 HOY 10:00", "Críticos -40%\n• Reposición entrada\n• Etiquetas descuento"),
        ("🟡 HOY 14:00", "Urgentes -25%\n• Promoción góndola\n• Monitoreo ventas"),
        ("🔵 MAÑANA 18:00", "Cierre operativo\n• Reporte final\n• Re-evaluación stock")
    ]
    for i, (tiempo, accion) in enumerate(timeline):
        with cols[i]:
            st.markdown(f"""
            <div style='text-align:center;padding:15px;background:#f5f5f5;border-radius:10px;border-top:4px solid {"#d32f2f" if i==0 else "#f57c00" if i==1 else "#fbc02d" if i==2 else "#1976d2"};'>
                <strong style='color:#1a237e'>{tiempo}</strong><br>
                <small style='color:#666'>{accion.replace(chr(10), "<br>")}</small>
            </div>
            """, unsafe_allow_html=True)
    
    return {
        'credito_tributario': credito_tributario,
        'recuperacion_descuentos': recuperacion_criticos + recuperacion_urgentes,
        'total_recuperado': total_recuperado
    }

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal de la aplicación Streamlit"""
    
    # Configuración de página
    st.set_page_config(
        page_title="Sistema de Gestión de Vencimientos",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Cargar CSS personalizado
    cargar_css()
    
    # Título principal
    st.title("📦 SISTEMA DE GESTIÓN DE VENCIMIENTOS")
    st.markdown("---")
    
    # =============================================================================
    # SIDEBAR - CARGA DE ARCHIVOS
    # =============================================================================
    with st.sidebar:
        st.header("📁 Carga de Archivos")
        st.markdown("---")
        
        st.markdown("**Archivos Disponibles:**")
        
        archivo_sucursales = st.file_uploader(
            "1️⃣ Sucursales (opcional)",
            type=['csv'],
            help="Ubicaciones con coordenadas GPS",
            key="uploader_sucursales"
        )
        
        archivo_stock = st.file_uploader(
            "2️⃣ Stock Actual (requerido)",
            type=['csv'],
            help="Inventario con días para vencer",
            key="uploader_stock"
        )
        
        archivo_productos = st.file_uploader(
            "3️⃣ Productos Master (opcional)",
            type=['csv'],
            help="Catálogo de productos",
            key="uploader_productos"
        )
        
        st.markdown("---")
        
        # Progreso de carga
        archivos_cargados = sum([
            archivo_sucursales is not None,
            archivo_stock is not None,
            archivo_productos is not None
        ])
        st.progress(archivos_cargados / 3)
        st.caption(f"{archivos_cargados}/3 archivos")
        
        # Opciones adicionales
        mostrar_mapa = st.checkbox("🗺️ Mostrar Mapa", value=True)
        mostrar_detalle = st.checkbox("📋 Mostrar Tablas Detalladas", value=True)
        
        # Botón de ejecución
        archivos_listos = archivo_stock is not None
        if archivos_listos:
            boton_ejecutar = st.button("✅ Ejecutar Análisis", type="primary", use_container_width=True)
        else:
            st.warning("⚠️ Cargue **Stock Actual** para continuar")
            boton_ejecutar = False
    
    # =============================================================================
    # SESSION STATE
    # =============================================================================
    if 'ejecutar' not in st.session_state:
        st.session_state['ejecutar'] = False
    if 'ver_detalle' not in st.session_state:
        st.session_state['ver_detalle'] = False
    if 'datos_procesados' not in st.session_state:
        st.session_state['datos_procesados'] = None
    
    # =============================================================================
    # EJECUCIÓN DEL ANÁLISIS
    # =============================================================================
    if boton_ejecutar or st.session_state['ejecutar']:
        
        if archivo_stock is None:
            st.warning("⚠️ Por favor cargue el archivo de Stock Actual")
            st.stop()
        
        try:
            with st.spinner("🔄 Procesando datos..."):
                
                # Cargar archivo principal
                df = pd.read_csv(archivo_stock)
                df.columns = df.columns.str.strip()
                
                # Mapear columnas
                df = mapear_columnas(df)
                
                # Parsear fecha si existe
                if 'Fecha' in df.columns or 'Fecha_Movimiento' in df.columns:
                    col_fecha = 'Fecha' if 'Fecha' in df.columns else 'Fecha_Movimiento'
                    df = parsear_fecha(df, col_fecha)
                    fecha_hoy = df[col_fecha].max() if df[col_fecha].notna().any() else datetime.now()
                else:
                    fecha_hoy = datetime.now()
                
                # Calcular valor de stock
                df = calcular_valor_stock(df)
                
                # Aplicar clasificación de riesgo
                df = aplicar_clasificacion(df)
                
                # Filtrar productos en riesgo
                df_riesgo = filtrar_productos_riesgo(df)
                
                # Calcular total en riesgo
                total_riesgo = df_riesgo['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
                
                # Cargar sucursales para enriquecimiento
                df_sucursales = None
                if archivo_sucursales:
                    try:
                        df_sucursales = pd.read_csv(archivo_sucursales)
                        df_sucursales.columns = df_sucursales.columns.str.strip()
                    except:
                        st.warning("⚠️ No se pudo procesar archivo de sucursales")
                
                st.success("✅ Datos procesados correctamente!")
                st.info(f"📅 Análisis: {fecha_hoy.strftime('%d/%m/%Y')} | Riesgo: {len(df_riesgo)} productos | {clp(total_riesgo)} CLP")
                
                # Verificar antigüedad de datos
                if isinstance(fecha_hoy, (datetime, pd.Timestamp)):
                    dias_antiguedad = (datetime.now() - fecha_hoy).days
                    if dias_antiguedad > 0:
                        st.warning(f"⚠️ Datos con {dias_antiguedad} día(s) de antigüedad. Se recomienda actualización diaria.")
                
                # =============================================================================
                # MOSTRAR RESULTADOS
                # =============================================================================
                
                # 1. Resumen ejecutivo
                mostrar_resumen_ejecutivo(df_riesgo, total_riesgo, fecha_hoy)
                st.markdown("---")
                
                # 2. Clasificación de inventario
                metrics = mostrar_clasificacion_inventario(df_riesgo)
                st.markdown("---")
                
                # 3. Mapa de sucursales
                if mostrar_mapa and 'Latitud' in df.columns and 'Longitud' in df.columns:
                    st.markdown('<div class="section-title-box"><h2>🗺️ Mapa de Sucursales</h2></div>', unsafe_allow_html=True)
                    fig, stock_sucursal = crear_mapa_inventario(df_riesgo, df_sucursales)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    st.markdown("---")
                
                # 4. Visualización gráfica
                mostrar_visualizacion(df_riesgo)
                st.markdown("---")
                
                # 5. Tablas detalladas por nivel
                if mostrar_detalle:
                    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
                        mostrar_detalle_productos(df_riesgo, fecha_hoy, nivel)
                    st.markdown("---")
                
                # 6. Plan de acción
                plan_resultados = mostrar_plan_accion(df_riesgo, fecha_hoy)
                
                # Guardar resultados en session state
                st.session_state['ejecutar'] = True
                st.session_state['datos_procesados'] = {
                    'fecha': fecha_hoy,
                    'total_riesgo': total_riesgo,
                    'total_productos': len(df_riesgo),
                    'plan_resultados': plan_resultados
                }
                
                # Botón para volver a ejecutar
                if st.button("🔄 Nuevo Análisis", type="secondary"):
                    st.session_state['ejecutar'] = False
                    st.rerun()
        
        except FileNotFoundError as e:
            st.error(f"❌ Archivo no encontrado: {e}")
        except pd.errors.EmptyDataError:
            st.error("❌ El archivo CSV está vacío")
        except pd.errors.ParserError as e:
            st.error(f"❌ Error de formato CSV: {e}")
        except KeyError as e:
            st.error(f"❌ Columna requerida no encontrada: {e}")
            with st.expander("🔍 Ver columnas disponibles"):
                if 'df' in locals():
                    st.write(df.columns.tolist())
        except Exception as e:
            st.error(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Detalles del error"):
                st.exception(e)
    
    else:
        # Pantalla de bienvenida
        st.info("👈 Seleccione los archivos en el panel lateral y presione **Ejecutar Análisis**")
        
        st.markdown("""
        ### 📋 Instrucciones de Uso
        
        1. **Cargue el archivo de Stock Actual** (requerido)
        2. Opcionalmente cargue Sucursales y Productos Master
        3. Presione "Ejecutar Análisis"
        4. Revise el resumen ejecutivo y clasificación
        5. Consulte el mapa y gráficos de distribución
        6. Ejecute el plan de acción recomendado
        
        ### 🎯 Clasificación de Riesgo
        
        | Nivel | Días | Acción Recomendada |
        |-------|------|-------------------|
        | 🟣 Vencido | < 0 | Donación inmediata (crédito 27%) |
        | 🔴 Crítico | 1-3 | Descuento 40% - Alta prioridad |
        | 🟠 Urgente | 4-7 | Descuento 25% - Monitoreo |
        | 🟡 Preventivo | 8-10 | Descuento 15% - Planificación |
        """)

if __name__ == "__main__":
    main()
