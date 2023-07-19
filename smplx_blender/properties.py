import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    PointerProperty,
    StringProperty,
    CollectionProperty,
)
from bpy.types import (
    PropertyGroup,
)
from .blender import (
    update_corrective_poseshapes,
)
from .globals import (
    HIGH,
    MEDIUM,
    LOW,
    SMPL_V1,
    # SMPL_V0,
)

def MeasurementsToShape(self, context):
    bpy.ops.object.measurements_to_shape('EXEC_DEFAULT')
    context.window_manager.smpl_tool.alert = False


class PG_SMPLProperties(PropertyGroup):
    alert: BoolProperty(default=False)

    SMPL_version: EnumProperty(
        name = "SMPL version",
        description = "SMPL family version of the avatar you'd like to create",
        items = [ 
            ("SMPLH", "SMPL-H", ""),  #removing this for now because we don't have a joint regressor for it
            ("SMPLX", "SMPL-X", ""), 
            ("SUPR", "SUPR", "") 
        ]
    )

    gender: EnumProperty(
        name="Gender",
        description="SMPL-X model",
        items=[
            ("female", "Female", ""),
            ("male", "Male", ""),
            ("neutral", "Neutral", ""),
        ]
    )

    texture: EnumProperty(
        name="",
        description="SMPL-X model texture",
        items=[
            ("NONE", "None", ""),
            ("f", "Female", ""),
            ("m", "Male", ""),
            ("texture_rainbow.png", "Rainbow", ""),
            ("UV_GRID", "UV Grid", ""),
            ("COLOR_GRID", "Color Grid", ""),
        ]
    )

    handpose: EnumProperty(
        name="Hands",
        description="SMPL-X hand pose",
        items=[
            ("relaxed", "Relaxed", ""),
            ("flat", "Flat", ""),
        ]
    )

    export_setting_shape_keys: EnumProperty(
        name="",
        description="Blend shape export settings",
        items=[
            (
                "SHAPE_POSE",
                "All: Shape + Posecorrectives",
                "Export shape keys for body shape and pose correctives",
            ),
            (
                "SHAPE",
                "Reduced: Shape space only",
                "Export only shape keys for body shape",
            ),
            (
                "NONE",
                "None: Apply shape space",
                "Do not export any shape keys, shape keys for body shape will be baked into mesh",
            ),
        ],
    )

    height: FloatProperty(
        update=MeasurementsToShape, 
        name="Target Height [cm]", 
        default=170, 
        min=140, 
        max=220
    )

    weight: FloatProperty(
        update=MeasurementsToShape, 
        name="Target Weight [kg]", 
        default=60, 
        min=40, 
        max=110
    )

    random_body_mult: FloatProperty(
        name="Body Multiplier",
        default=1.5, 
        min=0, 
        max=5
    )
    
    random_face_mult: FloatProperty(
        name="Face Multiplier", 
        default=1.5, 
        min=0, 
        max=5
    )


PROPERTY_CLASSES = [
    PG_SMPLProperties,
]


def define_props():
    # Store properties under WindowManager (not Scene) so that they are not saved
    # in .blend files and always show default values after loading
    bpy.types.WindowManager.smpl_tool = PointerProperty(type=PG_SMPLProperties)


def destroy_props():
    del bpy.types.WindowManager.smpl_tool
