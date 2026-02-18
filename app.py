#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SISTEMA DE GESTIÓN DE INVENTARIO BI - ANÁLISIS COMPLETO v2
================================================================================
Mejoras:
- Resumen del plan de acción arriba
- Botón "Ver más detalle" para análisis completo
- Lista completa de productos
- Gráfico de estado de inventario
- Mapa más pequeño y arriba con pestañas
- Riesgo por sucursal

"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import pytz

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

def configurar_pagina():
    st.set_page_config(
        page_title="Sistema de Gestión de Inventario BI",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

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

COLOR_MAP = {
    'VENCIDO': '#9c27b0',
    'CRITICO': '#d32f2f',
    'URGENTE': '#f57c00',
    'PREVENTIVO': '#fbc02d',
    'NORMAL': '#4caf50'
}

# =============================================================================
# CSS PERSONALIZADO
# =============================================================================

def cargar_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1a237e; text-align: center; margin-bottom: 2rem; }
    .section-title-box { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 15px 25px; border-radius: 10px; display: inline-block; margin: 1rem 0; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
    .section-title-box h2 { color: white !important; margin: 0; font-size: 1.5rem; font-weight: 600; }
    .info-card { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 15px; padding: 20px; text-align: center; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .classification-item { padding: 15px; margin: 10px 0; border-radius: 10px; display: flex; align-items: center; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .vencido { background: #f3e5f5; color: #7b1fa2; border-left: 5px solid #9c27b0; }
    .critico { background: #ffebee; color: #c62828; border-left: 5px solid #d32f2f; }
    .urgente { background: #fff3e0; color: #e65100; border-left: 5px solid #f57c00; }
    .preventivo { background: #fffde7; color: #f9a825; border-left: 5px solid #fbc02d; }
    .total-box { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 20px; border-radius: 15px; text-align: center; margin: 15px 0; }
    .total-box h3 { color: white; margin: 0 0 10px 0; font-size: 1.3rem; }
    .badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
    .badge-vencido { background: #f3e5f5; color: #7b1fa2; }
    .badge-critico { background: #ffebee; color: #c62828; }
    .badge-urgente { background: #fff3e0; color: #e65100; }
    .badge-preventivo { background: #fffde7; color: #f9a825; }
    .indicator { display: inline-block; width: 14px; height: 14px; border-radius: 50%; margin-right: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }
    .plan-section { border-radius: 15px; padding: 20px; margin: 15px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 6px solid; }
    .plan-vencido { background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-color: #d32f2f; }
    .plan-critico { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-color: #f57c00; }
    .plan-urgente { background: linear-gradient(135deg, #fffde7 0%, #fff9c4 100%); border-color: #fbc02d; }
    .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 15px 0; }
    .metric-item { background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .metric-label { font-size: 0.8rem; color: #666; margin-bottom: 5px; text-transform: uppercase; }
    .metric-value { font-size: 1.5rem; font-weight: 700; color: #1a237e; }
    .decision-box { background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%); border-radius: 15px; padding: 25px; text-align: center; border: 3px solid #1a237e; margin: 15px 0; }
    .plan-summary { background: white; border-radius: 10px; padding: 15px; margin: 15px 0; border-left: 5px solid #4CAF50; text-align: left; }
    .plan-metrics { background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 10px; padding: 15px; margin: 15px 0; border: 2px solid #4CAF50; }
    .metric-row { display: flex; justify-content: space-between; padding: 8px; margin: 5px 0; background: white; border-radius: 5px; font-weight: 600; }
    .small-map { height: 350px; }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# ETL
# =============================================================================

def cargar_datos_etl(archivos_subidos):
    try:
        df_sucursales = pd.read_csv(archivos_subidos['sucursales'])
        df_productos = pd.read_csv(archivos_subidos['productos'])
        df_lotes = pd.read_csv(archivos_subidos['lotes'])
        df_inventario = pd.read_csv(archivos_subidos['inventario'])
        df_stock_geo = pd.read_csv(archivos_subidos['stock_geo'])
        
        for df in [df_sucursales, df_productos, df_lotes, df_inventario, df_stock_geo]:
            df.columns = df.columns.str.strip()
        
        if 'Fecha_Vencimiento_Lote' in df_stock_geo.columns:
            df_stock_geo['Fecha_Vencimiento_Lote'] = pd.to_datetime(df_stock_geo['Fecha_Vencimiento_Lote'], errors='coerce')
        
        if 'Latitud' in df_stock_geo.columns:
            df_stock_geo['Latitud'] = pd.to_numeric(df_stock_geo['Latitud'], errors='coerce')
            df_stock_geo['Longitud'] = pd.to_numeric(df_stock_geo['Longitud'], errors='coerce')
        
        return {
            'sucursales': df_sucursales, 'productos': df_productos,
            'lotes': df_lotes, 'inventario': df_inventario, 'stock_geo': df_stock_geo
        }
    except Exception as e:
        st.error(f"Error en ETL: {e}")
        return None

# =============================================================================
# FUNCIONES DE ANÁLISIS
# =============================================================================

def clasificar_riesgo(dias):
    if pd.isna(dias):
        return None
    elif dias <= 0:
        return 'VENCIDO'
    elif dias <= 3:
        return 'CRITICO'
    elif dias <= 7:
        return 'URGENTE'
    elif dias <= 10:
        return 'PREVENTIVO'
    else:
        return None

def preparar_datos_analisis(df_stock):
    fecha_actual = datetime.now()
    df_stock['Nivel_Riesgo'] = df_stock['Dias_Para_Vencer'].apply(clasificar_riesgo)
    
    if 'Stock_Teorico_Unidades' in df_stock.columns and 'Precio_Venta_CLP' in df_stock.columns:
        df_stock['Valor_Stock'] = df_stock['Stock_Teorico_Unidades'] * df_stock['Precio_Venta_CLP']
    
    df_riesgo = df_stock[df_stock['Nivel_Riesgo'].notna()].copy()
    df_riesgo = df_riesgo[df_riesgo['Dias_Para_Vencer'] >= 0].copy()
    
    return df_riesgo, fecha_actual

def calcular_estadisticas(df_riesgo):
    if df_riesgo is None or len(df_riesgo) == 0:
        return None
    
    stats = {}
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
        df_nivel = df_riesgo[df_riesgo['Nivel_Riesgo'] == nivel]
        stats[nivel] = {
            'productos': len(df_nivel),
            'unidades': int(df_nivel['Stock_Teorico_Unidades'].sum()) if 'Stock_Teorico_Unidades' in df_nivel.columns else 0,
            'valor': df_nivel['Valor_Stock'].sum() if 'Valor_Stock' in df_nivel.columns else 0
        }
    
    stats['TOTAL'] = {
        'productos': len(df_riesgo),
        'unidades': int(df_riesgo['Stock_Teorico_Unidades'].sum()) if 'Stock_Teorico_Unidades' in df_riesgo.columns else 0,
        'valor': df_riesgo['Valor_Stock'].sum() if 'Valor_Stock' in df_riesgo.columns else 0
    }
    return stats

def calcular_proporcion_mes(df_stock):
    if df_stock is None or len(df_stock) == 0:
        return None
    
    mes_actual = datetime.now().month
    if 'Fecha_Vencimiento_Lote' in df_stock.columns:
        df_stock['Mes_Vencimiento'] = pd.to_datetime(df_stock['Fecha_Vencimiento_Lote'], errors='coerce').dt.month
        df_mes = df_stock[df_stock['Mes_Vencimiento'] == mes_actual]
        total_stock = df_stock['Stock_Teorico_Unidades'].sum()
        stock_mes = df_mes['Stock_Teorico_Unidades'].sum()
        proporcion = (stock_mes / total_stock) * 100 if total_stock > 0 else 0
        return {'stock_mes': stock_mes, 'total_stock': total_stock, 'proporcion': proporcion}
    return None

# =============================================================================
# VISUALIZACIONES
# =============================================================================

def crear_mapa_con_pestañas(df_stock, df_riesgo):
    """Crea mapa con pestañas: Stock general y Riesgo por sucursal"""
    
    if df_stock is None or len(df_stock) == 0:
        return None
    
    tab1, tab2 = st.tabs(["📦 Stock General", "⚠️ Riesgo por Sucursal"])
    
    with tab1:
        df_mapa = df_stock.copy()
        df_mapa = df_mapa[(df_mapa['Latitud'].notna()) & (df_mapa['Longitud'].notna()) & (df_mapa['Stock_Teorico_Unidades'] > 0)]
        
        if len(df_mapa) == 0:
            st.warning("No hay datos para el mapa")
            return None
        
        df_sucursal = df_mapa.groupby('Sucursal').agg({
            'Stock_Teorico_Unidades': 'sum', 'Valor_Stock': 'sum',
            'Latitud': 'first', 'Longitud': 'first'
        }).reset_index()
        
        fig = px.scatter_mapbox(
            df_sucursal, lat="Latitud", lon="Longitud",
            size="Stock_Teorico_Unidades", color="Valor_Stock",
            hover_name="Sucursal",
            hover_data={"Stock_Teorico_Unidades": True, "Valor_Stock": ":,.0f"},
            color_continuous_scale="Viridis", size_max=40, zoom=10,
            center={"lat": -33.45, "lon": -70.65},
            mapbox_style="open-street-map", title="<b>Stock por Sucursal</b>"
        )
        fig.update_layout(height=350, margin={"r": 0, "t": 40, "l": 0, "b": 0})
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if df_riesgo is not None and len(df_riesgo) > 0:
            df_riesgo_mapa = df_riesgo.copy()
            df_riesgo_mapa = df_riesgo_mapa[(df_riesgo_mapa['Latitud'].notna()) & (df_riesgo_mapa['Longitud'].notna())]
            
            df_sucursal_riesgo = df_riesgo_mapa.groupby('Sucursal').agg({
                'Stock_Teorico_Unidades': 'sum', 'Valor_Stock': 'sum',
                'Latitud': 'first', 'Longitud': 'first'
            }).reset_index()
            
            fig2 = px.scatter_mapbox(
                df_sucursal_riesgo, lat="Latitud", lon="Longitud",
                size="Stock_Teorico_Unidades", color="Valor_Stock",
                hover_name="Sucursal",
                hover_data={"Stock_Teorico_Unidades": True, "Valor_Stock": ":,.0f"},
                color_continuous_scale="Reds", size_max=40, zoom=10,
                center={"lat": -33.45, "lon": -70.65},
                mapbox_style="open-street-map", title="<b>Inventario en Riesgo por Sucursal</b>"
            )
            fig2.update_layout(height=350, margin={"r": 0, "t": 40, "l": 0, "b": 0})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No hay productos en riesgo")

def crear_grafico_estado(df_stock, stats):
    """Crea gráfico de estado general del inventario"""
    
    if df_stock is None:
        return None
    
    # Calcular estado
    total_unidades = df_stock['Stock_Teorico_Unidades'].sum()
    unidades_riesgo = stats['TOTAL']['unidades'] if stats else 0
    unidades_normales = total_unidades - unidades_riesgo
    
    fig = go.Figure(go.Pie(
        labels=['Normal', 'En Riesgo'],
        values=[unidades_normales, unidades_riesgo],
        marker_colors=['#4caf50', '#f44336'],
        hole=0.5,
        textinfo='percent+label',
        textposition='outside',
        name='Estado'
    ))
    
    fig.update_layout(
        height=280, showlegend=True,
        title_text="<b>Estado del Inventario</b>",
        title_x=0.5, title_font_size=16,
        margin=dict(t=40, b=20, l=20, r=20)
    )
    
    return fig

def crear_graficos_distribucion(stats):
    if stats is None:
        return None
    
    niveles = ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']
    colores = ['#9c27b0', '#d32f2f', '#f57c00', '#fbc02d']
    
    productos = [stats[n]['productos'] for n in niveles]
    valores = [stats[n]['valor'] for n in niveles]
    
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{'type': 'pie'}, {'type': 'pie'}]],
        subplot_titles=['<b>Por SKUs</b>', '<b>Por Valor (CLP)</b>']
    )
    
    fig.add_trace(go.Pie(labels=niveles, values=productos, marker_colors=colores, hole=0.4, textinfo='percent+label'), row=1, col=1)
    fig.add_trace(go.Pie(labels=niveles, valores=colores, hole=0.4, textinfo='percent+label'), row=1, col=2)
    
    fig.update_layout(height=350, showlegend=False, title_text="<b>Distribución Inventario en Riesgo</b>", title_x=0.5, title_font_size=18, margin=dict(t=60, b=20, l=20, r=20))
    
    return fig

def crear_matriz_riesgo(df_riesgo, fecha_hoy):
    if df_riesgo is None or len(df_riesgo) == 0:
        return None
    
    df_viz = df_riesgo.copy()
    
    if 'Valor_Stock' not in df_viz.columns or df_viz['Valor_Stock'].sum() == 0:
        df_viz['Valor_Stock'] = df_viz['Stock_Teorico_Unidades'] * 1000
    
    sizes = np.clip(df_viz['Valor_Stock'] / df_viz['Valor_Stock'].max() * 600 + 40, 40, 600)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x_map = {'VENCIDO': 0.0, 'CRITICO': 1.0, 'URGENTE': 2.0, 'PREVENTIVO': 3.0}
    df_viz['x_pos'] = df_viz['Nivel_Riesgo'].map(x_map).astype(float)
    df_viz = df_viz.sort_values(['Nivel_Riesgo', 'Valor_Stock'], ascending=[True, True]).reset_index(drop=True)
    df_viz['pos_y_rel'] = df_viz.groupby('Nivel_Riesgo')['Valor_Stock'].rank(pct=True, method='first')
    df_viz['y_pos'] = df_viz['Nivel_Riesgo'].map({'VENCIDO': 0.0, 'CRITICO': 1.0, 'URGENTE': 2.0, 'PREVENTIVO': 3.0}) + (df_viz['pos_y_rel'] - 0.5) * 0.8
    
    ax.scatter(df_viz['x_pos'], df_viz['y_pos'], s=sizes, c=df_viz['Nivel_Riesgo'].map(COLOR_MAP), alpha=0.85, edgecolors='black', linewidth=0.9, zorder=3)
    
    for pos in [0.5, 1.5, 2.5]:
        ax.axhline(pos, color='gray', linestyle='--', linewidth=1.0, alpha=0.35)
        ax.axvline(pos, color='gray', linestyle='--', linewidth=1.0, alpha=0.35)
    
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(['VENCIDO', 'CRÍTICO', 'URGENTE', 'PREVENTIVO'], fontsize=10, fontweight='bold')
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(['Hoy', '1-3 días', '4-7 días', '8-10 días'], fontsize=9)
    ax.set_xlabel('Nivel de Riesgo', fontsize=11, fontweight='bold')
    ax.set_ylabel('Días para Vencimiento', fontsize=11, fontweight='bold')
    ax.set_title(f'Riesgo de Vencimiento - {fecha_hoy.date()}\n{len(df_viz)} productos', fontsize=12, pad=10)
    
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='VENCIDO', markerfacecolor='#9c27b0', markersize=12),
        Line2D([0], [0], marker='o', color='w', label='CRÍTICO', markerfacecolor='#d32f2f', markersize=12),
        Line2D([0], [0], marker='o', color='w', label='URGENTE', markerfacecolor='#f57c00', markersize=12),
        Line2D([0], [0], marker='o', color='w', label='PREVENTIVO', markerfacecolor='#fbc02d', markersize=12),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9, frameon=True)
    ax.set_xlim(-0.7, 3.7)
    ax.set_ylim(-0.7, 3.7)
    ax.grid(False)
    plt.tight_layout()
    
    return fig

# =============================================================================
# RESUMEN Y PLAN 48H
# =============================================================================

def mostrar_resumen_plan(stats):
    """Muestra el resumen del plan de acción"""
    
    if stats is None:
        return
    
    valor_vencido = stats['VENCIDO']['valor']
    valor_critico = stats['CRITICO']['valor']
    valor_urgente = stats['URGENTE']['valor']
    
    credito_trib = valor_vencido * 0.27
    recuperacion = valor_critico * 0.50 + valor_urgente * 0.40
    total_recuperado = credito_trib + recuperacion
    
    st.markdown(f"""
    <div class="decision-box">
        <h3 style="color: #1a237e; margin: 0 0 15px 0;">📋 PLAN DE ACCIÓN 48H - RESUMEN</h3>
        <div class="plan-summary">
            <div class="metric-row">
                <span>🔴 {stats['VENCIDO']['productos']} productos vencidos → Donación</span>
                <span style="color: #2e7d32;">+{clp(credito_trib)} CLP (27%)</span>
            </div>
            <div class="metric-row">
                <span>🟠 {stats['CRITICO']['productos']} productos críticos → 40% dto</span>
                <span style="color: #1565c0;">+{clp(valor_critico * 0.50)} CLP</span>
            </div>
            <div class="metric-row">
                <span>🟡 {stats['URGENTE']['productos']} productos urgentes → 25% dto</span>
                <span style="color: #1565c0;">+{clp(valor_urgente * 0.40)} CLP</span>
            </div>
        </div>
        <div class="plan-metrics">
            <div class="metric-row" style="background: #c8e6c9; font-size: 1.1rem;">
                <span style="color: #2e7d32;">✅ TOTAL RECUPERADO ESTIMADO:</span>
                <span style="color: #1565c0;">{clp(total_recuperado)} CLP</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def mostrar_analisis_sensibilidad(stats):
    if stats is None:
        return
    
    valor_vencido = stats['VENCIDO']['valor']
    valor_critico = stats['CRITICO']['valor']
    valor_urgente = stats['URGENTE']['valor']
    credito_trib = valor_vencido * 0.27
    
    escenarios = {
        'Muy Pesimista': 0.3, 'Pesimista': 0.5, 'Conservador': 0.7, 'Base': 0.85, 'Optimista': 1.0
    }
    
    st.markdown("### 📊 Análisis de Sensibilidad")
    
    cols = st.columns(5)
    for i, (nombre, factor) in enumerate(escenarios.items()):
        recuperacion = (valor_critico * 0.50 + valor_urgente * 0.40) * factor
        total = recuperacion + credito_trib
        es_base = nombre == 'Base'
        
        with cols[i]:
            st.markdown(f"""
            <div style='background: {"#e8f5e9" if es_base else "white"}; padding: 12px; border-radius: 8px; text-align: center; border: {"3px solid #4caf50" if es_base else "1px solid #ddd"};'>
                <div style='font-size: 0.75rem; font-weight: 600;'>{nombre}</div>
                <div style='font-size: 1.1rem; font-weight: 700; color: #1a237e;'>{clp(total)}</div>
            </div>
            """, unsafe_allow_html=True)

def mostrar_plan_48h_detalle(stats):
    if stats is None:
        return
    
    st.markdown("---")
    st.markdown('<div class="section-title-box"><h2>⏱️ PLAN DE ACCIÓN 48H - DETALLE</h2></div>', unsafe_allow_html=True)
    
    valor_vencido = stats['VENCIDO']['valor']
    valor_critico = stats['CRITICO']['valor']
    valor_urgente = stats['URGENTE']['valor']
    credito_trib = valor_vencido * 0.27
    
    if stats['VENCIDO']['productos'] > 0:
        st.markdown(f"""
        <div class="plan-section plan-vencido">
            <h3 style="color: #d32f2f; margin: 0 0 10px 0;">🔴 HOY 08:00-12:00 | DONACIONES</h3>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">Productos</div><div class="metric-value">{stats['VENCIDO']['productos']}</div></div>
                <div class="metric-item"><div class="metric-label">Unidades</div><div class="metric-value">{clp(stats['VENCIDO']['unidades'])}</div></div>
                <div class="metric-item"><div class="metric-label">Valor</div><div class="metric-value">{clp(valor_vencido)}</div></div>
            </div>
            <div style="background: #c8e6c9; padding: 10px; border-radius: 8px; text-align: center;">
                <span style="color: #2e7d32; font-weight: 700;">+{clp(credito_trib)} CLP crédito tributario (27%)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if stats['CRITICO']['productos'] > 0:
        st.markdown(f"""
        <div class="plan-section plan-critico">
            <h3 style="color: #f57c00; margin: 0 0 10px 0;">🟠 HOY 12:00-18:00 | MARKDOWN 40%</h3>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">Productos</div><div class="metric-value">{stats['CRITICO']['productos']}</div></div>
                <div class="metric-item"><div class="metric-label">Unidades</div><div class="metric-value">{clp(stats['CRITICO']['unidades'])}</div></div>
                <div class="metric-item"><div class="metric-label">Valor</div><div class="metric-value">{clp(valor_critico)}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if stats['URGENTE']['productos'] > 0:
        st.markdown(f"""
        <div class="plan-section plan-urgente">
            <h3 style="color: #f9a825; margin: 0 0 10px 0;">🟡 MAÑANA | MARKDOWN 25%</h3>
            <div class="metric-grid">
                <div class="metric-item"><div class="metric-label">Productos</div><div class="metric-value">{stats['URGENTE']['productos']}</div></div>
                <div class="metric-item"><div class="metric-label">Unidades</div><div class="metric-value">{clp(stats['URGENTE']['unidades'])}</div></div>
                <div class="metric-item"><div class="metric-label">Valor</div><div class="metric-value">{clp(valor_urgente)}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def mostrar_tabla_productos_completa(df_riesgo):
    """Muestra tabla completa de productos por nivel"""
    
    if df_riesgo is None or len(df_riesgo) == 0:
        st.info("No hay productos en riesgo")
        return
    
    st.markdown("### 📦 Productos por Nivel de Riesgo")
    
    niveles = ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']
    config = {
        'VENCIDO': {'color': '#9c27b0', 'badge': 'badge-vencido', 'emoji': '🟣'},
        'CRITICO': {'color': '#d32f2f', 'badge': 'badge-critico', 'emoji': '🔴'},
        'URGENTE': {'color': '#f57c00', 'badge': 'badge-urgente', 'emoji': '🟠'},
        'PREVENTIVO': {'color': '#fbc02d', 'badge': 'badge-preventivo', 'emoji': '🟡'}
    }
    
    for nivel in niveles:
        df_nivel = df_riesgo[df_riesgo['Nivel_Riesgo'] == nivel].sort_values('Dias_Para_Vencer', ascending=True)
        
        if len(df_nivel) == 0:
            continue
        
        conf = config[nivel]
        valor_total = df_nivel['Valor_Stock'].sum() if 'Valor_Stock' in df_nivel.columns else 0
        
        with st.expander(f"{conf['emoji']} {nivel} ({len(df_nivel)} productos | {clp(valor_total)} CLP)", expanded=False):
            df_display = df_nivel[['Producto', 'Sucursal', 'Stock_Teorico_Unidades', 'Dias_Para_Vencer', 'Valor_Stock']].copy()
            df_display.columns = ['Producto', 'Sucursal', 'Stock', 'Días Vencer', 'Valor (CLP)']
            df_display['Valor (CLP)'] = df_display['Valor (CLP)'].apply(lambda x: clp(x))
            st.dataframe(df_display, use_container_width=True, hide_index=True)

# =============================================================================
# SECCIONES PRINCIPALES
# =============================================================================

def mostrar_resumen_ejecutivo(stats, proporcion_mes, fecha_actual):
    chile_tz = pytz.timezone('America/Santiago')
    hora_chile = datetime.now(chile_tz)
    fecha_inicio = datetime(2026, 2, 1)
    
    st.markdown(f"""
    <div class="info-card">
        <h2 style="color: #1565c0; margin: 0;">Análisis: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_actual.strftime('%d/%m/%Y')}</h2>
        <p style="font-size: 1.2rem; margin: 10px 0; font-weight: 600;">
            <span style="color: #1a237e;">{stats['TOTAL']['productos']}</span> productos en riesgo | 
            <span style="color: #1976d2;">{clp(stats['TOTAL']['unidades'])}</span> unidades | 
            <span style="color: #f57c00;">{clp(stats['TOTAL']['valor'])} CLP</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

def mostrar_clasificacion(stats):
    st.markdown("### 📊 Clasificación por Nivel de Riesgo")
    
    col1, col2, col3, col4 = st.columns(4)
    niveles = [
        ('VENCIDO', 'vencido', '🟣', '#9c27b0'),
        ('CRITICO', 'critico', '🔴', '#d32f2f'),
        ('URGENTE', 'urgente', '🟠', '#f57c00'),
        ('PREVENTIVO', 'preventivo', '🟡', '#fbc02d')
    ]
    columnas = [col1, col2, col3, col4]
    
    for (nivel, clase, emoji, color), col in zip(niveles, columnas):
        with col:
            st.markdown(f"""
            <div class="classification-item {clase}" style="text-align: center; display: block;">
                <span class="indicator" style="background-color: {color}; margin: 0 auto 8px auto;"></span>
                <strong>{emoji} {nivel}</strong><br>
                <div style="font-size: 1.2rem;">{stats[nivel]['productos']}</div>
                <small>productos</small><br>
                <div style="font-size: 1rem;">{clp(stats[nivel]['unidades'])}</div>
                <small>unidades</small><br>
                <div style="font-size: 0.9rem; color: {color};"><strong>{clp(stats[nivel]['valor'])} CLP</strong></div>
            </div>
            """, unsafe_allow_html=True)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    configurar_pagina()
    cargar_css()
    
    st.title("📦 Sistema de Gestión de Inventario BI")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("📁 Carga de Datos")
    archivos_subidos = st.sidebar.file_uploader("Seleccionar archivos CSV", type=['csv'], accept_multiple_files=True)
    boton_ejecutar = st.sidebar.button("🚀 Ejecutar Análisis", type="primary")
    
    if not archivos_subidos:
        st.markdown("""
        <div style="text-align: center; padding: 40px;">
            <h2>📦 Sistema de Gestión de Inventario BI</h2>
            <p style="color: #666;">Sube los 5 archivos CSV en el panel lateral</p>
            <div style="background: #e3f2fd; padding: 15px; border-radius: 10px; margin-top: 20px;">
                <ul style="text-align: left; display: inline-block;">
                    <li>1_SUCURSALES_MASTER.csv</li>
                    <li>2_PRODUCTOS_MASTER.csv</li>
                    <li>3_LOTES_PRODUCTOS.csv</li>
                    <li>4_INVENTARIO_COMPLETO_LOTES.csv</li>
                    <li>5_STOCK_ACTUAL_GEO_POWERBI.csv</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if len(archivos_subidos) < 5:
        st.sidebar.error(f"Falta subir archivos. Has subido {len(archivos_subidos)} de 5.")
        return
    
    archivos_dict = {}
    for archivo in archivos_subidos:
        nombre = archivo.name.lower()
        if 'sucursal' in nombre:
            archivos_dict['sucursales'] = archivo
        elif 'producto' in nombre and 'lote' not in nombre:
            archivos_dict['productos'] = archivo
        elif 'lote' in nombre and 'producto' in nombre:
            archivos_dict['lotes'] = archivo
        elif 'inventario' in nombre and 'stock' not in nombre:
            archivos_dict['inventario'] = archivo
        elif 'stock' in nombre and 'geo' in nombre:
            archivos_dict['stock_geo'] = archivo
    
    if not all(k in archivos_dict for k in ['sucursales', 'productos', 'lotes', 'inventario', 'stock_geo']):
        st.sidebar.error("No se reconocieron todos los archivos.")
        return
    
    if not boton_ejecutar:
        st.sidebar.info("👆 Sube los 5 archivos y haz clic en 'Ejecutar Análisis'")
        return
    
    # ETL
    with st.spinner("Ejecutando análisis..."):
        datos = cargar_datos_etl(archivos_dict)
    
    if datos is None:
        st.error("Error en ETL")
        return
    
    df_stock = datos['stock_geo']
    df_riesgo, fecha_actual = preparar_datos_analisis(df_stock)
    stats = calcular_estadisticas(df_riesgo)
    proporcion_mes = calcular_proporcion_mes(df_stock)
    
    st.success("✅ Análisis completado")
    
    # VISTA RESUMEN
    mostrar_resumen_ejecutivo(stats, proporcion_mes, fecha_actual)
    mostrar_clasificacion(stats)
    
    # MAPA (arriba, más pequeño)
    st.markdown('<div class="section-title-box"><h2>🗺️ Mapa de Stock</h2></div>', unsafe_allow_html=True)
    crear_mapa_con_pestañas(df_stock, df_riesgo)
    
    # RESUMEN PLAN
    mostrar_resumen_plan(stats)
    
    # GRÁFICO ESTADO
    st.markdown("### 📈 Estado del Inventario")
    fig_estado = crear_grafico_estado(df_stock, stats)
    if fig_estado:
        st.plotly_chart(fig_estado, use_container_width=True)
    
    # BOTÓN VER MÁS DETALLE
    if 'ver_detalle' not in st.session_state:
        st.session_state['ver_detalle'] = False
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("📊 Ver Análisis Completo", type="primary", use_container_width=True):
            st.session_state['ver_detalle'] = True
            st.rerun()
    with col_btn2:
        if st.session_state['ver_detalle']:
            if st.button("⬆️ Ocultar Detalle", use_container_width=True):
                st.session_state['ver_detalle'] = False
                st.rerun()
    
    # ANÁLISIS COMPLETO
    if st.session_state['ver_detalle']:
        st.markdown("---")
        
        # Distribución
        st.markdown('<div class="section-title-box"><h2>📊 Distribución del Inventario en Riesgo</h2></div>', unsafe_allow_html=True)
        fig_dist = crear_graficos_distribucion(stats)
        if fig_dist:
            st.plotly_chart(fig_dist, use_container_width=True)
        
        # Matriz
        st.markdown('<div class="section-title-box"><h2>🎯 Matriz de Riesgo</h2></div>', unsafe_allow_html=True)
        fig_matriz = crear_matriz_riesgo(df_riesgo, fecha_actual)
        if fig_matriz:
            st.pyplot(fig_matriz)
        
        # Sensibilidad
        mostrar_analisis_sensibilidad(stats)
        
        # Plan 48h detalle
        mostrar_plan_48h_detalle(stats)
        
        # Tabla completa
        mostrar_tabla_productos_completa(df_riesgo)
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666; padding: 10px;'>📊 Sistema de Gestión de Inventario BI</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
