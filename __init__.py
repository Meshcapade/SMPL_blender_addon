bl_info = {
    "name": "Meshcapade Blender Tools",
    "blender": (3, 5, 1),
    "category": "Meshcapade",
}

if "bpy" in locals():
    import importlib
    if "meshcapade_addon" in locals():
        importlib.reload(meshcapade_addon)
    else:
        from .meshcapade_addon import meshcapade_addon
else:
    import bpy
    from .meshcapade_addon import meshcapade_addon

def register():
    meshcapade_addon.register()

def unregister():
    meshcapade_addon.unregister()