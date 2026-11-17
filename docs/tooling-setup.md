# Tooling setup

Target version: **KiCad 10.x** (10.0.8 as of 2026-11-11). KiCad 10 files do not open in older versions.

---

## 1. CachyOS / Arch Linux (Berten)

```bash
sudo pacman -S kicad kicad-library kicad-library-3d
kicad-cli version            # must be 10.x
```

**Do not use the Flatpak version.** It lacks `pip` and `requests`, which the JLC plugin needs.

## 2. Windows (alternative)

```powershell
winget install KiCad.KiCad
```

## 3. Ubuntu 24.04 (Claude Code container or CI)

Ubuntu's default repository only has KiCad 7, which is **not usable**. Use the official PPA:

```bash
sudo add-apt-repository -y ppa:kicad/kicad-10.0-releases
sudo apt-get update
sudo apt-get install -y --no-install-recommends kicad
kicad-cli version
```

Tested on 2026-11-11: the PPA was reachable from the cloud environment. Without a GUI, `kicad-cli` is sufficient.

---

## 4. easyeda2kicad (importing parts by LCSC number)

```bash
pipx install easyeda2kicad          # or: pip install --user easyeda2kicad
easyeda2kicad --full --lcsc_id=C719095 --output lib/nexus
```

- `--full` fetches symbol, footprint and 3D model.
- Everything ends up in `lib/nexus.kicad_sym`, `lib/nexus.pretty/` and `lib/nexus.3dshapes/`.
- **Check every footprint** against the datasheet (see CLAUDE.md §7.5).

Adding the library to the project (project-specific library tables `sym-lib-table` / `fp-lib-table` next to the `.kicad_pro` file):

```
(sym_lib_table
  (lib (name "nexus")(type "KiCad")(uri "${KIPRJMOD}/../lib/nexus.kicad_sym")(options "")(descr ""))
)
(fp_lib_table
  (lib (name "nexus")(type "KiCad")(uri "${KIPRJMOD}/../lib/nexus.pretty")(options "")(descr ""))
)
```

---

## 5. kicad-jlcpcb-tools (GUI plugin, for Berten)

1. In KiCad, open **Plugin and Content Manager → Manage repositories**.
2. Add: `https://raw.githubusercontent.com/Bouni/bouni-kicad-repository/main/repository.json`
3. Install **KiCad JLCPCB tools**.

With it you can search and assign LCSC numbers, set rotation corrections and generate Gerbers, BOM and CPL in the project's `jlcpcb/` folder. The plugin supports KiCad 7 to 10.

---

## 6. Freerouting (autorouter)

- Requires Java 21+ (`sudo pacman -S jre-openjdk` or `apt install openjdk-21-jre`).
- Download the latest release jar from github.com/freerouting/freerouting.
- Workflow: export a Specctra DSN from KiCad, run Freerouting headless, import the SES:
  ```bash
  java -jar freerouting.jar -de board.dsn -do board.ses -mp 20
  ```
- **Signal nets only.** Lay out power nets and polygons by hand first and lock them.

---

## 7. KiKit (optional: panelization and JLC export)

```bash
pipx install kikit
kikit fab jlcpcb --assembly --schematic toolboard/toolboard.kicad_sch toolboard/toolboard.kicad_pcb fab/rev-A/toolboard
```

**First check that KiKit supports KiCad 10.** If it does not, use `kicad-cli` for Gerbers, drill and position file, plus a custom script that converts the BOM and CPL to the JLC format.

---

## 8. Useful `kicad-cli` commands

```bash
# ERC / DRC
kicad-cli sch erc --severity-all --exit-code-violations -o out/erc.rpt toolboard/toolboard.kicad_sch
kicad-cli pcb drc --severity-all --exit-code-violations --schematic-parity -o out/drc.rpt toolboard/toolboard.kicad_pcb

# Schematic as PDF
kicad-cli sch export pdf -o out/toolboard-schematic.pdf toolboard/toolboard.kicad_sch

# PCB layers as SVG or 3D render (PNG) for review
kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts -o out/toolboard-top.svg toolboard/toolboard.kicad_pcb
kicad-cli pcb render --side top -o out/toolboard-3d-top.png toolboard/toolboard.kicad_pcb

# BOM
kicad-cli sch export bom --fields "Reference,Value,Footprint,LCSC,MPN,Assembly,\${QUANTITY}" --group-by "LCSC,Value,Footprint" -o out/bom.csv toolboard/toolboard.kicad_sch

# Production
kicad-cli pcb export gerbers -o fab/rev-A/toolboard/gerber/ toolboard/toolboard.kicad_pcb
kicad-cli pcb export drill   -o fab/rev-A/toolboard/gerber/ toolboard/toolboard.kicad_pcb
kicad-cli pcb export pos --format csv --units mm --side both -o fab/rev-A/toolboard/pos.csv toolboard/toolboard.kicad_pcb
```

Options may differ between KiCad versions. Check with `kicad-cli <cmd> --help`.

---

## 9. `.gitignore`

```
out/
*-backups/
*.lck
fp-info-cache
*.kicad_prl
_autosave-*
\#auto_saved_files#
```
