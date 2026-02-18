import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Control Panel Geo", layout="wide")

st.title("🚀 Panel de Control de Inventario Inteligente")

# 1. Carga y Procesamiento (Igual al anterior con reconocimiento automático)
uploaded_files = st.sidebar.file_uploader("Sube tus archivos", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "inventario": None, "productos": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        if "Latitud" in df_temp.columns and "ID_Ciudad" in df_temp.columns:
            data["sucursales"] = df_temp
        elif "Tipo_Movimiento" in df_temp.columns:
            data["inventario"] = df_temp
        elif "Categoria" in df_temp.columns and "Producto_ID" in df_temp.columns:
            data["productos"] = df_temp

    if data["inventario"] is not None and data["sucursales"] is not None and data["productos"] is not None:
        
        # --- CONSOLIDACIÓN COMPLETA ---
        df = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
        df = df.merge(data["productos"][['Producto_ID', 'Categoria']], on='Producto_ID', how='left')
        
        # Filtramos para tener solo el stock actual (último movimiento por lote/sucursal)
        df_actual = df.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
        df_actual['Valor_Total_CLP'] = df_actual['Stock_Teorico_Unidades'] * df_actual['Precio_Venta_CLP']

        # --- PANEL DE CONTROL (SIDEBAR) ---
        st.sidebar.header("Configuración del Mapa")
        
        # Filtro de Categoría
        cats = ["Todas"] + list(df_actual['Categoria'].unique())
        cat_sel = st.sidebar.selectbox("Filtrar por Categoría", cats)
        
        if cat_sel != "Todas":
            df_actual = df_actual[df_actual['Categoria'] == cat_sel]

        # Selector de Métrica para el Mapa
        metrica = st.sidebar.radio(
            "¿Qué quieres ver en el mapa?",
            ["Stock Físico (Unidades)", "Valorización ($ CLP)", "Días para Vencer (Promedio)"]
        )

        map_config = {
            "Stock Físico (Unidades)": {"col": "Stock_Teorico_Unidades", "color": "Viridis", "agg": "sum"},
            "Valorización ($ CLP)": {"col": "Valor_Total_CLP", "color": "Greens", "agg": "sum"},
            "Días para Vencer (Promedio)": {"col": "Dias_Para_Vencer", "color": "RdYlGn", "agg": "mean"}
        }

        # Agrupamos datos para el mapa según la selección
        sel = map_config[metrica]
        df_resumen = df_actual.groupby(['Sucursal', 'Latitud', 'Longitud']).agg({
            sel['col']: sel['agg']
        }).reset_index()

        # --- MAPA INTERACTIVO ---
        st.subheader(f"Visualizando: {metrica}")
        
        fig = px.scatter_mapbox(
            df_resumen,
            lat="Latitud",
            lon="Longitud",
            size=sel['col'],
            color=sel['col'],
            color_continuous_scale=sel['color'],
            size_max=35,
            zoom=10,
            hover_name="Sucursal",
            hover_data={sel['col']: True, "Latitud": False, "Longitud": False},
            mapbox_style="carto-positron"
        )

        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            mapbox=dict(center=dict(lat=df_resumen['Latitud'].mean(), lon=df_resumen['Longitud'].mean())),
        )

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # --- ANÁLISIS COMPLEMENTARIO ---
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 🏆 Top Sucursales")
            st.dataframe(df_resumen.sort_values(by=sel['col'], ascending=False).head(5))
        with col2:
            st.write("### 📉 Resumen por Categoría")
            res_cat = df_actual.groupby('Categoria')[sel['col']].sum().reset_index()
            fig_bar = px.bar(res_cat, x='Categoria', y=sel['col'], color='Categoria')
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("Sube los archivos (Sucursales, Productos e Inventario) para habilitar el panel.")
