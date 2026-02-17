import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
import calendar
import streamlit as st

# =============================================================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# =============================================================================
st.set_page_config(page_title="Reporte de Vencimientos", layout="wide")

# =============================================================================
# DICCIONARIOS Y CONSTANTES
# =============================================================================
MESES_ESP = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

COLUMNAS_ESPERADAS = {
    'Días_para_Vencimiento': ['Días_para_Vencimiento', 'Días para Vencimiento', 'Días_para_Vencer', 'Días Vencimiento'],
    'Stock_Inicial': ['Stock_Inicial', 'Stock Sala', 'Stock_Sala', 'stock_sala', 'Stock'],
    'Costo_Unitario_Neto': ['Costo_Unitario_Neto', 'Costo Unitario Neto', 'costo_unitario_neto', 'Costo'],
    'Precio_Venta_Bruto': ['Precio_Venta_Bruto', 'Precio Venta Bruto', 'precio_venta_bruto', 'Precio'],
    'Producto': ['Producto', 'producto', 'SKU_Descripcion'],
    'Categoría': ['Categoría', 'Categoria', 'categoria', 'Category']
}

COLUMNAS_REQUERIDAS = ['Días_para_Vencimiento', 'Stock_Inicial', 'Costo_Unitario_Neto', 'Precio_Venta_Bruto', 'Producto']

COLOR_MAP = {
    'VENCIDO': '#000000',
    'CRITICO': '#d32f2f',
    'URGENTE': '#f57c00',
    'PREVENTIVO': '#fbc02d'
}

# =============================================================================
# FUNCIONES DE CARGA Y PREPARACIÓN DE DATOS
# =============================================================================

def cargar_datos(ruta_csv):
    """Carga y prepara el dataset desde CSV"""
    df = pd.read_csv(ruta_csv)
    df.columns = df.columns.str.strip()
    
    # Convertir columna Fecha a datetime
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
        try:
            df['Fecha'] = pd.to_datetime(df['Fecha'], format=fmt, errors='coerce')
            if df['Fecha'].notna().sum() > 0:
                break
        except:
            continue
    
    if df['Fecha'].isna().all():
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce', dayfirst=True)
    
    return df


def obtener_fecha_hoy(df):
    """Obtiene la fecha más reciente del dataset"""
    return df['Fecha'].max()


def filtrar_por_fecha(df, fecha_hoy):
    """Filtra el dataframe para solo la fecha de hoy"""
    return df[df['Fecha'] == fecha_hoy].copy().reset_index(drop=True)


def mapear_columnas(df):
    """Mapea las columnas del dataset a los nombres estándar"""
    for col_destino, col_posibles in COLUMNAS_ESPERADAS.items():
        for col_posible in col_posibles:
            if col_posible in df.columns:
                df.rename(columns={col_posible: col_destino}, inplace=True)
                break
    return df


def verificar_columnas(df):
    """Verifica que existan las columnas requeridas"""
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")


# =============================================================================
# FUNCIONES DE FILTRADO Y CLASIFICACIÓN
# =============================================================================

def filtrar_productos_riesgo(df_hoy, dias_min=0, dias_max=10):
    """Filtra productos en riesgo de vencimiento"""
    return df_hoy[
        (df_hoy['Días_para_Vencimiento'] <= dias_max) &
        (df_hoy['Días_para_Vencimiento'] >= dias_min) &
        (df_hoy['Stock_Inicial'] > 0)
    ].copy()


def calcular_valor_stock(df):
    """Calcula el valor del stock a costo"""
    df['Valor_Stock_Costo'] = df['Stock_Inicial'] * df['Costo_Unitario_Neto']
    return df


def clasificar_riesgo(dias):
    """Clasifica el nivel de riesgo según días para vencimiento"""
    if dias == 0:
        return 'VENCIDO'
    elif dias <= 3:
        return 'CRITICO'
    elif dias <= 7:
        return 'URGENTE'
    else:
        return 'PREVENTIVO'


def aplicar_clasificacion(df):
    """Aplica la clasificación de riesgo al dataframe"""
    df['Nivel_Riesgo'] = df['Días_para_Vencimiento'].apply(clasificar_riesgo)
    return df


# =============================================================================
# FUNCIONES DE CÁLCULO CONTABLE
# =============================================================================

def calcular_fechas_vencimiento(df, fecha_hoy):
    """Calcula la fecha real de vencimiento para cada producto"""
    df['Fecha_Vencimiento_Real'] = df.apply(
        lambda row: fecha_hoy + timedelta(days=int(row['Días_para_Vencimiento']))
        if pd.notna(row['Días_para_Vencimiento']) else pd.NaT,
        axis=1
    )
    return df


