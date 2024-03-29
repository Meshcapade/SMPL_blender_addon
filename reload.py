import bpy
import importlib
import sys

addon_name = "meshcapade"
module = "meshcapade_addon"
parts_to_reload = [
    "blender",
    "globals",
    "operators",
    "properties",
    "meshcapade_addon",
    "ui",
]

for part in parts_to_reload:
    # Unregister the addon
    if addon_name in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_disable(module=addon_name)

    # Reload the addon modules
    module_name = f"{addon_name}.{module}.{part}"
    importlib.reload(sys.modules[module_name])

    # Register the addon again
    bpy.ops.preferences.addon_enable(module=addon_name)