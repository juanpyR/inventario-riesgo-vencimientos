# Inventario Riesgo Vencimientos

Sistema determinista para detectar riesgo de vencimiento en inventario de PYMES.

## Características

- Análisis basado en reglas claras (no probabilístico)
- Clasificación automática en:
  - VENCIDO
  - CRÍTICO
  - URGENTE
  - PREVENTIVO
- Cálculo de valor total en riesgo
- Visualización simple y entendible

## Cómo usar

1. Subir archivo CSV con columnas:
   - Fecha
   - Días_para_Vencimiento
   - Stock_Inicial
   - Costo_Unitario_Neto
   - Precio_Venta_Bruto
   - Producto

2. El sistema analiza el snapshot más reciente.

## Objetivo

Reducir pérdida por vencimiento mediante decisiones operativas simples.
