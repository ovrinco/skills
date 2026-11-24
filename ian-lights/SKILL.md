---
name: ian-lights
description: Control an explicitly supported RGB hardware profile with preserved unrelated device state.
---

# Three-control RGB profile

This integration supports ASRock X870E Taichi Lite, two Corsair Vengeance RGB DDR5 modules, and LANCOOL 216/LAN216-1. Its three controls are RAM sticks, front-fan rings and front-fan centers. Confirm that hardware and wiring match before a write. The bundled wiring.json is a measured profile, not generic discovery.

The real Python control driver, QML panel, wiring and vendored OpenRGB transport are in assets/plugin. Status and presets use local settings. Explicit color writes connect to OpenRGB and preserve unrelated pixels. The fan profile swaps red/green and uses a whole-device buffer; RAM uses Direct mode. The tests assert these exact boundaries using synthetic devices.

Read references/profile.md before using the driver. The driver is source material for an integration, with no automatic installation. A system OpenRGB SDK server and the supported hardware are runtime requirements. Match the service and command integration to the destination setup before enabling it. State lives under the user's local state directory; keep existing presets separate and preserve them during upgrades.

Run python3 -m unittest discover -s assets/tests -p test_control.py for the actual software tests. They use temporary state and synthetic device buffers; no real hardware is contacted. Physical output must be observed separately. The long-suspend controller-sync problem remains unresolved and is not advertised as fixed.

The vendored openrgb-python transport retains its GPLv3 license and package metadata. First-party docs follow the repository license; third-party terms remain applicable. This supported profile is published for inspection and adaptation, not as a universal hardware driver.
