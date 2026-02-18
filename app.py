#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SISTEMA DE GESTIÓN DE INVENTARIO - ANÁLISIS BI COMPLETO
================================================================================
Este script realiza:
- ETL (Extract, Transform, Load) de los 5 archivos CSV
- Análisis de inventario por estado (Vencido, Crítico, Urgente, Preventivo)
- Visualización geográfica con mapa interactivo
- Dashboard estilo BI profesional

Archivos requeridos en la carpeta data/:
- 1_SUCURSALES_MASTER.csv
- 2_PRODUCTOS_MASTER.csv
- 3_LOTES_PRODUCTOS.csv
- 4_INVENTARIO_COMPLETO_LOTES.csv
- 5_STOCK_ACTUAL_GEO_POWERBI.csv

Autor: MiniMax Agent
Fecha: 2026-02-18
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import pytz

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# =============================================================================

def configurar_pagina():
    """Configura la página principal de Streamlit"""
    st.set_page_config(
        page_title="Sistema de Gestión de Inventario BI",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# =============================================================================
# FUNCIONES DE FORMATO
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

# Colores del semáforo
COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # Violeta
    'CRITICO': '#d32f2f',      # Rojo
    'URGENTE': '#f57c00',      # Naranja
    'PREVENTIVO': '#fbc02d',   # Amarillo
    'NORMAL': '#4caf50'        # Verde
}

# =============================================================================
# CSS PERSONALIZADO - ESTILO BI
# =============================================================================

