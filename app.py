import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Gestión de Inventario 360", layout="wide")

# Estética Profesional (Power BI Style)
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; }
    div[data-testid="stExpander"] { border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🎛️ Centro de Comando de Inventario")

uploaded_files = st.sidebar.file_uploader("Sube tus archivos", type="csv", accept_multiple_files=True)

# Lógica de carga robusta
data = {"sucursales": None, "inventario": None, "productos": None}
if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        df_temp.columns = df_temp.columns.str.strip()
        if "Latitud" in df_temp.columns and "ID_Ciudad" in df_temp.columns and "Stock_Teorico_Unidades" not in df_temp.columns:
            data["sucursales"] = df_temp
        elif "Tipo_Movimiento" in df_temp.columns:
            data["inventario"] = df_temp
        elif "Categoria" in df_temp.columns and "Producto_ID" in df_temp.columns:
            data["productos"] = df_temp

    if data["inventario"] is not None and data["sucursales"] is not None:
        # 1. Consolidación de Inteligencia de Negocios
        df = data["inventario"].merge(data["sucursales"], on='Sucursal', how='left')
        if data["productos"] is not None:
            df = df.merge(data["productos"][['Producto_ID', 'Categoria', 'Categoria_Rotacion']], on='Producto_ID', how='left')

        # 2. Cálculo de Estado Actual (Snapshot)
        df_now = df.sort_values('Fecha_Movimiento').groupby(['Lote_ID', 'Sucursal']).tail(1).copy()
        df_now['Valor_Total'] = df_now['Stock_Teorico_Unidades'] * df_now['Precio_Venta_CLP']

        # --- BARRA LATERAL AVANZADA ---
        st.sidebar.header("🎯 Filtros Tácticos")
        cat_list = st.sidebar.multiselect("Categorías", df_now['Categoria'].unique(), default=df_now['Categoria'].unique())
        risk_filter = st.sidebar.slider("Días mínimos para vencer", 0, 365, 0)
        
        df_filtered = df_now[(df_now['Categoria'].isin(cat_list)) & (df_now['Dias_Para_Vencer'] >= risk_filter)]

        # --- KPIS SUPERIORES ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valor del Inventario", f"${int(df_filtered['Valor_Total'].sum()):,}")
        c2.metric("Unidades Totales", f"{int(df_filtered['Stock_Teorico_Unidades'].sum()):,}")
        c3.metric("Riesgo Medio (Días)", f"{int(df_filtered['Dias_Para_Vencer'].mean())} d")
        c4.metric("SKUs Activos", df_filtered['Producto_ID'].nunique())

        # --- MAPA MULTI-VARIABLE ---
        st.subheader("📍 Análisis Geográfico de Riesgo y Volumen")
        
        # Agrupación rica para el mapa
        df_mapa = df_filtered.groupby(['Sucursal', 'Latitud', 'Longitud', 'Direccion_Aprox']).agg({
            'Stock_Teorico_Unidades': 'sum',
            'Valor_Total': 'sum',
            'Dias_Para_Vencer': 'mean',
            'Producto_ID': 'nunique'
        }).reset_index()

        fig = px.scatter_mapbox(
            df_mapa,
            lat="Latitud", lon="Longitud",
            size="Stock_Teorico_Unidades",  # Tamaño = Cantidad
            color="Dias_Para_Vencer",       # Color = Riesgo de vencimiento
            color_continuous_scale="RdYlGn", # Rojo (vence pronto) a Verde (seguro)
            hover_name="Sucursal",
            hover_data={
                "Stock_Teorico_Unidades": ":,f",
                "Valor_Total": ":$,.0f",
                "Dias_Para_Vencer": ":.1f",
                "Producto_ID": True,
                "Latitud": False, "Longitud": False
            },
            size_max=45, zoom=10,
            mapbox_style="carto-positron"
        )
        
        fig.update_layout(height=600, margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)

        # --- SECCIÓN INFERIOR: ANALÍTICA DETALLADA ---
        st.markdown("---")
        col_left, col_right = st.columns([6, 4])

        with col_left:
            st.subheader("📦 Stock y Valor por Categoría")
            # Gráfico de doble eje o barras apiladas
            fig_cat = px.bar(
                df_filtered.groupby('Categoria').agg({'Stock_Teorico_Unidades':'sum', 'Valor_Total':'sum'}).reset_index(),
                x='Categoria', y='Stock_Teorico_Unidades',
                color='Valor_Total',
                text_auto='.2s',
                title="Volumen por Categoría (Color = Valor Monetario)"
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_right:
            st.subheader("⚠️ Alerta de Lotes Críticos")
            # Tabla de productos que necesitan atención inmediata
            criticos = df_filtered.sort_values('Dias_Para_Vencer').head(10)
            st.dataframe(
                criticos[['Producto', 'Sucursal', 'Dias_Para_Vencer', 'Stock_Teorico_Unidades']],
                hide_index=True
            )

    else:
        st.info("Sube los archivos para activar el Centro de Comando.")
