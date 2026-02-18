import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Consolidador Geo-Interactiva", layout="wide")

st.title("🗺️ Mapa de Inventario Dinámico")

# 1. Carga múltiple
uploaded_files = st.sidebar.file_uploader("Arrastra tus archivos aquí", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "inventario": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        cols = df_temp.columns
        if "Latitud" in cols and "ID_Ciudad" in cols and "Stock_Teorico_Unidades" not in cols:
            data["sucursales"] = df_temp
        elif "Tipo_Movimiento" in cols:
            data["inventario"] = df_temp

    if data["inventario"] is not None and data["sucursales"] is not None:
        # Consolidación rápida para el mapa
        df_central = data["inventario"].merge(
            data["sucursales"][['Sucursal', 'Latitud', 'Longitud']], 
            on='Sucursal', 
            how='left'
        )
        
        # Último stock por sucursal/lote
        df_mapa = df_central.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1)
        df_resumen = df_mapa.groupby(['Sucursal', 'Latitud', 'Longitud'])['Stock_Teorico_Unidades'].sum().reset_index()

        # --- MAPA INTERACTIVO MEJORADO ---
        st.subheader("Selecciona y haz zoom sobre las sucursales")
        
        fig = px.scatter_mapbox(
            df_resumen,
            lat="Latitud",
            lon="Longitud",
            size="Stock_Teorico_Unidades",
            color="Stock_Teorico_Unidades",
            color_continuous_scale=px.colors.sequential.Plasma,
            size_max=40,  # Aumenta el tamaño máximo de la burbuja para que sea más clicable
            zoom=9,       # Zoom inicial
            hover_name="Sucursal",
            hover_data={"Stock_Teorico_Unidades": True, "Latitud": False, "Longitud": False},
            mapbox_style="open-street-map" # Estilo más detallado y rápido para zoom
        )

        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            hovermode='closest',
            mapbox=dict(
                bearing=0,
                # Centrado automático en el promedio de tus coordenadas
                center=dict(lat=df_resumen['Latitud'].mean(), lon=df_resumen['Longitud'].mean()),
                pitch=0,
                zoom=9,
            )
        )

        # Mostramos el mapa con una altura mayor para facilitar la navegación
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # --- TABLA DE APOYO ---
        st.write("### Detalle de Stock por Ubicación")
        st.table(df_resumen.sort_values(by="Stock_Teorico_Unidades", ascending=False))

    else:
        st.info("Sube los archivos de Inventario y Sucursales para activar el mapa.")
