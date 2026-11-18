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
    value=50
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
    min_value=0.10,
    format="%.2f"
)

# --- Sección: Análisis de Sensibilidad ---
st.sidebar.divider()
st.sidebar.subheader("Análisis de Sensibilidad")

usar_darcy = st.sidebar.checkbox(
    "Reemplazar Hf por Darcy-Weisbach real",
    value=False,
    help="Calcula fricción en línea y accesorios (K=16) con ecuaciones de Darcy-Weisbach/Swamee-Jain y propiedades reales del LCO2 saturado a -20°C."
)

if usar_darcy:
    tipo_conduccion = st.sidebar.radio(
        "Tipo de conducción",
        ["Tubería rígida (Inox Sch 40)", "Manguera flexible corrugada"],
        help="Las mangueras metálicas corrugadas presentan mayor rugosidad efectiva y menor diámetro interno que una cañería Schedule 40."
    )
else:
    tipo_conduccion = None

usar_calor = st.sidebar.checkbox(
    "Incorporar ganancia de calor (Espuma Ø100 mm en buen estado)",
    value=False,
    help="Considera aislación criogénica de espuma de 100 mm de diámetro exterior en buen estado (k=0.030 W/m·K, ΔT=40°C) más puentes térmicos en válvulas, filtro Y y bridas."
)

# --- Cálculos Matemáticos Internos ---
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

# Propiedades físicas LCO2 saturado a -20°C (19.7 bar abs) para Q = 600 L/h
G = 9.81
RHO_LCO2 = 1032.0                         # Densidad líquido (kg/m3)
NU_LCO2 = 1.153e-7                        # Viscosidad cinemática (m2/s)
CP_LCO2 = 2050.0                          # Calor específico líquido (J/(kg·K))
DP_DT_LCO2 = 61400.0                      # Pendiente dPsat/dT a -20°C (Pa/K)
CAUDAL_M3_S = (600.0 / 1000.0) / 3600.0   # 600 L/h en m3/s
FLUJO_MASICO = RHO_LCO2 * CAUDAL_M3_S     # ~0.172 kg/s

# 1. Cálculo Situación Base (Referencia original)
base_hf = {
    "1 pulgada": 0.01,
    "3/4 pulgada": 0.05,
    "1/2 pulgada": 0.35
}
hf_linea_base = base_hf[diametro_linea] * (longitud_linea / 3.0)
hf_accesorios_base = 0.20
npsha_base = z_liquido + z_bomba - hf_linea_base - hf_accesorios_base

# 2. Evaluación Hidráulica (Base vs Darcy-Weisbach)
if usar_darcy:
    if tipo_conduccion == "Tubería rígida (Inox Sch 40)":
        # Diámetros internos reales ASTM A312 Sch 40S (m)
        diametros_id = {
            "1 pulgada": 0.02664,
            "3/4 pulgada": 0.02093,
            "1/2 pulgada": 0.01580
        }
        rugosidad = 0.000015  # 0.015 mm (Inox comercial)
    else:
        # Diámetros internos nominales de manguera criogénica (m)
        diametros_id = {
            "1 pulgada": 0.02540,
            "3/4 pulgada": 0.01905,
            "1/2 pulgada": 0.01270
        }
        rugosidad = 0.000800  # 0.80 mm (rugosidad efectiva corrugación anular)

    d_int = diametros_id[diametro_linea]
    area_tubo = math.pi * ((d_int / 2.0) ** 2)
    velocidad = CAUDAL_M3_S / area_tubo
    reynolds = (velocidad * d_int) / NU_LCO2

    # Ecuación de Swamee-Jain para factor de fricción de Darcy
    f_darcy = 0.25 / (math.log10((rugosidad / (3.7 * d_int)) + (5.74 / (reynolds ** 0.9))) ** 2)
    carga_velocidad = (velocidad ** 2) / (2.0 * G)

    hf_linea = f_darcy * (longitud_linea / d_int) * carga_velocidad
    
    # K_total = 16.0 (Salida tanque + válvula globo criogénica + filtro Y + 2 codos + válvula corte)
    k_total = 16.0
    hf_accesorios = k_total * carga_velocidad
else:
    hf_linea = hf_linea_base
    hf_accesorios = hf_accesorios_base

