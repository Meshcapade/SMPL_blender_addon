import bpy
from .globals import (
    VERSION,
)


class SMPL_PT_Convert_UV(bpy.types.Panel):
    bl_label = "Convert UV"
    bl_category = "Meshcapade Utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.operator("object.smpl_set_source_objs", text="Select source OBJs")
        split.operator("object.smpl_clear_source_objs", icon="CANCEL", text="Clear")
        col.prop(context.window_manager.smpl_tool, "smpl_uv_source_objs")
        col.separator()
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.operator("object.smpl_set_source_fbxs", text="Select source FBXs")
        split.operator("object.smpl_clear_source_fbxs", icon="CANCEL", text="Clear")
        col.prop(context.window_manager.smpl_tool, "smpl_uv_source_fbxs")
        col.separator()
        row = col.row(align=True)
        row.prop(context.window_manager.smpl_tool, "smpl_uv_type")
        col.separator()
        row = col.row(align=True)
        row.prop(context.window_manager.smpl_tool, "smpl_uv_output_dir")
        col.separator()
        col.separator()
        num_source_objs = len(context.window_manager.smpl_tool.smpl_uv_source_objs)
        num_source_fbxs = len(context.window_manager.smpl_tool.smpl_uv_source_fbxs)
        num_source_items = num_source_objs + num_source_fbxs
        output_dir = context.window_manager.smpl_tool.smpl_uv_output_dir

        if num_source_items == 0:
            col.label(
                icon="ERROR",
                text="No SMPL mesh items to convert, select source OBJs or FBXs",
            )
        elif not output_dir:
            col.label(
                icon="ERROR",
                text="No output directory specified",
            )

        col.operator("object.smpl_execute_convert_uv")


class SMPLX_PT_Model(bpy.types.Panel):
    bl_label = "SMPL-X Model"
    bl_category = "SMPL-X"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        col.prop(context.window_manager.smplx_tool, "smplx_gender")
        col.operator("scene.smplx_add_gender", text="Add")
        col.separator()
        col.label(text="Texture:")
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.prop(context.window_manager.smplx_tool, "smplx_texture")
        split.operator("object.smplx_set_texture", text="Set")


class SMPLX_PT_Shape(bpy.types.Panel):
    bl_label = "Shape"
    bl_category = "SMPL-X"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.prop(context.window_manager.smplx_tool, "smplx_height")
        col.prop(context.window_manager.smplx_tool, "smplx_weight")
        col.operator("object.smplx_measurements_to_shape")
        col.separator()

        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.operator("object.smplx_random_shape")
        split.operator("object.smplx_reset_shape")
        col.separator()

        col.operator("object.smplx_snap_ground_plane")
        col.separator()

        col.operator("object.smplx_update_joint_locations")
        col.separator()
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.operator("object.smplx_random_expression_shape")
        split.operator("object.smplx_reset_expression_shape")


class SMPLX_PT_Pose(bpy.types.Panel):
    bl_label = "Pose"
    bl_category = "SMPL-X"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.prop(context.window_manager.smplx_tool, "smplx_corrective_poseshapes")
        col.separator()
        col.operator("object.smplx_set_poseshapes")

        col.separator()
        col.label(text="Hand Pose:")
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.prop(context.window_manager.smplx_tool, "smplx_handpose")
        split.operator("object.smplx_set_handpose", text="Set")

        col.separator()
        col.operator("object.smplx_write_pose")
        col.separator()
        col.operator("object.smplx_load_pose")


class SMPLX_PT_Export(bpy.types.Panel):
    bl_label = "Export"
    bl_category = "SMPL-X"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.label(text="Shape Keys (Blend Shapes):")
        col.prop(context.window_manager.smplx_tool, "smplx_export_setting_shape_keys")
        col.separator()
        col.separator()

        col.operator("object.smplx_export_unity_fbx")
        col.separator()

        row = col.row(align=True)
        row.operator("ed.undo", icon='LOOP_BACK')
        row.operator("ed.redo", icon='LOOP_FORWARDS')
        col.separator()

        (year, month, day) = VERSION
        col.label(text="Version: %s-%s-%s" % (year, month, day))


UI_CLASSES = [
    SMPLX_PT_Model,
    SMPLX_PT_Shape,
    SMPLX_PT_Pose,
    SMPLX_PT_Export,
    SMPL_PT_Convert_UV,
]
