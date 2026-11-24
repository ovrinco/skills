# Optional application frontends

A GUI or application framework receives input, calls the same typed library operation and presents its result. Keep database state and product rules in that library. Test the library behavior without a window, then test the actual frontend entry and error presentation separately.

For a Tauri front, register the command at the framework boundary and serialize the typed result. For a Qt/QML front, expose an adapter with the same operation and retain a documented error surface. The receiving project selects its framework and runtime. This example does not bring a GUI dependency into the dependency-free crate.
