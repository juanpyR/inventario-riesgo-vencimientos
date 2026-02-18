import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
import calendar
import textwrap
import warnings
import pytz
import io
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import tempfile
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
    'VE NCIDO': '#9c27b0',      # Violeta
    'CRITICO': '#d32f2f',       # Rojo
    'URGENTE': '#f57c00',       # Naranja
    'PREVENTIVO': '#fbc02d'     # Amarillo
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
    'Días_para_Vencimiento': ['Días_para_Vencimiento', 'Días para Vencimiento', 'Días_para_Vencer', 'Días Vencimiento', 'Dias_Para_Vencer'],
    'Stock_Inicial': ['Stock_Inicial', 'Stock Sala', 'Stock_Sala', 'stock_sala', 'Stock', 'Stock_Teorico_Unidades'],
    'Costo_Unitario_Neto': ['Costo_Unitario_Neto', 'Costo Unitario Neto', 'costo_unitario_neto', 'Costo', 'Valor_Unitario_CLP'],
    'Precio_Venta_Bruto': ['Precio_Venta_Bruto', 'Precio Venta Bruto', 'precio_venta_bruto', 'Precio', 'Precio_Venta_CLP'],
    'Producto': ['Producto', 'producto', 'SKU_Descripcion'],
    'Sucursal': ['Sucursal', 'sucursal', 'Tienda', 'Store'],
    'Latitud': ['Latitud', 'lat', 'Latitude'],
    'Longitud': ['Longitud', 'lon', 'Longitude']
}

COLUMNAS_REQUERIDAS = ['Días_para_Vencimiento', 'Stock_Inicial', 'Producto']

# =============================================================================
# FUNCIONES DE CARGA Y PREPARACIÓN
# =============================================================================
def cargar_datos(archivo):
    """Carga y prepara datos desde archivo CSV con manejo robusto de columnas"""
    try:
        df = pd.read_csv(archivo)
        df.columns = df.columns.str.strip()
        
        # Mapeo de columnas alternativas
        for col_destino, col_posibles in COLUMNAS_ESPERADAS.items():
            for col_posible in col_posibles:
                if col_posible in df.columns and col_destino not in df.columns:
                    df.rename(columns={col_posible: col_destino}, inplace=True)
                    break
        
        # Parseo de fechas
        if 'Fecha' in df.columns or 'Fecha_Movimiento' in df.columns:
            fecha_col = 'Fecha' if 'Fecha' in df.columns else 'Fecha_Movimiento'
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    df[fecha_col] = pd.to_datetime(df[fecha_col], format=fmt, errors='coerce')
                    if df[fecha_col].notna().sum() > 0:
                        break
                except:
                    continue
            if df[fecha_col].isna().all():
                df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce', dayfirst=True)
            if fecha_col != 'Fecha' and 'Fecha' not in df.columns:
                df.rename(columns={fecha_col: 'Fecha'}, inplace=True)
        
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return None

def obtener_fecha_hoy(df):
    """Obtiene la fecha más reciente del dataframe"""
    if 'Fecha' in df.columns and df['Fecha'].notna().any():
        return df['Fecha'].max()
    return datetime.now()

def verificar_columnas(df, columnas_requeridas):
    """Verifica existencia de columnas requeridas"""
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {faltantes}")
    return True

# =============================================================================
# FUNCIONES DE CLASIFICACIÓN Y CÁLCULO
# =============================================================================
def clasificar_riesgo(dias):
    """Clasifica nivel de riesgo según días para vencimiento"""
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

def aplicar_clasificacion(df, columna_dias='Días_para_Vencimiento'):
    """Aplica clasificación de riesgo al dataframe con validación"""
    if columna_dias not in df.columns:
        st.warning(f"⚠️ Columna '{columna_dias}' no encontrada. Clasificación omitida.")
        df['Nivel_Riesgo'] = 'SIN_CLASIFICAR'
        return df
    
    df['Nivel_Riesgo'] = df[columna_dias].apply(clasificar_riesgo)
    return df

def calcular_valor_stock(df, stock_col='Stock_Inicial', costo_col='Costo_Unitario_Neto'):
    """Calcula valor del stock con fallback a precio de venta"""
    if stock_col not in df.columns:
        st.warning("⚠️ Columna de stock no encontrada")
        df['Valor_Stock_Costo'] = 0
        return df
    
    if costo_col in df.columns:
        df['Valor_Stock_Costo'] = df[stock_col] * df[costo_col]
    elif 'Precio_Venta_Bruto' in df.columns:
        # Estimación: costo ≈ 70% del precio de venta
        df['Costo_Unitario_Neto'] = df['Precio_Venta_Bruto'] * 0.70
        df['Valor_Stock_Costo'] = df[stock_col] * df['Costo_Unitario_Neto']
    else:
        df['Valor_Stock_Costo'] = df[stock_col]  # Fallback: usar unidades como proxy
        st.warning("⚠️ Sin columnas de costo/precio. Usando stock como valor proxy.")
    
    return df

