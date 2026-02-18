import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Consolidador Inteligente", layout="wide")

st.title("🔄 Consolidador Automático de Inventario")
st.markdown("""
Sube los 5 archivos en cualquier orden. El sistema reconocerá automáticamente cuál es cuál 
basándose en sus columnas y generará el archivo central.
""")

# 1. Carga múltiple de archivos
uploaded_files = st.sidebar.file_uploader("Sube tus 5 archivos CSV", type="csv", accept_multiple_files=True)

# Diccionario para almacenar los DataFrames identificados
data = {
    "sucursales": None,
    "productos": None,
    "lotes": None,
    "inventario": None,
    "stock_geo": None
}

if uploaded_files:
    for file in uploaded_files:
        df_temp = pd.read_csv(file)
        cols = set(df_temp.columns)
        
        # Lógica de identificación por columnas clave
        if "Latitud" in cols and "ID_Ciudad" in cols and "Direccion_Aprox" in cols and "Sucursal" in cols and "Stock_Teorico_Unidades" not in cols:
            data["sucursales"] = df_temp
            st.sidebar.success(f"✅ Sucursales: {file.name}")
            
        elif "Dias_Caducidad_Base" in cols and "Producto_ID" in cols and "Lote_ID" not in cols:
            data["productos"] = df_temp
            st.sidebar.success(f"✅ Productos: {file.name}")
            
        elif "Fecha_Creacion_Lote" in cols:
            data["lotes"] = df_temp
            st.sidebar.success(f"✅ Lotes: {file.name}")
            
        elif "Tipo_Movimiento" in cols:
            data["inventario"] = df_temp
            st.sidebar.success(f"✅ Inventario: {file.name}")
            
        elif "Stock_Teorico_Unidades" in cols and "Latitud" in cols:
            data["stock_geo"] = df_temp
            st.sidebar.success(f"✅ Stock GEO: {file.name}")

    # Verificar si tenemos los archivos necesarios para consolidar
    # (Usaremos Inventario, Productos y Sucursales para el Central)
    if data["inventario"] is not None and data["productos"] is not None and data["sucursales"] is not None:
        
        # --- PROCESO DE CONSOLIDACIÓN ---
        df_inv = data["inventario"]
        df_prod = data["productos"]
        df_suc = data["sucursales"]
        
        # 1. Unir con Productos para traer Categoría y Rotación
        # Eliminamos columnas duplicadas antes de unir si existen
        df_central = df_inv.merge(
            df_prod[['Producto_ID', 'Categoria', 'Categoria_Rotacion']], 
            on='Producto_ID', 
            how='left'
        )
        
        # 2. Unir con Sucursales para traer Geolocalización
        df_central = df_central.merge(
            df_suc[['Sucursal', 'ID_Ciudad', 'Latitud', 'Longitud', 'Direccion_Aprox']], 
            on='Sucursal', 
            how='left'
        )

        st.info("### 📈 Vista Previa del Archivo Central Consolidado")
        st.dataframe(df_central.head(10), use_container_width=True)

        # Gráfico rápido de Salud de Inventario
        if "Estado_Inventario" in df_central.columns:
            st.subheader("Estado de Inventario Consolidado")
            fig = px.pie(df_central, names='Estado_Inventario', title="Distribución de Estados (Normal vs Vencido)")
            st.plotly_chart(fig)

        # Botón de descarga
        csv = df_central.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CENTRAL_CONSOLIDADO.csv",
            data=csv,
            file_name='CENTRAL_INVENTARIO_CONSOLIDADO.csv',
            mime='text/csv',
        )
    else:
        st.warning("Esperando a que se suban todos los archivos necesarios para identificar las relaciones...")
