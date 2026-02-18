"""
================================================================================
SISTEMA DE GESTIÓN DE INVENTARIO - ANÁLISIS COMPLETO
================================================================================
Este script realiza:
- ETL de los 5 archivos CSV subidos por el usuario
- Análisis desde 1 de Febrero hasta la fecha actual
- Clasificación de riesgo: VENCIDO, CRÍTICO, URGENTE, PREVENTIVO
- Proporción de mercancía del mes
- Análisis de sensibilidad
- Plan de acción 48h
- Matriz de riesgo visual
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
        page_title="Sistema de Gestión de Inventario",
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

# Colores del semáforo
COLOR_MAP = {
    'VENCIDO': '#9c27b0',      # Violeta
    'CRITICO': '#d32f2f',      # Rojo
    'URGENTE': '#f57c00',      # Naranja
    'PREVENTIVO': '#fbc02d'    # Amarillo
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

    .total-box {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    .total-box h3 { color: white; margin: 0 0 15px 0; font-size: 1.5rem; }

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

    .indicator {
        display: inline-block;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        margin-right: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
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

    .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }
    .metric-item { background: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .metric-label { font-size: 0.85rem; color: #666; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #1a237e; }

    .decision-box {
        background: linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%);
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        border: 3px solid #1a237e;
        margin: 20px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    .plan-summary {
        background: white;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        border-left: 5px solid #4CAF50;
        text-align: left;
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

    .metric-label-green { color: #2e7d32; }
    .metric-value-blue { color: #1565c0; font-size: 1.1rem; }
    
    /* Estilos para análisis de sensibilidad */
    .sensibilidad-header {
        background: linear-gradient(135deg, #e1bee7 0%, #f3e5f5 100%);
        padding: 20px;
        border-radius: 15px 15px 0 0;
        margin-bottom: 0;
    }
    
    .sensibilidad-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        padding: 20px;
        background: #fafafa;
    }
    
    .escenario-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 2px solid transparent;
    }
    
    .escenario-card.base {
        border: 3px solid #4caf50;
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    }
    
    .escenario-title {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-weight: 600;
        margin-bottom: 10px;
    }
    
    .escenario-valor {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 10px 0;
    }
    
    .escenario-detalle {
        font-size: 0.85rem;
        color: #666;
        line-height: 1.6;
    }
    
    .nota-proyeccion {
        background: #fff8e1;
        border-left: 4px solid #ffc107;
        padding: 15px 20px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# ETL - CARGA DE DATOS
# =============================================================================

def cargar_datos_etl(archivos_subidos):
    """Carga y procesa los 5 archivos CSV"""

    try:
        # Cargar archivos
        df_sucursales = pd.read_csv(archivos_subidos['sucursales'])
        df_productos = pd.read_csv(archivos_subidos['productos'])
        df_lotes = pd.read_csv(archivos_subidos['lotes'])
        df_inventario = pd.read_csv(archivos_subidos['inventario'])
        df_stock_geo = pd.read_csv(archivos_subidos['stock_geo'])

        # Limpiar columnas
        for df in [df_sucursales, df_productos, df_lotes, df_inventario, df_stock_geo]:
            df.columns = df.columns.str.strip()

        # Procesar fechas
        if 'Fecha_Vencimiento_Lote' in df_stock_geo.columns:
            df_stock_geo['Fecha_Vencimiento_Lote'] = pd.to_datetime(
                df_stock_geo['Fecha_Vencimiento_Lote'], errors='coerce'
            )

        # Procesar coordenadas
        if 'Latitud' in df_stock_geo.columns:
            df_stock_geo['Latitud'] = pd.to_numeric(df_stock_geo['Latitud'], errors='coerce')
            df_stock_geo['Longitud'] = pd.to_numeric(df_stock_geo['Longitud'], errors='coerce')

        return {
            'sucursales': df_sucursales,
            'productos': df_productos,
            'lotes': df_lotes,
            'inventario': df_inventario,
            'stock_geo': df_stock_geo
        }

    except Exception as e:
        st.error(f"Error en ETL: {e}")
        return None

# =============================================================================
# FUNCIONES DE CLASIFICACIÓN Y ANÁLISIS
# =============================================================================

def clasificar_riesgo(dias):
    """Clasifica el riesgo según días para vencimiento"""
    if pd.isna(dias):
        return None
    elif dias == 0:
        return 'VENCIDO'      # Solo día = 0 (hoy)
    elif dias >= 1 and dias <= 3:
        return 'CRITICO'      # 1-3 días
    elif dias >= 4 and dias <= 7:
        return 'URGENTE'      # 4-7 días
    elif dias >= 8 and dias <= 10:
        return 'PREVENTIVO'   # 8-10 días
    else:
        return None  # No es riesgo en el rango de análisis

def preparar_datos_analisis(df_stock):
    """Prepara los datos para el análisis considerando el rango de fechas"""

    # Fecha actual del sistema
    fecha_actual = datetime.now()

    # Aplicar clasificación de riesgo
    df_stock['Nivel_Riesgo'] = df_stock['Dias_Para_Vencer'].apply(clasificar_riesgo)

    # Calcular valor de stock
    if 'Stock_Teorico_Unidades' in df_stock.columns and 'Precio_Venta_CLP' in df_stock.columns:
        df_stock['Valor_Stock'] = df_stock['Stock_Teorico_Unidades'] * df_stock['Precio_Venta_CLP']

    # Filtrar solo productos en riesgo (VENCIDO, CRITICO, URGENTE, PREVENTIVO)
    df_riesgo = df_stock[df_stock['Nivel_Riesgo'].notna()].copy()

    # Filtrar solo productos con días >= 0 (no considerar los que ya vencieron antes de hoy)
    df_riesgo = df_riesgo[df_riesgo['Dias_Para_Vencer'] >= 0].copy()

    return df_riesgo, fecha_actual

def calcular_estadisticas(df_riesgo):
    """Calcula estadísticas por nivel de riesgo"""

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

    # Total
    stats['TOTAL'] = {
        'productos': len(df_riesgo),
        'unidades': int(df_riesgo['Stock_Teorico_Unidades'].sum()) if 'Stock_Teorico_Unidades' in df_riesgo.columns else 0,
        'valor': df_riesgo['Valor_Stock'].sum() if 'Valor_Stock' in df_riesgo.columns else 0
    }

    return stats

def calcular_proporcion_mes(df_stock):
    """Calcula la proporción de mercancía del mes"""

    if df_stock is None or len(df_stock) == 0:
        return None

    # Obtener el mes actual
    mes_actual = datetime.now().month
    año_actual = datetime.now().year

    # Filtrar productos del mes actual
    if 'Fecha_Vencimiento_Lote' in df_stock.columns:
        df_stock['Mes_Vencimiento'] = pd.to_datetime(df_stock['Fecha_Vencimiento_Lote'], errors='coerce').dt.month
        df_mes = df_stock[df_stock['Mes_Vencimiento'] == mes_actual]

        total_stock = df_stock['Stock_Teorico_Unidades'].sum()
        stock_mes = df_mes['Stock_Teorico_Unidades'].sum()

        if total_stock > 0:
            proporcion = (stock_mes / total_stock) * 100
        else:
            proporcion = 0

        return {
            'mes_actual': mes_actual,
            'año_actual': año_actual,
            'stock_mes': stock_mes,
            'total_stock': total_stock,
            'proporcion': proporcion
        }

    return None

# =============================================================================
# VISUALIZACIONES
# =============================================================================

def crear_graficos_distribucion(stats):
    """Crea gráficos de distribución del inventario - 3 gráficos: Productos, Valor y Unidades"""

    if stats is None:
        return None

    niveles = ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']
    colores = ['#9c27b0', '#d32f2f', '#f57c00', '#fbc02d']

    productos = [stats[n]['productos'] for n in niveles]
    valores = [stats[n]['valor'] for n in niveles]
    unidades = [stats[n]['unidades'] for n in niveles]

    # Crear subplots con 3 gráficos circulares
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{'type': 'pie'}, {'type': 'pie'}, {'type': 'pie'}]],
        subplot_titles=['<b>Por Cantidad de Productos</b>', '<b>Por Valor (CLP)</b>', '<b>Por Unidades de Inventario</b>']
    )

    # Gráfico 1 - Productos (SKUs)
    fig.add_trace(go.Pie(
        labels=niveles,
        values=productos,
        marker_colors=colores,
        hole=0.4,
        textinfo='percent+label',
        insidetextorientation='radial',
        name='Productos'
    ), row=1, col=1)

    # Gráfico 2 - Valor
    fig.add_trace(go.Pie(
        labels=niveles,
        values=valores,
        marker_colors=colores,
        hole=0.4,
        textinfo='percent+label',
        insidetextorientation='radial',
        name='Valor'
    ), row=1, col=2)

    # Gráfico 3 - Unidades de Inventario
    fig.add_trace(go.Pie(
        labels=niveles,
        values=unidades,
        marker_colors=colores,
        hole=0.4,
        textinfo='percent+label',
        insidetextorientation='radial',
        name='Unidades'
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

    return fig

def crear_matriz_riesgo(df_riesgo, fecha_hoy):
    """Crea la matriz de riesgo visual"""

    if df_riesgo is None or len(df_riesgo) == 0:
        return None

    df_viz = df_riesgo.copy()

    # Asegurar que hay valores para graficar
    if 'Valor_Stock' not in df_viz.columns or df_viz['Valor_Stock'].sum() == 0:
        df_viz['Valor_Stock'] = df_viz['Stock_Teorico_Unidades'] * 1000  # Valor estimado

    sizes = np.clip(df_viz['Valor_Stock'] / df_viz['Valor_Stock'].max() * 600 + 40, 40, 600)

    fig, ax = plt.subplots(figsize=(12, 7))

    x_map = {'VENCIDO': 0.0, 'CRITICO': 1.0, 'URGENTE': 2.0, 'PREVENTIVO': 3.0}
    df_viz['x_pos'] = df_viz['Nivel_Riesgo'].map(x_map).astype(float)

    df_viz = df_viz.sort_values(['Nivel_Riesgo', 'Valor_Stock'], ascending=[True, True]).reset_index(drop=True)
    df_viz['pos_y_rel'] = df_viz.groupby('Nivel_Riesgo')['Valor_Stock'].rank(pct=True, method='first')

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
    ax.set_xticklabels(['VENCIDO', 'CRÍTICO', 'URGENTE', 'PREVENTIVO'],
                       fontsize=11, fontweight='bold')
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(['Hoy', '1-3 días', '4-7 días', '8-10 días'], fontsize=10)

    ax.set_xlabel('Nivel de Riesgo', fontsize=12, fontweight='bold')
    ax.set_ylabel('Días para Vencimiento', fontsize=12, fontweight='bold')
    ax.set_title(f'Riesgo de Vencimiento - {fecha_hoy.date()}\n{len(df_viz)} productos',
                fontsize=13, pad=15)

    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='VENCIDO', markerfacecolor='#9c27b0', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='CRÍTICO', markerfacecolor='#d32f2f', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='URGENTE', markerfacecolor='#f57c00', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='PREVENTIVO', markerfacecolor='#fbc02d', markersize=14),
    ]

    ax.legend(handles=legend_elements, loc='upper left', title='Nivel de Riesgo',
              fontsize=10, title_fontsize=11, frameon=True, edgecolor='gray', facecolor='white')

    ax.set_xlim(-0.7, 3.7)
    ax.set_ylim(-0.7, 3.7)
    ax.grid(False)
    plt.tight_layout()

    return fig

def crear_mapa_stock(df_stock):
    """Crea un mapa interactivo con el stock total"""

    if df_stock is None or len(df_stock) == 0:
        return None

    df_mapa = df_stock.copy()
    df_mapa = df_mapa[
        (df_mapa['Latitud'].notna()) &
        (df_mapa['Longitud'].notna()) &
        (df_mapa['Stock_Teorico_Unidades'] > 0)
    ]

    if len(df_mapa) == 0:
        return None

    # Agrupar por sucursal
    df_sucursal = df_mapa.groupby('Sucursal').agg({
        'Stock_Teorico_Unidades': 'sum',
        'Valor_Stock': 'sum',
        'Latitud': 'first',
        'Longitud': 'first'
    }).reset_index()

    # Calcular centro dinámico del mapa (promedio de coordenadas)
    centro_lat = df_sucursal['Latitud'].mean()
    centro_lon = df_sucursal['Longitud'].mean()

    fig = px.scatter_mapbox(
        df_sucursal,
        lat="Latitud",
        lon="Longitud",
        size="Stock_Teorico_Unidades",
        color="Valor_Stock",
        hover_name="Sucursal",
        hover_data={"Stock_Teorico_Unidades": True, "Valor_Stock": ":,.0f"},
        color_continuous_scale="Viridis",
        size_max=50,
        zoom=9,
        center={"lat": centro_lat, "lon": centro_lon},
        mapbox_style='carto-positron',
        title="<b>Stock Total por Sucursal</b>"
    )

    fig.update_layout(
        height=600,
        width=600,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        title_font_size=20,
        title_font_color='#1a237e',
        mapbox=dict(
            bearing=0,
            pitch=0,
            zoom=9
        )
    )

    return fig

def crear_mapa_inventario_riesgo(df_riesgo):
    """Crea un mapa interactivo con el inventario en riesgo (Vencido, Crítico, Urgente, Preventivo)"""

    if df_riesgo is None or len(df_riesgo) == 0:
        return None

    df_mapa = df_riesgo.copy()
    df_mapa = df_mapa[
        (df_mapa['Latitud'].notna()) &
        (df_mapa['Longitud'].notna()) &
        (df_mapa['Stock_Teorico_Unidades'] > 0)
    ]

    if len(df_mapa) == 0:
        return None

    # Agrupar por sucursal y nivel de riesgo
    df_sucursal_riesgo = df_mapa.groupby(['Sucursal', 'Nivel_Riesgo']).agg({
        'Stock_Teorico_Unidades': 'sum',
        'Valor_Stock': 'sum',
        'Latitud': 'first',
        'Longitud': 'first'
    }).reset_index()

    # Crear resumen por sucursal para hover
    df_sucursal_total = df_mapa.groupby('Sucursal').agg({
        'Stock_Teorico_Unidades': 'sum',
        'Valor_Stock': 'sum',
        'Latitud': 'first',
        'Longitud': 'first'
    }).reset_index()

    # Calcular totales por nivel de riesgo por sucursal
    pivot_riesgo = df_mapa.pivot_table(
        index='Sucursal',
        columns='Nivel_Riesgo',
        values='Stock_Teorico_Unidades',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Merge con coordenadas
    df_sucursal_total = df_sucursal_total.merge(pivot_riesgo, on='Sucursal', how='left')

    # Rellenar valores NaN con 0
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
        if nivel not in df_sucursal_total.columns:
            df_sucursal_total[nivel] = 0
        df_sucursal_total[nivel] = df_sucursal_total[nivel].fillna(0).astype(int)

    # Crear texto hover personalizado
    df_sucursal_total['hover_text'] = df_sucursal_total.apply(
        lambda row: f"<b>{row['Sucursal']}</b><br>" +
                    f"<b>Total en Riesgo:</b> {int(row['Stock_Teorico_Unidades']):,} uds<br>" +
                    f"<b>Valor:</b> ${int(row['Valor_Stock']):,} CLP<br>" +
                    f"<br><b>Desglose:</b><br>" +
                    f"🟣 Vencido (hoy): {int(row['VENCIDO']):,} uds<br>" +
                    f"🔴 Crítico (1-3 días): {int(row['CRITICO']):,} uds<br>" +
                    f"🟠 Urgente (4-7 días): {int(row['URGENTE']):,} uds<br>" +
                    f"🟡 Preventivo (8-10 días): {int(row['PREVENTIVO']):,} uds",
        axis=1
    )

    # Calcular centro dinámico del mapa
    centro_lat = df_sucursal_total['Latitud'].mean()
    centro_lon = df_sucursal_total['Longitud'].mean()

    # Crear mapa con colores según nivel de riesgo predominante
    df_sucursal_total['Riesgo_Predominante'] = df_sucursal_total.apply(
        lambda row: 'VENCIDO' if row['VENCIDO'] > 0 else
                    ('CRITICO' if row['CRITICO'] > 0 else
                    ('URGENTE' if row['URGENTE'] > 0 else 'PREVENTIVO')),
        axis=1
    )

    # Mapear colores
    color_orden = {'VENCIDO': 4, 'CRITICO': 3, 'URGENTE': 2, 'PREVENTIVO': 1}
    df_sucursal_total['Color_Orden'] = df_sucursal_total['Riesgo_Predominante'].map(color_orden)

    fig = go.Figure()

    # Agregar puntos por cada nivel de riesgo para leyenda y colores correctos
    for nivel, color in COLOR_MAP.items():
        df_nivel = df_sucursal_total[df_sucursal_total['Riesgo_Predominante'] == nivel]
        if len(df_nivel) > 0:
            fig.add_trace(go.Scattermapbox(
                lat=df_nivel['Latitud'],
                lon=df_nivel['Longitud'],
                mode='markers',
                marker=dict(
                    size=df_nivel['Stock_Teorico_Unidades'] / df_sucursal_total['Stock_Teorico_Unidades'].max() * 40 + 15,
                    color=color,
                    opacity=0.85
                ),
                text=df_nivel['hover_text'],
                hovertemplate='%{text}<extra></extra>',
                name=nivel
            ))

    fig.update_layout(
        mapbox=dict(
            style='carto-positron',
            center={"lat": centro_lat, "lon": centro_lon},
            zoom=9
        ),
        height=600,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        title=dict(
            text="<b>Inventario en Riesgo por Sucursal</b>",
            font=dict(size=20, color='#1a237e')
        ),
        legend=dict(
            title="Nivel de Riesgo",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )

    return fig

# =============================================================================
# ANÁLISIS DE SENSIBILIDAD Y PLAN 48H
# =============================================================================

def mostrar_analisis_sensibilidad(stats):
    """Muestra el análisis de sensibilidad con 6 escenarios"""

    if stats is None:
        return

    # Valores base
    valor_vencido = stats['VENCIDO']['valor']
    valor_critico = stats['CRITICO']['valor']
    valor_urgente = stats['URGENTE']['valor']
    valor_preventivo = stats['PREVENTIVO']['valor']

    # Crédito tributario constante (27% sobre donaciones de vencidos)
    credito_trib = valor_vencido * 0.27

    # Recuperación base (escenario base): 100% de lo esperado
    # Críticos: 50% del valor, Urgentes: 40% del valor, Preventivo: 15% del valor
    recuperacion_base = (valor_critico * 0.50) + (valor_urgente * 0.40) + (valor_preventivo * 0.15)
    total_base = recuperacion_base + credito_trib

    # 6 Escenarios con factores sobre la recuperación
    escenarios = [
        {'nombre': 'Muy Pesimista', 'factor': 0.50, 'signo': '-50%', 'color': '#d32f2f', 'icono': '🔴'},
        {'nombre': 'Pesimista', 'factor': 0.70, 'signo': '-30%', 'color': '#f57c00', 'icono': '🟠'},
        {'nombre': 'Conservador', 'factor': 0.85, 'signo': '-15%', 'color': '#fbc02d', 'icono': '🟡'},
        {'nombre': 'Escenario Base', 'factor': 1.0, 'signo': '✓', 'color': '#4caf50', 'icono': '✅', 'es_base': True},
        {'nombre': 'Optimista', 'factor': 1.30, 'signo': '+30%', 'color': '#4caf50', 'icono': '🟢'},
        {'nombre': 'Muy Optimista', 'factor': 1.50, 'signo': '+50%', 'color': '#1565c0', 'icono': '🔵'},
    ]

    # Header
    st.markdown("""
    <div class="sensibilidad-header">
        <h2 style='color: #4a148c; margin: 0;'>📊 ANÁLISIS DE SENSIBILIDAD</h2>
        <p style='color: #7b1fa2; margin: 10px 0 0 0;'>Proyección de recuperación según diferentes escenarios de venta</p>
    </div>
    """, unsafe_allow_html=True)

    # Grid 3x2 de escenarios
    col1, col2, col3 = st.columns(3)
    columnas = [col1, col2, col3, col1, col2, col3]

    for i, esc in enumerate(escenarios):
        recuperacion = recuperacion_base * esc['factor']
        total = recuperacion + credito_trib
        es_base = esc.get('es_base', False)

        with columnas[i]:
            if i < 3:
                # Primera fila
                st.markdown(f"""
                <div class='escenario-card {"base" if es_base else ""}'>
                    <div class='escenario-title'>
                        <span>{esc['icono']}</span>
                        <span>{esc['nombre']} ({esc['signo']})</span>
                    </div>
                    <div class='escenario-valor' style='color: {esc["color"]};'>
                        {clp(total)} CLP
                    </div>
                    <div class='escenario-detalle'>
                        Recuperación: {clp(recuperacion)}<br>
                        + Crédito: {clp(credito_trib)}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Segunda fila
    col1, col2, col3 = st.columns(3)
    columnas2 = [col1, col2, col3]

    for i, esc in enumerate(escenarios[3:]):
        recuperacion = recuperacion_base * esc['factor']
        total = recuperacion + credito_trib
        es_base = esc.get('es_base', False)

        with columnas2[i]:
            st.markdown(f"""
            <div class='escenario-card {"base" if es_base else ""}'>
                <div class='escenario-title'>
                    <span>{esc['icono']}</span>
                    <span>{esc['nombre']} ({esc['signo']})</span>
                </div>
                <div class='escenario-valor' style='color: {esc["color"]};'>
                    {clp(total)} CLP
                </div>
                <div class='escenario-detalle'>
                    Recuperación: {clp(recuperacion)}<br>
                    + Crédito: {clp(credito_trib)}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Nota de proyección
    st.markdown("""
    <div class="nota-proyeccion">
        <strong>⚠️ Nota:</strong> Estas son <strong>proyecciones estimadas</strong>. 
        Los resultados reales dependen del tráfico de tienda, ubicación de productos y respuesta de clientes.
    </div>
    """, unsafe_allow_html=True)

def mostrar_plan_48h(stats, df_riesgo):
    """Muestra el plan de acción de 48 horas con desglose por sucursal"""

    if stats is None:
        return

    st.markdown("---")
    st.markdown('<div class="section-title-box"><h2>⏱️ PLAN DE ACCIÓN 48H</h2></div>', unsafe_allow_html=True)

    # Calcular valores
    valor_vencido = stats['VENCIDO']['valor']
    valor_critico = stats['CRITICO']['valor']
    valor_urgente = stats['URGENTE']['valor']
    valor_preventivo = stats['PREVENTIVO']['valor']

    # Cálculos del escenario BASE
    credito_trib = valor_vencido * 0.27
    recuperacion_criticos = valor_critico * 0.50
    recuperacion_urgentes = valor_urgente * 0.40
    recuperacion_preventivo = valor_preventivo * 0.15
    
    recuperacion_descuentos = recuperacion_criticos + recuperacion_urgentes + recuperacion_preventivo
    total_recuperado = credito_trib + recuperacion_descuentos

    # =========================================================================
    # FUNCIÓN AUXILIAR PARA MOSTRAR DESGLOSE POR SUCURSAL
    # =========================================================================
    def mostrar_desglose_sucursal(df_nivel, titulo_color):
    """Muestra tabla de productos agrupados por sucursal en formato grid"""
    if len(df_nivel) == 0:
        return
    
    # Agrupar por sucursal
    resumen_sucursal = df_nivel.groupby('Sucursal').agg({
        'Producto': lambda x: list(x.unique()),
        'Stock_Teorico_Unidades': 'sum',
        'Valor_Stock': 'sum'
    }).reset_index()
    
    resumen_sucursal = resumen_sucursal.sort_values('Valor_Stock', ascending=False)
    
    st.markdown(f"**📍 Desglose por Sucursal:**")
    
    # Calcular número de columnas (máximo 3-4 dependiendo de la cantidad)
    num_sucursales = len(resumen_sucursal)
    num_cols = min(3, num_sucursales) if num_sucursales > 1 else 1
    
    # Crear columnas
    columnas = st.columns(num_cols)
    
    for idx, row in resumen_sucursal.iterrows():
        sucursal = row['Sucursal']
        productos = row['Producto']
        unidades = int(row['Stock_Teorico_Unidades'])
        valor = row['Valor_Stock']
        
        productos_str = ", ".join(productos[:3])  # Mostrar máx 3 productos
        if len(productos) > 3:
            productos_str += f" (+{len(productos)-3} más)"
        
        # Determinar en qué columna va
        col_idx = idx % num_cols
        
        with columnas[col_idx]:
            st.markdown(f"""
            <div style='background: white; padding: 15px; border-radius: 10px; margin: 8px 0; 
                        border-left: 5px solid {titulo_color}; 
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                <strong style='font-size: 1.1rem;'>🏪 {sucursal}</strong><br><br>
                <div style='display: flex; justify-content: space-between; margin: 8px 0;'>
                    <span style='color: #666;'>📦 Unidades:</span>
                    <span style='font-weight: 600;'>{unidades:,}</span>
                </div>
                <div style='display: flex; justify-content: space-between; margin: 8px 0;'>
                    <span style='color: #666;'>💰 Valor:</span>
                    <span style='font-weight: 600; color: #d32f2f;'>{clp(valor)} CLP</span>
                </div>
                <div style='margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;'>
                    <span style='color: #999; font-size: 0.85rem;'>📋 {productos_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # =========================================================================
    # SECCIÓN VENCIDOS CON DESGLOSE
    # =========================================================================
    if stats['VENCIDO']['productos'] > 0:
        df_vencidos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO'].copy()
        
        st.markdown(f"""
        <div class="plan-section plan-vencido">
            <h3 style='color: #d32f2f; margin: 0 0 15px 0;'>🟣 HOY 08:00-12:00 | DONACIONES (VENCIDOS - Día 0)</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">📦 Productos</div>
                    <div class="metric-value">{stats['VENCIDO']['productos']}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">📊 Unidades</div>
                    <div class="metric-value">{clp(stats['VENCIDO']['unidades'])}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">💰 Valor</div>
                    <div class="metric-value">{clp(valor_vencido)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Desglose por sucursal para VENCIDOS
        mostrar_desglose_sucursal(df_vencidos, '#9c27b0')
        
        st.markdown(f"""
        <div style='background: #c8e6c9; padding: 15px; border-radius: 10px; text-align: center; margin-top: 15px;'>
            <span style='font-size: 1.2rem; font-weight: 700; color: #2e7d32;'>
                💰 +{clp(credito_trib)} CLP ahorro fiscal (27%)
            </span>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # SECCIÓN CRÍTICOS CON DESGLOSE
    # =========================================================================
    if stats['CRITICO']['productos'] > 0:
        df_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO'].copy()
        
        st.markdown(f"""
        <div class="plan-section plan-critico">
            <h3 style='color: #f57c00; margin: 0 0 15px 0;'>🔴 HOY 12:00-18:00 | MARKDOWN 40% (CRÍTICOS - 1 a 3 días)</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">📦 Productos</div>
                    <div class="metric-value">{stats['CRITICO']['productos']}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">📊 Unidades</div>
                    <div class="metric-value">{clp(stats['CRITICO']['unidades'])}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">💰 Valor</div>
                    <div class="metric-value">{clp(valor_critico)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Desglose por sucursal para CRÍTICOS
        mostrar_desglose_sucursal(df_criticos, '#d32f2f')
        
        st.markdown(f"""
        <div style='background: #fff3e0; padding: 15px; border-radius: 10px; text-align: center; margin-top: 15px;'>
            <span style='font-size: 1.2rem; font-weight: 700; color: #e65100;'>
                📈 Recuperación estimada: {clp(recuperacion_criticos)} CLP (50%)
            </span>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # SECCIÓN URGENTES CON DESGLOSE
    # =========================================================================
    if stats['URGENTE']['productos'] > 0:
        df_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE'].copy()
        
        st.markdown(f"""
        <div class="plan-section plan-urgente">
            <h3 style='color: #f9a825; margin: 0 0 15px 0;'>🟠 MAÑANA 08:00-12:00 | MARKDOWN 25% (URGENTES - 4 a 7 días)</h3>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">📦 Productos</div>
                    <div class="metric-value">{stats['URGENTE']['productos']}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">📊 Unidades</div>
                    <div class="metric-value">{clp(stats['URGENTE']['unidades'])}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">💰 Valor</div>
                    <div class="metric-value">{clp(valor_urgente)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Desglose por sucursal para URGENTES
        mostrar_desglose_sucursal(df_urgentes, '#f57c00')
        
        st.markdown(f"""
        <div style='background: #fffde7; padding: 15px; border-radius: 10px; text-align: center; margin-top: 15px;'>
            <span style='font-size: 1.2rem; font-weight: 700; color: #f57c00;'>
                📈 Recuperación estimada: {clp(recuperacion_urgentes)} CLP (40%)
            </span>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# SECCIONES DEL DASHBOARD
# =============================================================================

def mostrar_resumen_ejecutivo(stats, proporcion_mes, fecha_actual):
    """Muestra el resumen ejecutivo"""

    st.markdown('<h1 class="main-header">📦 Dashboard de Gestión de Inventario</h1>', unsafe_allow_html=True)

    chile_tz = pytz.timezone('America/Santiago')
    hora_chile = datetime.now(chile_tz)

    # Información del rango de análisis
    fecha_inicio = datetime(2026, 2, 1)

    st.markdown(f"""
    <div class='info-card'>
        <h2 style='color: #1565c0; margin: 0;'>Análisis: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_actual.strftime('%d/%m/%Y')}</h2>
        <p style='font-size: 1.3rem; margin: 15px 0; font-weight: 600;'>
            <span style='color: #1a237e;'>{stats['TOTAL']['productos']}</span> productos en riesgo |
            <span style='color: #1976d2;'>{clp(stats['TOTAL']['unidades'])}</span> unidades |
            <span style='color: #f57c00;'>{clp(stats['TOTAL']['valor'])} CLP</span>
        </p>
        <p style='color: #666; font-size: 0.9rem;'>
            🕒 Actualizado: {hora_chile.strftime('%d/%m/%Y %H:%M:%S')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Mostrar proporción del mes
    if proporcion_mes:
        st.markdown(f"""
        <div style='background: #e8f5e9; padding: 15px; border-radius: 10px; margin: 10px 0; text-align: center;'>
            <span style='font-size: 1rem; color: #2e7d32; font-weight: 600;'>
                📊 Proporción mercancía del mes: {proporcion_mes['proporcion']:.1f}%
                ({clp(proporcion_mes['stock_mes'])} de {clp(proporcion_mes['total_stock'])} unidades)
            </span>
        </div>
        """, unsafe_allow_html=True)

def mostrar_clasificacion(stats):
    """Muestra la clasificación del inventario"""

    st.markdown('<div class="section-title-box"><h2>📊 Clasificación por Nivel de Riesgo</h2></div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    niveles = [
        ('VENCIDO', 'vencido', '🟣', '#9c27b0', 'Día 0 (Hoy)'),
        ('CRITICO', 'critico', '🔴', '#d32f2f', '1-3 días'),
        ('URGENTE', 'urgente', '🟠', '#f57c00', '4-7 días'),
        ('PREVENTIVO', 'preventivo', '🟡', '#fbc02d', '8-10 días')
    ]

    columnas = [col1, col2, col3, col4]

    for (nivel, clase, emoji, color, dias), col in zip(niveles, columnas):
        with col:
            st.markdown(f"""
            <div class='classification-item {clase}' style='text-align: center; display: block;'>
                <span class='indicator' style='background-color: {color}; margin: 0 auto 10px auto;'></span>
                <strong>{emoji} {nivel}</strong><br>
                <small style='color: #666;'>({dias})</small><br><br>
                <div style='font-size: 1.4rem;'>{stats[nivel]['productos']}</div>
                <small>productos</small><br>
                <div style='font-size: 1.1rem;'>{clp(stats[nivel]['unidades'])}</div>
                <small>unidades</small><br>
                <div style='font-size: 1rem; color: {color};'><strong>{clp(stats[nivel]['valor'])} CLP</strong></div>
            </div>
            """, unsafe_allow_html=True)

def mostrar_productos_por_riesgo(df_riesgo, stats):
    """Muestra los productos agrupados por nivel de riesgo en secciones expandibles"""

    st.markdown("---")
    st.markdown('<div class="section-title-box"><h2>📦 PRODUCTOS POR NIVEL DE RIESGO</h2></div>', unsafe_allow_html=True)

    if df_riesgo is None or len(df_riesgo) == 0:
        st.success("No hay productos en riesgo")
        return

    niveles_config = [
        ('VENCIDO', '🟣', '#9c27b0', 'Día 0 - Hoy'),
        ('CRITICO', '🔴', '#d32f2f', '1-3 días'),
        ('URGENTE', '🟠', '#f57c00', '4-7 días'),
        ('PREVENTIVO', '🟡', '#fbc02d', '8-10 días')
    ]

    for nivel, emoji, color, dias in niveles_config:
        df_nivel = df_riesgo[df_riesgo['Nivel_Riesgo'] == nivel].copy()
        
        if len(df_nivel) > 0:
            # Header del expander
            n_productos = stats[nivel]['productos']
            n_unidades = stats[nivel]['unidades']
            valor = stats[nivel]['valor']
            
            with st.expander(f"{emoji} {nivel} ({n_productos} productos | {clp(n_unidades)} unidades | {clp(valor)} CLP)"):
                # Ordenar por valor descendente
                df_display = df_nivel.sort_values('Valor_Stock', ascending=False)
                
                # Seleccionar columnas relevantes
                columnas = ['Producto', 'Sucursal', 'Stock_Teorico_Unidades', 'Dias_Para_Vencer', 'Valor_Stock']
                
                # Verificar que las columnas existen
                columnas_existentes = [c for c in columnas if c in df_display.columns]
                df_display = df_display[columnas_existentes].copy()
                
                # Renombrar columnas
                rename_map = {
                    'Producto': 'Producto',
                    'Sucursal': 'Sucursal',
                    'Stock_Teorico_Unidades': 'Stock (uds)',
                    'Dias_Para_Vencer': 'Días Vencer',
                    'Valor_Stock': 'Valor (CLP)'
                }
                df_display = df_display.rename(columns={k: v for k, v in rename_map.items() if k in df_display.columns})
                
                # Formatear valor
                if 'Valor (CLP)' in df_display.columns:
                    df_display['Valor (CLP)'] = df_display['Valor (CLP)'].apply(lambda x: clp(x))
                
                # Mostrar tabla
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    height=min(400, len(df_display) * 35 + 38)
                )
        else:
            st.markdown(f"""
            <div style='padding: 10px; background: #f5f5f5; border-radius: 8px; margin: 5px 0;'>
                <span style='color: #999;'>{emoji} {nivel} - Sin productos en esta categoría</span>
            </div>
            """, unsafe_allow_html=True)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    configurar_pagina()
    cargar_css()

    st.title("📦 Sistema de Gestión de Inventario")
    st.markdown("---")

    # =====================================================================
    # SIDEBAR - Carga de archivos
    # =====================================================================

    st.sidebar.header("📁 Carga de Datos")
    st.sidebar.markdown("Sube los 5 archivos CSV:")

    archivos_subidos = st.sidebar.file_uploader(
        "Seleccionar archivos CSV",
        type=['csv'],
        accept_multiple_files=True,
        help="Sube: Sucursales, Productos, Lotes, Inventario, Stock Geo"
    )

    boton_ejecutar = st.sidebar.button("🚀 Ejecutar Análisis", type="primary")

    # Verificar archivos
    if not archivos_subidos:
        st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h2>📦 Sistema de Gestión de Inventario</h2>
            <p style='color: #666; font-size: 1.2rem;'>
                Por favor sube los 5 archivos CSV en el panel lateral.
            </p>
            <div style='background: #e3f2fd; padding: 20px; border-radius: 10px; margin-top: 30px;'>
                <h4>📋 Archivos requeridos:</h4>
                <ul style='text-align: left; display: inline-block;'>
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
        st.sidebar.error(f"⚠️ Falta subir archivos. Has subido {len(archivos_subidos)} de 5.")
        return

    # Procesar archivos
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

    archivos_requeridos = ['sucursales', 'productos', 'lotes', 'inventario', 'stock_geo']
    if not all(k in archivos_dict for k in archivos_requeridos):
        st.sidebar.error("⚠️ No se reconocieron todos los archivos.")
        return

    if not boton_ejecutar:
        st.sidebar.info("👆 Sube los 5 archivos y haz clic en 'Ejecutar Análisis'")
        return

    # =====================================================================
    # ETL y Análisis
    # =====================================================================

    with st.spinner("🔄 Ejecutando análisis..."):
        datos = cargar_datos_etl(archivos_dict)

    if datos is None:
        st.error("❌ Error en el proceso ETL.")
        return

    df_stock = datos['stock_geo']

    st.success("✅ Análisis completado")

    # Preparar datos
    df_riesgo, fecha_actual = preparar_datos_analisis(df_stock)
    stats = calcular_estadisticas(df_riesgo)
    proporcion_mes = calcular_proporcion_mes(df_stock)

    # =====================================================================
    # MOSTRAR RESULTADOS
    # =====================================================================

    mostrar_resumen_ejecutivo(stats, proporcion_mes, fecha_actual)
    st.markdown("---")

    mostrar_clasificacion(stats)
    st.markdown("---")

    # Gráficos de distribución (ahora con 3 gráficos)
    st.markdown('<div class="section-title-box"><h2>📈 Distribución del Inventario en Riesgo</h2></div>', unsafe_allow_html=True)
    fig_dist = crear_graficos_distribucion(stats)
    if fig_dist:
        st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("---")

    # Matriz de riesgo
    st.markdown('<div class="section-title-box"><h2>🎯 Matriz de Riesgo</h2></div>', unsafe_allow_html=True)
    fig_matriz = crear_matriz_riesgo(df_riesgo, fecha_actual)
    if fig_matriz:
        st.pyplot(fig_matriz)

    st.markdown("---")

    # Mapa con pestañas
    st.markdown('<div class="section-title-box"><h2>🗺️ Mapa Geográfico</h2></div>', unsafe_allow_html=True)

    # Crear pestañas para el mapa
    tab_stock, tab_riesgo = st.tabs(["📦 Stock Total", "⚠️ Inventario en Riesgo"])

    with tab_stock:
        st.markdown("### Stock Total por Sucursal")
        st.markdown("*Muestra el stock total de todas las sucursales*")
        fig_mapa = crear_mapa_stock(df_stock)
        if fig_mapa:
            st.plotly_chart(fig_mapa, use_container_width=True,config={'scrollZoom': True})
        else:
            st.warning("No hay datos geográficos disponibles para mostrar el mapa.")

    with tab_riesgo:
        st.markdown("### Inventario en Riesgo por Sucursal")
        st.markdown("*Muestra solo el inventario clasificado como: **Vencido** (hoy), **Crítico** (1-3 días), **Urgente** (4-7 días) y **Preventivo** (8-10 días)*")

        # Mostrar leyenda de colores
        st.markdown("""
        <div style='display: flex; gap: 20px; margin: 10px 0; flex-wrap: wrap;'>
            <span style='display: flex; align-items: center;'><span style='width: 15px; height: 15px; background: #9c27b0; border-radius: 50%; margin-right: 5px;'></span> Vencido (Día 0 - Hoy)</span>
            <span style='display: flex; align-items: center;'><span style='width: 15px; height: 15px; background: #d32f2f; border-radius: 50%; margin-right: 5px;'></span> Crítico (1-3 días)</span>
            <span style='display: flex; align-items: center;'><span style='width: 15px; height: 15px; background: #f57c00; border-radius: 50%; margin-right: 5px;'></span> Urgente (4-7 días)</span>
            <span style='display: flex; align-items: center;'><span style='width: 15px; height: 15px; background: #fbc02d; border-radius: 50%; margin-right: 5px;'></span> Preventivo (8-10 días)</span>
        </div>
        """, unsafe_allow_html=True)

        fig_mapa_riesgo = crear_mapa_inventario_riesgo(df_riesgo)
        if fig_mapa_riesgo:
            st.plotly_chart(fig_mapa_riesgo, use_container_width=True, config={'scrollZoom': True})
        else:
            st.warning("No hay datos de inventario en riesgo con coordenadas geográficas.")

    st.markdown("---")
    # Productos por nivel de riesgo (accordions)
    mostrar_productos_por_riesgo(df_riesgo, stats)
    
    # Análisis de sensibilidad (6 escenarios)
    mostrar_analisis_sensibilidad(stats)

    # Plan 48h
    mostrar_plan_48h(stats, df_riesgo)


    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>📊 <strong>Sistema de Gestión de Inventario</strong></p>
        <p>Desarrollado con Streamlit</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