def filtrar_productos_riesgo(df, dias_min=0, dias_max=10, stock_min=1):
    """Filtra productos en rango de riesgo con validaciones"""
    if 'Días_para_Vencimiento' not in df.columns:
        return df[df['Stock_Inicial'] > 0].copy() if 'Stock_Inicial' in df.columns else df.copy()
    
    return df[
        (df['Días_para_Vencimiento'] <= dias_max) &
        (df['Días_para_Vencimiento'] >= dias_min) &
        (df['Stock_Inicial'] >= stock_min)
    ].copy()

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN - RESUMEN
# =============================================================================
def mostrar_resumen_ejecutivo_nuevo(df_riesgo, total_riesgo, fecha_hoy):
    """Muestra resumen ejecutivo con validación de datos"""
    st.markdown('<h1 class="main-header">Resúmen</h1>', unsafe_allow_html=True)
    
    # Validar datos mínimos
    if df_riesgo is None or df_riesgo.empty:
        st.warning("⚠️ No hay datos para mostrar en el resumen")
        return
    
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
        chile_tz = pytz.timezone('America/Santiago')
        hora_chile = datetime.now(chile_tz)
        st.info(f"🕒 {hora_chile.strftime('%H:%M:%S')}")

def mostrar_inventario_nuevo(df_riesgo, total_riesgo, fecha_hoy, df_con_meses=None):
    """Muestra clasificación del inventario con validación de columna Nivel_Riesgo"""
    st.markdown('<div class="section-title-box"><h2>Inventario</h2></div>', unsafe_allow_html=True)
    st.markdown("### Clasificación")
    
    # ✅ VALIDACIÓN CRÍTICA: Asegurar que Nivel_Riesgo existe
    if 'Nivel_Riesgo' not in df_riesgo.columns:
        st.warning("⚠️ Columna 'Nivel_Riesgo' no encontrada. Aplicando clasificación automática...")
        df_riesgo = aplicar_clasificacion(df_riesgo)
    
    # Filtrar por mes actual si hay datos agrupados
    if df_con_meses is not None and 'Mes_Vencimiento' in df_con_meses.columns:
        mes_actual_periodo = pd.Period(fecha_hoy, freq='M') if hasattr(fecha_hoy, 'strftime') else None
        if mes_actual_periodo:
            df_mes = df_con_meses[df_con_meses['Mes_Vencimiento'] == mes_actual_periodo].copy()
            df_mes_riesgo = df_mes[df_mes['Días_para_Vencimiento'] >= 0].copy()
            if not df_mes_riesgo.empty and 'Nivel_Riesgo' in df_mes_riesgo.columns:
                df_riesgo_consistente = df_mes_riesgo
            else:
                df_riesgo_consistente = df_riesgo
        else:
            df_riesgo_consistente = df_riesgo
    else:
        df_riesgo_consistente = df_riesgo
    
    # Calcular métricas por nivel con validación
    niveles = ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']
    metricas = {}
    
    for nivel in niveles:
        mask = df_riesgo_consistente['Nivel_Riesgo'] == nivel  # ✅ Ahora seguro que existe
        df_nivel = df_riesgo_consistente[mask]
        metricas[nivel] = {
            'count': len(df_nivel),
            'valor': df_nivel['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_nivel.columns else 0
        }
    
    # Guardar en session state
    st.session_state['metricas_inventario'] = metricas
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        html_items = []
        for nivel in niveles:
            color = COLOR_MAP.get(nivel, '#999')
            bg_class = nivel.lower()
            html_items.append(f"""
                <div class='classification-item {bg_class}'>
                    <span class='indicator' style='background-color: {color};'></span>
                    <strong>{nivel.capitalize()}:</strong> {metricas[nivel]['count']} productos | {clp(metricas[nivel]['valor'])} CLP
                </div>
            """)
        st.markdown("".join(html_items), unsafe_allow_html=True)
    
    with col2:
        # Generar plan de acción dinámico
        acciones = []
        total_credito = 0
        total_recuperacion = 0
        
        if metricas['VENCIDO']['count'] > 0:
            credito = metricas['VENCIDO']['valor'] * 0.27
            total_credito += credito
            acciones.append(f"• <strong>{metricas['VENCIDO']['count']} vencidos</strong>: Donación → Crédito {clp(credito)} CLP (27%)")
        
        if metricas['CRITICO']['count'] > 0:
            recuperacion = metricas['CRITICO']['valor'] * 0.50
            total_recuperacion += recuperacion
            acciones.append(f"• <strong>{metricas['CRITICO']['count']} críticos</strong>: Descuento 40% → {clp(recuperacion)} CLP")
        
        if metricas['URGENTE']['count'] > 0:
            recuperacion = metricas['URGENTE']['valor'] * 0.40
            total_recuperacion += recuperacion
            acciones.append(f"• <strong>{metricas['URGENTE']['count']} urgentes</strong>: Descuento 25% → {clp(recuperacion)} CLP")
        
        total_recuperado = total_credito + total_recuperacion
        
        st.session_state['metricas_plan'] = {
            'credito_tributario': total_credito,
            'recuperacion_descuentos': total_recuperacion,
            'total_recuperado': total_recuperado
        }
        
        plan_texto = "<br>".join(acciones) if acciones else "No se requieren acciones inmediatas"
        
        st.markdown(f"""
        <div class='decision-box'>
            <h3>Decisión Requerida</h3>
            <p style='font-size: 1.1rem; color: #424242; margin: 20px 0;'>
                Se requieren <strong>acciones inmediatas</strong> para {metricas['VENCIDO']['count']} productos vencidos 
                y {metricas['CRITICO']['count']} productos críticos.<br><br>
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
                        <span class='metric-label'>📈 Recuperación por Descuentos:</span>
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

# =============================================================================
# FUNCIONES DE VISUALIZACIÓN - GRÁFICOS
# =============================================================================
def mostrar_visualizacion_nueva(df_riesgo):
    """Muestra visualización con validación de datos"""
    st.markdown('<div class="section-title-box"><h2>Visualización de datos</h2></div>', unsafe_allow_html=True)
    
    if df_riesgo is None or df_riesgo.empty or 'Nivel_Riesgo' not in df_riesgo.columns:
        st.warning("⚠️ No hay datos válidos para visualizar")
        return
    
    # Calcular distribuciones
    distribucion_nivel = df_riesgo['Nivel_Riesgo'].value_counts()
    
    valores_por_nivel = {}
    for nivel in COLOR_MAP.keys():
        mask = df_riesgo['Nivel_Riesgo'] == nivel
        valores_por_nivel[nivel] = df_riesgo[mask]['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
    
    # Crear gráfico
    fig = make_subplots(rows=1, cols=2, specs=[[{'type':'domain'}, {'type':'domain'}]])
    
    colors = [COLOR_MAP.get(n, '#999') for n in distribucion_nivel.index]
    
    fig.add_trace(go.Pie(
        labels=distribucion_nivel.index,
        values=distribucion_nivel.values,
        marker_colors=colors,
        hole=0.4,
        name='Por Cantidad'
    ), row=1, col=1)
    
    fig.add_trace(go.Pie(
        labels=[n for n in COLOR_MAP.keys() if valores_por_nivel.get(n, 0) > 0],
        values=[v for v in valores_por_nivel.values() if v > 0],
        marker_colors=[COLOR_MAP[n] for n in COLOR_MAP.keys() if valores_por_nivel.get(n, 0) > 0],
        hole=0.4,
        name='Por Valor'
    ), row=1, col=2)
    
    fig.update_layout(
        height=400,
        title_text="📊 Distribución de Inventario en Riesgo",
        showlegend=True,
        margin=dict(t=50, b=20, l=20, r=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal con manejo robusto de errores"""
    st.set_page_config(page_title="Sistema de Gestión de Vencimientos", layout="wide")
    cargar_css()
    
    # Inicializar session state
    for key in ['plan_aceptado', 'metricas_inventario', 'metricas_plan', 'ver_detalle', 'ejecutar', 'datos_procesados']:
        if key not in st.session_state:
            st.session_state[key] = False if key in ['plan_aceptado', 'ver_detalle', 'ejecutar'] else {}
    
    st.title("📦 SISTEMA DE GESTIÓN DE VENCIMIENTOS")
    st.markdown("---")
    
    with st.sidebar:
        st.header("Configuración")
        archivo_subido = st.file_uploader("Subir archivo CSV", type=['csv'], help="Seleccione el archivo con el inventario")
        boton_ejecutar = st.button("Ejecutar Análisis", type="primary")
    
    if boton_ejecutar or st.session_state['ejecutar']:
        if archivo_subido is None:
            st.warning("⚠️ Por favor suba un archivo CSV para continuar")
            st.stop()
        
        try:
            with st.spinner("🔄 Cargando y procesando datos..."):
                # Cargar datos
                df = cargar_datos(archivo_subido)
                if df is None or df.empty:
                    st.error("❌ No se pudieron cargar los datos")
                    st.stop()
                
                # Fecha de referencia
                fecha_hoy = obtener_fecha_hoy(df)
                
                # Filtrar por fecha más reciente
                if 'Fecha' in df.columns:
                    df_hoy = df[df['Fecha'] == fecha_hoy].copy().reset_index(drop=True)
                else:
                    df_hoy = df.copy()
                
                # Verificar columnas mínimas
                if not verificar_columnas(df_hoy, ['Stock_Inicial', 'Producto']):
                    st.stop()
                
                # Calcular valor de stock
                df_hoy = calcular_valor_stock(df_hoy)
                
                # Aplicar clasificación de riesgo (CRÍTICO: antes de cualquier filtrado)
                df_hoy = aplicar_clasificacion(df_hoy)
                
                # Filtrar productos en riesgo
                df_riesgo = filtrar_productos_riesgo(df_hoy)
                
                if df_riesgo.empty:
                    st.warning("ℹ️ No hay productos en riesgo (0-10 días) en el snapshot actual")
                    st.stop()
                
                # Calcular total en riesgo
                total_riesgo = df_riesgo['Valor_Stock_Costo'].sum() if 'Valor_Stock_Costo' in df_riesgo.columns else 0
                
                # Agrupar por mes para análisis temporal
                resumen_por_mes = None
                df_con_meses = None
                if 'Fecha_Vencimiento_Real' not in df_hoy.columns and 'Días_para_Vencimiento' in df_hoy.columns and 'Fecha' in df_hoy.columns:
                    df_temp = df_hoy.copy()
                    df_temp['Fecha_Vencimiento_Real'] = df_temp.apply(
                        lambda row: row['Fecha'] + timedelta(days=int(row['Días_para_Vencimiento']))
                        if pd.notna(row['Días_para_Vencimiento']) else pd.NaT, axis=1)
                    df_temp = df_temp[df_temp['Fecha_Vencimiento_Real'].notna()].copy()
                    df_temp['Mes_Vencimiento'] = df_temp['Fecha_Vencimiento_Real'].dt.to_period('M')
                    df_con_meses = df_temp
                
                st.success(f"✅ Datos procesados: {len(df_riesgo)} productos en riesgo")
                st.info(f"📅 Análisis para: {fecha_hoy.strftime('%d/%m/%Y') if hasattr(fecha_hoy, 'strftime') else fecha_hoy}")
                
                # Verificar antigüedad de datos
                if hasattr(fecha_hoy, 'date'):
                    dias_sin_actualizar = (datetime.now().date() - fecha_hoy.date()).days
                    if dias_sin_actualizar > 0:
                        st.warning(f"⚠️ Datos con {dias_sin_actualizar} día(s) de antigüedad")
            
            # MOSTRAR RESULTADOS
            mostrar_resumen_ejecutivo_nuevo(df_riesgo, total_riesgo, fecha_hoy)
            st.markdown("---")
            mostrar_inventario_nuevo(df_riesgo, total_riesgo, fecha_hoy, df_con_meses)
            st.markdown("---")
            mostrar_visualizacion_nueva(df_riesgo)
            
            # Vista de detalle opcional
            if st.session_state.get('ver_detalle', False):
                st.markdown("### 📋 Detalle de Productos en Riesgo")
                
                # Validar columna antes de filtrar (SOLUCIÓN DEL ERROR)
                if 'Nivel_Riesgo' not in df_riesgo.columns:
                    df_riesgo = aplicar_clasificacion(df_riesgo)
                
                for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
                    # ✅ FILTRO SEGURO: columna validada arriba
                    mask = df_riesgo['Nivel_Riesgo'] == nivel
                    df_nivel = df_riesgo[mask].sort_values('Valor_Stock_Costo', ascending=False) if 'Valor_Stock_Costo' in df_riesgo.columns else df_riesgo[mask]
                    
                    if not df_nivel.empty:
                        with st.expander(f"{'🟣' if nivel=='VENCIDO' else '🔴' if nivel=='CRITICO' else '🟠' if nivel=='URGENTE' else '🟡'} {nivel} ({len(df_nivel)} productos)", expanded=False):
                            cols_mostrar = [c for c in ['Producto', 'Sucursal', 'Stock_Inicial', 'Días_para_Vencimiento', 'Valor_Stock_Costo'] if c in df_nivel.columns]
                            if cols_mostrar:
                                st.dataframe(df_nivel[cols_mostrar].head(50), use_container_width=True, hide_index=True)
                
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
            
        except KeyError as e:
            st.error(f"❌ Columna no encontrada: {e}. Verifique que el archivo CSV tenga las columnas esperadas.")
            with st.expander("🔍 Columnas disponibles en el archivo"):
                if 'df_hoy' in locals():
                    st.write(df_hoy.columns.tolist())
        except FileNotFoundError:
            st.error("❌ Archivo no encontrado")
        except pd.errors.EmptyDataError:
            st.error("❌ El archivo CSV está vacío")
        except Exception as e:
            st.error(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
            with st.expander("🔍 Detalles técnicos"):
                st.exception(e)

if __name__ == "__main__":
    main()