def cargar_css():
    """Inyecta estilos CSS personalizados para el dashboard"""
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
    
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 5px solid;
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
    .normal { background: #e8f5e9; color: #2e7d32; border-left: 5px solid #4caf50; }
    
    .total-box {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .total-box h3 {
        color: white;
        margin: 0 0 15px 0;
        font-size: 1.5rem;
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
    .badge-normal { background: #e8f5e9; color: #2e7d32; }
    
    .indicator {
        display: inline-block;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        margin-right: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .legend-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# ETL - PROCESO DE EXTRACT, TRANSFORM, LOAD
# =============================================================================

def cargar_datos_etl():
    """
    Función principal de ETL:
    - Extrae datos de los 5 archivos CSV
    - Transforma y limpia los datos
    - Los integra en un DataFrame unificado
    """
    
    # Rutas de los archivos (ajustar según sea necesario)
    base_path = "user_input_files/"
    
    try:
        # =========================================================================
        # EXTRACT - Extracción de datos
        # =========================================================================
        
        # Cargar archivos CSV
        df_sucursales = pd.read_csv(f"{base_path}1_SUCURSALES_MASTER.csv")
        df_productos = pd.read_csv(f"{base_path}2_PRODUCTOS_MASTER.csv")
        df_lotes = pd.read_csv(f"{base_path}3_LOTES_PRODUCTOS.csv")
        df_inventario = pd.read_csv(f"{base_path}4_INVENTARIO_COMPLETO_LOTES.csv")
        df_stock_geo = pd.read_csv(f"{base_path}5_STOCK_ACTUAL_GEO_POWERBI.csv")
        
        # Limpiar nombres de columnas
        for df in [df_sucursales, df_productos, df_lotes, df_inventario, df_stock_geo]:
            df.columns = df.columns.str.strip()
        
        # =========================================================================
        # TRANSFORM - Transformación de datos
        # =========================================================================
        
        # 1. Procesar fechas
        for df in [df_inventario, df_stock_geo]:
            if 'Fecha_Vencimiento_Lote' in df.columns:
                df['Fecha_Vencimiento_Lote'] = pd.to_datetime(
                    df['Fecha_Vencimiento_Lote'], 
                    errors='coerce'
                )
            if 'Fecha_Movimiento' in df.columns:
                df['Fecha_Movimiento'] = pd.to_datetime(
                    df['Fecha_Movimiento'], 
                    errors='coerce'
                )
        
        # 2. Procesar coordenadas
        if 'Latitud' in df_stock_geo.columns:
            df_stock_geo['Latitud'] = pd.to_numeric(df_stock_geo['Latitud'], errors='coerce')
            df_stock_geo['Longitud'] = pd.to_numeric(df_stock_geo['Longitud'], errors='coerce')
        
        # 3. Clasificar riesgo basado en días para vencer
        def clasificar_riesgo(dias):
            if pd.isna(dias):
                return 'NORMAL'
            elif dias <= 0:
                return 'VENCIDO'
            elif dias <= 3:
                return 'CRITICO'
            elif dias <= 7:
                return 'URGENTE'
            elif dias <= 10:
                return 'PREVENTIVO'
            else:
                return 'NORMAL'
        
        # Aplicar clasificación al stock geo
        if 'Dias_Para_Vencer' in df_stock_geo.columns:
            df_stock_geo['Nivel_Riesgo'] = df_stock_geo['Dias_Para_Vencer'].apply(clasificar_riesgo)
        
        # 4. Calcular valor de stock
        if 'Stock_Teorico_Unidades' in df_stock_geo.columns and 'Precio_Venta_CLP' in df_stock_geo.columns:
            df_stock_geo['Valor_Stock'] = df_stock_geo['Stock_Teorico_Unidades'] * df_stock_geo['Precio_Venta_CLP']
        
        # 5. Unir datos de sucursales para obtener coordenadas faltantes
        if 'Latitud' not in df_stock_geo.columns or df_stock_geo['Latitud'].isna().all():
            df_stock_geo = df_stock_geo.merge(
                df_sucursales[['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']],
                on='Sucursal',
                how='left',
                suffixes=('', '_suc')
            )
        
        # 6. Unir datos de productos
        if 'Producto_ID' in df_stock_geo.columns:
            # Combinar con datos de productos si es necesario
            df_stock_geo = df_stock_geo.merge(
                df_productos[['Producto_ID', 'Categoria', 'Categoria_Rotacion']],
                on='Producto_ID',
                how='left'
            )
        
        # =========================================================================
        # LOAD - Carga de datos integrados
        # =========================================================================
        
        return {
            'sucursales': df_sucursales,
            'productos': df_productos,
            'lotes': df_lotes,
            'inventario': df_inventario,
            'stock_geo': df_stock_geo
        }
        
    except FileNotFoundError as e:
        st.error(f"Error: No se encontró el archivo - {e}")
        return None
    except Exception as e:
        st.error(f"Error en el proceso ETL: {e}")
        return None

# =============================================================================
# FUNCIONES DE ANÁLISIS
# =============================================================================

def analizar_inventario(df_stock):
    """Analiza el inventario y retorna estadísticas por nivel de riesgo"""
    
    if df_stock is None or len(df_stock) == 0:
        return None
    
    # Calcular estadísticas por nivel de riesgo
    stats = {}
    
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO', 'NORMAL']:
        df_nivel = df_stock[df_stock['Nivel_Riesgo'] == nivel]
        
        stats[nivel] = {
            'productos': len(df_nivel),
            'unidades': int(df_nivel['Stock_Teorico_Unidades'].sum()) if 'Stock_Teorico_Unidades' in df_nivel.columns else 0,
            'valor': df_nivel['Valor_Stock'].sum() if 'Valor_Stock' in df_nivel.columns else 0
        }
    
    # Totales
    stats['TOTAL'] = {
        'productos': len(df_stock),
        'unidades': int(df_stock['Stock_Teorico_Unidades'].sum()) if 'Stock_Teorico_Unidades' in df_stock.columns else 0,
        'valor': df_stock['Valor_Stock'].sum() if 'Valor_Stock' in df_stock.columns else 0
    }
    
    return stats

def analizar_por_sucursal(df_stock):
    """Analiza el inventario por sucursal"""
    
    if df_stock is None or len(df_stock) == 0:
        return None
    
    # Agrupar por sucursal
    sucursal_stats = df_stock.groupby('Sucursal').agg({
        'Stock_Teorico_Unidades': 'sum',
        'Valor_Stock': 'sum'
    }).reset_index()
    
    # Contar productos por nivel de riesgo por sucursal
    riesgo_por_sucursal = df_stock.groupby(['Sucursal', 'Nivel_Riesgo']).size().unstack(fill_value=0)
    
    # Unir datos
    sucursal_stats = sucursal_stats.merge(
        riesgo_por_sucursal.reset_index(),
        on='Sucursal',
        how='left'
    )
    
    # Agregar coordenadas
    if 'Latitud' in df_stock.columns and 'Longitud' in df_stock.columns:
        coords = df_stock.groupby('Sucursal').agg({
            'Latitud': 'first',
            'Longitud': 'first'
        }).reset_index()
        sucursal_stats = sucursal_stats.merge(coords, on='Sucursal', how='left')
    
    return sucursal_stats

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN
# =============================================================================

def crear_mapa_stock(df_stock):
    """Crea un mapa interactivo con el stock por sucursal"""
    
    if df_stock is None or len(df_stock) == 0:
        st.warning("No hay datos para mostrar en el mapa")
        return None
    
    # Preparar datos para el mapa
    df_mapa = df_stock.copy()
    
    # Filtrar solo registros con coordenadas válidas
    df_mapa = df_mapa[
        (df_mapa['Latitud'].notna()) & 
        (df_mapa['Longitud'].notna()) &
        (df_mapa['Stock_Teorico_Unidades'] > 0)
    ]
    
    if len(df_mapa) == 0:
        st.warning("No hay coordenadas válidas para mostrar en el mapa")
        return None
    
    # Agregar datos por sucursal para el mapa
    df_sucursal_mapa = df_mapa.groupby('Sucursal').agg({
        'Stock_Teorico_Unidades': 'sum',
        'Valor_Stock': 'sum',
        'Latitud': 'first',
        'Longitud': 'first',
        'Direccion_Aprox': 'first'
    }).reset_index()
    
    # Agregar conteo de productos por riesgo
    riesgo_counts = df_mapa.groupby(['Sucursal', 'Nivel_Riesgo']).size().unstack(fill_value=0)
    df_sucursal_mapa = df_sucursal_mapa.merge(
        riesgo_counts.reset_index(),
        on='Sucursal',
        how='left'
    )
    
    # Crear el mapa con Plotly
    fig = px.scatter_mapbox(
        df_sucursal_mapa,
        lat="Latitud",
        lon="Longitud",
        size="Stock_Teorico_Unidades",
        color="Valor_Stock",
        hover_name="Sucursal",
        hover_data={
            "Stock_Teorico_Unidades": True,
            "Valor_Stock": ":,.0f",
            "Latitud": False,
            "Longitud": False
        },
        color_continuous_scale="Viridis",
        size_max=50,
        zoom=10,
        center={"lat": -33.45, "lon": -70.65},
        mapbox_style="open-street-map",
        title="<b>Mapa de Stock por Sucursal</b>"
    )
    
    fig.update_layout(
        height=600,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        title_font_size=20,
        title_font_color='#1a237e'
    )
    
    return fig

def crear_mapa_riesgo(df_stock):
    """Crea un mapa highlighting el riesgo por sucursal"""
    
    if df_stock is None or len(df_stock) == 0:
        return None
    
    # Preparar datos
    df_mapa = df_stock.copy()
    df_mapa = df_mapa[
        (df_mapa['Latitud'].notna()) & 
        (df_mapa['Longitud'].notna()) &
        (df_mapa['Stock_Teorico_Unidades'] > 0)
    ]
    
    if len(df_mapa) == 0:
        return None
    
    # Calcular stock en riesgo por sucursal
    df_riesgo = df_mapa[df_mapa['Nivel_Riesgo'].isin(['VENCIDO', 'CRITICO', 'URGENTE'])]
    
    df_sucursal_riesgo = df_riesgo.groupby('Sucursal').agg({
        'Stock_Teorico_Unidades': 'sum',
        'Valor_Stock': 'sum',
        'Latitud': 'first',
        'Longitud': 'first'
    }).reset_index()
    
    # Crear mapa de riesgo
    fig = px.scatter_mapbox(
        df_sucursal_riesgo,
        lat="Latitud",
        lon="Longitud",
        size="Stock_Teorico_Unidades",
        color="Valor_Stock",
        hover_name="Sucursal",
        hover_data={
            "Stock_Teorico_Unidades": True,
            "Valor_Stock": ":,.0f"
        },
        color_continuous_scale="Reds",
        size_max=50,
        zoom=10,
        center={"lat": -33.45, "lon": -70.65},
        mapbox_style="open-street-map",
        title="<b>Mapa de Inventario en Riesgo por Sucursal</b>"
    )
    
    fig.update_layout(
        height=600,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        title_font_size=20,
        title_font_color='#d32f2f'
    )
    
    return fig

def crear_graficos_estado(df_stock, stats):
    """Crea gráficos de distribución del inventario"""
    
    if stats is None:
        return None
    
    # Preparar datos para gráficos
    niveles = ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO', 'NORMAL']
    colores = ['#9c27b0', '#d32f2f', '#f57c00', '#fbc02d', '#4caf50']
    
    productos = [stats[n]['productos'] for n in niveles]
    unidades = [stats[n]['unidades'] for n in niveles]
    valores = [stats[n]['valor'] for n in niveles]
    
    # Crear subplots
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{'type': 'pie'}, {'type': 'pie'}, {'type': 'pie'}]],
        subplot_titles=['<b>Por Cantidad de SKUs</b>', '<b>Por Unidades</b>', '<b>Por Valor (CLP)</b>']
    )
    
    # Gráfico 1 - SKUs
    fig.add_trace(go.Pie(
        labels=niveles,
        values=productos,
        marker_colors=colores,
        hole=0.4,
        textinfo='percent+label',
        insidetextorientation='radial',
        name='SKUs'
    ), row=1, col=1)
    
    # Gráfico 2 - Unidades
    fig.add_trace(go.Pie(
        labels=niveles,
        values=unidades,
        marker_colors=colores,
        hole=0.4,
        textinfo='percent+label',
        insidetextorientation='radial',
        name='Unidades'
    ), row=1, col=2)
    
    # Gráfico 3 - Valor
    fig.add_trace(go.Pie(
        labels=niveles,
        values=valores,
        marker_colors=colores,
        hole=0.4,
        textinfo='percent+label',
        insidetextorientation='radial',
        name='Valor'
    ), row=1, col=3)
    
    fig.update_layout(
        height=450,
        showlegend=False,
        title_text="<b>Distribución del Inventario por Estado</b>",
        title_x=0.5,
        title_font_size=22,
        title_font_color='#1a237e',
        margin=dict(t=80, b=20, l=20, r=20)
    )
    
    return fig

def crear_tabla_sucursales(sucursal_stats):
    """Crea una tabla interactiva de sucursales"""
    
    if sucursal_stats is None or len(sucursal_stats) == 0:
        return None
    
    # Preparar datos
    df_display = sucursal_stats.copy()
    
    # Renombrar columnas
    df_display.columns = [
        'Sucursal', 'Unidades Totales', 'Valor Total (CLP)', 
        'Latitud', 'Longitud', 
        'CRITICO', 'NORMAL', 'PREVENTIVO', 'URGENTE', 'VENCIDO'
    ]
    
    # Formatear valores
    df_display['Valor Total (CLP)'] = df_display['Valor Total (CLP)'].apply(lambda x: clp(x))
    
    return df_display

# =============================================================================
# SECCIONES DEL DASHBOARD
# =============================================================================

def mostrar_resumen_ejecutivo(stats, fecha_analisis):
    """Muestra el resumen ejecutivo del análisis"""
    
    st.markdown('<h1 class="main-header">📦 Dashboard de Gestión de Inventario</h1>', unsafe_allow_html=True)
    
    # Fecha y hora
    chile_tz = pytz.timezone('America/Santiago')
    hora_chile = datetime.now(chile_tz)
    
    st.markdown(f"""
    <div class='info-card'>
        <h2 style='color: #1565c0; margin: 0;'>Análisis al {fecha_analisis}</h2>
        <p style='font-size: 1.3rem; margin: 15px 0; font-weight: 600;'>
            <span style='color: #1a237e;'>{stats['TOTAL']['productos']}</span> productos | 
            <span style='color: #1976d2;'>{clp(stats['TOTAL']['unidades'])}</span> unidades | 
            <span style='color: #f57c00;'>{clp(stats['TOTAL']['valor'])} CLP</span>
        </p>
        <p style='color: #666; font-size: 0.9rem;'>
            🕒 Actualizado: {hora_chile.strftime('%d/%m/%Y %H:%M:%S')}
        </p>
    </div>
    """, unsafe_allow_html=True)

def mostrar_clasificacion(stats):
    """Muestra la clasificación del inventario por nivel de riesgo"""
    
    st.markdown('<div class="section-title-box"><h2>📊 Clasificación del Inventario</h2></div>', unsafe_allow_html=True)
    
    # Crear columnas para cada nivel
    col1, col2, col3, col4, col5 = st.columns(5)
    
    niveles = [
        ('VENCIDO', 'vencido', '🟣', '#9c27b0'),
        ('CRITICO', 'critico', '🔴', '#d32f2f'),
        ('URGENTE', 'urgente', '🟠', '#f57c00'),
        ('PREVENTIVO', 'preventivo', '🟡', '#fbc02d'),
        ('NORMAL', 'normal', '🟢', '#4caf50')
    ]
    
    columnas = [col1, col2, col3, col4, col5]
    
    for (nivel, clase, emoji, color), col in zip(niveles, columnas):
        with col:
            st.markdown(f"""
            <div class='classification-item {clase}' style='text-align: center; display: block;'>
                <span class='indicator' style='background-color: {color}; margin: 0 auto 10px auto;'></span>
                <strong>{emoji} {nivel}</strong><br><br>
                <div style='font-size: 1.4rem;'>{stats[nivel]['productos']}</div>
                <small>productos</small><br>
                <div style='font-size: 1.1rem;'>{clp(stats[nivel]['unidades'])}</div>
                <small>unidades</small><br>
                <div style='font-size: 1rem; color: {color};'><strong>{clp(stats[nivel]['valor'])} CLP</strong></div>
            </div>
            """, unsafe_allow_html=True)

def mostrar_mapa_seccion(df_stock):
    """Muestra la sección del mapa"""
    
    st.markdown('<div class="section-title-box"><h2>🗺️ Mapa Geográfico del Stock</h2></div>', unsafe_allow_html=True)
    
    # Crear tabs para diferentes vistas del mapa
    tab1, tab2 = st.tabs(["📦 Stock General", "⚠️ Inventario en Riesgo"])
    
    with tab1:
        fig_mapa = crear_mapa_stock(df_stock)
        if fig_mapa:
            st.plotly_chart(fig_mapa, use_container_width=True)
        else:
            st.warning("No hay datos suficientes para mostrar el mapa")
    
    with tab2:
        fig_riesgo = crear_mapa_riesgo(df_stock)
        if fig_riesgo:
            st.plotly_chart(fig_riesgo, use_container_width=True)
        else:
            st.warning("No hay datos de riesgo para mostrar")

def mostrar_detalle_sucursales(sucursal_stats):
    """Muestra el detalle por sucursales"""
    
    st.markdown('<div class="section-title-box"><h2>🏪 Detalle por Sucursal</h2></div>', unsafe_allow_html=True)
    
    if sucursal_stats is None or len(sucursal_stats) == 0:
        st.warning("No hay datos por sucursal")
        return
    
    # Mostrar tabla
    df_display = crear_tabla_sucursales(sucursal_stats)
    
    if df_display is not None:
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico de barras por sucursal
        fig_bar = px.bar(
            sucursal_stats,
            x='Sucursal',
            y='Stock_Teorico_Unidades',
            color='Valor_Stock',
            color_continuous_scale='Viridis',
            title='<b>Stock por Sucursal</b>',
            labels={
                'Sucursal': 'Sucursal',
                'Stock_Teorico_Unidades': 'Unidades en Stock',
                'Valor_Stock': 'Valor (CLP)'
            }
        )
        
        fig_bar.update_layout(
            xaxis_title="Sucursal",
            yaxis_title="Unidades",
            title_font_size=18,
            title_font_color='#1a237e'
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)

def mostrar_analisis_productos(df_stock, limite=20):
    """Muestra los productos con mayor riesgo"""
    
    st.markdown('<div class="section-title-box"><h2>⚠️ Productos en Mayor Riesgo</h2></div>', unsafe_allow_html=True)
    
    # Filtrar productos en riesgo
    df_riesgo = df_stock[df_stock['Nivel_Riesgo'].isin(['VENCIDO', 'CRITICO', 'URGENTE'])]
    
    if len(df_riesgo) == 0:
        st.success("No hay productos en riesgo de vencimiento")
        return
    
    # Ordenar por días para vencer
    df_riesgo = df_riesgo.sort_values('Dias_Para_Vencer', ascending=True)
    
    # Seleccionar columnas relevantes
    columnas_mostrar = ['Producto', 'Sucursal', 'Stock_Teorico_Unidades', 
                        'Dias_Para_Vencer', 'Nivel_Riesgo', 'Valor_Stock']
    
    df_display = df_riesgo[columnas_mostrar].head(limite).copy()
    
    # Renombrar columnas
    df_display.columns = ['Producto', 'Sucursal', 'Stock', 'Días para Vencer', 'Nivel', 'Valor']
    
    # Formatear valor
    df_display['Valor'] = df_display['Valor'].apply(lambda x: clp(x))
    
    # Mostrar tabla
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )
    
    # Descargar datos
    csv = df_riesgo.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Descargar Datos de Riesgo",
        csv,
        "inventario_riesgo.csv",
        "text/csv",
        key='download-riesgo'
    )

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """Función principal de la aplicación"""
    
    # Configurar página
    configurar_pagina()
    
    # Cargar CSS
    cargar_css()
    
    # Título principal
    st.title("📦 Sistema de Gestión de Inventario - BI Dashboard")
    st.markdown("---")
    
    # =====================================================================
    # ETL - Carga de datos
    # =====================================================================
    
    with st.spinner("🔄 Ejecutando proceso ETL..."):
        datos = cargar_datos_etl()
    
    if datos is None:
        st.error("❌ Error en el proceso ETL. Verifique que los archivos estén disponibles.")
        return
    
    # Extraer DataFrames
    df_stock = datos['stock_geo']
    df_sucursales = datos['sucursales']
    
    st.success("✅ Proceso ETL completado exitosamente")
    
    # Mostrar información de los datos cargados
    with st.expander("📋 Información de Datos Cargados", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sucursales", len(df_sucursales))
        with col2:
            st.metric("Registros de Stock", len(df_stock))
        with col3:
            if 'Fecha_Vencimiento_Lote' in df_stock.columns:
                fecha_max = df_stock['Fecha_Vencimiento_Lote'].max()
                st.metric("Fecha Máx. Vencimiento", fecha_max.strftime('%d/%m/%Y') if pd.notna(fecha_max) else "N/A")
    
    st.markdown("---")
    
    # =====================================================================
    # ANÁLISIS
    # =====================================================================
    
    # Análisis de inventario
    stats = analizar_inventario(df_stock)
    sucursal_stats = analizar_por_sucursal(df_stock)
    
    # Fecha de análisis
    fecha_analisis = datetime.now().strftime('%d/%m/%Y')
    
    # =====================================================================
    # RESUMEN EJECUTIVO
    # =====================================================================
    
    mostrar_resumen_ejecutivo(stats, fecha_analisis)
    st.markdown("---")
    
    # =====================================================================
    # CLASIFICACIÓN
    # =====================================================================
    
    mostrar_clasificacion(stats)
    st.markdown("---")
    
    # =====================================================================
    # GRÁFICOS DE DISTRIBUCIÓN
    # =====================================================================
    
    st.markdown('<div class="section-title-box"><h2>📈 Distribución del Inventario</h2></div>', unsafe_allow_html=True)
    
    fig_graficos = crear_graficos_estado(df_stock, stats)
    if fig_graficos:
        st.plotly_chart(fig_graficos, use_container_width=True)
    
    st.markdown("---")
    
    # =====================================================================
    # MAPA GEOGRÁFICO
    # =====================================================================
    
    mostrar_mapa_seccion(df_stock)
    st.markdown("---")
    
    # =====================================================================
    # DETALLE POR SUCURSAL
    # =====================================================================
    
    mostrar_detalle_sucursales(sucursal_stats)
    st.markdown("---")
    
    # =====================================================================
    # PRODUCTOS EN RIESGO
    # =====================================================================
    
    mostrar_analisis_productos(df_stock, limite=30)
    st.markdown("---")
    
    # =====================================================================
    # FOOTER
    # =====================================================================
    
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>📊 <strong>Sistema de Gestión de Inventario BI</strong></p>
        <p>Desarrollado con Streamlit | Datos actualizados automáticamente</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
