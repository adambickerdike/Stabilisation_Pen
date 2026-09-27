#!/usr/bin/env python3
"""Rev A research electronics: declarative circuit specification.

Status: PROPOSED DESIGN (development draft, not released for fabrication).
Nothing here has been built or measured.  Values marked VERIFY must be checked
against the named datasheet or reference design before layout; parts marked
SELECT are placeholders for a parameter class, not a chosen part number.

Design decisions carried by this circuit (see docs/decisions.md and
electronics/README.md):
  * nRF5340 in normal-voltage, LDO-only mode (DCC/DCCD/DCCH unconnected): no
    switching regulator next to the Hall and current-sense front ends; the
    few mA of LDO penalty are small against ~0.1-0.5 W of actuator load.
  * Two DRV8212P H-bridges (IN/IN PWM), one per stage axis, fed from the
    cell through a load switch (VMOT) that is ANDed in hardware with a latched
    over-current fault and a charging interlock.
  * In-line shunt (0.1 ohm) + INA241A1 (G = 10, enhanced PWM rejection)
    referenced to a 1.25 V reference; SAADC reads ISNS_x - VREF differentially.
  * One 3-axis Hall sensor (TMAG5170) at the lever tail gives both stage
    angles (x, y) and the axial slide (z -> axial force through k_ax).
  * ADS1220 + strain-gauge bridge and DRV5055 analog Hall sensors are DNP
    alternatives for bench experiments.

Run:  python3 electronics/gen/design_revA.py   (writes electronics/kicad/)
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kicad_gen import Generator, Part, Sheet, SymbolLib  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "kicad")

FP_R = "Resistor_SMD:R_0402_1005Metric"
FP_R0603 = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0402_1005Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_L = "Inductor_SMD:L_0402_1005Metric"
FP_TP = "TestPoint:TestPoint_Pad_D1.0mm"
FP_JST2 = "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal"
FP_JST4 = "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal"
FP_FPC7 = "Connector_FFC-FPC:TE_0-1734839-7_1x07-1MP_P0.5mm_Horizontal"
FP_WIRE = "Connector_Wire:SolderWirePad_1x01_SMD_1x2mm"


def R(ref, value, a, b, fp=FP_R, dnp=False, **fields):
    return Part(ref, "Device:R", value, fp, {"#1": a, "#2": b}, dict(fields), dnp)


def C(ref, value, a, b, fp=FP_C, dnp=False, **fields):
    return Part(ref, "Device:C", value, fp, {"#1": a, "#2": b}, dict(fields), dnp)


def TP(ref, net):
    return Part(ref, "Connector:TestPoint", net, FP_TP, {"#1": net})


def WP(ref, net, label):
    """Solder pad for a flying lead (battery, coils, NTC, ERM): zero height, no connector body."""
    return Part(ref, "Connector:TestPoint", label, FP_WIRE, {"#1": net}, {"Board": "main"})


def V(text):
    return {"Verify": text}


# ============================================================ sheets
def sheet_power_charge():
    s = Sheet("power_charge", "power_charge.kicad_sch", "USB-C input, ESD, Li-ion charger")
    s.parts += [
        Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C receptacle (USB 2.0)",
             "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
             {"VBUS": "VBUS", "GND": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_DP", "D-": "USB_DM",
              "SBU1": "NC", "SBU2": "NC", "SHIELD": "GND"},
             {"MPN": "TYPE-C-31-M-12", "Manufacturer": "HRO", **V("mid-mount height vs 11 mm board width")}),
        R("R1", "5k1", "CC1", "GND", Tolerance="1%"),
        R("R2", "5k1", "CC2", "GND", Tolerance="1%"),
        Part("U1", "Power_Protection:USBLC6-2P6", "USBLC6-2P6", "Package_TO_SOT_SMD:SOT-666",
             {"I/O1": "USB_DP", "I/O2": "USB_DM", "GND": "GND", "VBUS": "VBUS"},
             {"MPN": "USBLC6-2P6", "Manufacturer": "STMicroelectronics"}),
        Part("U2", "Battery_Management:MCP73831-2-OT", "MCP73831-2-OT", "Package_TO_SOT_SMD:SOT-23-5",
             {"V_{DD}": "VBUS", "V_{SS}": "GND", "V_{BAT}": "VBAT", "PROG": "CHG_PROG", "STAT": "CHG_STAT"},
             {"MPN": "MCP73831T-2ACI/OT", "Manufacturer": "Microchip",
              **V("4.20 V variant; charge current 1000/R_PROG[kohm] mA -> 147 mA (0.7 C of 200 mAh)")}),
        R("R3", "6k8", "CHG_PROG", "GND", Tolerance="1%"),
        R("R4", "100k", "CHG_STAT", "+3V0"),
        C("C1", "4u7", "VBUS", "GND", Voltage="10V"),
        C("C2", "4u7", "VBAT", "GND", Voltage="6.3V"),
        R("R5", "100k", "VBUS", "CHG_DET", Tolerance="1%"),
        R("R6", "100k", "CHG_DET", "GND", Tolerance="1%"),
    ]
    s.pwr_flags = ["VBUS", "GND"]
    s.notes = [
        "CHG_DET = VBUS/2 (2.37-2.62 V for 4.75-5.25 V VBUS): valid logic high at VDD 3.0 V, below VDD+0.3 V.",
        "CHG_DET also drives the charging interlock (sheet fault_handling): actuation is disabled while VBUS is present.",
        "Charge current 147 mA (R3): check against the selected cell's 0.5-1 C limit and the 43 C skin limit.",
    ]
    return s


def sheet_battery_supply():
    s = Sheet("battery_supply", "battery_supply.kicad_sch", "Cell protection, 3.0 V LDO, actuator load switch, reference")
    s.parts += [
        WP("TP20", "VBAT", "cell +"),
        WP("TP21", "CELL_NEG", "cell -"),
        Part("U3", "Battery_Management:BQ297xy", "BQ29700", "Package_SON:WSON-6_1.5x1.5mm_P0.5mm",
             {"BAT": "BQ_BAT", "VSS": "CELL_NEG", "V-": "BQ_VM", "Dout": "DSG_G", "Cout": "CHG_G"},
             {"MPN": "BQ29700DSER", "Manufacturer": "Texas Instruments",
              **V("variant thresholds (OVP/UVP/OCD) vs cell; X2SON/WSON package code")}),
        R("R7", "330", "VBAT", "BQ_BAT"),
        C("C3", "100n", "BQ_BAT", "CELL_NEG"),
        R("R8", "2k2", "BQ_VM", "GND"),
        Part("Q1", "Device:Q_NMOS_GSD", "NMOS 20V <=30mR@2.5V (DSG)", "Package_TO_SOT_SMD:SOT-23",
             {"G": "DSG_G", "S": "CELL_NEG", "D": "PROT_MID"}, {**V("SELECT: common-drain dual NMOS in one package preferred")}),
        Part("Q2", "Device:Q_NMOS_GSD", "NMOS 20V <=30mR@2.5V (CHG)", "Package_TO_SOT_SMD:SOT-23",
             {"G": "CHG_G", "S": "GND", "D": "PROT_MID"}, {**V("SELECT: see Q1")}),
        Part("U4", "Regulator_Linear:TLV75530PDBV", "TLV75530PDBV", "Package_TO_SOT_SMD:SOT-23-5",
             {"IN": "VBAT", "EN": "VBAT", "GND": "GND", "OUT": "+3V0"},
             {"MPN": "TLV75530PDBVR", "Manufacturer": "Texas Instruments"}),
        C("C4", "1u", "VBAT", "GND"),
        C("C5", "1u", "+3V0", "GND"),
        Part("FB1", "Device:FerriteBead", "600R@100MHz", "Inductor_SMD:L_0402_1005Metric",
             {"#1": "+3V0", "#2": "+3V0A"}, {**V("DCR <= 0.5 ohm at 30 mA")}),
        C("C6", "1u", "+3V0A", "GND"),
        C("C7", "100n", "+3V0A", "GND"),
        Part("U5", "Power_Management:TPS22917DBV", "TPS22917DBV", "Package_TO_SOT_SMD:SOT-23-6",
             {"VIN": "VBAT", "GND": "GND", "ON": "ACT_EN", "CT": "LS_CT", "QOD": "LS_QOD", "VOUT": "VMOT"},
             {"MPN": "TPS22917DBVR", "Manufacturer": "Texas Instruments",
              **V("2 A continuous, Ron ~80 mOhm at 3.6 V; QOD to VOUT = fastest discharge")}),
        R("R16", "0R", "LS_QOD", "VMOT", **V("QOD-to-VOUT link; a resistor here slows output discharge")),
        C("C8", "1n", "LS_CT", "GND", **V("sets VMOT slew; check inrush into 2 x 10 uF")),
        C("C9", "1u", "VBAT", "GND"),
        R("R9", "470k", "VBAT", "VBAT_SENSE", Tolerance="0.5%"),
        R("R10", "470k", "VBAT_SENSE", "GND", Tolerance="0.5%"),
        C("C10", "100n", "VBAT_SENSE", "GND"),
        Part("U6", "Reference_Voltage:REF3012", "REF3012", "Package_TO_SOT_SMD:SOT-23",
             {"IN": "+3V0A", "OUT": "VREF_1V25", "GND": "GND"},
             {"MPN": "REF3012AIDBZR", "Manufacturer": "Texas Instruments",
              **V("output capacitor range for stability; load = 2 x INA241 REF + SAADC input")}),
        C("C11", "1n", "VREF_1V25", "GND", **V("REF3012 capacitive-load limit")),
    ]
    s.pwr_flags = ["CELL_NEG", "+3V0A"]
    s.notes = [
        "Cell: LiPo pouch >= 5 C continuous, ~200 mAh (5 x 12 x 32 mm class, VERIFY); omit U3/Q1/Q2 if the cell carries its own PCM.",
        "VBAT 3.0-4.2 V. +3V0 LDO keeps logic regulated down to ~3.05 V cell voltage; below that it tracks VBAT.",
        "VMOT = VBAT through U5 only when ACT_EN is high (hardware AND of request, no latched fault, not charging).",
        "Actuation cut-off in firmware at VBAT < 3.3 V (config electrical.v_bat_min); U3 is the last-resort UVP.",
    ]
    return s


def sheet_mcu():
    s = Sheet("mcu", "mcu.kicad_sch", "nRF5340: clocks, RF, USB, debug", paper="A2")
    nrf = {
        "VDD": "+3V0", "VDDH": "+3V0", "VSS": "GND", "VBUS": "VBUS", "D+": "USB_DP", "D-": "USB_DM",
        "DECUSB": "DECUSB", "DCCH": "NC", "DCC": "NC", "DCCD": "NC",
        "DECA": "DECA", "DECD": "DECD", "DECN": "DECN", "DECR": "DECR", "DECRF": "DECRF",
        "XC1": "XC1", "XC2": "XC2", "ANT": "ANT_RF", "SWDCLK": "SWDCLK", "SWDIO": "SWDIO", "~{RESET}": "NRESET",
        "XL1/P0.00": "XL1", "XL2/P0.01": "XL2",
        "NFC1/P0.02": "ADC_DRDY_N", "NFC2/P0.03": "ADC_CS_N",
        "AIN0/P0.04": "ISNS_X", "AIN1/P0.05": "ISNS_Y", "AIN2/P0.06": "VBAT_SENSE", "AIN3/P0.07": "NTC_COIL",
        "SCK/TRACEDATA3/P0.08": "SPIA_SCK_M", "MOSI/TRACEDATA2/P0.09": "SPIA_MOSI_M", "MISO/TRACEDATA1/P0.10": "SPIA_MISO",
        "CSN/TRACEDATA0/P0.11": "HALL_CS_N", "DCX/TRACECLK/P0.12": "OPT1_CS_N",
        "IO0/P0.13": "QSPI_IO0", "IO1/P0.14": "QSPI_IO1", "IO2/P0.15": "QSPI_IO2", "IO3/P0.16": "QSPI_IO3",
        "SCK/P0.17": "QSPI_SCK", "CSN/P0.18": "QSPI_CS_N",
        "P0.19": "IN1_X", "P0.20": "IN2_X", "P0.21": "IN1_Y", "P0.22": "IN2_Y", "P0.23": "DRV_SLEEP_N",
        "P0.24": "ACT_EN_REQ", "AIN4/P0.25": "VREF_ADC", "AIN5/P0.26": "HALL_AN_X", "AIN6/P0.27": "HALL_AN_Y",
        "AIN7/P0.28": "AIN7_SPARE", "P0.29": "OPT2_CS_N", "P0.30": "OPT3_CS_N", "P0.31": "OPT_IRQ",
        "P1.00": "IMU_INT1", "P1.01": "IMU_CS_N", "TWI/P1.02": "SPIB_SCK", "TWI/P1.03": "SPIB_MOSI", "P1.04": "SPIB_MISO",
        "P1.05": "UART_TX", "P1.06": "UART_RX", "P1.07": "FAULT_N", "P1.08": "BTN_MODE", "P1.09": "LED_STAT",
        "P1.10": "CHG_STAT", "P1.11": "HAPTIC_EN", "P1.12": "FAULT_CLR_N", "P1.13": "HALL_ALERT_N",
        "P1.14": "CHG_DET", "P1.15": "IMU_INT2",
    }
    s.parts += [
        Part("U7", "MCU_Nordic:nRF5340-QKxx", "nRF5340-QKAA", "Package_DFN_QFN:Nordic_AQFN-94-1EP_7x7mm_P0.4mm", nrf,
             {"MPN": "NRF5340-QKAA-R7", "Manufacturer": "Nordic Semiconductor",
              **V("decoupling values and DEC-pin wiring against nRF5340 PS reference circuitry (LDO-only, normal voltage mode); "
                  "P0.02/P0.03 as GPIO need UICR.NFCPINS = 0")}),
        C("C12", "4u7", "+3V0", "GND", **V("Nordic ref.")),
        C("C13", "100n", "+3V0", "GND"), C("C14", "100n", "+3V0", "GND"), C("C15", "100n", "+3V0", "GND"),
        C("C16", "4u7", "DECUSB", "GND", **V("Nordic ref.")),
        C("C17", "100n", "DECA", "GND", **V("Nordic ref.")),
        C("C18", "100n", "DECD", "GND", **V("Nordic ref.")),
        C("C19", "100n", "DECN", "GND", **V("Nordic ref.")),
        C("C20", "1u", "DECR", "GND", **V("Nordic ref.")),
        C("C21", "100n", "DECRF", "GND", **V("Nordic ref.")),
        Part("Y1", "Device:Crystal_GND24", "32MHz", "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm",
             {"#1": "XC1", "#3": "XC2", "#2": "GND", "#4": "GND"},
             {**V("CL within nRF5340 internal HFXO load-cap range; +/-40 ppm total for BLE")}),
        Part("Y2", "Device:Crystal", "32.768kHz", "Crystal:Crystal_SMD_2012-2Pin_2.0x1.2mm",
             {"#1": "XL1", "#2": "XL2"}, {**V("CL 7-9 pF (internal LFXO caps)")}),
        Part("L1", "Device:L", "RF match L", FP_L, {"#1": "ANT_RF", "#2": "ANT_M"}, {**V("Nordic ref. matching value")}),
        C("C22", "RF match C", "ANT_M", "GND", **V("Nordic ref. matching value")),
        R("R11", "0R", "ANT_M", "ANT_FEED", **V("antenna pi-pad series; tune with VNA on assembled pen")),
        C("C23", "DNP", "ANT_M", "GND", dnp=True), C("C24", "DNP", "ANT_FEED", "GND", dnp=True),
        Part("AE1", "Device:Antenna_Chip", "2450AT18A100", "RF_Antenna:Johanson_2450AT18x100",
             {"FEED": "ANT_FEED", "PCB_Trace": "NC"},
             {"MPN": "2450AT18A100E", "Manufacturer": "Johanson Technology", **V("keep-out and ground clearance in a 15 mm metal-free tail")}),
        Part("J3", "Connector:Conn_ARM_SWD_TagConnect_TC2030-NL", "TC2030-NL", "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
             {"VCC": "+3V0", "SWDIO": "SWDIO", "~{RESET}": "NRESET", "SWCLK": "SWDCLK", "GND": "GND", "SWO": "NC"},
             {"Board": "main", **V("pads only (zero height); needs 3 locating holes inside an 11.5 mm board")}),
        R("R17", "10k", "NRESET", "+3V0"),
        R("R18", "100", "VREF_1V25", "VREF_ADC", **V("isolates SAADC sampling kick-back from the INA241 REF pins")),
        C("C34", "10n", "VREF_ADC", "GND", **V("C0G")),
        R("R12", "33", "SPIA_SCK_M", "SPIA_SCK", **V("series termination for 60 mm flex to optics; tune from SI check")),
        R("R13", "33", "SPIA_MOSI_M", "SPIA_MOSI"),
    ]
    s.notes = [
        "LDO-only, normal-voltage mode: VDDH = VDD = +3V0; DCC, DCCD, DCCH left open (no DC/DC inductors).",
        "SAADC: ISNS_X/ISNS_Y read differentially against AIN4 = VREF_ADC (VREF_1V25 via 100 ohm/10 nF); sampling triggered by PWM via DPPI.",
        "SPIM4 (P0.08-P0.12, up to 32 MHz) serves the Hall sensor and optics; SPIB (P1.02-P1.04) serves IMU and optional ADC.",
    ]
    return s


def sheet_sensing():
    s = Sheet("sensing", "sensing.kicad_sch", "IMU, optical tracking modules, coil temperature")
    s.parts += [
        Part("U8", "Sensor_Motion:LSM6DSM", "LSM6DSV16X", "Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
             {"SDO/SA0": "SPIB_MISO", "SDX": "GND", "SCX": "GND", "INT1": "IMU_INT1", "VDDIO": "+3V0", "GND": "GND",
              "VDD": "+3V0", "INT2": "IMU_INT2", "OCS_Aux": "NC", "SDO_Aux": "NC", "CS": "IMU_CS_N",
              "SCL": "SPIB_SCK", "SDA": "SPIB_MOSI"},
             {"MPN": "LSM6DSV16XTR", "Manufacturer": "STMicroelectronics",
              **V("LSM6DSM symbol used as LGA-14 placeholder: confirm LSM6DSV16X pins 2, 3, 10, 11 functions and unused-pin handling")}),
        C("C25", "100n", "+3V0", "GND"), C("C26", "100n", "+3V0", "GND"),
    ]
    for k, cs in ((1, "OPT1_CS_N"), (2, "OPT2_CS_N"), (3, "OPT3_CS_N")):
        s.parts.append(Part(f"J{3 + k}", "Connector_Generic_MountingPin:Conn_01x07_MountingPin", f"optical module {k}", FP_FPC7,
                            {"Pin_1": "+3V0", "Pin_2": "GND", "Pin_3": "SPIA_SCK", "Pin_4": "SPIA_MOSI", "Pin_5": "SPIA_MISO",
                             "Pin_6": cs, "Pin_7": "OPT_IRQ", "MountPin": "NC"},
                            {**V("module interface pending sensor selection (EXP-S01); 3 modules at 30/150/270 deg, z = 14.2 mm")}))
    s.parts += [
        WP("TP22", "NTC_COIL", "NTC a"),
        WP("TP23", "GND", "NTC b"),
        R("R14", "10k", "+3V0A", "NTC_COIL", Tolerance="0.5%"),
        C("C27", "100n", "NTC_COIL", "GND"),
    ]
    s.notes = [
        "NTC 10k (B25/85 ~3435 K) bonded to the coil former; ratiometric SAADC read (REFSEL VDD/4, gain 1/4).",
        "Optical modules share SPIM4 with the Hall sensor; OPT_IRQ is a shared open-drain motion interrupt (VERIFY per module).",
    ]
    return s


def sheet_force():
    s = Sheet("force", "force.kicad_sch", "Optional strain-gauge axial force channel (DNP)")
    s.parts += [
        Part("U9", "Analog_ADC:ADS1220xPW", "ADS1220IPW", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
             {"SCLK": "SPIB_SCK", "~{CS}": "ADC_CS_N", "CLK": "GND", "DGND": "GND", "AVSS": "GND", "AIN3/REFN1": "NC",
              "AIN2": "NC", "REFN0": "GND", "REFP0": "+3V0A", "AIN1": "BRIDGE_N", "AIN0/REFP1": "BRIDGE_P",
              "AVDD": "+3V0A", "DVDD": "+3V0", "~{DRDY}": "ADC_DRDY_N", "DOUT/~{DRDY}": "SPIB_MISO", "DIN": "SPIB_MOSI"},
             {"MPN": "ADS1220IPWR", "Manufacturer": "Texas Instruments"}, dnp=True),
        C("C28", "100n", "+3V0A", "GND", dnp=True), C("C29", "100n", "+3V0", "GND", dnp=True),
        C("C30", "10n", "BRIDGE_P", "BRIDGE_N", dnp=True, **V("differential RC with bridge output resistance")),
        Part("J8", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "strain bridge", FP_JST4,
             {"Pin_1": "+3V0A", "Pin_2": "BRIDGE_P", "Pin_3": "BRIDGE_N", "Pin_4": "GND", "MountPin": "NC"}, {}, dnp=True),
    ]
    s.notes = [
        "Primary axial force = TMAG5170 z channel x k_ax (sheet stage_position). This channel is a bench reference only.",
        "Ratiometric bridge: excitation +3V0A is also REFP0/REFN0, so supply drift cancels.",
    ]
    return s


def sheet_stage_position():
    s = Sheet("stage_position", "stage_position.kicad_sch", "Stage angle and axial slide sensing (3-axis Hall)")
    s.parts += [
        Part("U10", "Sensor_Magnetic:TMAG5170-Q1", "TMAG5170A1", "Package_SO:VSSOP-8_3x3mm_P0.65mm",
             {"SCLK": "SPIA_SCK", "MOSI": "SPIA_MOSI", "MISO": "SPIA_MISO", "~{CS}": "HALL_CS_N", "VCC": "+3V0A",
              "GND": "GND", "TEST": "GND", "~{ALERT}": "HALL_ALERT_N"},
             {"MPN": "TMAG5170A1QDGKR", "Manufacturer": "Texas Instruments",
              **V("range variant (A1 +/-25..100 mT vs A2) from magnet field map; TEST pin handling; mounted on tail flex")}),
        C("C31", "100n", "+3V0A", "GND"),
        R("R15", "10k", "HALL_ALERT_N", "+3V0"),
        Part("U11", "Sensor_Magnetic:DRV5055A1xDBZxQ1", "DRV5055A1", "Package_TO_SOT_SMD:SOT-23",
             {"VCC": "+3V0A", "OUT": "HALL_AN_X", "GND": "GND"}, {**V("ratiometric; 3.0 V supply below 3.3 V min? check")}, dnp=True),
        Part("U12", "Sensor_Magnetic:DRV5055A1xDBZxQ1", "DRV5055A1", "Package_TO_SOT_SMD:SOT-23",
             {"VCC": "+3V0A", "OUT": "HALL_AN_Y", "GND": "GND"}, {}, dnp=True),
        C("C32", "100n", "+3V0A", "GND", dnp=True), C("C33", "100n", "+3V0A", "GND", dnp=True),
    ]
    s.notes = [
        "TMAG5170 at the lever tail reads a sense magnet on the carrier: Bx, By -> stage angles; Bz -> axial slide s -> F_ax = F_pre + k_ax s.",
        "Cross-axis and actuator-field coupling calibrated on the bench (EXP-B04); sample mid-PWM to avoid coil-field ripple.",
    ]
    return s


def sheet_actuator(axis):
    ax = axis.upper()
    s = Sheet(f"actuator_{axis}", f"actuator_{axis}.kicad_sch", f"Stage actuator channel {ax}: H-bridge, shunt, current sense, window comparator")
    base = {"x": 0, "y": 20}[axis]
    rr = lambda i: f"R{30 + base + i}"   # noqa: E731
    cc = lambda i: f"C{40 + base + i}"   # noqa: E731
    uu = lambda i: f"U{13 + (0 if axis == 'x' else 4) + i}"  # noqa: E731
    s.parts += [
        Part(uu(0), "Driver_Motor:DRV8212P", "DRV8212PDSG", "Package_SON:WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm_ThermalVias",
             {"VM": "VMOT", "OUT1": f"OUT1_{ax}", "OUT2": f"OUT2_{ax}", "GND": "GND", "IN1": f"IN1_{ax}", "IN2": f"IN2_{ax}",
              "~{SLEEP}": "DRV_SLEEP_N", "VCC": "+3V0"},
             {"MPN": "DRV8212PDSGR", "Manufacturer": "Texas Instruments",
              **V("Rds(on) HS+LS, PWM frequency limit, input pull-downs, OCP threshold")}),
        C(cc(0), "10u", "VMOT", "GND", fp=FP_C0603, Voltage="6.3V"),
        C(cc(1), "100n", "VMOT", "GND"),
        C(cc(2), "100n", "+3V0", "GND"),
        R(rr(0), "0R1", f"OUT1_{ax}", f"COIL_{ax}_P", fp=FP_R0603, Tolerance="1%", Power="0.1W", **V("sense shunt, <= 50 ppm/K")),
        Part(uu(1), "Amplifier_Current:INA241A1xDDF", "INA241A1", "Package_TO_SOT_SMD:SOT-23-8",
             {"#8": f"OUT1_{ax}", "#1": f"COIL_{ax}_P", "GND": "GND", "REF1": "VREF_1V25", "REF2": "VREF_1V25",
              "#5": f"ISNS_{ax}_RAW", "V+": "+3V0A"},
             {"MPN": "INA241A1IDDFR", "Manufacturer": "Texas Instruments",
              **V("G = 10 V/V; CM range and PWM transient recovery at 3-4.2 V VMOT; REF pin load on REF3012")}),
        C(cc(3), "100n", "+3V0A", "GND"),
        R(rr(1), "1k", f"ISNS_{ax}_RAW", f"ISNS_{ax}"),
        C(cc(4), "10n", f"ISNS_{ax}", "GND", **V("C0G; 15.9 kHz anti-alias corner")),
        WP(f"TP{24 + (0 if axis == 'x' else 2)}", f"COIL_{ax}_P", f"coil {ax} +"),
        WP(f"TP{25 + (0 if axis == 'x' else 2)}", f"OUT2_{ax}", f"coil {ax} -"),
        Part(uu(2), "Comparator:LMV331", "LMV331", "Package_TO_SOT_SMD:SOT-353_SC-70-5",
             {"#1": "VTH_HI", "#3": f"ISNS_{ax}", "V-": "GND", "V+": "+3V0A", "#4": "OC_N"},
             {"MPN": "LMV331IDCKR", "Manufacturer": "Texas Instruments"}),
        Part(uu(3), "Comparator:LMV331", "LMV331", "Package_TO_SOT_SMD:SOT-353_SC-70-5",
             {"#1": f"ISNS_{ax}", "#3": "VTH_LO", "V-": "GND", "V+": "+3V0A", "#4": "OC_N"},
             {"MPN": "LMV331IDCKR", "Manufacturer": "Texas Instruments"}),
        C(cc(5), "100n", "+3V0A", "GND"),
    ]
    s.notes = [
        f"ISNS_{ax} = VREF_1V25 + 1.0 V/A x I_coil (0.1 ohm x 10); linear range +/-1.2 A; trip window +/-0.8 A (VTH_HI 2.05 V, VTH_LO 0.45 V).",
        "IN/IN drive: PWM on one input, other low = drive/brake (slow decay); both low + SLEEP low = coast. Centre-aligned PWM, current sampled at period centre.",
    ]
    return s


def sheet_storage_comm():
    s = Sheet("storage_comm", "storage_comm.kicad_sch", "QSPI flash and debug UART")
    s.parts += [
        Part("U21", "Memory_Flash:W25Q128JVP", "W25Q128JVPIQ", "Package_SON:WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4.3mm",
             {"~{CS}": "QSPI_CS_N", "DO(IO1)": "QSPI_IO1", "IO2": "QSPI_IO2", "GND": "GND", "DI(IO0)": "QSPI_IO0",
              "CLK": "QSPI_SCK", "IO3": "QSPI_IO3", "VCC": "+3V0"},
             {"MPN": "W25Q128JVPIQ", "Manufacturer": "Winbond", **V("QE bit default for quad mode; 2.7 V minimum VCC")}),
        C("C80", "100n", "+3V0", "GND"),
        R("R60", "10k", "QSPI_CS_N", "+3V0"),
        TP("TP1", "UART_TX"), TP("TP2", "UART_RX"),
    ]
    s.notes = [
        "16 MB: ~1 h of 200 Hz x 24 B product capture; research logging at 2 kHz streams over USB (bench) instead.",
    ]
    return s


def sheet_user_interface():
    s = Sheet("user_interface", "user_interface.kicad_sch", "Button, status LED, haptic ERM, test points")
    s.parts += [
        Part("SW1", "Switch:SW_Push", "mode button", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
             {"#1": "BTN_MODE", "#2": "GND"}, {}),
        Part("D1", "Device:LED", "green", "LED_SMD:LED_0402_1005Metric", {"A": "LED_A", "K": "LED_STAT"}, {}),
        R("R61", "1k", "+3V0", "LED_A"),
        WP("TP28", "VBAT", "ERM +"),
        WP("TP29", "ERM_N", "ERM -"),
        Part("Q3", "Device:Q_NMOS_GSD", "NMOS logic-level", "Package_TO_SOT_SMD:SOT-723",
             {"G": "HAPTIC_G", "S": "GND", "D": "ERM_N"}, {**V("SELECT: Vgs(th) < 1.0 V, Id >= 0.3 A")}),
        R("R62", "100", "HAPTIC_EN", "HAPTIC_G"),
        R("R63", "100k", "HAPTIC_G", "GND"),
        Part("D2", "Device:D_Schottky", "Schottky 0.5A", "Diode_SMD:D_SOD-523", {"K": "VBAT", "A": "ERM_N"}, {}),
    ]
    for i, net in enumerate(("VMOT", "+3V0", "+3V0A", "GND", "VBAT", "ISNS_X", "ISNS_Y", "VREF_1V25", "AIN7_SPARE")):
        s.parts.append(TP(f"TP{3 + i}", net))
    s.notes = ["ERM: coin vibration motor on flying leads (TP28/TP29); limit PWM duty to its rated voltage."]
    return s


def sheet_fault_handling():
    s = Sheet("fault_handling", "fault_handling.kicad_sch", "Hardware interlock: over-current latch, charge interlock, enable gate")
    s.parts += [
        Part("U22", "74xGxx:74AUP1G74", "74AUP1G74", "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
             {"C": "GND", "D": "GND", "~{Q}": "FAULT_N", "GND": "GND", "Q": "NC", "~{CLR}": "FAULT_CLR_N",
              "~{PRE}": "OC_N", "VCC": "+3V0"},
             {"MPN": "SN74AUP1G74DCUR", "Manufacturer": "Texas Instruments",
              **V("PRE and CLR both low gives Q = ~Q = high: firmware clears only with ACT_EN_REQ low")}),
        C("C70", "100n", "+3V0", "GND"),
        Part("U23", "74xGxx:74LVC1G11", "74LVC1G11", "Package_TO_SOT_SMD:SOT-363_SC-70-6",
             {"#1": "ACT_EN_REQ", "#3": "FAULT_N", "#6": "NOCHG", "#4": "ACT_EN", "GND": "GND", "VCC": "+3V0"},
             {"MPN": "SN74LVC1G11DCKR", "Manufacturer": "Texas Instruments"}),
        C("C71", "100n", "+3V0", "GND"),
        Part("Q4", "Device:Q_NMOS_GSD", "NMOS logic-level", "Package_TO_SOT_SMD:SOT-723",
             {"G": "CHG_DET", "S": "GND", "D": "NOCHG"}, {**V("SELECT: Vgs(th) max < 1.2 V (CHG_DET high = 2.37 V min)")}),
        R("R70", "100k", "NOCHG", "+3V0"),
        R("R71", "100k", "ACT_EN_REQ", "GND"),
        R("R72", "100k", "ACT_EN", "GND"),
        R("R73", "10k", "OC_N", "+3V0"),
        R("R74", "10k", "FAULT_CLR_N", "+3V0"),
        R("R75", "10k", "+3V0A", "VTH_HI", Tolerance="1%"),
        R("R76", "21k5", "VTH_HI", "GND", Tolerance="1%"),
        R("R77", "56k", "+3V0A", "VTH_LO", Tolerance="1%"),
        R("R78", "10k", "VTH_LO", "GND", Tolerance="1%"),
        C("C72", "100n", "VTH_HI", "GND"), C("C73", "100n", "VTH_LO", "GND"),
    ]
    s.notes = [
        "ACT_EN = ACT_EN_REQ AND FAULT_N AND NOCHG. Any comparator trip sets the latch (FAULT_N low) and opens VMOT within ~2 us + switch turn-off.",
        "Latch clear sequence (firmware): ACT_EN_REQ low -> pulse FAULT_CLR_N low 1 us -> read FAULT_N high -> ACT_EN_REQ high.",
        "Independent watchdog: MCU reset releases ACT_EN_REQ (R71 pull-down) and DRV_SLEEP_N (driver internal pull-down), so VMOT opens.",
        "Thresholds from +3V0A: VTH_HI = 2.048 V (+0.80 A), VTH_LO = 0.455 V (-0.80 A) about VREF 1.25 V.",
    ]
    return s


def build():
    sheets = [sheet_power_charge(), sheet_battery_supply(), sheet_mcu(), sheet_sensing(), sheet_force(),
              sheet_stage_position(), sheet_actuator("x"), sheet_actuator("y"), sheet_storage_comm(),
              sheet_user_interface(), sheet_fault_handling()]
    return sheets


ROOT_NOTES = [
    "Active stabilisation pen - research electronics Rev A.  PROPOSED DESIGN: not built, not measured.",
    "Every part marked VERIFY or SELECT in its fields must be checked against the named source before layout.",
    "Power tree: USB-C -> MCP73831 -> cell (BQ29700 + 2 NMOS) -> TLV75530 (+3V0, +3V0A) and TPS22917 (VMOT, gated).",
    "Calculations: electronics/calcs/drive_sense.py -> results/electronics/; ngspice drive stage: electronics/spice/.",
]


def main():
    lib = SymbolLib()
    gen = Generator(lib)
    sheets = build()
    refs = [p.ref for s in sheets for p in s.parts]
    dup = sorted({r for r in refs if refs.count(r) > 1})
    if dup:
        print("DUPLICATE REFERENCES:", dup)
        return 2
    issues = gen.write(sheets, OUT, ROOT_NOTES)
    print(f"library version {lib.version}; wrote {OUT}")
    for i in issues:
        print("ISSUE:", i)
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
