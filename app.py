#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inventario BI Dashboard - Versión Final
Dashboard interactivo para análisis de inventario con métricas de riesgo,
mapa geográfico, análisis de sensibilidad y plan de acción de 48h.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import warnings

# Configuración de la página
st.set_page_config(
    page_title="Inventario BI - Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de matplotlib para matplotlib
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "PingFang SC", "Arial Unicode MS", "Hiragino Sans GB"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================
# FUNCIONES DE ETL Y CARGA DE DATOS
# ============================================

def cargar_datos_etl(archivos_subidos):
    """
    Realiza el proceso ETL: Extrae, Transforma y Carga los datos desde los archivos subidos.
    
    Args:
        archivos_subidos: Diccionario con los nombres de archivo como claves y los objetos de archivo como valores.
    
    Returns:
        DataFrame con los datos integrados y limpios.
    """
    try:
        # Identificar cada archivo por su nombre
        archivos_dict = {}
        for archivo in archivos_subidos:
            nombre = archivo.name.lower()
            if 'sucursal' in nombre:
                archivos_dict['sucursales'] = archivo
            elif 'producto' in nombre:
                archivos_dict['productos'] = archivo
            elif 'lote' in nombre:
                archivos_dict['lotes'] = archivo
            elif 'inventario' in nombre:
                archivos_dict['inventario'] = archivo
            elif 'stock' in nombre or 'geo' in nombre:
                archivos_dict['stock_geo'] = archivo
        
        # Cargar cada archivo
        df_sucursales = pd.read_csv(archivos_dict['sucursales'])
        df_productos = pd.read_csv(archivos_dict['productos'])
        df_lotes = pd.read_csv(archivos_dict['lotes'])
        df_inventario = pd.read_csv(archivos_dict['inventario'])
        df_stock_geo = pd.read_csv(archivos_dict['stock_geo'])
        
        # Mostrar información de las columnas para depuración
        with st.expander("Debug: Columnas de cada archivo"):
            st.write("SUCURSALES:", df_sucursales.columns.tolist())
            st.write("PRODUCTOS:", df_productos.columns.tolist())
            st.write("LOTES:", df_lotes.columns.tolist())
            st.write("INVENTARIO:", df_inventario.columns.tolist())
            st.write("STOCK_GEO:", df_stock_geo.columns.tolist())
        
        # Realizar los merge para integrar los datos
        # Primero unimos inventario con lotes
        df_inventario = df_inventario.merge(
            df_lotes, 
            left_on=['ID_PRODUCTO', 'ID_SUCURSAL'], 
            right_on=['ID_PRODUCTO', 'ID_SUCURSAL'],
            how='left',
            suffixes=('', '_lote')
        )
        
        # Luego unimos con productos
        df_inventario = df_inventario.merge(
            df_productos, 
            on='ID_PRODUCTO', 
            how='left'
        )
        
        # Después unimos con sucursales
        df_inventario = df_inventario.merge(
            df_sucursales, 
            on='ID_SUCURSAL', 
            how='left',
            suffixes=('', '_suc')
        )
        
        # Finalmente unimos con stock_geo
        df_inventario = df_inventario.merge(
            df_stock_geo, 
            on=['ID_PRODUCTO', 'ID_SUCURSAL'], 
            how='left',
            suffixes=('', '_geo')
        )
        
        # Limpiar datos: eliminar duplicados y manejar valores nulos
        df_inventario = df_inventario.drop_duplicates()
        df_inventario = df_inventario.fillna(0)
        
        return df_inventario
        
    except Exception as e:
        st.error(f"Error en el proceso ETL: {str(e)}")
        return None


def preparar_datos_analisis(df):
    """
    Prepara los datos para el análisis filtrando por fecha y calculando días hasta vencimiento.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
        DataFrame filtrado y enriquecido.
    """
    # Convertir columnas de fecha
    fecha_cols = [col for col in df.columns if 'FECHA' in col.upper()]
    for col in fecha_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Fecha de análisis (hoy)
    fecha_analisis = datetime.now()
    
    # Filtrar: considerar solo registros desde el 1 de febrero del año actual
    fecha_inicio = datetime(fecha_analisis.year, 2, 1)
    
    # Crear columna de días hasta vencimiento
    if 'FECHA_VENCIMIENTO' in df.columns:
        df['DIAS_VENCIMIENTO'] = (df['FECHA_VENCIMIENTO'] - fecha_analisis).dt.days
    elif 'FECHA_VENC' in df.columns:
        df['DIAS_VENCIMIENTO'] = (df['FECHA_VENC'] - fecha_analisis).dt.days
    else:
        # Buscar cualquier columna relacionada con fecha de vencimiento
        for col in df.columns:
            if 'venc' in col.lower():
                df['DIAS_VENCIMIENTO'] = (pd.to_datetime(df[col], errors='coerce') - fecha_analisis).dt.days
                break
    
    # Filtrar: solo datos desde el 1 de febrero y días >= 0 (no considerar productos ya vencidos para el análisis prospectivo)
    # Pero queremos mostrar los vencidos también
    df_analisis = df.copy()
    
    return df_analisis, fecha_analisis


def clasificar_riesgo(dias):
    """
    Clasifica el riesgo según los días hasta el vencimiento.
    
    Args:
        dias: Número de días hasta el vencimiento.
    
    Returns:
        String con la clasificación de riesgo.
    """
    if dias is None or pd.isna(dias):
        return 'NORMAL'
    
    if dias < 0:
        return 'VENCIDO'
    elif dias == 0:
        return 'VENCIDO'
    elif dias <= 3:
        return 'CRITICO'
    elif dias <= 7:
        return 'URGENTE'
    elif dias <= 10:
        return 'PREVENTIVO'
    else:
        return 'NORMAL'


def analizar_por_sucursal(df):
    """
    Analiza el inventario por sucursal con clasificación de riesgo.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
        DataFrame con el análisis por sucursal.
    """
    # Clasificar riesgo
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    # Agrupar por sucursal y riesgo
    riesgo_por_sucursal = df.groupby(['ID_SUCURSAL', 'RIESGO']).size().unstack(fill_value=0)
    
    # Asegurar el orden de las columnas
    column_order = ['CRITICO', 'NORMAL', 'PREVENTIVO', 'URGENTE', 'VENCIDO']
    for col in column_order:
        if col not in riesgo_por_sucursal.columns:
            riesgo_por_sucursal[col] = 0
    
    riesgo_por_sucursal = riesgo_por_sucursal.reindex(columns=column_order, fill_value=0)
    
    # Obtener información de sucursales (latitud, longitud)
    if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
        coords = df.groupby('ID_SUCURSAL').agg({
            'LATITUD': 'first',
            'LONGITUD': 'first'
        }).reset_index()
        
        # Unir coordenadas
        riesgo_por_sucursal = riesgo_por_sucursal.reset_index()
        riesgo_por_sucursal = riesgo_por_sucursal.merge(coords, on='ID_SUCURSAL', how='left')
    
    return riesgo_por_sucursal


def crear_tabla_sucursales(df):
    """
    Crea una tabla consolidada por sucursal con coordenadas correctas.
    
    Args:
        df: DataFrame con los datos del análisis por sucursal.
    
    Returns:
        DataFrame formateado para mostrar.
    """
    # Obtener coordenadas de stock_geo
    if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
        df_display = df.copy()
        # Reordenar columnas para que coordenadas estén al final
        cols = [c for c in df_display.columns if c not in ['LATITUD', 'LONGITUD']]
        cols.extend(['LATITUD', 'LONGITUD'])
        df_display = df_display[cols]
    else:
        df_display = df.copy()
    
    return df_display


def obtener_metricas(df, fecha_analisis):
    """
    Calcula las métricas principales del inventario.
    
    Args:
        df: DataFrame con los datos del inventario.
        fecha_analisis: Fecha de análisis actual.
    
    Returns:
        Diccionario con las métricas calculadas.
    """
    # Clasificar riesgo
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    # Calcular métricas
    total_productos = len(df)
    vencido = len(df[df['RIESGO'] == 'VENCIDO'])
    critico = len(df[df['RIESGO'] == 'CRITICO'])
    urgente = len(df[df['RIESGO'] == 'URGENTE'])
    preventivo = len(df[df['RIESGO'] == 'PREVENTIVO'])
    normal = len(df[df['RIESGO'] == 'NORMAL'])
    
    # Calcular proporción de stock del mes actual
    mes_actual = fecha_analisis.month
    anio_actual = fecha_analisis.year
    
    if 'FECHA_VENCIMIENTO' in df.columns:
        df['MES_VENC'] = df['FECHA_VENCIMIENTO'].dt.month
        df['AÑO_VENC'] = df['FECHA_VENCIMIENTO'].dt.year
        stock_mes = len(df[(df['MES_VENC'] == mes_actual) & (df['AÑO_VENC'] == anio_actual)])
        proporcion_mes = (stock_mes / total_productos * 100) if total_productos > 0 else 0
    else:
        proporcion_mes = 0
    
    return {
        'total': total_productos,
        'vencido': vencido,
        'critico': critico,
        'urgente': urgente,
        'preventivo': preventivo,
        'normal': normal,
        'proporcion_mes': proporcion_mes
    }


def crear_grafico_estado(df):
    """
    Crea un gráfico circular del estado del inventario.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
        Figure de Plotly.
    """
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    conteo = df['RIESGO'].value_counts()
    
    # Orden personalizado
    orden = ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO', 'NORMAL']
    conteo = conteo.reindex([r for r in orden if r in conteo.index])
    
    colores = {
        'VENCIDO': '#e74c3c',
        'CRITICO': '#e67e22',
        'URGENTE': '#f39c12',
        'PREVENTIVO': '#27ae60',
        'NORMAL': '#3498db'
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=conteo.index,
        values=conteo.values,
        marker=dict(colors=[colores.get(c, '#95a5a6') for c in conteo.index]),
        hole=0.4,
        textinfo='label+percent',
        textposition='outside'
    )])
    
    fig.update_layout(
        title="Estado del Inventario",
        showlegend=True,
        height=400,
        margin=dict(t=50, b=20, l=20, r=20)
    )
    
    return fig


