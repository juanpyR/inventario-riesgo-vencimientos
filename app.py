import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Mapa de Inventario", layout="wide")

st.title("📍 Mapa de Inventario por Sucursales")

# Cargar datos
@st.cache_data
def cargar_datos():
    sucursales = pd.read_csv("1_SUCURSALES_MASTER.csv")
    stock = pd.read_csv("5_STOCK_ACTUAL_GEO_POWERBI.csv")
    productos = pd.read_csv("2_PRODUCTOS_MASTER.csv")
    lotes = pd.read_csv("3_LOTES_PRODUCTOS.csv")
    inventario = pd.read_csv("4_INVENTARIO_COMPLETO_LOTES.csv")
    return sucursales, stock, productos, lotes, inventario

sucursales, stock, productos, lotes, inventario = cargar_datos()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Filtro por estado de inventario
estados_disponibles = stock['Estado_Inventario'].unique().tolist()
estado_seleccionado = st.sidebar.multiselect(
    "Estado del Inventario:",
    options=estados_disponibles,
    default=estados_disponibles
)

# Filtro por sucursal
sucursales_disponibles = stock['Sucursal'].unique().tolist()
sucursal_seleccionada = st.sidebar.multiselect(
    "Sucursales:",
    options=sucursales_disponibles,
    default=sucursales_disponibles
)

# Filtrar datos
stock_filtrado = stock[
    (stock['Estado_Inventario'].isin(estado_seleccionado)) &
    (stock['Sucursal'].isin(sucursal_seleccionada))
]

# Agrupar por sucursal para el mapa
stock_por_sucursal = stock_filtrado.groupby(['Sucursal', 'Latitud', 'Longitud', 'ID_Ciudad']).agg({
    'Stock_Teorico_Unidades': 'sum',
    'Precio_Venta_CLP': 'mean'
}).reset_index()

# Crear mapa
st.subheader("🗺️ Distribución Geográfica del Inventario")

fig = px.scatter_mapbox(
    stock_por_sucursal,
    lat="Latitud",
    lon="Longitud",
    size="Stock_Teorico_Unidades",
    color="Stock_Teorico_Unidades",
    hover_name="Sucursal",
    hover_data={
        "Stock_Teorico_Unidades": ":,.0f",
        "Precio_Venta_CLP": ":,.0f",
        "Latitud": False,
        "Longitud": False
    },
    color_continuous_scale=px.colors.sequential.Reds,
    size_max=50,
    zoom=9,
    center={"lat": -33.45, "lon": -70.65},
    mapbox_style="open-street-map"
)

fig.update_layout(
    height=600,
    margin={"r":0,"t":30,"l":0,"b":0},
    coloraxis_colorbar_title="Stock Total"
)

st.plotly_chart(fig, use_container_width=True)

# Mostrar métricas por sucursal
st.subheader("📊 Resumen por Sucursal")

col1, col2, col3 = st.columns(3)

with col1:
    total_stock = stock_filtrado['Stock_Teorico_Unidades'].sum()
    st.metric("Total Unidades en Stock", f"{total_stock:,.0f}")

with col2:
    total_sucursales = stock_filtrado['Sucursal'].nunique()
    st.metric("Sucursales Activas", total_sucursales)

with col3:
    valor_total = (stock_filtrado['Stock_Teorico_Unidades'] * stock_filtrado['Precio_Venta_CLP']).sum()
    st.metric("Valor Total del Inventario", f"${valor_total:,.0f}")

# Tabla detallada
st.subheader("📋 Detalle por Sucursal")
st.dataframe(
    stock_por_sucursal[[
        'Sucursal', 
        'Stock_Teorico_Unidades', 
        'Precio_Venta_CLP'
    ]].sort_values('Stock_Teorico_Unidades', ascending=False),
    use_container_width=True,
    hide_index=True
)

# Alertas de inventario crítico
st.subheader("⚠️ Alertas de Inventario")

stock_critico = stock_filtrado[stock_filtrado['Estado_Inventario'].isin(['Vencido', 'Crítico (4 días)'])]

if len(stock_critico) > 0:
    alertas_por_sucursal = stock_critico.groupby('Sucursal').agg({
        'Lote_ID': 'count',
        'Stock_Teorico_Unidades': 'sum'
    }).reset_index()
    alertas_por_sucursal.columns = ['Sucursal', 'Lotes Críticos', 'Unidades Críticas']
    
    st.dataframe(
        alertas_por_sucursal.sort_values('Lotes Críticos', ascending=False),
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("✅ No hay inventario crítico en las sucursales seleccionadas")
