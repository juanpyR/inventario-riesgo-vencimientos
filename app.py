import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Inventario Geo-Estratégico", layout="wide")

# Estilo CSS para que se vea más limpio
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Control de Distribución")

uploaded_files = st.sidebar.file_uploader("Carga tus 5 archivos", type="csv", accept_multiple_files=True)

data = {"sucursales": None, "inventario": None, "productos": None}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        cols = df_temp.columns
        
        if "Latitud" in cols and "ID_Ciudad" in cols and "Stock_Teorico_Unidades" not in cols:
            data["sucursales"] = df_temp
        elif "Tipo_Movimiento" in cols:
            data["inventario"] = df_temp
        elif "Categoria" in cols and "Producto_ID" in cols:
            data["productos"] = df_temp

    if data["inventario"] is not None and data["sucursales"] is not None:
        # Consolidación
        df_central = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
        if data["productos"] is not None:
            df_central = df_central.merge(data["productos"][['Producto_ID', 'Categoria']], on='Producto_ID', how='left')

        # Procesamiento de Stock Actual
        df_actual = df_central.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
        df_actual['Valor_Inventario'] = df_actual['Stock_Teorico_Unidades'] * df_actual['Precio_Venta_CLP']

        # Filtros Sidebar estilo Power BI
        st.sidebar.header("Filtros de Informe")
        color_theme = st.sidebar.selectbox("Tema del Mapa", ["Claro Minimalista", "Oscuro Elegante"])
        map_style = "carto-positron" if color_theme == "Claro Minimalista" else "carto-darkmatter"
        
        view_mode = st.sidebar.radio("Métrica Principal", ["Stock Unidades", "Valorización ($)", "Días Vencimiento"])

        # Configuración de escala de colores
        config = {
            "Stock Unidades": ("Stock_Teorico_Unidades", px.colors.sequential.Blues, "sum"),
            "Valorización ($)": ("Valor_Inventario", px.colors.sequential.Greens, "sum"),
            "Días Vencimiento": ("Dias_Para_Vencer", px.colors.diverging.RdYlGn, "mean")
        }
        
        target_col, colors, mode = config[view_mode]
        
        # Agrupación por Sucursal
        df_mapa = df_actual.groupby(['Sucursal', 'Latitud', 'Longitud'])[target_col].agg(mode).reset_index()

        # --- MAPA ESTILO POWER BI ---
        st.subheader(f"Análisis Geográfico: {view_mode}")
        
        fig = px.scatter_mapbox(
            df_mapa,
            lat="Latitud",
            lon="Longitud",
            size=target_col,
            color=target_col,
            color_continuous_scale=colors,
            size_max=35, # Burbujas más grandes y visibles
            zoom=10,
            hover_name="Sucursal",
            hover_data={target_col: True, "Latitud": False, "Longitud": False},
            mapbox_style=map_style
        )

        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            coloraxis_showscale=True,
            mapbox=dict(
                center=dict(lat=df_mapa['Latitud'].mean(), lon=df_mapa['Longitud'].mean()),
            )
        )

        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # Métricas destacadas
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Unidades", f"{int(df_actual['Stock_Teorico_Unidades'].sum()):,}")
        with c2:
            st.metric("Inversión Total", f"${int(df_actual['Valor_Inventario'].sum()):,}")
        with c3:
            st.metric("Promedio Días a Vencer", f"{int(df_actual['Dias_Para_Vencer'].mean())} d")

    else:
        st.info("Sube los archivos para generar la vista de Power BI.")
