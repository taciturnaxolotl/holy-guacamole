"""(6b) hand calcs for the ring-ear joint: Ti M3 bolts, PA11 under the head, brass heat-sets. Inputs from fea_ears (per-ear force)."""
import numpy as np, math, os
ear = np.load('ears_earf.npy') if os.path.exists('ears_earf.npy') else None
Fe = np.linalg.norm(ear, axis=1).max() if ear is not None else 2333.
A3 = math.pi/4*2.387**2                      # M3 minor-diameter area, mm2 (fully threaded M3x20)
TAU_TI = 0.6*950                              # Ti-6Al-4V gr5 shear ultimate ~570 MPa
print(f"worst ear force (11 kN tooth hit, bolts-only path): {Fe:.0f} N")
dbl = 2*A3*TAU_TI
print(f"Ti M3, double shear (ear sandwiched between the halves): {dbl/1e3:.1f} kN -> FoS {dbl/Fe:.1f}")
# PA11 bearing on the bolt in the lower bore (z 3.3..12.1) and on the insert in the upper (16.9..25)
bl = Fe/2/(3.0*8.8); bu = Fe/2/(4.6*5.7)
print(f"nominal bore bearing if the bolts take it all: lower {bl:.0f} MPa, upper (via insert) {bu:.0f} MPa vs PA11 ~52 MPa yield")
# friction carried by the clamp before anything bears
for T_ in (0.3, 0.4, 0.6):
    P = T_*1e3/(0.2*3.0)
    head = P/(math.pi/4*(5.7**2-3.4**2)); wash = P/(math.pi/4*(7.0**2-3.4**2))
    print(f"torque {T_:.1f} N m -> preload ~{P:.0f} N | PA11 under button head {head:.0f} MPa, with a 7 mm washer {wash:.0f} MPa | friction per ear 2 faces x0.3: {2*0.3*P:.0f} N")
# heat-set: M3 x 5.7 brass knurled, OD ~4.6, in MJF PA11; knurl-shear estimate (efficiency 0.5-0.7 of the full cylinder)
Ash = math.pi*4.6*5.7; tau = 0.58*48
lo, hi = 0.5*Ash*tau, 0.7*Ash*tau
print(f"insert retention estimate {lo/1e3:.1f}-{hi/1e3:.1f} kN (knurl shear, PA11 tau ~{tau:.0f} MPa) -> pull test on a coupon to pin down")
# vertical hit on the ring: the 6 bolts are all that hold the halves together, insert loaded toward the head (into its seat)
m_low, m_tot = 0.235, 0.445
for Fv in (2000, 5000, 11000):
    tot = m_low/m_tot*Fv
    print(f"vertical ring hit {Fv/1e3:4.1f} kN -> bolt tension total {tot:.0f} N: {tot/6:.0f} N each if shared, ~{tot/2.5:.0f} N on the nearest bolt (+ preload)")
