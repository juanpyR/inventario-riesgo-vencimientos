import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Control de Inventario Pro", layout="wide")

st.title("📊 Dashboard de Inventario Geo-Inteligente")
st.markdown("Sube tus 5 archivos para consolidar y visualizar la red de distribución.")

# 1. Carga múltiple de archivos
uploaded_files = st.sidebar.file_uploader("Carga tus archivos CSV aquí", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "inventario": None, "productos": None, "lotes": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        # Limpieza de columnas: eliminar espacios en blanco y convertir a nombres estándar
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        # Identificación robusta
        if "Latitud" in cols and "ID_Ciudad" in cols and "Tipo_Movimiento" not in cols and "Stock_Teorico_Unidades" not in cols:
            data["sucursales"] = df_temp
            st.sidebar.success(f"✅ Sucursales: {file.name}")
        elif "Tipo_Movimiento" in cols:
            data["inventario"] = df_temp
            st.sidebar.success(f"✅ Movimientos: {file.name}")
        elif "Categoria" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
            st.sidebar.success(f"✅ Productos: {file.name}")
        elif "Fecha_Creacion_Lote" in cols:
            data["lotes"] = df_temp
            st.sidebar.success(f"✅ Lotes: {file.name}")

    # Verificar requisitos mínimos para el análisis
    if data["inventario"] is not None and data["sucursales"] is not None and data["productos"] is not None:
        
        # --- PROCESO DE CONSOLIDACIÓN ---
        # 1. Unir movimientos con sucursales
        df_central = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
        
        # 2. Unir con productos
        df_central = df_central.merge(
            data["productos"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], 
            on='Producto_ID', 
            how='left'
        )
        
        # --- CÁLCULO DE STOCK ACTUAL Y VALORIZACIÓN ---
        # Filtramos para obtener el último estado de cada lote en cada sucursal
        df_actual = df_central.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
        df_actual['Valor_Inventario_CLP'] = df_actual['Stock_Teorico_Unidades'] * df_actual['Precio_Venta_CLP']

        # --- PANEL DE CONTROL ---
        st.sidebar.markdown("---")
        st.sidebar.header("🕹️ Controles del Mapa")
        
        view_option = st.sidebar.radio(
            "Selecciona la Métrica del Mapa:",
            ["Stock (Unidades)", "Valorización ($)", "Días para Vencer (Promedio)"]
        )
        
        cat_filter = st.sidebar.multiselect(
            "Filtrar por Categoría:",
            options=df_actual['Categoria'].unique(),
            default=df_actual['Categoria'].unique()
        )
        
        # Aplicar filtros
        mask = df_actual['Categoria'].isin(cat_filter)
        df_filtered = df_actual[mask]

        # Configuración dinámica del mapa
        map_map = {
            "Stock (Unidades)": {"col": "Stock_Teorico_Unidades", "color": "Blues", "label": "Unidades"},
            "Valorización ($)": {"col": "Valor_Inventario_CLP", "color": "Greens", "label": "Valor CLP"},
            "Días para Vencer (Promedio)": {"col": "Dias_Para_Vencer", "color": "Reds_r", "label": "Días Restantes"}
        }
        
        config = map_map[view_option]
        
        # Agrupar para el mapa
        df_mapa = df_filtered.groupby(['Sucursal', 'Latitud', 'Longitud']).agg({
            config['col']: 'sum' if view_option != "Días para Vencer (Promedio)" else 'mean'
        }).reset_index()

        # --- MAPA INTERACTIVO ---
        st.subheader(f"Mapa de {view_option} por Sucursal")
        
        fig = px.scatter_mapbox(
            df_mapa,
            lat="Latitud",
            lon="Longitud",
            size=config['col'],
            color=config['col'],
            color_continuous_scale=config['color'],
            size_max=40,
            zoom=10,
            hover_name="Sucursal",
            hover_data={config['col']: True, "Latitud": False, "Longitud": False},
            mapbox_style="carto-positron"
        )
        
        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            mapbox=dict(center=dict(lat=df_mapa['Latitud'].mean(), lon=df_mapa['Longitud'].mean()))
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # --- MÉTRICAS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Stock Total", f"{int(df_filtered['Stock_Teorico_Unidades'].sum()):,}")
        c2.metric("Valor Total", f"${int(df_filtered['Valor_Inventario_CLP'].sum()):,}")
        c3.metric("Promedio Días Venc.", f"{int(df_filtered['Dias_Para_Vencer'].mean())} días")

    else:
        st.warning("⚠️ Faltan archivos. Asegúrate de subir: SUCURSALES, PRODUCTOS e INVENTARIO.")