def agrupar_por_mes_vencimiento(df_base, fecha_referencia):
    """Agrupa productos por mes de vencimiento con lógica contable"""
    df_temp = df_base.copy()
    
    df_temp['Fecha_Vencimiento_Real'] = df_temp.apply(
        lambda row: row['Fecha'] + timedelta(days=int(row['Días_para_Vencimiento']))
        if pd.notna(row['Días_para_Vencimiento']) else pd.NaT,
        axis=1
    )
    
    df_temp = df_temp[
        (df_temp['Fecha_Vencimiento_Real'].notna()) &
        (df_temp['Stock_Inicial'] > 0) &
        (df_temp['Días_para_Vencimiento'].notna())
    ].copy()
    
    df_temp['Valor_Stock_Costo'] = df_temp['Stock_Inicial'] * df_temp['Costo_Unitario_Neto']
    df_temp['Mes_Vencimiento'] = df_temp['Fecha_Vencimiento_Real'].dt.to_period('M')
    
    df_temp['Valor_Perdido'] = df_temp.apply(
        lambda row: row['Valor_Stock_Costo'] if row['Días_para_Vencimiento'] < 0 else 0,
        axis=1
    )
    df_temp['Valor_Recuperable'] = df_temp.apply(
        lambda row: row['Valor_Stock_Costo'] if row['Días_para_Vencimiento'] >= 0 else 0,
        axis=1
    )
    
    resumen_mes = df_temp.groupby('Mes_Vencimiento').agg({
        'Producto': 'count',
        'Stock_Inicial': 'sum',
        'Valor_Stock_Costo': 'sum',
        'Valor_Perdido': 'sum',
        'Valor_Recuperable': 'sum'
    }).round(0)
    
    resumen_mes['% Perdido'] = (resumen_mes['Valor_Perdido'] / resumen_mes['Valor_Stock_Costo'] * 100).round(1)
    resumen_mes['% Recuperable'] = (resumen_mes['Valor_Recuperable'] / resumen_mes['Valor_Stock_Costo'] * 100).round(1)
    resumen_mes = resumen_mes.fillna(0)
    
    return resumen_mes, df_temp


def obtener_nombre_mes(mes_periodo):
    """Obtiene el nombre del mes en español"""
    return f"{MESES_ESP[mes_periodo.month]} {mes_periodo.year}"


def determinar_meses_a_mostrar(resumen_por_mes, fecha_hoy):
    """Determina qué meses mostrar según cruce de fechas"""
    mes_actual_periodo = pd.Period(fecha_hoy, freq='M')
    mes_siguiente_periodo = pd.Period(fecha_hoy + pd.offsets.MonthBegin(1), freq='M')
    
    fecha_max_riesgo = fecha_hoy + timedelta(days=10)
    mostrar_siguiente_mes = (fecha_max_riesgo.month != fecha_hoy.month) or \
                           (fecha_max_riesgo.year != fecha_hoy.year)
    
    meses_a_mostrar = [mes_actual_periodo]
    if mostrar_siguiente_mes and mes_siguiente_periodo in resumen_por_mes.index and \
       resumen_por_mes.loc[mes_siguiente_periodo, 'Valor_Stock_Costo'] > 0:
        meses_a_mostrar.append(mes_siguiente_periodo)
    
    return meses_a_mostrar


# =============================================================================
# FUNCIONES DE VISUALIZACIÓN - MATRIZ
# =============================================================================

