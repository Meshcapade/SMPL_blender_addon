import bpy
from .globals import (
    VERSION,
)

ENABLE_AFM = False

class SMPL_PT_Load(bpy.types.Panel):
    bl_label = "Load Avatar"
    bl_category = "Meshcapade"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("object.load_avatar")


class SMPL_PT_Create(bpy.types.Panel):
    bl_label = "Create Avatar"
    bl_category = "Meshcapade"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        
        row = col.row(align=True)
        col.prop(context.window_manager.smpl_tool, "SMPL_version")
        col.separator()

        col.prop(context.window_manager.smpl_tool, "gender")
        col.separator()

        col.operator("scene.create_avatar", text="Create")

        col.separator()
        col.label(text="Texture:")
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.prop(context.window_manager.smpl_tool, "texture")
        split.operator("object.set_texture", text="Set")


class SMPL_PT_Shape(bpy.types.Panel):
    bl_label = "Shape"
    bl_category = "Meshcapade"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is not SMPLH because we can't support that right now
            return (bpy.context.object['SMPL version'] != 'SMPLH')
        except: return False

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col2 = layout.column(align=True)

        col.alert = not ENABLE_AFM
        col.prop(context.window_manager.smpl_tool, "height")
        col.prop(context.window_manager.smpl_tool, "weight")
        
        if (not ENABLE_AFM):
            col.label(text="Measurements are outdated.")

        row = col2.row(align=True)
        split = row.split(factor=0.5, align=True)
        split.operator("object.random_body_shape")
        split.operator("object.random_face_shape")

        row2 = col2.row(align=True)
        split2 = row2.split(factor=0.5, align=True)
        split2.operator("object.reset_body_shape")
        split2.operator("object.reset_face_shape")

        row3 = col2.row(align=True)
        split3 = row3.split(factor=0.5, align=True)
        split3.prop(context.window_manager.smpl_tool, "random_body_mult")
        split3.prop(context.window_manager.smpl_tool, "random_face_mult")

        col2.separator()
        col2.operator("object.update_joint_locations")
        col2.separator()


class SMPL_PT_Pose(bpy.types.Panel):
    bl_label = "Pose"
    bl_category = "Meshcapade"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.operator("object.load_pose")
        col.separator()

        col.label(text="Hand Pose:")
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.prop(context.window_manager.smpl_tool, "handpose")
        split.operator("object.set_handpose", text="Set")
        
        col.prop(context.window_manager.smpl_tool, "pose_correctives_enabled")
        col.separator()
        col.operator("object.update_pose_correctives")
        col.operator("object.set_pose_shapes_sequence")
        col.separator()
        col.operator("object.snap_to_ground_plane")


class SMPL_PT_Expression(bpy.types.Panel):
    bl_label = "Facial Expressions"
    bl_idname = "OBJECT_PT_expression_presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Meshcapade"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return (bpy.context.object['SMPL version'] != 'SMPLH')
        except: return False

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row2 = col.row(align=True)
        col.separator()
        row3 = col.row(align=True)
        split = row3.split(factor=0.75, align=True)

        row.operator("object.set_expression_preset", text="Pleasant").preset = "pleasant"
        row.operator("object.set_expression_preset", text="Happy").preset = "happy"
        row.operator("object.set_expression_preset", text="Excited").preset = "excited"

        row2.operator("object.set_expression_preset", text="Sad").preset = "sad"
        row2.operator("object.set_expression_preset", text="Frustrated").preset = "frustrated"
        row2.operator("object.set_expression_preset", text="Angry").preset = "angry"

        split.operator("object.random_expression_shape")
        split.operator("object.reset_expression_shape")


class SMPL_PT_Export(bpy.types.Panel):
    bl_label = "Export"
    bl_category = "Meshcapade"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.label(text="Shape Keys (Blend Shapes):")
        col.prop(context.window_manager.smpl_tool, "export_setting_shape_keys")
        col.separator()

        col.operator("object.export_unity_fbx")
        col.separator()


UI_CLASSES = [
    SMPL_PT_Load,
    SMPL_PT_Create,
    SMPL_PT_Shape,
    SMPL_PT_Pose,
    SMPL_PT_Expression,
    SMPL_PT_Export,
]
