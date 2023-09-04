bl_info = {
    "name": "Meshcapade Blender tools",
    "author": "Max Planck Institute for Intelligent Systems; Meshcapade GmbH",
    "version": (2023, 8, 1),
    "blender": (3, 5, 1),
    "location": "Viewport > Right panel",
    "description": "SMPL family avatar tools in Blender",
    "wiki_url": "smpl.wiki",
    "smplx_wiki_url": "https://smpl-x.is.tue.mpg.de/",
    "category": "Meshcapade",
}

if "bpy" in locals():
    import importlib
    if "meshcapade_addon" in locals():
        importlib.reload(meshcapade_addon)
    else:
        from . import meshcapade_addon
else:
    import bpy
    from . import meshcapade_addon

def register():
    meshcapade_addon.register()

def unregister():
    meshcapade_addon.unregister()