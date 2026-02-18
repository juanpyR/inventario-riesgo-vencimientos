import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Consolidador e Inventario Geo", layout="wide")

st.title("📍 Análisis Geográfico de Stock")
st.markdown("""
Sube tus archivos en cualquier orden. El sistema consolidará la información y mostrará 
la distribución de inventario en el mapa.
""")

# 1. Carga múltiple de archivos
uploaded_files = st.sidebar.file_uploader("Sube tus 5 archivos CSV", type="csv", accept_multiple_files=True)

# Diccionario para almacenar los DataFrames identificados
data = {"sucursales": None, "productos": None, "lotes": None, "inventario": None, "stock_geo": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        cols = set(df_temp.columns)
        
        # Lógica de identificación automática por columnas
        if "Latitud" in cols and "ID_Ciudad" in cols and "Stock_Teorico_Unidades" not in cols:
            data["sucursales"] = df_temp
            st.sidebar.success(f"✅ Sucursales detectadas")
        elif "Dias_Caducidad_Base" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
            st.sidebar.success(f"✅ Productos detectados")
        elif "Tipo_Movimiento" in cols:
            data["inventario"] = df_temp
            st.sidebar.success(f"✅ Inventario detectado")

    # Si tenemos los datos base, procedemos
    if data["inventario"] is not None and data["sucursales"] is not None:
        
        # --- CONSOLIDACIÓN ---
        # Unimos inventario con sucursales para tener coordenadas
        df_central = data["inventario"].merge(
            data["sucursales"][['Sucursal', 'Latitud', 'Longitud', 'ID_Ciudad']], 
            on='Sucursal', 
            how='left'
        )
        
        # --- CÁLCULO DE STOCK ACTUAL PARA EL MAPA ---
        # Obtenemos el último estado de stock para cada lote en cada sucursal
        df_mapa = df_central.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1)
        
        # Agrupamos por sucursal para el mapa de burbujas
        df_sucursales_stock = df_mapa.groupby(['Sucursal', 'Latitud', 'Longitud']).agg({
            'Stock_Teorico_Unidades': 'sum'
        }).reset_index()

        # --- SECCIÓN DEL MAPA ---
        st.subheader("🌐 Mapa de Stock por Sucursal")
        
        fig_mapa = px.scatter_mapbox(
            df_sucursales_stock,
            lat="Latitud",
            lon="Longitud",
            size="Stock_Teorico_Unidades", # El tamaño de la burbuja depende del stock
            color="Stock_Teorico_Unidades",
            color_continuous_scale=px.colors.sequential.Viridis,
            hover_name="Sucursal",
            hover_data={"Latitud": False, "Longitud": False, "Stock_Teorico_Unidades": True},
            zoom=10,
            height=500
        )

        # Configuración para que el mapa sea "limpio" (sin excesivo detalle)
        fig_mapa.update_layout(
            mapbox_style="carto-positron", # Estilo minimalista claro
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        st.plotly_chart(fig_mapa, use_container_width=True)

        # --- MÉTRICAS Y TABLA ---
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Stock Total en Red", int(df_sucursales_stock['Stock_Teorico_Unidades'].sum()))
        with col2:
            sucursal_top = df_sucursales_stock.sort_values('Stock_Teorico_Unidades', ascending=False).iloc[0]
            st.metric("Sucursal con más Stock", sucursal_top['Sucursal'])

        with st.expander("Ver tabla de datos consolidada"):
            st.dataframe(df_central, use_container_width=True)
            
        # Botón de descarga
        csv = df_central.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Central Consolidado",
            data=csv,
            file_name='CENTRAL_INVENTARIO.csv',
            mime='text/csv'
        )
    else:
        st.info("Sube al menos los archivos de Inventario y Sucursales para generar el mapa.")
