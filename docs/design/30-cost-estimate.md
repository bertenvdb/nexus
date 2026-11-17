# Nexus Tools Board — Prototype cost estimate (5 units)

| | |
|---|---|
| **Date** | 2026-11-17 |
| **Basis** | Architecture v1.6, detailed design part 1 v0.3, part 2 v0.4, part 3 v0.3 |
| **Scope** | Nexus Tools Board only. Nexus Docks Board, cables, panel connectors and PSU are not included. |
| **Status** | Estimate (±25 %). To be replaced by a real JLC quote once the BOM and Gerbers are ready. |

Amounts in USD, LCSC/JLC prices as of 2026-11-10.

## Per board

| Item | Per board |
|---|---|
| Parts placed by JLC | $10.67 |
| Parts you solder yourself (XT60, fuses, screw terminals, JST-XH) | $4.10 |

## Order of 5 boards

| Item | Amount |
|---|---|
| PCB 4 layers, ≈ 110 × 80 mm, 5 pcs | $15.00 |
| Setup + stencil (Economic PCBA) | $9.71 |
| Extended fee (≈ 11 unique parts × $3.07) | $33.77 |
| Placement (≈ 450 solder joints × 5) | $3.60 |
| MOQ surplus parts | $5.00 |
| Parts for JLC placement (5×) | $53.35 |
| Hand-soldered parts (5×) | $20.50 |
| JLC shipping (DHL) | $22.00 |
| LCSC shipping (hand-soldered parts) | $15.00 |
| **Subtotal** | **$177.93** |
| VAT 21 % (via IOSS at checkout) | $37.37 |
| **Total** | **≈ $215** |
| **Per board** | **≈ $43** |
| CAN populated (AD-12, v0.8): 2 Extended fees + ≈ $0.97 parts/board, incl. VAT | **+ ≈ $13–17** |
| **Total with CAN** | **≈ $230 (≈ $46 per board)** |
| Design additions 2026-11-11…17 (rail sense + bleeder, 8 extra filament motion inputs, signal ESD diodes, 14 diagnostic LEDs): ≈ $0.50 parts/board + possibly 1 extra Extended fee (signal ESD diode), incl. VAT | **+ ≈ $3–7** |
| **Current total** | **≈ $235 (≈ $47 per board)** |

## Assumptions and uncertainties

- **PCB:** board ≈ 110 × 80 mm, 4 layers, 1 oz. Above 100 × 100 mm or with 2 oz copper it gets more expensive ($+10–30).
- **Extended fee:** CAN connectors (THT), connectors and fuses are hand-soldered. If BAT54S, SMF30CA or the USB-C turn out to be Basic, the fee will be lower.
- **Setup coupon:** JLC regularly hands out coupons that cover the setup fee ($8). These are not included.
- **Shipping:** including the hand-soldered parts in the same shipment saves ≈ $15.
- **Not included:** cable-side plugs and crimp contacts (JST-XH housings, ferrules).

## Breakdown

| Block | Share |
|---|---|
| Parts | ≈ 41 % |
| Fixed order costs (PCB, setup, Extended fee) | ≈ 35 % |
| Shipping | ≈ 21 % |

About half of the cost is fixed per order. At 10 boards the price per board drops to roughly $28–30.