def crear_matriz_riesgo(df_riesgo, total_riesgo, fecha_hoy):
    """Crea y muestra la matriz de riesgo visual"""
    df_viz = df_riesgo.copy()
    
    df_viz['Rango_Dias'] = pd.cut(df_viz['Días_para_Vencimiento'],
                                   bins=[-0.5, 0, 3, 7, 10],
                                   labels=['VENCIDO', '1-3 días', '4-7 días', '8-10 días'],
                                   include_lowest=True)
    
    sizes = np.clip(df_viz['Valor_Stock_Costo'] / df_viz['Valor_Stock_Costo'].max() * 600 + 40, 40, 600)
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
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
    ax.set_xticklabels(['VENCIDO\n(días = 0)', 'CRITICO\n(1-3 días)', 'URGENTE\n(4-7 días)', 'PREVENTIVO\n(8-10 días)'],
                       fontsize=13, fontweight='bold')
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(['VENCIDO', '1-3 días', '4-7 días', '8-10 días'], fontsize=12)
    
    ax.set_xlabel('Nivel de Riesgo', fontsize=14, fontweight='bold')
    ax.set_ylabel('Días para Vencimiento', fontsize=14, fontweight='bold')
    ax.set_title(f'Riesgo de Vencimiento - {fecha_hoy.date()}\n{len(df_viz)} productos en riesgo | {total_riesgo:,.0f} CLP en valor total',
                fontsize=16, pad=25)
    
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='VENCIDO (hoy)', markerfacecolor='#000000', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='CRITICO (1-3 días)', markerfacecolor='#d32f2f', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='URGENTE (4-7 días)', markerfacecolor='#f57c00', markersize=14),
        Line2D([0], [0], marker='o', color='w', label='PREVENTIVO (8-10 días)', markerfacecolor='#fbc02d', markersize=14),
        plt.scatter([], [], s=80, c='gray', alpha=0.6, label='~100k CLP'),
        plt.scatter([], [], s=300, c='gray', alpha=0.6, label='~500k CLP'),
        plt.scatter([], [], s=600, c='gray', alpha=0.6, label='~1M+ CLP')
    ]
    ax.legend(handles=legend_elements, loc='center left',
              title='Tamaño = Valor en riesgo', fontsize=12, title_fontsize=14,
              frameon=True, edgecolor='gray', facecolor='white', fancybox=True,
              borderpad=1.2, labelspacing=1.1)
    
    ax.set_xlim(-0.7, 3.7)
    ax.set_ylim(-0.7, 3.7)
    ax.grid(False)
    plt.tight_layout()
    
    return fig


# =============================================================================
# FUNCIONES DE VISUALIZACIÓN - TABLAS Y REPORTES
# =============================================================================

def formato_rango_fechas(fecha_inicio, fecha_fin):
    """Formatea rango de fechas considerando cruce de mes"""
    inicio_str = fecha_inicio.strftime('%d/%m')
    fin_str = fecha_fin.strftime('%d/%m')
    return f"{inicio_str} a {fin_str}"


def calcular_fechas_por_nivel(fecha_hoy):
    """Calcula las fechas de vencimiento por nivel de riesgo"""
    niveles_config = {
        'VENCIDO': (0, 0),
        'CRITICO': (1, 3),
        'URGENTE': (4, 7),
        'PREVENTIVO': (8, 10)
    }
    
    fechas = {}
    for nivel, (dias_inicio, dias_fin) in niveles_config.items():
        fecha_inicio = fecha_hoy + timedelta(days=dias_inicio)
        fecha_fin = fecha_hoy + timedelta(days=dias_fin)
        fechas[nivel] = formato_rango_fechas(fecha_inicio, fecha_fin)
    
    return fechas


def generar_resumen_por_nivel(df_riesgo, total_riesgo_mes):
    """Genera el resumen agrupado por nivel de riesgo"""
    resumen = df_riesgo.groupby('Nivel_Riesgo').agg({
        'Producto': 'count',
        'Stock_Inicial': 'sum',
        'Valor_Stock_Costo': 'sum'
    }).round(0)
    resumen.columns = ['Productos', 'Unidades', 'Valor Riesgo']
    resumen = resumen.reindex(['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO'], fill_value=0)
    resumen['% del Mes'] = (resumen['Valor Riesgo'] / total_riesgo_mes * 100).round(1) if total_riesgo_mes > 0 else 0
    return resumen


