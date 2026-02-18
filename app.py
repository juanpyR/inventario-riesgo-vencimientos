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
# COLORES SEMÁFORO
# =============================================================================
COLOR_MAP = {
    'VENCIDO': '#9c27b0',
    'CRITICO': '#d32f2f',
    'URGENTE': '#f57c00',
    'PREVENTIVO': '#fbc02d',
    'NORMAL': '#2e7d32'
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
    .section-title-box { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 15px 25px; border-radius: 10px; display: inline-block; margin: 2rem 0 1rem 0; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
    .section-title-box h2 { color: white !important; margin: 0; font-size: 1.8rem; font-weight: 600; }
    .info-card { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 15px; padding: 25px; text-align: center; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .classification-item { padding: 15px; margin: 10px 0; border-radius: 10px; display: flex; align-items: center; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .vencido { background: #f3e5f5; color: #7b1fa2; border-left: 5px solid #9c27b0; }
    .critico { background: #ffebee; color: #c62828; border-left: 5px solid #d32f2f; }
    .urgente { background: #fff3e0; color: #e65100; border-left: 5px solid #f57c00; }
    .preventivo { background: #fffde7; color: #f9a825; border-left: 5px solid #fbc02d; }
    .dataframe { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-size: 0.9rem; width: 100%; }
    .dataframe thead th { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 700; padding: 15px; text-align: left; border: none; }
    .dataframe tbody tr:nth-child(even) { background-color: #f8f9fa; }
    .dataframe tbody tr:nth-child(odd) { background-color: white; }
    .dataframe tbody tr:hover { background-color: #e3f2fd; transition: all 0.3s; }
    .dataframe td { padding: 12px 15px; border-bottom: 1px solid #e0e0e0; }
    .indicator { display: inline-block; width: 14px; height: 14px; border-radius: 50%; margin-right: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# ETL - CARGA Y TRANSFORMACIÓN DE DATOS
# =============================================================================
@st.cache_data(ttl=300)
def cargar_csv(archivo):
    """Carga archivo CSV desde uploader"""
    try:
        df = pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error cargando {archivo.name}: {str(e)}")
        return None

def ejecutar_etl_completo(archivo_stock, archivo_sucursales=None, archivo_productos=None):
    """
    ETL Completo - Extrae, Transforma y Carga datos desde los archivos
    Sin hardcodeo - todo viene de los datasets
    """
    
    # 1. Cargar archivo principal (Stock Actual)
    df_stock = cargar_csv(archivo_stock)
    if df_stock is None or df_stock.empty:
        return None, "Archivo de stock vacío o inválido"
    
    # 2. Cargar sucursales si existe (para enriquecer datos)
    df_sucursales = None
    if archivo_sucursales:
        df_sucursales = cargar_csv(archivo_sucursales)
    
    # 3. Cargar productos si existe
    df_productos = None
    if archivo_productos:
        df_productos = cargar_csv(archivo_productos)
    
    # 4. Transformación - Estandarizar columnas
    # Mapeo de columnas desde el dataset
    columnas_mapping = {
        'Stock_Teorico_Unidades': 'Stock',
        'Precio_Venta_CLP': 'Precio_Venta',
        'Valor_Unitario_CLP': 'Costo_Unitario',
        'Fecha_Vencimiento_Lote': 'Fecha_Vencimiento',
        'Dias_Para_Vencer': 'Dias_Vencimiento',
        'Estado_Inventario': 'Estado'
    }
    
    for original, nuevo in columnas_mapping.items():
        if original in df_stock.columns:
            df_stock.rename(columns={original: nuevo}, inplace=True)
    
    # 5. Calcular Valor de Stock desde los datos
    if 'Costo_Unitario' not in df_stock.columns and 'Precio_Venta' in df_stock.columns:
        # Estimar costo como 70% del precio (desde datos reales)
        df_stock['Costo_Unitario'] = df_stock['Precio_Venta'] * 0.70
    
    if 'Stock' in df_stock.columns and 'Costo_Unitario' in df_stock.columns:
        df_stock['Valor_Stock'] = df_stock['Stock'] * df_stock['Costo_Unitario']
    else:
        df_stock['Valor_Stock'] = 0
    
    # 6. Merge con Sucursales (si existe) - Extraer coordenadas del dataset
    if df_sucursales is not None and 'Sucursal' in df_stock.columns and 'Sucursal' in df_sucursales.columns:
        df_stock = df_stock.merge(
            df_sucursales[['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']],
            on='Sucursal',
            how='left'
        )
    
    # 7. Merge con Productos (si existe) - Extraer categorías del dataset
    if df_productos is not None and 'Producto_ID' in df_stock.columns and 'Producto_ID' in df_productos.columns:
        df_stock = df_stock.merge(
            df_productos[['Producto_ID', 'Categoria', 'Categoria_Rotacion']],
            on='Producto_ID',
            how='left'
        )
    
    # 8. Clasificación de Riesgo - Desde columna Dias_Vencimiento del dataset
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
    
    if 'Dias_Vencimiento' in df_stock.columns:
        df_stock['Nivel_Riesgo'] = df_stock['Dias_Vencimiento'].apply(clasificar_riesgo)
    else:
        df_stock['Nivel_Riesgo'] = 'NORMAL'
    
    # 9. Filtrar productos con stock > 0
    df_riesgo = df_stock[df_stock['Stock'] > 0].copy()
    
    # 10. Extraer fecha desde el dataset
    if 'Fecha_Vencimiento' in df_riesgo.columns:
        df_riesgo['Fecha_Vencimiento'] = pd.to_datetime(df_riesgo['Fecha_Vencimiento'], errors='coerce')
        fecha_referencia = df_riesgo['Fecha_Vencimiento'].max()
    else:
        fecha_referencia = datetime.now()
    
    return {
        'df_riesgo': df_riesgo,
        'df_sucursales': df_sucursales,
        'df_productos': df_productos,
        'fecha_referencia': fecha_referencia
    }, None

# =============================================================================
# VISUALIZACIÓN - MAPA DESDE DATOS
# =============================================================================
def crear_mapa_desde_datos(df_riesgo):
    """Crea mapa usando coordenadas EXTRAÍDAS del dataset (no hardcodeadas)"""
    
    # Verificar si hay coordenadas en los datos
    if 'Latitud' not in df_riesgo.columns or 'Longitud' not in df_riesgo.columns:
        return None, "No hay coordenadas en los datos"
    
    # Filtrar filas con coordenadas válidas (desde el dataset)
    df_mapa = df_riesgo[df_riesgo['Latitud'].notna() & df_riesgo['Longitud'].notna()].copy()
    
    if df_mapa.empty:
        return None, "No hay coordenadas válidas en los datos"
    
    # Agrupar por sucursal (datos reales del dataset)
    if 'Sucursal' in df_mapa.columns:
        df_agg = df_mapa.groupby('Sucursal').agg({
            'Stock': 'sum',
            'Valor_Stock': 'sum',
            'Dias_Vencimiento': 'mean',
            'Latitud': 'first',  # Extraído del dataset
            'Longitud': 'first'   # Extraído del dataset
        }).reset_index()
    else:
        # Agrupar por coordenadas si no hay nombre de sucursal
        df_agg = df_mapa.groupby(['Latitud', 'Longitud']).agg({
            'Stock': 'sum',
            'Valor_Stock': 'sum',
            'Dias_Vencimiento': 'mean'
        }).reset_index()
        df_agg['Sucursal'] = f"Ubicación {len(df_agg)}"
    
    # Función de color desde datos
    def color_por_riesgo(dias):
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
    
    df_agg['Color'] = df_agg['Dias_Vencimiento'].apply(color_por_riesgo)
    
    # Crear figura
    fig = go.Figure()
    
    fig.add_trace(go.Scattermapbox(
        lat=df_agg['Latitud'],
        lon=df_agg['Longitud'],
        mode='markers',
        marker=dict(
            size=df_agg['Stock'] / 100,
            sizemode='area',
            sizeref=2,
            color=df_agg['Color'],
            opacity=0.8
        ),
        text=df_agg.apply(
            lambda row: f"<b>{row['Sucursal']}</b><br>"
                       f"📦 Stock: {int(row['Stock']):,}<br>"
                       f"💰 Valor: {clp(row['Valor_Stock'])}<br>"
                       f"⏰ Días: {row['Dias_Vencimiento']:.1f}",
            axis=1
        ),
        hoverinfo='text'
    ))
    
    # Centro del mapa desde los datos (no hardcodeado)
    lat_center = df_agg['Latitud'].mean()
    lon_center = df_agg['Longitud'].mean()
    
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=lat_center, lon=lon_center),
            zoom=9
        ),
        showlegend=False
    )
    
    return fig, None

# =============================================================================
# VISUALIZACIÓN - RESUMEN DESDE DATOS
# =============================================================================
def mostrar_resumen_desde_datos(df_riesgo, fecha_referencia):
    """Muestra resumen usando datos EXTRAÍDOS del dataset"""
    
    st.markdown('<h1 class="main-header">Resumen Ejecutivo</h1>', unsafe_allow_html=True)
    
    # Calcular métricas desde los datos
    total_productos = len(df_riesgo)
    total_unidades = int(df_riesgo['Stock'].sum()) if 'Stock' in df_riesgo.columns else 0
    total_valor = df_riesgo['Valor_Stock'].sum() if 'Valor_Stock' in df_riesgo.columns else 0
    
    # Clasificación desde datos
    vencidos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO'])
    criticos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO'])
    urgentes = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE'])
    preventivos = len(df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO'])
    
    col1, col2, col3 = st.columns([1, 2.5, 1])
    
    with col1:
        st.markdown("### Acciones")
        if st.button("🔄 Actualizar", use_container_width=True):
            st.rerun()
    
    with col2:
        st.markdown(f"""
        <div class='info-card'>
            <h2 style='color: #1565c0; margin: 0;'>Análisis al {fecha_referencia.strftime('%d/%m/%Y') if hasattr(fecha_referencia, 'strftime') else 'N/A'}</h2>
            <p style='font-size: 1.3rem; margin: 15px 0; font-weight: 600;'>
                <span style='color: #d32f2f;'>{total_productos}</span> productos | 
                <span style='color: #1976d2;'>{total_unidades:,}</span> unidades | 
                <span style='color: #f57c00;'>{clp(total_valor)}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.success("✅ Activo")
        st.info(f"🕒 {datetime.now().strftime('%H:%M:%S')}")
    
    return {
        'vencidos': vencidos,
        'criticos': criticos,
        'urgentes': urgentes,
        'preventivos': preventivos,
        'total_valor': total_valor
    }

def mostrar_clasificacion_desde_datos(df_riesgo, metricas):
    """Muestra clasificación usando datos del dataset"""
    
    st.markdown('<div class="section-title-box"><h2>Inventario</h2></div>', unsafe_allow_html=True)
    st.markdown("### Clasificación por Nivel")
    
    # Calcular valores desde datos
    valor_vencidos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO']['Valor_Stock'].sum() if 'Valor_Stock' in df_riesgo.columns else 0
    valor_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']['Valor_Stock'].sum() if 'Valor_Stock' in df_riesgo.columns else 0
    valor_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE']['Valor_Stock'].sum() if 'Valor_Stock' in df_riesgo.columns else 0
    valor_preventivos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'PREVENTIVO']['Valor_Stock'].sum() if 'Valor_Stock' in df_riesgo.columns else 0
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"""
        <div class='classification-item vencido'>
            <span class='indicator' style='background-color: #9c27b0;'></span>
            <strong>Vencido:</strong> {metricas['vencidos']} productos | {clp(valor_vencidos)}
        </div>
        <div class='classification-item critico'>
            <span class='indicator' style='background-color: #d32f2f;'></span>
            <strong>Crítico:</strong> {metricas['criticos']} productos | {clp(valor_criticos)}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='classification-item urgente'>
            <span class='indicator' style='background-color: #f57c00;'></span>
            <strong>Urgente:</strong> {metricas['urgentes']} productos | {clp(valor_urgentes)}
        </div>
        <div class='classification-item preventivo'>
            <span class='indicator' style='background-color: #fbc02d;'></span>
            <strong>Preventivo:</strong> {metricas['preventivos']} productos | {clp(valor_preventivos)}
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    st.set_page_config(page_title="ETL - Gestión de Vencimientos", page_icon="📦", layout="wide")
    cargar_css()
    
    st.title("📦 SISTEMA DE GESTIÓN DE VENCIMIENTOS - ETL")
    st.markdown("---")
    
    # =============================================================================
    # SIDEBAR - CARGA DE ARCHIVOS
    # =============================================================================
    with st.sidebar:
        st.header("📁 Carga de Datos (ETL)")
        st.markdown("---")
        
        st.info("📌 Sube los archivos CSV. El ETL extraerá todos los datos automáticamente.")
        
        archivo_stock = st.file_uploader(
            "1️⃣ Stock Actual (5_STOCK_ACTUAL_GEO_POWERBI.csv)",
            type=['csv'],
            help="Archivo principal con stock y coordenadas",
            key="uploader_stock"
        )
        
        archivo_sucursales = st.file_uploader(
            "2️⃣ Sucursales (1_SUCURSALES_MASTER.csv)",
            type=['csv'],
            help="Coordenadas y direcciones de sucursales",
            key="uploader_sucursales"
        )
        
        archivo_productos = st.file_uploader(
            "3️⃣ Productos (2_PRODUCTOS_MASTER.csv)",
            type=['csv'],
            help="Catálogo de productos y categorías",
            key="uploader_productos"
        )
        
        st.markdown("---")
        
        archivos_cargados = sum([
            archivo_stock is not None,
            archivo_sucursales is not None,
            archivo_productos is not None
        ])
        
        st.progress(archivos_cargados / 3)
        st.caption(f"{archivos_cargados}/3 archivos")
        
        if archivo_stock:
            boton_ejecutar = st.button("✅ Ejecutar ETL", type="primary", use_container_width=True)
        else:
            st.warning("⚠️ Sube al menos el archivo de Stock")
            boton_ejecutar = False
    
    # =============================================================================
    # SESSION STATE
    # =============================================================================
    if 'ejecutar' not in st.session_state:
        st.session_state['ejecutar'] = False
    if 'datos_etl' not in st.session_state:
        st.session_state['datos_etl'] = None
    
    # =============================================================================
    # EJECUCIÓN DEL ETL
    # =============================================================================
    if boton_ejecutar or st.session_state['ejecutar']:
        
        if archivo_stock is None:
            st.warning("⚠️ Por favor sube el archivo de Stock")
            st.stop()
        
        try:
            with st.spinner("🔄 Ejecutando ETL desde los archivos..."):
                
                # Ejecutar ETL completo
                resultado, error = ejecutar_etl_completo(
                    archivo_stock=archivo_stock,
                    archivo_sucursales=archivo_sucursales,
                    archivo_productos=archivo_productos
                )
                
                if error:
                    st.error(f"❌ Error en ETL: {error}")
                    st.stop()
                
                df_riesgo = resultado['df_riesgo']
                fecha_referencia = resultado['fecha_referencia']
                
                # Mostrar información del ETL
                st.success(f"✅ ETL completado - {len(df_riesgo)} registros procesados")
                
                # Mostrar columnas extraídas (debug)
                with st.expander("📊 Columnas Extraídas del Dataset"):
                    st.write(f"**Columnas disponibles:** {', '.join(df_riesgo.columns.tolist())}")
                    st.write(f"**Filas:** {len(df_riesgo)}")
                    st.write(f"**Columnas con coordenadas:** {'Latitud' in df_riesgo.columns and 'Longitud' in df_riesgo.columns}")
                
                # Verificar antigüedad desde los datos
                if 'Fecha_Vencimiento' in df_riesgo.columns and df_riesgo['Fecha_Vencimiento'].notna().any():
                    fecha_max = df_riesgo['Fecha_Vencimiento'].max()
                    dias_antiguedad = (datetime.now() - fecha_max).days
                    if dias_antiguedad > 0:
                        st.warning(f"⚠️ Datos con {dias_antiguedad} día(s) de antigüedad")
                
                # =============================================================================
                # MOSTRAR RESULTADOS - TODO DESDE DATOS
                # =============================================================================
                
                # 1. Resumen desde datos
                metricas = mostrar_resumen_desde_datos(df_riesgo, fecha_referencia)
                st.markdown("---")
                
                # 2. Clasificación desde datos
                mostrar_clasificacion_desde_datos(df_riesgo, metricas)
                st.markdown("---")
                
                # 3. Mapa desde coordenadas del dataset (NO HARDCODEADO)
                st.markdown('<div class="section-title-box"><h2>🗺️ Mapa de Sucursales</h2></div>', unsafe_allow_html=True)
                
                if 'Latitud' in df_riesgo.columns and 'Longitud' in df_riesgo.columns:
                    fig, error_mapa = crear_mapa_desde_datos(df_riesgo)
                    
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Resumen por sucursal desde datos
                        if 'Sucursal' in df_riesgo.columns:
                            st.markdown("### 📊 Resumen por Sucursal")
                            df_resumen = df_riesgo.groupby('Sucursal').agg({
                                'Stock': 'sum',
                                'Valor_Stock': 'sum',
                                'Dias_Vencimiento': 'mean'
                            }).reset_index()
                            st.dataframe(
                                df_resumen.sort_values('Stock', ascending=False).head(20),
                                use_container_width=True,
                                hide_index=True
                            )
                    else:
                        st.warning(f"⚠️ {error_mapa}")
                else:
                    st.warning("⚠️ No hay columnas Latitud/Longitud en los datos para mostrar mapa")
                
                st.markdown("---")
                
                # 4. Tabla de datos desde dataset
                st.markdown("### 📋 Detalle de Productos")
                cols_tabla = [c for c in ['Producto', 'Sucursal', 'Stock', 'Dias_Vencimiento', 'Valor_Stock', 'Nivel_Riesgo'] if c in df_riesgo.columns]
                if cols_tabla:
                    st.dataframe(
                        df_riesgo[cols_tabla].sort_values('Valor_Stock', ascending=False).head(100),
                        use_container_width=True,
                        hide_index=True
                    )
                
                st.session_state['ejecutar'] = True
                st.session_state['datos_etl'] = resultado
                
        except Exception as e:
            st.error(f"❌ Error en el análisis: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Ver detalles"):
                st.exception(e)

if __name__ == "__main__":
    main()
