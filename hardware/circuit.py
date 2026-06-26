from skidl import *


@requirement("Carrier supplies the Seeed XIAO RP2350 5V pad from a 2S LiPo bus using a fixed 5.0V AP63205 buck regulator; AP63203 is not used because it is fixed 3.3V.")
@requirement("XIAO A0/D0 and A2/D2 physical pads are reserved for VBAT and piezo analog sensing; current/eRPM telemetry comes from the Repeat AM32 dual ESC bidirectional DSHOT links.")
@requirement("Three H3LIS331DL accelerometers share SPI SCK/MOSI/MISO and have independent active-low chip-selects with boot-safe pull-ups.")
@requirement("APA102/SK9822 status LED data and clock are level-shifted from 3.3V to 5V and disabled during non-LED SPI traffic.")
@requirement("Piezo ADC input has a 1MΩ pulldown, 10nF filter capacitor, and BAT54S Schottky clamps to GND and 3V3.")
@requirement("Repeat AM32 dual ESC connects through one signal connector carrying two direct RP2350 bidirectional DSHOT/EDT lines and ground; the ESC BEC is not tied to the carrier 5V rail.")
@requirement("Dedicated orange 2-3S TinySLED meltybrain heading output uses XIAO edge pin D1/A1 and a low-side MOSFET so firmware can generate phase-locked 100-500us strobes at 4000rpm without underside GPIOs.")
@requirement("Expose test pads for SPI, IMU chip-selects, DSHOT, CRSF, VBAT, piezo, heading strobe timing, SWD, GND, 3V3, and 5V.")
def build_circuit():
    gnd = Ground("GND")
    v5 = Power("5V", voltage_domain=5.0, current=2.0)
    v3v3 = Power("3V3", voltage_domain=3.3, current=0.4)
    vbus = Net("VBUS", voltage=VoltageDomain.range(6.0, 8.4), drive=POWER)

    spi_sck = Net("SPI_SCK", voltage_domain=3.3)
    spi_mosi = Net("SPI_MOSI", voltage_domain=3.3)
    spi_miso = Net("SPI_MISO", voltage_domain=3.3)
    exp_cs_n = Net("EXP_CS_N", voltage_domain=3.3)
    cs_a = Net("CS_A", voltage_domain=3.3)
    cs_b = Net("CS_B", voltage_domain=3.3)
    cs_c = Net("CS_C", voltage_domain=3.3)
    led_oe_n = Net("LED_OE_N", voltage_domain=3.3)
    led_di = Net("LED_DI", voltage_domain=5.0)
    led_ck = Net("LED_CK", voltage_domain=5.0)
    dshot1_io = Net("DS1_IO", voltage_domain=3.3)
    dshot2_io = Net("DS2_IO", voltage_domain=3.3)
    dshot1 = Net("DSHOT1", voltage_domain=3.3)
    dshot2 = Net("DSHOT2", voltage_domain=3.3)
    crsf_tx = Net("CRSF_TX", voltage_domain=3.3)
    crsf_rx = Net("CRSF_RX", voltage_domain=3.3)
    vbat_sense = Net("VBAT_SNS", voltage_domain=3.3)
    piezo = Net("PIEZO", voltage_domain=3.3)
    head_led = Net("HEAD_LED", voltage_domain=3.3)
    head_gate = Net("HEAD_GATE")
    head_sw = Net("HEAD_SW")
    swdio = Net("SWDIO", voltage_domain=3.3)
    swdck = Net("SWDCK", voltage_domain=3.3)
    sw = Net("SW")
    bst = Net("BST")
    miso_a = Net("MISO_A", voltage_domain=3.3)
    miso_b = Net("MISO_B", voltage_domain=3.3)
    miso_c = Net("MISO_C", voltage_domain=3.3)

    xiao = Part("Library", "XIAO-RP2350-SMD", ref="U1", value="Seeed XIAO RP2350", footprint="Library:XIAO-RP2350-SMD")
    xiao.fields["LCSC"] = "NONE"
    xiao.fields["info"] = "XIAO RP2350 module on official Seeed XIAO-RP2350-SMD land pattern from Seeed OPL KiCad library. Runtime IO uses edge/castellated pads only: A0/A2 are analog VBAT/piezo inputs, A1 drives the orange 2-3S TinySLED heading MOSFET, and D4/D5 are direct bidirectional DSHOT/EDT links to the Repeat AM32 dual ESC. A0-A3 are aliases of edge pads D0-D3, so this revision still uses MCP23S17 for IMU chip-selects and LED_OE_N rather than underside GPIOs. Official footprint also exposes D11-D18, EN, BOOT, 3V3_OUT, VBAT, SWDIO, SWDCLK, and extra GND underside pads; unused underside GPIO/control pads are left NC for now. 3V3 output limit from spec: do not load over 400mA total. RP2350 CRSF inversion can be handled in IO_BANK0 GPIO INOVER/OUTOVER firmware."
    design_intent(xiao, "SMD-mounted Seeed XIAO RP2350 compute module using the official Seeed XIAO-RP2350-SMD footprint; no headers.", group="XIAO module", placement="Mount flat near the board centre with epoxy fillets at four corners after soldering; confirm USB connector clearance against the board outline.")
    vbat_sense += xiao[1]
    head_led += xiao[2]
    piezo += xiao[3]
    exp_cs_n += xiao[4]
    dshot1_io += xiao[5]
    dshot2_io += xiao[6]
    crsf_tx += xiao[7]
    crsf_rx += xiao[8]
    spi_sck += xiao[9]
    spi_miso += xiao[10]
    spi_mosi += xiao[11]
    v3v3 += xiao[12], xiao[28]
    gnd += xiao[13], xiao[26], xiao[30]
    v5 += xiao[14]
    swdio += xiao[23]
    swdck += xiao[24]
    xiao[15] += NC
    xiao[16] += NC
    xiao[17] += NC
    xiao[18] += NC
    xiao[19] += NC
    xiao[20] += NC
    xiao[21] += NC
    xiao[22] += NC
    xiao[25] += NC
    xiao[27] += NC
    xiao[29] += NC
    xiao[12].set_current_source(0.4)

    j_pwr = Part("Connector_Generic", "Conn_01x02", ref="J1", value="VBUS input fly-leads", footprint="Connector_Wire:SolderWire-0.5sqmm_1x02_P4.6mm_D0.9mm_OD2.1mm_Relief")
    j_pwr.fields["LCSC"] = "NONE"
    design_intent(j_pwr, "Switched 2S LiPo power input from Fingertech switch: pin 1 VBUS, pin 2 GND.", group="Power entry", placement="Place near radial wire exit; use wide copper from pin 1 to buck input capacitor.")
    vbus += j_pwr[1]
    gnd += j_pwr[2]

    u_buck = Part("Library", "AP63205WU-7", ref="U2", value="AP63205WU-7", footprint="Library:TSOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL")
    u_buck.fields["LCSC"] = "C2071056"
    u_buck.fields["info"] = "Fixed 5.0V AP63205, 2A output, 3.8-32V input. FB pin connects directly to 5V; no feedback divider. Datasheet recommends 4.7uH inductor, input ceramic close to VIN, and 100nF BST-SW bootstrap capacitor."
    design_intent(u_buck, "2S LiPo to 5.0V buck regulator feeding the XIAO 5V pad and 5V status LED rail.", group="5V buck", placement="Keep VIN capacitor at VIN/GND pins, keep BST cap at BST/SW pins, and keep SW copper compact and away from IMUs.")
    v5 += u_buck[1]
    vbus += u_buck[2], u_buck[3]
    gnd += u_buck[4]
    sw += u_buck[5]
    bst += u_buck[6]

    l_buck = Part("Device", "L_Small", ref="L1", value="4.7uH", footprint="Inductor_SMD:L_Wuerth_MAPI-4020")
    l_buck.fields["LCSC"] = "C2041623"
    l_buck.fields["info"] = "Bourns SRP4020TA-4R7M: 4.7uH, Isat 3.5A, Irms 2.6A, DCR 95mΩ, low-profile 4020-class inductor. AP63205 full 2A operation asks for about 2.7A current headroom; this is acceptable for the expected carrier load but review if the 5V rail will be loaded near 2A continuously."
    design_intent(l_buck, "Buck output inductor from AP63205 SW node to 5V rail.", group="5V buck", placement="Place adjacent to U2 SW pin; keep SW node short and away from SPI/IMU routes.")
    sw += l_buck[1]
    v5 += l_buck[2]

    c_buck_in = Part("Device", "C_Small", ref="C1", value="22uF", footprint="Capacitor_SMD:C_0805_2012Metric")
    c_buck_in.fields["LCSC"] = "NONE"
    c_buck_in.fields["info"] = "Use X7R/X5R ceramic rated at least 25V for 2S LiPo input transients and DC-bias margin."
    design_intent(c_buck_in, "AP63205 input bulk capacitor from VBUS to GND.", group="5V buck", placement="Place at U2 VIN/GND pins with the smallest possible loop.")
    vbus += c_buck_in[1]
    gnd += c_buck_in[2]

    c_buck_in_hf = Part("Device", "C_Small", ref="C2", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_buck_in_hf.fields["LCSC"] = "NONE"
    c_buck_in_hf.fields["info"] = "Use at least 25V rating; this is the high-frequency bypass for the 2S LiPo buck input."
    design_intent(c_buck_in_hf, "High-frequency bypass at AP63205 VIN.", group="5V buck", placement="Place directly beside U2 VIN/GND pins, inside the input current loop.")
    vbus += c_buck_in_hf[1]
    gnd += c_buck_in_hf[2]

    c_boot = Part("Device", "C_Small", ref="C3", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_boot.fields["LCSC"] = "NONE"
    c_boot.fields["info"] = "Bootstrap capacitor between BST and SW; 10V or higher ceramic is sufficient for the AP63205 gate drive bootstrap voltage."
    design_intent(c_boot, "AP63205 bootstrap capacitor.", group="5V buck", placement="Place immediately between U2 BST and SW pins.")
    bst += c_boot[1]
    sw += c_boot[2]

    c_buck_out1 = Part("Device", "C_Small", ref="C4", value="22uF", footprint="Capacitor_SMD:C_0805_2012Metric")
    c_buck_out1.fields["LCSC"] = "NONE"
    c_buck_out1.fields["info"] = "Use 10V or 16V X5R/X7R ceramic to retain capacitance under 5V DC bias."
    design_intent(c_buck_out1, "AP63205 5V output capacitor, first of two 22uF ceramics.", group="5V buck", placement="Place from 5V to GND near L1 output and U2 ground return.")
    v5 += c_buck_out1[1]
    gnd += c_buck_out1[2]

    c_buck_out2 = Part("Device", "C_Small", ref="C5", value="22uF", footprint="Capacitor_SMD:C_0805_2012Metric")
    c_buck_out2.fields["LCSC"] = "NONE"
    c_buck_out2.fields["info"] = "Use 10V or 16V X5R/X7R ceramic to retain capacitance under 5V DC bias."
    design_intent(c_buck_out2, "AP63205 5V output capacitor, second of two 22uF ceramics.", group="5V buck", placement="Place from 5V to GND near L1 output and U2 ground return.")
    v5 += c_buck_out2[1]
    gnd += c_buck_out2[2]

    c_3v3_bulk = Part("Device", "C_Small", ref="C6", value="10uF", footprint="Capacitor_SMD:C_0603_1608Metric")
    c_3v3_bulk.fields["LCSC"] = "NONE"
    c_3v3_bulk.fields["info"] = "Use 6.3V or higher ceramic with DC-bias margin on the XIAO 3V3 output rail."
    design_intent(c_3v3_bulk, "Local bulk capacitor for 3V3 sensors, MCP23S17, piezo clamp reference, and level-shifter control logic.", group="3V3 rail", placement="Place near the cluster of 3V3 loads, not at the buck switching node.")
    v3v3 += c_3v3_bulk[1]
    gnd += c_3v3_bulk[2]

    u_exp = Part("Library", "MCP23S17T-E_SS", ref="U3", value="MCP23S17T-E/SS", footprint="Library:SSOP-28_L10.2-W5.3-P0.65-LS7.8-BL")
    u_exp.fields["LCSC"] = "C128577"
    u_exp.fields["info"] = "3.3V SPI GPIO expander. GPIOs default to inputs/high-Z at reset; external pull-ups on IMU CS and LED_OE_N make boot state safe. I_DD max 1mA at 1MHz SPI from datasheet; use slower expander writes than IMU data SPI if current must be bounded by this spec."
    design_intent(u_exp, "SPI GPIO expander that creates active-low IMU chip-selects and LED buffer enable from the pin-limited XIAO RP2350.", group="SPI chip-select expander", placement="Place near XIAO/SPI fanout; keep CS_A/CS_B/CS_C routes away from the buck switch node.")
    v3v3 += u_exp[9]
    gnd += u_exp[10], u_exp[15], u_exp[16], u_exp[17]
    exp_cs_n += u_exp[11]
    spi_sck += u_exp[12]
    spi_mosi += u_exp[13]
    spi_miso += u_exp[14]
    v3v3 += u_exp[18]
    cs_a += u_exp[21]
    cs_b += u_exp[22]
    cs_c += u_exp[23]
    led_oe_n += u_exp[24]
    u_exp[9].set_current_sink(0.001)
    u_exp[1] += NC
    u_exp[2] += NC
    u_exp[3] += NC
    u_exp[4] += NC
    u_exp[5] += NC
    u_exp[6] += NC
    u_exp[7] += NC
    u_exp[8] += NC
    u_exp[19] += NC
    u_exp[20] += NC
    u_exp[25] += NC
    u_exp[26] += NC
    u_exp[27] += NC
    u_exp[28] += NC

    c_exp = Part("Device", "C_Small", ref="C7", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_exp.fields["LCSC"] = "NONE"
    c_exp.fields["info"] = "6.3V or higher ceramic MCP23S17 local bypass."
    design_intent(c_exp, "MCP23S17 3V3 decoupling capacitor.", group="SPI chip-select expander", placement="Place directly at U3 VDD/VSS pins.")
    v3v3 += c_exp[1]
    gnd += c_exp[2]

    r_exp_cs = Part("Device", "R_Small", ref="R1", value="10kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_exp_cs.fields["LCSC"] = "NONE"
    design_intent(r_exp_cs, "Pull-up keeps MCP23S17 SPI chip-select inactive while the XIAO boots.", group="SPI chip-select expander", placement="Place near U3 CS pin.")
    v3v3 += r_exp_cs[1]
    exp_cs_n += r_exp_cs[2]

    r_led_oe = Part("Device", "R_Small", ref="R2", value="10kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_led_oe.fields["LCSC"] = "NONE"
    design_intent(r_led_oe, "Pull-up disables 5V LED level-shifter outputs until firmware enables them through U3 GPA3.", group="Status LED", placement="Place near the level-shifter OE pins.")
    v3v3 += r_led_oe[1]
    led_oe_n += r_led_oe[2]

    r_cs_a = Part("Device", "R_Small", ref="R3", value="10kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_cs_a.fields["LCSC"] = "NONE"
    design_intent(r_cs_a, "Boot-safe pull-up for active-low IMU-A chip select while MCP23S17 GPIO is high-Z.", group="IMU SPI", placement="Place near U4 CS pin or expander output fanout.")
    v3v3 += r_cs_a[1]
    cs_a += r_cs_a[2]

    r_cs_b = Part("Device", "R_Small", ref="R4", value="10kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_cs_b.fields["LCSC"] = "NONE"
    design_intent(r_cs_b, "Boot-safe pull-up for active-low IMU-B chip select while MCP23S17 GPIO is high-Z.", group="IMU SPI", placement="Place near U5 CS pin or expander output fanout.")
    v3v3 += r_cs_b[1]
    cs_b += r_cs_b[2]

    r_cs_c = Part("Device", "R_Small", ref="R5", value="10kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_cs_c.fields["LCSC"] = "NONE"
    design_intent(r_cs_c, "Boot-safe pull-up for active-low IMU-C chip select while MCP23S17 GPIO is high-Z.", group="IMU SPI", placement="Place near U6 CS pin or expander output fanout.")
    v3v3 += r_cs_c[1]
    cs_c += r_cs_c[2]

    imu_a = Part("Library", "H3LIS331DLTR", ref="U4", value="H3LIS331DLTR", footprint="Library:LGA-16_L3.0-W3.0-P0.50-BL")
    imu_a.fields["LCSC"] = "C2655074"
    imu_a.fields["info"] = "SPI mode: Vdd_IO pin 1 and Vdd pin 14 to 3V3, reserved pin 10 to GND, reserved pin 15 to Vdd, INT pins unused/NC. Datasheet gives typical 300uA normal-mode supply current but no maximum; rail budget is therefore not fully current-verified for IMUs. Axis intent: +X points toward pins 1-4 edge, +Y toward pins 5-8 edge."
    design_intent(imu_a, "IMU-A high-G accelerometer at nominal 0°/East, inner radius target 12mm; X axis radial outward and Y axis tangential.", group="IMU array", placement="Place centroid at r=12mm, angle 0°. Orient pin 1 so +X is radial outward per datasheet axis diagram.")
    v3v3 += imu_a[1], imu_a[14], imu_a[15]
    gnd += imu_a[5], imu_a[10], imu_a[12], imu_a[13], imu_a[16]
    spi_sck += imu_a[4]
    spi_mosi += imu_a[6]
    miso_a += imu_a[7]
    cs_a += imu_a[8]
    imu_a[2] += NC
    imu_a[3] += NC
    imu_a[9] += NC
    imu_a[11] += NC

    c_imu_a = Part("Device", "C_Small", ref="C8", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_imu_a.fields["LCSC"] = "NONE"
    c_imu_a.fields["info"] = "Use 6.3V or higher ceramic at H3LIS331DL Vdd."
    design_intent(c_imu_a, "Local Vdd decoupling for IMU-A.", group="IMU array", placement="Place as close as possible to U4 pin 14 and nearby ground pins.")
    v3v3 += c_imu_a[1]
    gnd += c_imu_a[2]

    r_miso_a = Part("Device", "R_Small", ref="R6", value="33Ω", footprint="Resistor_SMD:R_0402_1005Metric")
    r_miso_a.fields["LCSC"] = "NONE"
    design_intent(r_miso_a, "Series isolation resistor from IMU-A SDO to shared MISO to limit bus-contention current and ringing.", group="IMU SPI", placement="Place close to U4 SDO pin.")
    miso_a += r_miso_a[1]
    spi_miso += r_miso_a[2]

    imu_b = Part("Library", "H3LIS331DLTR", ref="U5", value="H3LIS331DLTR", footprint="Library:LGA-16_L3.0-W3.0-P0.50-BL")
    imu_b.fields["LCSC"] = "C2655074"
    imu_b.fields["info"] = "SPI mode: Vdd_IO pin 1 and Vdd pin 14 to 3V3, reserved pin 10 to GND, reserved pin 15 to Vdd, INT pins unused/NC. Datasheet gives typical 300uA normal-mode supply current but no maximum; rail budget is therefore not fully current-verified for IMUs. Axis intent: +X points toward pins 1-4 edge, +Y toward pins 5-8 edge."
    design_intent(imu_b, "IMU-B high-G accelerometer at nominal 90°/North, outer radius target from spec; X axis radial outward and Y axis tangential.", group="IMU array", placement="Spec target r=20mm/angle 90° exceeds a 35mm circular board radius; place per revised board outline and keep within sensor G limit. Orient pin 1 for radial +X.")
    v3v3 += imu_b[1], imu_b[14], imu_b[15]
    gnd += imu_b[5], imu_b[10], imu_b[12], imu_b[13], imu_b[16]
    spi_sck += imu_b[4]
    spi_mosi += imu_b[6]
    miso_b += imu_b[7]
    cs_b += imu_b[8]
    imu_b[2] += NC
    imu_b[3] += NC
    imu_b[9] += NC
    imu_b[11] += NC

    c_imu_b = Part("Device", "C_Small", ref="C9", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_imu_b.fields["LCSC"] = "NONE"
    c_imu_b.fields["info"] = "Use 6.3V or higher ceramic at H3LIS331DL Vdd."
    design_intent(c_imu_b, "Local Vdd decoupling for IMU-B.", group="IMU array", placement="Place as close as possible to U5 pin 14 and nearby ground pins.")
    v3v3 += c_imu_b[1]
    gnd += c_imu_b[2]

    r_miso_b = Part("Device", "R_Small", ref="R7", value="33Ω", footprint="Resistor_SMD:R_0402_1005Metric")
    r_miso_b.fields["LCSC"] = "NONE"
    design_intent(r_miso_b, "Series isolation resistor from IMU-B SDO to shared MISO to limit bus-contention current and ringing.", group="IMU SPI", placement="Place close to U5 SDO pin.")
    miso_b += r_miso_b[1]
    spi_miso += r_miso_b[2]

    imu_c = Part("Library", "H3LIS331DLTR", ref="U6", value="H3LIS331DLTR", footprint="Library:LGA-16_L3.0-W3.0-P0.50-BL")
    imu_c.fields["LCSC"] = "C2655074"
    imu_c.fields["info"] = "SPI mode: Vdd_IO pin 1 and Vdd pin 14 to 3V3, reserved pin 10 to GND, reserved pin 15 to Vdd, INT pins unused/NC. Datasheet gives typical 300uA normal-mode supply current but no maximum; rail budget is therefore not fully current-verified for IMUs. Axis intent: +X points toward pins 1-4 edge, +Y toward pins 5-8 edge."
    design_intent(imu_c, "IMU-C high-G accelerometer at nominal 210°, outer radius target from spec; asymmetric placement breaks heading singularities.", group="IMU array", placement="Spec target r=20mm/angle 210° exceeds a 35mm circular board radius; place per revised board outline and keep within sensor G limit. Orient pin 1 for radial +X.")
    v3v3 += imu_c[1], imu_c[14], imu_c[15]
    gnd += imu_c[5], imu_c[10], imu_c[12], imu_c[13], imu_c[16]
    spi_sck += imu_c[4]
    spi_mosi += imu_c[6]
    miso_c += imu_c[7]
    cs_c += imu_c[8]
    imu_c[2] += NC
    imu_c[3] += NC
    imu_c[9] += NC
    imu_c[11] += NC

    c_imu_c = Part("Device", "C_Small", ref="C10", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_imu_c.fields["LCSC"] = "NONE"
    c_imu_c.fields["info"] = "Use 6.3V or higher ceramic at H3LIS331DL Vdd."
    design_intent(c_imu_c, "Local Vdd decoupling for IMU-C.", group="IMU array", placement="Place as close as possible to U6 pin 14 and nearby ground pins.")
    v3v3 += c_imu_c[1]
    gnd += c_imu_c[2]

    r_miso_c = Part("Device", "R_Small", ref="R8", value="33Ω", footprint="Resistor_SMD:R_0402_1005Metric")
    r_miso_c.fields["LCSC"] = "NONE"
    design_intent(r_miso_c, "Series isolation resistor from IMU-C SDO to shared MISO to limit bus-contention current and ringing.", group="IMU SPI", placement="Place close to U6 SDO pin.")
    miso_c += r_miso_c[1]
    spi_miso += r_miso_c[2]

    r_vbat_hi = Part("Device", "R_Small", ref="R9", value="100kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_vbat_hi.fields["LCSC"] = "NONE"
    design_intent(r_vbat_hi, "High-side resistor for 2S LiPo voltage divider to XIAO A0; 8.4V maps to about 2.08V.", group="Battery voltage sense", placement="Place near XIAO A0 with short ADC node; high side can route from VBUS after switch.")
    vbus += r_vbat_hi[1]
    vbat_sense += r_vbat_hi[2]

    r_vbat_lo = Part("Device", "R_Small", ref="R10", value="33kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_vbat_lo.fields["LCSC"] = "NONE"
    design_intent(r_vbat_lo, "Low-side resistor for battery voltage divider to XIAO A0.", group="Battery voltage sense", placement="Place adjacent to R9 and C12 at the ADC node.")
    vbat_sense += r_vbat_lo[1]
    gnd += r_vbat_lo[2]

    c_vbat = Part("Device", "C_Small", ref="C12", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_vbat.fields["LCSC"] = "NONE"
    c_vbat.fields["info"] = "6.3V or higher ceramic; ADC node sees about 2.08V maximum at 8.4V battery."
    design_intent(c_vbat, "Noise filter capacitor on VBAT ADC divider output.", group="Battery voltage sense", placement="Place at XIAO A0 / VBAT_SNS node.")
    vbat_sense += c_vbat[1]
    gnd += c_vbat[2]

    j_piezo = Part("Connector_Generic", "Conn_01x02", ref="J3", value="Piezo fly-lead", footprint="Connector_Wire:SolderWire-0.25sqmm_1x02_P4.2mm_D0.65mm_OD1.7mm_Relief")
    j_piezo.fields["LCSC"] = "NONE"
    design_intent(j_piezo, "Fly-lead connector to 20mm chassis-bonded piezo contact sensor: pin 1 signal, pin 2 GND.", group="Piezo impact sensor", placement="Place near radial wire exit and keep PIEZO trace short to clamp network and XIAO A2.")
    piezo += j_piezo[1]
    gnd += j_piezo[2]

    r_piezo = Part("Device", "R_Small", ref="R11", value="1MΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_piezo.fields["LCSC"] = "NONE"
    design_intent(r_piezo, "DC pulldown for piezo ADC input so it cannot float between impacts.", group="Piezo impact sensor", placement="Place at XIAO A2 / PIEZO node, next to clamp diode.")
    piezo += r_piezo[1]
    gnd += r_piezo[2]

    c_piezo = Part("Device", "C_Small", ref="C13", value="10nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_piezo.fields["LCSC"] = "NONE"
    c_piezo.fields["info"] = "6.3V or higher ceramic; forms the specified piezo input filter with the 1MΩ pulldown."
    design_intent(c_piezo, "Piezo impact sensor input filter capacitor.", group="Piezo impact sensor", placement="Place at XIAO A2 / PIEZO node, before long/noisy routing.")
    piezo += c_piezo[1]
    gnd += c_piezo[2]

    d_piezo = Part("Diode", "BAT54S", ref="D1", value="BAT54S", footprint="Package_TO_SOT_SMD:SOT-23")
    d_piezo.fields["LCSC"] = "C19726"
    d_piezo.fields["info"] = "BAT54S series Schottky pair used as rail clamps: pin 1 anode to GND, pin 3 common to PIEZO, pin 2 cathode to 3V3. Clamps negative and positive piezo spikes before the ADC pin."
    design_intent(d_piezo, "Schottky rail clamp protecting XIAO A2 from high-voltage piezo impact spikes.", group="Piezo impact sensor", placement="Place at the XIAO A2 / PIEZO node before the trace leaves the analog protection cluster.")
    gnd += d_piezo[1]
    v3v3 += d_piezo[2]
    piezo += d_piezo[3]

    j_head = Part("Connector_Generic", "Conn_01x02", ref="J2", value="Orange TinySLED", footprint="Connector_Wire:SolderWire-0.25sqmm_1x02_P4.2mm_D0.65mm_OD1.7mm_Relief")
    j_head.fields["LCSC"] = "NONE"
    j_head.fields["info"] = "External orange Tiny's LEDs 2-3S Micro LED heading marker: pin 1 switched 2S VBUS feed, pin 2 low-side switched return through Q1. Module is 2-3S capable with onboard current limiting; do not add series LED resistor unless the selected module variant requires it."
    design_intent(j_head, "Off-board orange 2-3S TinySLED heading LED mounted near the physical front/rim for phase-locked meltybrain strobing.", group="Heading LED", placement="Place at the radial wire exit closest to the front LED mount; route VBUS/HEAD_SW as a pulsed LED current loop away from IMU and analog sense nodes.")
    vbus += j_head[1]
    head_sw += j_head[2]

    q_head = Part("Library", "AO3402_C14385", ref="Q1", value="AO3402", footprint="Library:SOT-23_L2.9-W1.3-P1.90-LS2.4-BR")
    q_head.fields["LCSC"] = "C14385"
    q_head.fields["info"] = "AO3402 30V N-channel MOSFET used as low-side switch for external orange 2-3S TinySLED heading LED. Gate is driven from XIAO edge pin D1/A1 through 100Ω with 100kΩ pulldown. Firmware must cap pulse width and keep the LED off by default because TinySLED modules can get hot if left on."
    design_intent(q_head, "Low-side switch for the orange 2-3S TinySLED meltybrain heading marker.", group="Heading LED", placement="Place near J2; provide a short source return to ground and keep the pulsed LED current loop away from IMUs.")
    head_gate += q_head[1]
    gnd += q_head[2]
    head_sw += q_head[3]

    r_head_gate = Part("Device", "R_Small", ref="R16", value="100Ω", footprint="Resistor_SMD:R_0402_1005Metric")
    r_head_gate.fields["LCSC"] = "NONE"
    design_intent(r_head_gate, "Gate stopper between XIAO D1/A1 and Q1 for the orange TinySLED heading switch.", group="Heading LED", placement="Place close to Q1 gate.")
    head_led += r_head_gate[1]
    head_gate += r_head_gate[2]

    r_head_pd = Part("Device", "R_Small", ref="R17", value="100kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_head_pd.fields["LCSC"] = "NONE"
    design_intent(r_head_pd, "Gate pulldown holding the orange TinySLED heading MOSFET off while the RP2350 boots or resets.", group="Heading LED", placement="Place close to Q1 gate/source.")
    head_gate += r_head_pd[1]
    gnd += r_head_pd[2]

    r_ds1 = Part("Device", "R_Small", ref="R12", value="33Ω", footprint="Resistor_SMD:R_0402_1005Metric")
    r_ds1.fields["LCSC"] = "NONE"
    design_intent(r_ds1, "Series damping resistor for Repeat AM32 dual ESC channel 1 bidirectional DSHOT/EDT line.", group="DSHOT outputs", placement="Place at the PCB wire-exit side of the route, before J4.")
    dshot1_io += r_ds1[1]
    dshot1 += r_ds1[2]

    r_ds2 = Part("Device", "R_Small", ref="R13", value="33Ω", footprint="Resistor_SMD:R_0402_1005Metric")
    r_ds2.fields["LCSC"] = "NONE"
    design_intent(r_ds2, "Series damping resistor for Repeat AM32 dual ESC channel 2 bidirectional DSHOT/EDT line.", group="DSHOT outputs", placement="Place at the PCB wire-exit side of the route, before J4.")
    dshot2_io += r_ds2[1]
    dshot2 += r_ds2[2]

    j_esc = Part("Connector_Generic", "Conn_01x04", ref="J4", value="AM32 dual ESC", footprint="Connector_Wire:SolderWire-0.25sqmm_1x04_P4.2mm_D0.65mm_OD1.7mm_Relief")
    j_esc.fields["LCSC"] = "NONE"
    j_esc.fields["info"] = "Signal harness to Repeat AM32 Dual Brushless Drive ESC: pin 1 GND, pin 2 DSHOT1/white channel bidirectional DSHOT+EDT, pin 3 DSHOT2/yellow channel bidirectional DSHOT+EDT, pin 4 GND. ESC BEC output is intentionally not connected to the carrier 5V rail in this revision."
    design_intent(j_esc, "Combined signal connector for Repeat AM32 dual ESC; two direct RP2350 bidirectional DSHOT/EDT lines with ground returns.", group="DSHOT outputs", placement="Route as one short harness toward the dual ESC signal wires; keep away from motor phase wires and the buck SW node.")
    gnd += j_esc[1]
    dshot1 += j_esc[2]
    dshot2 += j_esc[3]
    gnd += j_esc[4]

    j_elrs = Part("Connector_Generic", "Conn_01x04", ref="J6", value="ELRS receiver", footprint="Connector_Wire:SolderWire-0.25sqmm_1x04_P4.2mm_D0.65mm_OD1.7mm_Relief")
    j_elrs.fields["LCSC"] = "NONE"
    design_intent(j_elrs, "Fly-leads to off-board ELRS receiver: 3V3, GND, CRSF TX, CRSF RX.", group="CRSF receiver", placement="Route to chassis-wall receiver mount for antenna clearance; keep away from buck inductor and switch node.")
    v3v3 += j_elrs[1]
    gnd += j_elrs[2]
    crsf_tx += j_elrs[3]
    crsf_rx += j_elrs[4]

    u_led_mosi = Part("Library", "SN74AHCT1G125DCKR", ref="U8", value="SN74AHCT1G125", footprint="Library:SC-70-5_L2.0-W1.3-P0.65-LS2.1-BL")
    u_led_mosi.fields["LCSC"] = "C350557"
    u_led_mosi.fields["info"] = "AHCT input threshold Vih min 2.0V at 5V VCC, so 3.3V RP2350/MCP logic is valid. Static ICC max 10uA plus ΔICC up to 1.5mA with 3.3V input high; budget 1.51mA. OE is active-low and driven by LED_OE_N."
    design_intent(u_led_mosi, "5V AHCT buffer/level shifter for APA102/SK9822 data input.", group="Status LED", placement="Place near U10 LED input pins; keep the 5V output trace short.")
    led_oe_n += u_led_mosi[1]
    spi_mosi += u_led_mosi[2]
    gnd += u_led_mosi[3]
    led_di += u_led_mosi[4]
    v5 += u_led_mosi[5]
    u_led_mosi[5].set_current_sink(0.00151)

    c_led_mosi = Part("Device", "C_Small", ref="C14", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_led_mosi.fields["LCSC"] = "NONE"
    c_led_mosi.fields["info"] = "6.3V or higher ceramic local bypass for 5V AHCT buffer."
    design_intent(c_led_mosi, "Decoupling capacitor for U8 MOSI level shifter.", group="Status LED", placement="Place at U8 VCC/GND pins.")
    v5 += c_led_mosi[1]
    gnd += c_led_mosi[2]

    u_led_sck = Part("Library", "SN74AHCT1G125DCKR", ref="U9", value="SN74AHCT1G125", footprint="Library:SC-70-5_L2.0-W1.3-P0.65-LS2.1-BL")
    u_led_sck.fields["LCSC"] = "C350557"
    u_led_sck.fields["info"] = "AHCT input threshold Vih min 2.0V at 5V VCC, so 3.3V RP2350/MCP logic is valid. Static ICC max 10uA plus ΔICC up to 1.5mA with 3.3V input high; budget 1.51mA. OE is active-low and driven by LED_OE_N."
    design_intent(u_led_sck, "5V AHCT buffer/level shifter for APA102/SK9822 clock input.", group="Status LED", placement="Place near U10 LED input pins; keep the 5V output trace short and paired with LED_DI where practical.")
    led_oe_n += u_led_sck[1]
    spi_sck += u_led_sck[2]
    gnd += u_led_sck[3]
    led_ck += u_led_sck[4]
    v5 += u_led_sck[5]
    u_led_sck[5].set_current_sink(0.00151)

    c_led_sck = Part("Device", "C_Small", ref="C15", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_led_sck.fields["LCSC"] = "NONE"
    c_led_sck.fields["info"] = "6.3V or higher ceramic local bypass for 5V AHCT buffer."
    design_intent(c_led_sck, "Decoupling capacitor for U9 SCK level shifter.", group="Status LED", placement="Place at U9 VCC/GND pins.")
    v5 += c_led_sck[1]
    gnd += c_led_sck[2]

    r_led_di_pd = Part("Device", "R_Small", ref="R14", value="100kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_led_di_pd.fields["LCSC"] = "NONE"
    design_intent(r_led_di_pd, "Weak pulldown holds SK9822 data input quiet while AHCT buffer output is disabled/high-Z.", group="Status LED", placement="Place near U10 SDI pin.")
    led_di += r_led_di_pd[1]
    gnd += r_led_di_pd[2]

    r_led_ck_pd = Part("Device", "R_Small", ref="R15", value="100kΩ", footprint="Resistor_SMD:R_0402_1005Metric")
    r_led_ck_pd.fields["LCSC"] = "NONE"
    design_intent(r_led_ck_pd, "Weak pulldown holds SK9822 clock input quiet while AHCT buffer output is disabled/high-Z.", group="Status LED", placement="Place near U10 CKI/CKL pin.")
    led_ck += r_led_ck_pd[1]
    gnd += r_led_ck_pd[2]

    led = Part("Library", "SK9822-EC20", ref="U10", value="SK9822-EC20", footprint="Library:LED-SMD_6P-L2.0-W2.0-P0.80-TL")
    led.fields["LCSC"] = "C2909059"
    led.fields["info"] = "2x2mm APA102-compatible two-wire addressable LED. Powered from 5V; budget 61mA worst-case full white including control IC. Inputs are fed by 5V AHCT buffers because 5V CMOS VIH may exceed 3.3V."
    design_intent(led, "Top-visible status LED for boot, RC, spin, heading lock, drift, low battery, impact, and failsafe indications.", group="Status LED", placement="Place visible from the chassis top window, away from the buck inductor and high-G edge stress risers.")
    led[1] += NC
    gnd += led[2]
    led_di += led[3]
    led_ck += led[4]
    v5 += led[5]
    led[6] += NC
    led[5].set_current_sink(0.061)

    c_led = Part("Device", "C_Small", ref="C16", value="100nF", footprint="Capacitor_SMD:C_0402_1005Metric")
    c_led.fields["LCSC"] = "NONE"
    c_led.fields["info"] = "Use 6.3V or higher ceramic at SK9822 5V VDD."
    design_intent(c_led, "Local decoupling for the 5V SK9822/APA102 status LED.", group="Status LED", placement="Place directly at U10 VDD/GND pins.")
    v5 += c_led[1]
    gnd += c_led[2]

    tp_sck = Part("Connector", "TestPoint", ref="TP1", value="TP_SCK", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_sck.fields["LCSC"] = "NONE"
    design_intent(tp_sck, "Scope/logic-analyzer pad for shared SPI clock.", group="Production test", placement="Place along SPI fanout where accessible by probe.")
    spi_sck += tp_sck[1]

    tp_cs_a = Part("Connector", "TestPoint", ref="TP2", value="TP_CS_A", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_cs_a.fields["LCSC"] = "NONE"
    design_intent(tp_cs_a, "Scope pad for IMU-A active-low chip-select.", group="Production test", placement="Place near U4 or expander CS fanout.")
    cs_a += tp_cs_a[1]

    tp_cs_b = Part("Connector", "TestPoint", ref="TP3", value="TP_CS_B", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_cs_b.fields["LCSC"] = "NONE"
    design_intent(tp_cs_b, "Scope pad for IMU-B active-low chip-select.", group="Production test", placement="Place near U5 or expander CS fanout.")
    cs_b += tp_cs_b[1]

    tp_cs_c = Part("Connector", "TestPoint", ref="TP4", value="TP_CS_C", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_cs_c.fields["LCSC"] = "NONE"
    design_intent(tp_cs_c, "Scope pad for IMU-C active-low chip-select.", group="Production test", placement="Place near U6 or expander CS fanout.")
    cs_c += tp_cs_c[1]

    tp_miso = Part("Connector", "TestPoint", ref="TP5", value="TP_MISO", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_miso.fields["LCSC"] = "NONE"
    design_intent(tp_miso, "Scope/logic-analyzer pad for shared SPI MISO after IMU series resistors.", group="Production test", placement="Place along SPI bus where accessible by probe.")
    spi_miso += tp_miso[1]

    tp_ds1 = Part("Connector", "TestPoint", ref="TP6", value="TP_DS1", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_ds1.fields["LCSC"] = "NONE"
    design_intent(tp_ds1, "Scope pad for AM32 channel 1 bidirectional DSHOT/EDT signal after series resistor.", group="Production test", placement="Place near J4 wire exit.")
    dshot1 += tp_ds1[1]

    tp_ds2 = Part("Connector", "TestPoint", ref="TP7", value="TP_DS2", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_ds2.fields["LCSC"] = "NONE"
    design_intent(tp_ds2, "Scope pad for AM32 channel 2 bidirectional DSHOT/EDT signal after series resistor.", group="Production test", placement="Place near J4 wire exit.")
    dshot2 += tp_ds2[1]

    tp_crsf_rx = Part("Connector", "TestPoint", ref="TP8", value="TP_CRSF_RX", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_crsf_rx.fields["LCSC"] = "NONE"
    design_intent(tp_crsf_rx, "Scope pad for CRSF packets from ELRS receiver into XIAO RX.", group="Production test", placement="Place near J6 and away from the buck SW node.")
    crsf_rx += tp_crsf_rx[1]

    tp_crsf_tx = Part("Connector", "TestPoint", ref="TP9", value="TP_CRSF_TX", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_crsf_tx.fields["LCSC"] = "NONE"
    design_intent(tp_crsf_tx, "Scope pad for CRSF telemetry from XIAO TX to ELRS receiver.", group="Production test", placement="Place near J6 and away from the buck SW node.")
    crsf_tx += tp_crsf_tx[1]

    tp_vbat = Part("Connector", "TestPoint", ref="TP10", value="TP_VBAT", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_vbat.fields["LCSC"] = "NONE"
    design_intent(tp_vbat, "Probe pad for scaled battery voltage ADC node.", group="Production test", placement="Place next to the divider and label clearly TP_VBAT.")
    vbat_sense += tp_vbat[1]

    tp_head = Part("Connector", "TestPoint", ref="TP11", value="TP_HEAD", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_head.fields["LCSC"] = "NONE"
    design_intent(tp_head, "Scope pad for the orange TinySLED meltybrain heading strobe GPIO before the MOSFET gate resistor.", group="Production test", placement="Place near Q1/R16 so firmware strobe timing can be checked at 4000rpm without loading the LED current path.")
    head_led += tp_head[1]

    tp_piezo = Part("Connector", "TestPoint", ref="TP12", value="TP_PIEZO", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_piezo.fields["LCSC"] = "NONE"
    design_intent(tp_piezo, "Probe pad for protected piezo ADC node.", group="Production test", placement="Place near clamp network and XIAO A2.")
    piezo += tp_piezo[1]

    tp_swdio = Part("Connector", "TestPoint", ref="TP13", value="TP_SWDIO", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_swdio.fields["LCSC"] = "NONE"
    design_intent(tp_swdio, "Picoprobe SWDIO debug pad for XIAO RP2350.", group="Production test", placement="Place with TP_SWDCK and TP_GND as a small SWD probe cluster.")
    swdio += tp_swdio[1]

    tp_swdck = Part("Connector", "TestPoint", ref="TP14", value="TP_SWDCK", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_swdck.fields["LCSC"] = "NONE"
    design_intent(tp_swdck, "Picoprobe SWD clock debug pad for XIAO RP2350.", group="Production test", placement="Place with TP_SWDIO and TP_GND as a small SWD probe cluster.")
    swdck += tp_swdck[1]

    tp_gnd = Part("Connector", "TestPoint", ref="TP15", value="TP_GND", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_gnd.fields["LCSC"] = "NONE"
    design_intent(tp_gnd, "Ground reference test pad for oscilloscope/logic analyzer.", group="Production test", placement="Place adjacent to signal test pads where probe ground can reach.")
    gnd += tp_gnd[1]

    tp_3v3 = Part("Connector", "TestPoint", ref="TP16", value="TP_3V3", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_3v3.fields["LCSC"] = "NONE"
    design_intent(tp_3v3, "3.3V rail probe pad to verify XIAO regulator output under sensor and receiver load.", group="Production test", placement="Place near 3V3 load cluster and accessible from top.")
    v3v3 += tp_3v3[1]

    tp_5v = Part("Connector", "TestPoint", ref="TP17", value="TP_5V", footprint="TestPoint:TestPoint_Pad_D1.0mm")
    tp_5v.fields["LCSC"] = "NONE"
    design_intent(tp_5v, "5V buck output probe pad to verify AP63205 output under load.", group="Production test", placement="Place near buck output capacitors and accessible from top.")
    v5 += tp_5v[1]

    for part, info in [
        (j_pwr, "Two-pad solder-wire input for switched 2S LiPo VBUS and GND feeding the carrier buck regulator."),
        (r_exp_cs, "10kΩ pull-up that keeps the MCP23S17 SPI chip-select inactive while the XIAO RP2350 boots."),
        (r_led_oe, "10kΩ pull-up that disables the AHCT LED level shifters until firmware intentionally enables LED SPI traffic."),
        (r_cs_a, "10kΩ pull-up that keeps IMU-A chip-select inactive while the MCP23S17 GPIO defaults to high impedance."),
        (r_cs_b, "10kΩ pull-up that keeps IMU-B chip-select inactive while the MCP23S17 GPIO defaults to high impedance."),
        (r_cs_c, "10kΩ pull-up that keeps IMU-C chip-select inactive while the MCP23S17 GPIO defaults to high impedance."),
        (r_miso_a, "33Ω series resistor from IMU-A SDO to the shared MISO bus for ringing and bus-contention limiting."),
        (r_miso_b, "33Ω series resistor from IMU-B SDO to the shared MISO bus for ringing and bus-contention limiting."),
        (r_miso_c, "33Ω series resistor from IMU-C SDO to the shared MISO bus for ringing and bus-contention limiting."),
        (r_vbat_hi, "100kΩ high-side resistor of the 2S battery voltage divider feeding XIAO A0."),
        (r_vbat_lo, "33kΩ low-side resistor of the 2S battery voltage divider feeding XIAO A0."),
        (j_piezo, "Two-pad solder-wire connector for the off-board chassis-mounted piezo disc signal and ground."),
        (r_piezo, "1MΩ pulldown that biases the piezo ADC input to ground between impact events."),
        (j_head, "Two-pad solder-wire connector for the external orange 2-3S TinySLED heading marker: switched VBUS feed and MOSFET-switched return."),
        (r_head_gate, "100Ω gate stopper from XIAO edge pin D1/A1 to the orange TinySLED MOSFET gate."),
        (r_head_pd, "100kΩ pulldown keeping the orange TinySLED MOSFET off during boot/reset."),
        (r_ds1, "33Ω series damping resistor on AM32 channel 1 bidirectional DSHOT/EDT near the fly-lead exit."),
        (r_ds2, "33Ω series damping resistor on AM32 channel 2 bidirectional DSHOT/EDT near the fly-lead exit."),
        (j_esc, "Four-pad solder-wire connector for Repeat AM32 dual ESC: GND, DSHOT1, DSHOT2, GND; ESC BEC intentionally not connected."),
        (j_elrs, "Four-pad solder-wire connector for the off-board ELRS receiver: 3V3, GND, CRSF TX, and CRSF RX."),
        (r_led_di_pd, "100kΩ pulldown that holds the 5V SK9822 data input quiet when the AHCT buffer is disabled."),
        (r_led_ck_pd, "100kΩ pulldown that holds the 5V SK9822 clock input quiet when the AHCT buffer is disabled."),
        (tp_sck, "1mm test pad for probing the shared SPI clock waveform."),
        (tp_cs_a, "1mm test pad for probing IMU-A active-low chip-select."),
        (tp_cs_b, "1mm test pad for probing IMU-B active-low chip-select."),
        (tp_cs_c, "1mm test pad for probing IMU-C active-low chip-select."),
        (tp_miso, "1mm test pad for probing shared SPI MISO after the IMU series resistors."),
        (tp_ds1, "1mm test pad for probing AM32 channel 1 bidirectional DSHOT/EDT after the series resistor."),
        (tp_ds2, "1mm test pad for probing AM32 channel 2 bidirectional DSHOT/EDT after the series resistor."),
        (tp_crsf_rx, "1mm test pad for probing CRSF packets arriving from the ELRS receiver."),
        (tp_crsf_tx, "1mm test pad for probing CRSF telemetry transmitted to the ELRS receiver."),
        (tp_vbat, "1mm test pad for measuring the scaled battery-voltage ADC node."),
        (tp_head, "1mm test pad for checking orange TinySLED heading strobe timing before the MOSFET gate resistor."),
        (tp_piezo, "1mm test pad for measuring the protected piezo impact-sensor ADC node."),
        (tp_swdio, "1mm test pad for XIAO RP2350 SWDIO debug access."),
        (tp_swdck, "1mm test pad for XIAO RP2350 SWD clock debug access."),
        (tp_gnd, "1mm test pad providing oscilloscope and logic-analyzer ground reference."),
        (tp_3v3, "1mm test pad for checking the XIAO-provided 3.3V rail."),
        (tp_5v, "1mm test pad for checking the AP63205 5.0V buck output rail."),
    ]:
        part.fields["info"] = info
