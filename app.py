import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Consolidador de Inventario", layout="wide")

st.title("📊 Consolidación de Inventario y Análisis")

# 1. Carga de Archivos
st.sidebar.header("Carga de Datos")
f_sucursales = st.sidebar.file_uploader("1_SUCURSALES_MASTER.csv", type="csv")
f_productos = st.sidebar.file_uploader("2_PRODUCTOS_MASTER.csv", type="csv")
f_lotes = st.sidebar.file_uploader("3_LOTES_PRODUCTOS.csv", type="csv")
f_inventario = st.sidebar.file_uploader("4_INVENTARIO_COMPLETO_LOTES.csv", type="csv")

if f_sucursales and f_productos and f_lotes and f_inventario:
    # Leer DataFrames
    df_suc = pd.read_csv(f_sucursales)
    df_prod = pd.read_csv(f_productos)
    df_lotes = pd.read_csv(f_lotes)
    df_inv = pd.read_csv(f_inventario)

    # 2. Proceso de Consolidación (Creación del Archivo Central)
    # Unimos el inventario con el maestro de productos para obtener la Categoría
    df_central = df_inv.merge(
        df_prod[['Producto_ID', 'Categoria', 'Categoria_Rotacion']], 
        on='Producto_ID', 
        how='left', 
        suffixes=('', '_master')
    )
    
    # Unimos con el maestro de sucursales para obtener coordenadas y IDs
    df_central = df_central.merge(
        df_suc[['Sucursal', 'ID_Ciudad', 'Latitud', 'Longitud', 'Direccion_Aprox']], 
        on='Sucursal', 
        how='left'
    )

    st.success("✅ Archivo Central Consolidado con éxito.")

    # 3. Visualización y Métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Movimientos", len(df_central))
    with col2:
        st.metric("Productos Únicos", df_central['Producto_ID'].nunique())
    with col3:
        st.metric("Sucursales", df_central['Sucursal'].nunique())
    with col4:
        stock_total = df_central.groupby(['Lote_ID', 'Sucursal'])['Stock_Teorico_Unidades'].last().sum()
        st.metric("Stock Total Teórico", int(stock_total))

    # 4. Análisis Gráfico
    st.subheader("Análisis de Stock por Categoría")
    # Calculamos el stock actual por categoría (tomando el último registro de stock teórico por lote/sucursal)
    df_stock_actual = df_central.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1)
    fig_cat = px.bar(df_stock_actual.groupby('Categoria')['Stock_Teorico_Unidades'].sum().reset_index(), 
                     x='Categoria', y='Stock_Teorico_Unidades', color='Categoria',
                     title="Distribución de Unidades por Categoría")
    st.plotly_chart(fig_cat, use_container_width=True)

    # 5. Tabla de Datos
    st.subheader("Vista Previa del Archivo Central")
    st.dataframe(df_central.head(100), use_container_width=True)

    # 6. Botón de Descarga
    csv = df_central.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Archivo Central Consolidado (CSV)",
        data=csv,
        file_name='CENTRAL_INVENTARIO_CONSOLIDADO.csv',
        mime='text/csv',
    )
else:
    st.info("Por favor, sube los 4 archivos maestros y transaccionales en la barra lateral para comenzar.")