# 3. Evaluación Térmica (Ganancia de calor con espuma de Ø100 mm exterior en buen estado)
if usar_calor:
    diametros_od = {
        "1 pulgada": 0.03340,
        "3/4 pulgada": 0.02667,
        "1/2 pulgada": 0.02134
    }
    r_int_ais = diametros_od[diametro_linea] / 2.0
    diametro_ext_ais = 0.233          # 200 mm de diámetro exterior total de aislación
    r_ext_ais = diametro_ext_ais / 2.0
    k_espuma = 0.030                  # Conductividad espuma en buen estado (W/(m·K))
    h_ext = 9.0                       # Convección natural + radiación exterior (W/(m2·K))
    delta_t_amb = 40.0                # T_ambiente (+20°C) - T_LCO2 (-20°C) = 40 K

    r_term_ais = math.log(r_ext_ais / r_int_ais) / (2.0 * math.pi * k_espuma)
    r_term_ext = 1.0 / (2.0 * math.pi * r_ext_ais * h_ext)
    q_lineal_w_m = delta_t_amb / (r_term_ais + r_term_ext)

    # Puentes térmicos fijos en vástagos de válvulas, filtro Y, soportes y brida bomba (~18 W)
    q_puentes_w = 18.0
    q_total_w = (q_lineal_w_m * longitud_linea) + q_puentes_w

    delta_t_fluido = q_total_w / (FLUJO_MASICO * CP_LCO2)
    delta_pv_pa = DP_DT_LCO2 * delta_t_fluido
    hf_calor = delta_pv_pa / (RHO_LCO2 * G)
else:
    q_total_w = 0.0
    delta_t_fluido = 0.0
    hf_calor = 0.0

# NPSHa Final
npsha = z_liquido + z_bomba - hf_linea - hf_accesorios - hf_calor

# --- Salidas en Pantalla (Panel Principal) ---
st.header("Resultados de Evaluación")

col1, col2, col3 = st.columns(3)
margen = npsha - npshr

# Mostrar variación respecto al caso base solo si algún checkbox de sensibilidad está activo
sensibilidad_activa = usar_darcy or usar_calor
delta_texto = f"{npsha - npsha_base:+.2f} m vs Caso Base" if sensibilidad_activa else None

col1.metric("NPSHa Calculado (m)", f"{npsha:.2f}", delta=delta_texto)
col2.metric("NPSHr Requerido (m)", f"{npshr:.2f}")
col3.metric("Margen / Diferencia", f"{margen:.2f} m")

if npsha >= npshr:
    st.success("CUMPLE (Sin riesgo aparente de cavitación bajo estas condiciones)")
else:
    st.error("NO CUMPLE (Riesgo inminente de cavitación / gasificación en la succión)")

st.subheader("Balance de Energía (Desglose)")

etiqueta_hidraulica = f"Darcy-Weisbach ({tipo_conduccion})" if usar_darcy else "Modelo Base"
desglose_md = f"""
- **(+) Altura de líquido en el tanque interior ($Z_{{liquido}}$):** `+{z_liquido:.2f} m`
- **(+) Altura estática de instalación ($Z_{{bomba}}$):** `+{z_bomba:.2f} m`
- **(-) Pérdida por fricción en línea ($hf_{{linea}}$ — *{etiqueta_hidraulica}*):** `-{hf_linea:.2f} m`
- **(-) Pérdida por accesorios ($hf_{{accesorios}}$ — *{etiqueta_hidraulica}*):** `-{hf_accesorios:.2f} m`
"""

if usar_calor:
    desglose_md += (
        f"- **(-) Pérdida por ganancia de calor ($hf_{{calor}}$ — *Espuma Ø100 mm*):** `-{hf_calor:.2f} m` "
        f"*(Ingreso estimado: {q_total_w:.1f} W → ΔT = +{delta_t_fluido:.3f} °C)*\n"
    )

desglose_md += f"- **(=) NPSHa Total:** `{npsha:.2f} m`"
st.markdown(desglose_md)

if orientacion == "Horizontal":
    st.info(f"Dato informativo: Largo calculado del cilindro horizontal = {largo_cilindro:.2f} m")

if not usar_calor:
    st.warning("(***) SE DEBE CONSIDERAR DISMINUCION DE NPSH POR GANANCIA DE CALOR EN LINEA DE SUCCION")
else:
    st.caption(
        "ℹ️ Nota térmica activa: Evaluado para LCO2 saturado a -20°C con aislación de espuma criogénica de Ø100 mm exterior en buen estado "
        "y ΔT ambiental de 40°C. Tramos desnudos o con hielo/escarcha aumentarán drásticamente esta pérdida."
    )