def mostrar_resumen_ejecutivo(fecha_hoy, df_riesgo, total_riesgo, total_riesgo_mes, resumen_por_mes, df_con_meses):
    """Muestra el resumen ejecutivo unificado"""
    st.header("RESUMEN EJECUTIVO")
    st.subheader(f"Riesgo al {fecha_hoy.strftime('%d/%m/%Y')}")
    
    meses_a_mostrar = determinar_meses_a_mostrar(resumen_por_mes, fecha_hoy)
    
    for mes_periodo in meses_a_mostrar:
        mes_nombre = obtener_nombre_mes(mes_periodo)
        
        if mes_periodo not in resumen_por_mes.index:
            continue
        
        fila = resumen_por_mes.loc[mes_periodo]
        es_mes_parcial = (mes_periodo.year == fecha_hoy.year and mes_periodo.month == fecha_hoy.month)
        
        if es_mes_parcial:
            primer_dia_mes_actual = pd.Timestamp(year=fecha_hoy.year, month=fecha_hoy.month, day=1)
            rango_fecha_mes = f"del {primer_dia_mes_actual.strftime('%d/%m')} al {fecha_hoy.strftime('%d/%m')}"
        else:
            rango_fecha_mes = f"{obtener_nombre_mes(mes_periodo)}"
        
        st.markdown(f"#### MES: {mes_nombre} ({rango_fecha_mes})")
        
        total_valor = fila['Valor_Stock_Costo']
        valor_perdido = fila['Valor_Perdido']
        valor_recuperable = fila['Valor_Recuperable']
        pct_perdido = fila['% Perdido']
        pct_recuperable = fila['% Recuperable']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Mercadería", f"{total_valor:,.0f} CLP")
        with col2:
            st.metric("Ya Perdida", f"{valor_perdido:,.0f} CLP", delta=f"-{pct_perdido:.1f}%")
        with col3:
            st.metric("Recuperable", f"{valor_recuperable:,.0f} CLP", delta=f"{pct_recuperable:.1f}%")
        
        if es_mes_parcial:
            st.info("Mes en curso. Los 'perdidos' incluyen vencimientos anteriores a hoy.")
        else:
            st.info("Mes completo. Los 'perdidos' representan mercadería no recuperada.")
        
        # Detalle por nivel de riesgo
        df_mes = df_con_meses[df_con_meses['Mes_Vencimiento'] == mes_periodo].copy()
        df_mes_riesgo = df_mes[df_mes['Días_para_Vencimiento'] >= 0].copy()
        
        if len(df_mes_riesgo) > 0:
            df_mes_riesgo['Nivel'] = df_mes_riesgo['Días_para_Vencimiento'].apply(clasificar_riesgo)
            
            st.markdown("##### Detalle de riesgo (mercadería recuperable)")
            
            tabla_detalle = []
            for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
                df_nivel = df_mes_riesgo[df_mes_riesgo['Nivel'] == nivel]
                if len(df_nivel) > 0:
                    valor_nivel = df_nivel['Valor_Stock_Costo'].sum()
                    pct_nivel = (valor_nivel / total_valor * 100) if total_valor > 0 else 0
                    tabla_detalle.append({
                        'Nivel': nivel,
                        'Productos': len(df_nivel),
                        'Unidades': int(df_nivel['Stock_Inicial'].sum()),
                        'Valor': f"{valor_nivel:,.0f}",
                        '% del Mes': f"{pct_nivel:.1f}%"
                    })
            
            if tabla_detalle:
                st.dataframe(pd.DataFrame(tabla_detalle), use_container_width=True, hide_index=True)
    
    # Alerta operativa
    st.markdown("### ALERTA OPERATIVA")
    col1, col2 = st.columns(2)
    with col1:
        st.error(f"Total en riesgo (10 días): {total_riesgo:,.0f} CLP")
        vencidos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'VENCIDO']
        st.warning(f"VENCIDOS hoy: {len(vencidos)} productos | {vencidos['Valor_Stock_Costo'].sum():,.0f} CLP")
    with col2:
        criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']
        st.info(f"CRITICOS (1-3 días): {len(criticos)} productos | {criticos['Valor_Stock_Costo'].sum():,.0f} CLP")


def mostrar_top_productos(df_riesgo, fecha_hoy):
    """Muestra el top 5 de productos por nivel de riesgo"""
    st.header("TOP 5 PRODUCTOS POR NIVEL")
    
    df_filtrado = df_riesgo[df_riesgo['Días_para_Vencimiento'] >= 0].copy()
    
    for nivel in ['VENCIDO', 'CRITICO', 'URGENTE', 'PREVENTIVO']:
        df_nivel = df_filtrado[df_filtrado['Nivel_Riesgo'] == nivel].nlargest(5, 'Valor_Stock_Costo')
        
        if len(df_nivel) == 0:
            continue
        
        st.subheader(f"{nivel} - Top 5 productos por valor en riesgo")
        
        tabla_datos = []
        for _, row in df_nivel.iterrows():
            dias = int(row['Días_para_Vencimiento'])
            unidades = int(row['Stock_Inicial'])
            valor = row['Valor_Stock_Costo']
            fecha_venc = fecha_hoy + timedelta(days=dias)
            
            if nivel == 'VENCIDO':
                accion = "DONAR HOY"
            elif nivel == 'CRITICO':
                accion = "40% dto"
            elif nivel == 'URGENTE':
                accion = "25% dto"
            else:
                accion = "15% dto"
            
            tabla_datos.append({
                'Producto': str(row['Producto'])[:33] if pd.notna(row['Producto']) else 'Sin nombre',
                'Días': dias,
                'Unidades': unidades,
                'Valor Riesgo': f"{valor:,.0f}",
                'Fecha Venc.': fecha_venc.strftime('%d/%m/%Y'),
                'Acción': accion
            })
        
        st.dataframe(pd.DataFrame(tabla_datos), use_container_width=True, hide_index=True)