def crear_graficos_distribucion(df):
    """
    Crea gráficos de distribución por SKUs y por valor.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
        Figure de Plotly con subplots.
    """
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    # Distribución por SKUs
    niveles = ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO', 'NORMAL']
    colores_list = ['#e74c3c', '#e67e22', '#f39c12', '#27ae60', '#3498db']
    
    conteo = df['RIESGO'].value_counts()
    valores = [conteo.get(n, 0) for n in niveles]
    
    # Crear subplots
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=("Distribución por SKUs", "Distribución por Valor")
    )
    
    # Primer pie chart (SKUs)
    fig.add_trace(
        go.Pie(
            labels=niveles,
            values=valores,
            marker=dict(colors=colores_list),
            hole=0.3,
            textinfo='label+percent',
            name="Por SKUs"
        ),
        row=1, col=1
    )
    
    # Segundo pie chart (Valor - usando valores absolutos simulados)
    # Asumimos que hay una columna de valor o usamos valores representativos
    if 'VALOR' in df.columns:
        valor_riesgo = df.groupby('RIESGO')['VALOR'].sum()
    elif 'PRECIO' in df.columns:
        valor_riesgo = df.groupby('RIESGO')['PRECIO'].sum()
    else:
        # Usar los mismos valores para demo
        valor_riesgo = df.groupby('RIESGO').size()
    
    valores_2 = [valor_riesgo.get(n, 0) for n in niveles]
    
    fig.add_trace(
        go.Pie(
            labels=niveles,
            values=valores_2,
            marker=dict(colors=colores_list),
            hole=0.3,
            textinfo='label+percent',
            name="Por Valor"
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=450,
        showlegend=False,
        title_text="Distribución del Inventario"
    )
    
    return fig


def crear_mapa_interactivo(df):
    """
    Crea un mapa interactivo con pestañas para diferentes vistas.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
        Figure de Plotly Express.
    """
    # Verificar que existen las columnas necesarias
    if 'LATITUD' not in df.columns or 'LONGITUD' not in df.columns:
        st.warning("No se encontraron columnas de latitud/longitud en los datos.")
        return None
    
    # Clasificar riesgo
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    # Agregar por sucursal para el mapa
    df_mapa = df.groupby(['ID_SUCURSAL', 'LATITUD', 'LONGITUD', 'RIESGO']).size().reset_index(name='CANTIDAD')
    
    # Color mapping
    colores = {
        'VENCIDO': '#e74c3c',
        'CRITICO': '#e67e22',
        'URGENTE': '#f39c12',
        'PREVENTIVO': '#27ae60',
        'NORMAL': '#3498db'
    }
    
    # Crear figura
    fig = px.scatter_mapbox(
        df_mapa,
        lat='LATITUD',
        lon='LONGITUD',
        size='CANTIDAD',
        color='RIESGO',
        color_discrete_map=colores,
        zoom=10,
        title="Mapa de Inventario por Sucursal",
        size_max=30,
        hover_name='ID_SUCURSAL',
        hover_data={
            'CANTIDAD': True,
            'RIESGO': True,
            'LATITUD': ':.4f',
            'LONGITUD': ':.4f'
        }
    )
    
    fig.update_layout(
        mapbox_style="open-street-map",
        height=500,
        margin=dict(t=50, b=20, l=20, r=20),
        title_x=0.5
    )
    
    return fig


def crear_matriz_riesgo(df):
    """
    Crea una matriz de riesgoscatter plot.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
    matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Preparar datos
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    # Agrupar por riesgo y días
    colores = {
        'VENCIDO': '#e74c3c',
        'CRITICO': '#e67e22',
        'URGENTE': '#f39c12',
        'PREVENTIVO': '#27ae60',
        'NORMAL': '#3498db'
    }
    
    for riesgo, color in colores.items():
        df_r = df[df['RIESGO'] == riesgo]
        if len(df_r) > 0:
            ax.scatter(
                df_r['DIAS_VENCIMIENTO'], 
                df_r.get('CANTIDAD', 1),
                c=color, 
                label=riesgo, 
                alpha=0.6, 
                s=50
            )
    
    ax.set_xlabel('Días hasta Vencimiento', fontsize=12)
    ax.set_ylabel('Cantidad en Inventario', fontsize=12)
    ax.set_title('Matriz de Riesgo de Inventario', fontsize=14, fontweight='bold')
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.5, label='Hoy')
    ax.axvline(x=3, color='orange', linestyle='--', alpha=0.5, label='Límite Crítico')
    ax.axvline(x=7, color='yellow', linestyle='--', alpha=0.5, label='Límite Urgente')
    ax.axvline(x=10, color='green', linestyle='--', alpha=0.5, label='Límite Preventivo')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def mostrar_analisis_sensibilidad(df):
    """
    Muestra un análisis de sensibilidad del inventario.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
        DataFrame con el análisis de sensibilidad.
    """
    # Clasificar riesgo
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    # Análisis por rango de días
    rangos = [
        (0, 3, 'Crítico (0-3 días)'),
        (4, 7, 'Urgente (4-7 días)'),
        (8, 10, 'Preventivo (8-10 días)'),
        (11, 30, 'Corto Plazo (11-30 días)'),
        (31, 90, 'Mediano Plazo (31-90 días)'),
        (91, 365, 'Largo Plazo (91-365 días)')
    ]
    
    sensibilidad = []
    for inicio, fin, etiqueta in rangos:
        df_rango = df[(df['DIAS_VENCIMIENTO'] >= inicio) & (df['DIAS_VENCIMIENTO'] <= fin)]
        cantidad = len(df_rango)
        if 'VALOR' in df_rango.columns:
            valor = df_rango['VALOR'].sum()
        elif 'PRECIO' in df_rango.columns:
            valor = df_rango['PRECIO'].sum()
        else:
            valor = cantidad * 100  # Valor estimado
        
        sensibilidad.append({
            'Rango': etiqueta,
            'Cantidad SKUs': cantidad,
            'Valor Estimado': valor,
            'Porcentaje': (cantidad / len(df) * 100) if len(df) > 0 else 0
        })
    
    return pd.DataFrame(sensibilidad)


def mostrar_plan_48h(df):
    """
    Genera un plan de acción para las próximas 48 horas.
    
    Args:
        df: DataFrame con los datos del inventario.
    
    Returns:
        DataFrame con el plan de acción.
    """
    # Clasificar riesgo
    df['RIESGO'] = df['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
    
    # Filtrar productos que requieren acción inmediata (próximas 48h = 2 días)
    df_accion = df[df['DIAS_VENCIMIENTO'] <= 2].copy()
    
    # Ordenar por urgencia
    df_accion = df_accion.sort_values('DIAS_VENCIMIENTO')
    
    # Crear plan
    plan = []
    for idx, row in df_accion.head(20).iterrows():  # Top 20 prioritarios
        accion = {
            'Producto': row.get('NOMBRE_PRODUCTO', row.get('PRODUCTO', f"SKU {row.get('ID_PRODUCTO', 'N/A')}")),
            'Sucursal': row.get('NOMBRE_SUCURSAL', row.get('SUCURSAL', f"ID {row.get('ID_SUCURSAL', 'N/A')}")),
            'Días Restantes': row['DIAS_VENCIMIENTO'],
            'Nivel Riesgo': row['RIESGO'],
            'Acción Recomendada': 'Venta urgente / Descuento' if row['RIESGO'] == 'VENCIDO' else 
                                  'Revisión inmediata' if row['RIESGO'] == 'CRITICO' else 
                                  'Monitoreo cercano'
        }
        plan.append(accion)
    
    return pd.DataFrame(plan)


# ============================================
# INTERFAZ PRINCIPAL
# ============================================

def main():
    """
    Función principal que controla el layout del dashboard.
    """
    # Título principal
    st.title("📦 Dashboard de Inventario - Análisis BI")
    st.markdown("---")
    
    # Sidebar para carga de archivos
    st.sidebar.header("📂 Carga de Datos")
    st.sidebar.markdown("Sube los 5 archivos CSV necesarios:")
    
    archivos_subidos = st.sidebar.file_uploader(
        "Selecciona los archivos (SUCURSALES, PRODUCTOS, LOTES, INVENTARIO, STOCK_GEO)",
        type=['csv'],
        accept_multiple_files=True
    )
    
    if not archivos_subidos:
        st.info("👈 Por favor, sube los 5 archivos CSV para comenzar el análisis.")
        
        # Mostrar información de los archivos esperados
        with st.expander("ℹ️ Archivos esperados"):
            st.markdown("""
            - **1_SUCURSALES_MASTER.csv** - Datos de sucursales
            - **2_PRODUCTOS_MASTER.csv** - Catálogo de productos
            - **3_LOTES_PRODUCTOS.csv** - Información de lotes
            - **4_INVENTARIO_COMPLETO_LOTES.csv** - Inventario completo
            - **5_STOCK_ACTUAL_GEO_POWERBI.csv** - Stock con coordenadas geográficas
            """)
        return
    
    # Proceso ETL
    with st.spinner("🔄 Procesando datos..."):
        df = cargar_datos_etl(archivos_subidos)
    
    if df is None:
        st.error("❌ Error al cargar los datos. Verifica que los archivos sean correctos.")
        return
    
    # Preparar datos para análisis
    df_analisis, fecha_analisis = preparar_datos_analisis(df)
    
    # Obtener métricas
    metricas = obtener_metricas(df_analisis, fecha_analisis)
    
    # ==============================
    # RESUMEN EJECUTIVO (48h Plan)
    # ==============================
    st.subheader("🎯 Plan de Acción - Próximas 48 horas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "⚠️ VENCIDO",
            metricas['vencido'],
            delta=None,
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "🔥 CRÍTICO (1-3 días)",
            metricas['critico'],
            delta=None,
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "⚡ URGENTE (4-7 días)",
            metricas['urgente'],
            delta=None,
            delta_color="normal"
        )
    
    with col4:
        st.metric(
            "🛡️ PREVENTIVO (8-10 días)",
            metricas['preventivo'],
            delta=None,
            delta_color="off"
        )
    
    st.markdown("---")
    
    # ==============================
    # MAPA INTERACTIVO (arriba)
    # ==============================
    st.subheader("🗺️ Mapa de Inventario por Sucursal")
    
    # Crear pestañas para el mapa
    pestana_mapa = st.tabs(["📊 Vista General", "⚠️ Vista de Riesgo"])
    
    with pestana_mapa[0]:
        fig_mapa = crear_mapa_interactivo(df_analisis)
        if fig_mapa:
            st.plotly_chart(fig_mapa, use_container_width=True)
    
    with pestana_mapa[1]:
        # Vista de riesgo en el mapa
        df_analisis['RIESGO'] = df_analisis['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
        fig_mapa_riesgo = crear_mapa_interactivo(df_analisis)
        if fig_mapa_riesgo:
            st.plotly_chart(fig_mapa_riesgo, use_container_width=True)
    
    st.markdown("---")
    
    # ==============================
    # GRÁFICO DE ESTADO (Resumen)
    # ==============================
    st.subheader("📈 Estado del Inventario")
    
    col_grafico, col_tabla = st.columns([2, 1])
    
    with col_grafico:
        fig_estado = crear_grafico_estado(df_analisis)
        st.plotly_chart(fig_estado, use_container_width=True)
    
    with col_tabla:
        st.markdown("### 📋 Leyenda de Estados")
        st.markdown("""
        - 🔴 **VENCIDO**: Productos vencidos (0 días)
        - 🟠 **CRÍTICO**: 1-3 días hasta vencer
        - 🟡 **URGENTE**: 4-7 días hasta vencer
        - 🟢 **PREVENTIVO**: 8-10 días hasta vencer
        - 🔵 **NORMAL**: Más de 10 días
        """)
        
        st.markdown("### 📊 Proporción del Mes")
        st.metric(
            "Stock vence este mes",
            f"{metricas['proporcion_mes']:.1f}%",
            delta=None
        )
    
    st.markdown("---")
    
    # ==============================
    # ANÁLISIS COMPLETO (Colapsible)
    # ==============================
    ver_detalle = st.checkbox("📊 Ver Análisis Completo")
    
    if ver_detalle:
        # Distribución
        st.subheader("📊 Distribución del Inventario")
        fig_dist = crear_graficos_distribucion(df_analisis)
        st.plotly_chart(fig_dist, use_container_width=True)
        
        st.markdown("---")
        
        # Matriz de Riesgo
        st.subheader("🎯 Matriz de Riesgo")
        fig_matriz = crear_matriz_riesgo(df_analisis)
        st.pyplot(fig_matriz)
        
        st.markdown("---")
        
        # Análisis de Sensibilidad
        st.subheader("📉 Análisis de Sensibilidad")
        df_sensibilidad = mostrar_analisis_sensibilidad(df_analisis)
        st.dataframe(
            df_sensibilidad.style.format({
                'Cantidad SKUs': '{:,.0f}',
                'Valor Estimado': '${:,.2f}',
                'Porcentaje': '{:.1f}%'
            }),
            use_container_width=True
        )
        
        # Gráfico de sensibilidad
        fig_sens = px.bar(
            df_sensibilidad,
            x='Rango',
            y='Cantidad SKUs',
            color='Rango',
            title="Análisis de Sensibilidad por Rango de Días",
            labels={'Cantidad SKUs': 'Cantidad', 'Rango': 'Rango de Días'}
        )
        st.plotly_chart(fig_sens, use_container_width=True)
        
        st.markdown("---")
        
        # Plan de 48h Detallado
        st.subheader("⏰ Plan de Acción Detallado (Próximas 48h)")
        plan_48h = mostrar_plan_48h(df_analisis)
        
        if len(plan_48h) > 0:
            st.dataframe(
                plan_48h.style.apply(
                    lambda x: ['background-color: #ffcccc' if x['Nivel Riesgo'] == 'VENCIDO' 
                              else 'background-color: #ffe6cc' if x['Nivel Riesgo'] == 'CRITICO'
                              else 'background-color: #fff3cd' for i in x], 
                    axis=1
                ),
                use_container_width=True
            )
        else:
            st.success("✅ No hay productos que requieran acción inmediata en las próximas 48 horas.")
        
        st.markdown("---")
        
        # Detalle por Sucursal
        st.subheader("🏪 Detalle por Sucursal")
        
        riesgo_sucursal = analizar_por_sucursal(df_analisis)
        tabla_sucursales = crear_tabla_sucursales(riesgo_sucursal)
        
        st.dataframe(
            tabla_sucursales.style.format({
                'CRITICO': '{:,.0f}',
                'NORMAL': '{:,.0f}',
                'PREVENTIVO': '{:,.0f}',
                'URGENTE': '{:,.0f}',
                'VENCIDO': '{:,.0f}',
                'LATITUD': '{:.4f}',
                'LONGITUD': '{:.4f}'
            }),
            use_container_width=True
        )
        
        # Tabla de productos detallada
        st.markdown("---")
        st.subheader("📋 Lista Completa de Productos")
        
        # Mostrar con filtros
        df_analisis['RIESGO'] = df_analisis['DIAS_VENCIMIENTO'].apply(clasificar_riesgo)
        
        filtro_riesgo = st.multiselect(
            "Filtrar por nivel de riesgo:",
            options=['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO', 'NORMAL'],
            default=['VENCIDO', 'CRITICO', 'URGENTE']
        )
        
        if filtro_riesgo:
            df_filtrado = df_analisis[df_analisis['RIESGO'].isin(filtro_riesgo)]
        else:
            df_filtrado = df_analisis
        
        # Seleccionar columnas para mostrar
        cols_mostrar = ['ID_PRODUCTO', 'NOMBRE_PRODUCTO', 'ID_SUCURSAL', 'NOMBRE_SUCURSAL', 
                        'DIAS_VENCIMIENTO', 'RIESGO']
        cols_existentes = [c for c in cols_mostrar if c in df_filtrado.columns]
        
        if cols_existentes:
            st.dataframe(
                df_filtrado[cols_existentes].sort_values('DIAS_VENCIMIENTO'),
                use_container_width=True
            )
        
        st.markdown("### Resumen de productos filtrados")
        st.write(f"Total de productos en la vista: {len(df_filtrado):,}")


if __name__ == "__main__":
    main()
