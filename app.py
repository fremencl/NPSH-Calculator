import streamlit as st
import math

# Configuración de la página
st.set_page_config(page_title="NPSH Calculadora LCO2", layout="wide")

st.title("Calculadora de NPSH para Tanque de LCO2")
st.info("Caudal de referencia: Fijo en 600 L/h")

# Barra lateral para entradas del usuario
st.sidebar.header("Parámetros del Sistema")

npshr = st.sidebar.number_input(
    "NPSHr de la bomba (m)", 
    value=1.50, 
    step=0.10, 
    format="%.2f"
)

orientacion = st.sidebar.radio(
    "Orientación del tanque", 
    ["Vertical", "Horizontal"]
)

capacidad_L = st.sidebar.number_input(
    "Capacidad total del tanque INTERIOR (Litros)", 
    value=5000.0, 
    step=100.0,
    help="Considerar el volumen geométrico del recipiente INTERIOR que contiene el LCO2, no de la envolvente exterior"
)

diametro = st.sidebar.number_input(
    "Diámetro del tanque INTERIOR (m)", 
    value=1.50, 
    step=0.10, 
    format="%.2f"
)
st.sidebar.caption("⚠️ Ingresar el diámetro del recipiente INTERIOR (descontando el espesor de la doble pared/aislación exterior)")

porcentaje_llenado = st.sidebar.slider(
    "Porcentaje de llenado a evaluar (%)", 
    min_value=1, 
    max_value=100, 
    value=15
)

z_bomba = st.sidebar.number_input(
    "Altura estática desde la salida del tanque hasta el eje de la bomba (Z_bomba en m)", 
    value=1.00, 
    step=0.10, 
    format="%.2f"
)

diametro_linea = st.sidebar.selectbox(
    "Diámetro de la manguera/línea de succión", 
    ["1 pulgada", "3/4 pulgada", "1/2 pulgada"]
)

longitud_linea = st.sidebar.number_input(
    "Longitud real de la línea de succión (m)", 
    value=3.0, 
    step=0.10, 
    format="%.2f"
)

# Cálculos Matemáticos Internos
volumen_m3 = capacidad_L / 1000.0
radio = diametro / 2.0
area_circulo = math.pi * (radio ** 2)

if orientacion == "Vertical":
    # Asumimos que la capacidad y el diámetro definen la altura total del cilindro
    altura_total_cilindro = volumen_m3 / area_circulo
    z_liquido = altura_total_cilindro * (porcentaje_llenado / 100.0)
    largo_cilindro = altura_total_cilindro
else:
    # Función para el área del segmento circular
    def area_segmento(h, R):
        if h <= 0.0: return 0.0
        if h >= 2 * R: return math.pi * (R ** 2)
        return (R ** 2) * math.acos((R - h) / R) - (R - h) * math.sqrt(2 * R * h - h ** 2)

    f = porcentaje_llenado / 100.0
    target_area = f * area_circulo
    
    # Bisección para encontrar Z_liquido (h)
    low, high = 0.0, diametro
    for _ in range(100):
        mid = (low + high) / 2.0
        if area_segmento(mid, radio) < target_area:
            low = mid
        else:
            high = mid
    z_liquido = (low + high) / 2.0
    largo_cilindro = volumen_m3 / area_circulo

# Pérdida en línea (hf_linea)
base_hf = {
    "1 pulgada": 0.01,
    "3/4 pulgada": 0.05,
    "1/2 pulgada": 0.35
}
hf_linea = base_hf[diametro_linea] * (longitud_linea / 3.0)

# Pérdida por accesorios (hf_accesorios)
hf_accesorios = 0.20

# NPSHa
npsha = z_liquido + z_bomba - hf_linea - hf_accesorios

# Salidas en Pantalla (Panel Principal)
st.header("Resultados de Evaluación")

col1, col2, col3 = st.columns(3)
margen = npsha - npshr

col1.metric("NPSHa Calculado (m)", f"{npsha:.2f}")
col2.metric("NPSHr Requerido (m)", f"{npshr:.2f}")
col3.metric("Margen / Diferencia", f"{margen:.2f} m")

if npsha >= npshr:
    st.success("CUMPLE (Sin riesgo aparente de cavitación bajo estas condiciones)")
else:
    st.error("NO CUMPLE (Riesgo inminente de cavitación / gasificación en la succión)")

st.subheader("Balance de Energía (Desglose)")
st.markdown(f"""
- **(+) Altura de líquido en el tanque interior ($Z_{{liquido}}$):** `+{z_liquido:.2f} m`
- **(+) Altura estática de instalación ($Z_{{bomba}}$):** `+{z_bomba:.2f} m`
- **(-) Pérdida por fricción en manguera ($hf_{{linea}}$):** `-{hf_linea:.2f} m`
- **(-) Pérdida fija por accesorios ($hf_{{accesorios}}$):** `-{hf_accesorios:.2f} m`
- **(=) NPSHa Total:** `{npsha:.2f} m`
""")

if orientacion == "Horizontal":
    st.info(f"Dato informativo: Largo calculado del cilindro horizontal = {largo_cilindro:.2f} m")

st.warning("(***) SE DEBE CONSIDERAR DISMINUCION DE NPSH POR GANANCIA DE CALOR EN LINEA DE SUCCION")