def mostrar_plan_accion(df_riesgo, fecha_hoy):
    """Muestra el plan de acción 48H"""
    st.header("PLAN DE ACCION 48H")
    
    # Productos vencidos
    productos_vencidos = df_riesgo[
        (df_riesgo['Nivel_Riesgo'] == 'VENCIDO') &
        (df_riesgo['Días_para_Vencimiento'] >= 0)
    ].copy()
    
    valor_vencido = productos_vencidos['Valor_Stock_Costo'].sum() if len(productos_vencidos) > 0 else 0
    credito_trib = valor_vencido * 0.27
    
    st.subheader("HOY 08:00 - 10:00 | DONACIONES OBLIGATORIAS")
    if len(productos_vencidos) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Productos", len(productos_vencidos))
        with col2:
            st.metric("Unidades", f"{productos_vencidos['Stock_Inicial'].sum():.0f}")
        with col3:
            st.metric("Valor en Riesgo", f"{valor_vencido:,.0f} CLP")
        st.success(f"Crédito tributario 27%: +{credito_trib:,.0f} CLP")
    else:
        st.info("Sin productos vencidos hoy")
    
    # Productos críticos
    productos_criticos = df_riesgo[
        (df_riesgo['Nivel_Riesgo'] == 'CRITICO') &
        (df_riesgo['Días_para_Vencimiento'] >= 1) &
        (df_riesgo['Días_para_Vencimiento'] <= 3)
    ].copy()
    
    st.subheader("HOY 10:00 - 12:00 | ACCION CRITICA")
    if len(productos_criticos) > 0:
        valor_critico = productos_criticos['Valor_Stock_Costo'].sum()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Productos", len(productos_criticos))
        with col2:
            st.metric("Unidades", f"{productos_criticos['Stock_Inicial'].sum():.0f}")
        with col3:
            st.metric("Valor en Riesgo", f"{valor_critico:,.0f} CLP")
        st.info("Aplicar 40% descuento en entrada principal")
    else:
        st.info("Sin productos críticos")
    
    # Productos urgentes
    productos_urgentes = df_riesgo[
        (df_riesgo['Nivel_Riesgo'] == 'URGENTE') &
        (df_riesgo['Días_para_Vencimiento'] >= 4) &
        (df_riesgo['Días_para_Vencimiento'] <= 7)
    ].copy()
    
    st.subheader("HOY 14:00 - 16:00 | ACCION URGENTE")
    if len(productos_urgentes) > 0:
        valor_urgente = productos_urgentes['Valor_Stock_Costo'].sum()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Productos", len(productos_urgentes))
        with col2:
            st.metric("Unidades", f"{productos_urgentes['Stock_Inicial'].sum():.0f}")
        with col3:
            st.metric("Valor en Riesgo", f"{valor_urgente:,.0f} CLP")
        st.info("Aplicar 25% descuento en góndola")
    else:
        st.info("Sin productos urgentes")
    
    # Cierre operativo
    st.subheader("MAÑANA 18:00 | CIERRE OPERATIVO 48H")
    valor_rescatado = (valor_critico * 0.50 if len(productos_criticos) > 0 else 0) + \
                     (valor_urgente * 0.40 if len(productos_urgentes) > 0 else 0)
    total_recuperado = valor_rescatado + credito_trib
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valor Rescatado", f"{valor_rescatado:,.0f} CLP")
    with col2:
        st.metric("Crédito Tributario", f"{credito_trib:,.0f} CLP")
    with col3:
        st.metric("Total Recuperado", f"{total_recuperado:,.0f} CLP")
    
    return valor_vencido, credito_trib, valor_critico, valor_urgente, total_recuperado


