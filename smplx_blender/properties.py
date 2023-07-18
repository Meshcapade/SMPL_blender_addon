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

class PG_SMPLXProperties(PropertyGroup):

    smplx_gender: EnumProperty(
        name="Model",
        description="SMPL-X model",
        items=[
            ("female", "Female", ""),
            ("male", "Male", ""),
            ("neutral", "Neutral", ""),
        ]
    )

    smplx_texture: EnumProperty(
        name="",
        description="SMPL-X model texture",
        items=[
            ("NONE", "None", ""),
            ("smplx_texture_f_alb.png", "Female", ""),
            ("smplx_texture_m_alb.png", "Male", ""),
            ("smplx_texture_rainbow.png", "Rainbow", ""),
            ("UV_GRID", "UV Grid", ""),
            ("COLOR_GRID", "Color Grid", ""),
        ]
    )

    smplx_corrective_poseshapes: BoolProperty(
        name="Corrective Pose Shapes",
        description="Enable/disable corrective pose shapes of SMPL-X model",
        update=update_corrective_poseshapes,
        default=True,
    )

    smplx_handpose: EnumProperty(
        name="",
        description="SMPL-X hand pose",
        items=[
            ("relaxed", "Relaxed", ""),
            ("flat", "Flat", ""),
        ]
    )

    smplx_export_setting_shape_keys: EnumProperty(
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

    smplx_height: FloatProperty(
        name="Target Height [m]",
        default=1.70,
        min=1.4,
        max=2.2,
    )

    smplx_weight: FloatProperty(
        name="Target Weight [kg]",
        default=60,
        min=40,
        max=110,
    )


class PG_SMPLConvertProperties(PropertyGroup):

    smpl_uv_source_objs: CollectionProperty(
        type=PropertyGroup,
    )

    smpl_uv_source_fbxs: CollectionProperty(
        type=PropertyGroup,
    )

    smpl_uv_output_dir: StringProperty(
        name="Output Directory",
        subtype='DIR_PATH',
        default="",
    )

    smpl_resolution: EnumProperty(
        name="SMPL Resolution",
        description="The SMPL resolution",
        items=[
            (HIGH, "High", ""),
            (MEDIUM, "Medium", ""),
            (LOW, "Low", ""),
        ]
    )

    smpl_uv_type: EnumProperty(
        name="Output UV Type",
        description="The UV coordinate version",
        items=[
            (SMPL_V1, "SMPL v1 (current)", ""),
            # (SMPL_V0, "SMPL v0 (legacy)", ""),
        ]
    )


PROPERTY_CLASSES = [
    PG_SMPLXProperties,
    PG_SMPLConvertProperties,
]


def define_props():
    # Store properties under WindowManager (not Scene) so that they are not saved
    # in .blend files and always show default values after loading
    bpy.types.WindowManager.smplx_tool = PointerProperty(type=PG_SMPLXProperties)
    bpy.types.WindowManager.smpl_tool = PointerProperty(type=PG_SMPLConvertProperties)


def destroy_props():
    del bpy.types.WindowManager.smplx_tool
    del bpy.types.WindowManager.smpl_tool