def mostrar_resumen_final(valor_vencido, credito_trib, productos_criticos, productos_urgentes, total_recuperado):
    """Muestra el resumen final ejecutivo"""
    st.header("RESUMEN FINAL")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### LO QUE SÍ CONTROLAMOS")
        st.success(f"Donar productos vencidos: {credito_trib:,.0f} CLP crédito tributario")
        st.success("Descuentos estratégicos: 40% (CRITICO), 25% (URGENTE), 15% (PREVENTIVO)")
        st.success("Posicionar en alto tráfico")
        st.success("Monitoreo cada 4 horas")
    
    with col2:
        st.markdown("#### LO QUE NO CONTROLAMOS")
        st.warning("Respuesta de clientes")
        st.warning("Eventos externos")
        st.warning("Stock residual")
    
    st.markdown("### CONCLUSION EJECUTIVA")
    
    valor_critico = productos_criticos['Valor_Stock_Costo'].sum() if len(productos_criticos) > 0 else 0
    valor_urgente = productos_urgentes['Valor_Stock_Costo'].sum() if len(productos_urgentes) > 0 else 0
    
    st.error(f"Si no donamos: Pérdida de {valor_vencido:,.0f} CLP hoy")
    st.success(f"Con donación: Recuperamos {credito_trib:,.0f} CLP en crédito")
    st.info(f"En 48h: Rescatamos entre {valor_critico*0.40 + valor_urgente*0.30:,.0f} y {valor_critico*0.60 + valor_urgente*0.50:,.0f} CLP")
    st.metric("Total recuperado esperado", f"{total_recuperado:,.0f} CLP")


# =============================================================================
# FUNCIÓN PRINCIPAL - STREAMLIT APP
# =============================================================================

def main():
    """Función principal de la aplicación Streamlit"""
    
    st.title("SISTEMA DE GESTION DE VENCIMIENTOS")
    st.markdown("---")
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("Configuración")
        ruta_csv = st.text_input("Ruta del CSV", "/kaggle/input/datasets/juancas/inventario-real/dataset_elasticidad_ampliado.csv")
        mostrar_grafico = st.checkbox("Mostrar Matriz de Riesgo", value=True)
        
        if st.button("Ejecutar Análisis"):
            st.session_state['ejecutar'] = True
    
    if 'ejecutar' not in st.session_state:
        st.session_state['ejecutar'] = False
    
    if st.session_state['ejecutar'] or True:  # Ejecutar por defecto
        try:
            # Carga y preparación de datos
            with st.spinner("Cargando datos..."):
                df = cargar_datos(ruta_csv)
                fecha_hoy = obtener_fecha_hoy(df)
                df_hoy = filtrar_por_fecha(df, fecha_hoy)
                df_hoy = mapear_columnas(df_hoy)
                verificar_columnas(df_hoy)
            
            st.info(f"Análisis para: {fecha_hoy.date()} | Productos: {len(df_hoy)}")
            
            # Filtrado y clasificación
            df_riesgo = filtrar_productos_riesgo(df_hoy)
            df_riesgo = calcular_valor_stock(df_riesgo)
            total_riesgo = df_riesgo['Valor_Stock_Costo'].sum()
            
            if len(df_riesgo) == 0:
                st.warning("NO HAY PRODUCTOS EN RIESGO (10 días) EN EL SNAPSHOT ACTUAL")
                st.stop()
            
            df_riesgo = aplicar_clasificacion(df_riesgo)
            
            # Cálculos contables
            resumen_por_mes, df_con_meses = agrupar_por_mes_vencimiento(df_hoy, fecha_hoy)
            total_riesgo_mes = df_riesgo['Valor_Stock_Costo'].sum()
            
            # Mostrar matriz de riesgo
            if mostrar_grafico:
                st.subheader("MATRIZ DE RIESGO")
                fig = crear_matriz_riesgo(df_riesgo, total_riesgo, fecha_hoy)
                st.pyplot(fig)
            
            # Mostrar resúmenes
            mostrar_resumen_ejecutivo(fecha_hoy, df_riesgo, total_riesgo, total_riesgo_mes, resumen_por_mes, df_con_meses)
            mostrar_top_productos(df_riesgo, fecha_hoy)
            
            # Plan de acción
            st.markdown("---")
            valor_vencido, credito_trib, valor_critico, valor_urgente, total_recuperado = mostrar_plan_accion(df_riesgo, fecha_hoy)
            
            # Resumen final
            st.markdown("---")
            productos_criticos = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'CRITICO']
            productos_urgentes = df_riesgo[df_riesgo['Nivel_Riesgo'] == 'URGENTE']
            mostrar_resumen_final(valor_vencido, credito_trib, productos_criticos, productos_urgentes, total_recuperado)
            
        except Exception as e:
            st.error(f"Error en el análisis: {str(e)}")


if __name__ == "__main__":
    main()
