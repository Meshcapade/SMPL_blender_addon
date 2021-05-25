# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "SMPL-X for Blender",
    "author": "Joachim Tesch, Max Planck Institute for Intelligent Systems",
    "version": (2021, 5, 25),
    "blender": (2, 80, 0),
    "location": "Viewport > Right panel",
    "description": "SMPL-X for Blender",
    "wiki_url": "https://smpl-x.is.tue.mpg.de/",
    "category": "SMPL-X"}

import bpy
import bmesh
from bpy_extras.io_utils import ImportHelper,ExportHelper # ImportHelper/ExportHelper is a helper class, defines filename and invoke() function which calls the file selector.

from mathutils import Vector, Quaternion
from math import radians
import numpy as np
import os
import pickle

from bpy.props import ( BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty )
from bpy.types import ( PropertyGroup )

# SMPL-X globals
SMPLX_MODELFILE = "smplx_model_20210421.blend"

SMPLX_JOINT_NAMES = [
    'pelvis','left_hip','right_hip','spine1','left_knee','right_knee','spine2','left_ankle','right_ankle','spine3', 'left_foot','right_foot','neck','left_collar','right_collar','head','left_shoulder','right_shoulder','left_elbow', 'right_elbow','left_wrist','right_wrist',
    'jaw','left_eye_smplhf','right_eye_smplhf','left_index1','left_index2','left_index3','left_middle1','left_middle2','left_middle3','left_pinky1','left_pinky2','left_pinky3','left_ring1','left_ring2','left_ring3','left_thumb1','left_thumb2','left_thumb3','right_index1','right_index2','right_index3','right_middle1','right_middle2','right_middle3','right_pinky1','right_pinky2','right_pinky3','right_ring1','right_ring2','right_ring3','right_thumb1','right_thumb2','right_thumb3'
]
NUM_SMPLX_JOINTS = len(SMPLX_JOINT_NAMES)
NUM_SMPLX_BODYJOINTS = 21
NUM_SMPLX_HANDJOINTS = 15
# End SMPL-X globals

def rodrigues_from_pose(armature, bone_name):
    # Use quaternion mode for all bone rotations
    if armature.pose.bones[bone_name].rotation_mode != 'QUATERNION':
        armature.pose.bones[bone_name].rotation_mode = 'QUATERNION'

    quat = armature.pose.bones[bone_name].rotation_quaternion
    (axis, angle) = quat.to_axis_angle()
    rodrigues = axis
    rodrigues.normalize()
    rodrigues = rodrigues * angle
    return rodrigues

def update_corrective_poseshapes(self, context):
    if self.smplx_corrective_poseshapes:
        bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')
    else:
        bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')

def set_pose_from_rodrigues(armature, bone_name, rodrigues, rodrigues_reference=None):
    rod = Vector((rodrigues[0], rodrigues[1], rodrigues[2]))
    angle_rad = rod.length
    axis = rod.normalized()

    if armature.pose.bones[bone_name].rotation_mode != 'QUATERNION':
        armature.pose.bones[bone_name].rotation_mode = 'QUATERNION'

    quat = Quaternion(axis, angle_rad)

    if rodrigues_reference is None:
        armature.pose.bones[bone_name].rotation_quaternion = quat
    else:
        # SMPL-X is adding the reference rodrigues rotation to the relaxed hand rodrigues rotation, so we have to do the same here.
        # This means that pose values for relaxed hand model cannot be interpreted as rotations in the local joint coordinate system of the relaxed hand.
        # https://github.com/vchoutas/smplx/blob/f4206853a4746139f61bdcf58571f2cea0cbebad/smplx/body_models.py#L1190
        #   full_pose += self.pose_mean
        rod_reference = Vector((rodrigues_reference[0], rodrigues_reference[1], rodrigues_reference[2]))
        rod_result = rod + rod_reference
        angle_rad_result = rod_result.length
        axis_result = rod_result.normalized()
        quat_result = Quaternion(axis_result, angle_rad_result)
        armature.pose.bones[bone_name].rotation_quaternion = quat_result

        """
        rod_reference = Vector((rodrigues_reference[0], rodrigues_reference[1], rodrigues_reference[2]))
        angle_rad_reference = rod_reference.length
        axis_reference = rod_reference.normalized()
        quat_reference = Quaternion(axis_reference, angle_rad_reference)

        # Rotate first into reference pose and then add the target pose
        armature.pose.bones[bone_name].rotation_quaternion = quat_reference @ quat
        """
    return

# Property groups for UI
class PG_SMPLXProperties(PropertyGroup):

    smplx_gender: EnumProperty(
        name = "Model",
        description = "SMPL-X model",
        items = [ ("female", "Female", ""), ("male", "Male", ""), ("neutral", "Neutral", "") ]
    )

    smplx_texture: EnumProperty(
        name = "",
        description = "SMPL-X model texture",
        items = [ ("NONE", "None", ""), ("smplx_texture_f_alb.png", "Female", ""), ("smplx_texture_m_alb.png", "Male", ""), ("smplx_texture_rainbow.png", "Rainbow", ""), ("UV_GRID", "UV Grid", ""), ("COLOR_GRID", "Color Grid", "") ]
    )

    smplx_corrective_poseshapes: BoolProperty(
        name = "Corrective Pose Shapes",
        description = "Enable/disable corrective pose shapes of SMPL-X model",
        update = update_corrective_poseshapes,
        default = True
    )

    smplx_handpose: EnumProperty(
        name = "",
        description = "SMPL-X hand pose",
        items = [ ("relaxed", "Relaxed", ""), ("flat", "Flat", "") ]
    )

    smplx_export_setting_shape_keys: EnumProperty(
        name = "",
        description = "Blend shape export settings",
        items = [ ("SHAPE_POSE", "All: Shape + Posecorrectives", "Export shape keys for body shape and pose correctives"), ("SHAPE", "Reduced: Shape space only", "Export only shape keys for body shape"), ("NONE", "None: Apply shape space", "Do not export any shape keys, shape keys for body shape will be baked into mesh") ],
    )

class SMPLXAddGender(bpy.types.Operator):
    bl_idname = "scene.smplx_add_gender"
    bl_label = "Add"
    bl_description = ("Add SMPL-X model of selected gender to scene")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in Object Mode
            if (context.active_object is None) or (context.active_object.mode == 'OBJECT'):
                return True
            else: 
                return False
        except: return False

    def execute(self, context):
        gender = context.window_manager.smplx_tool.smplx_gender
        print("Adding gender: " + gender)

        path = os.path.dirname(os.path.realpath(__file__))
        objects_path = os.path.join(path, "data", SMPLX_MODELFILE, "Object")
        object_name = "SMPLX-mesh-" + gender

        bpy.ops.wm.append(filename=object_name, directory=str(objects_path))

        # Select imported mesh
        object_name = context.selected_objects[0].name
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = bpy.data.objects[object_name]
        bpy.data.objects[object_name].select_set(True)

        # Set currently selected hand pose
        bpy.ops.object.smplx_set_handpose('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXSetTexture(bpy.types.Operator):
    bl_idname = "scene.smplx_set_texture"
    bl_label = "Set"
    bl_description = ("Set selected texture")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if in active object is mesh
            if (context.object.type == 'MESH'):
                return True
            else:
                return False
        except: return False

    def execute(self, context):
        texture = context.window_manager.smplx_tool.smplx_texture
        print("Setting texture: " + texture)

        obj = bpy.context.object
        if (len(obj.data.materials) == 0) or (obj.data.materials[0] is None):
            self.report({'WARNING'}, "Selected mesh has no material: %s" % obj.name)
            return {'CANCELLED'}

        mat = obj.data.materials[0]
        links = mat.node_tree.links
        nodes = mat.node_tree.nodes

        # Find texture node
        node_texture = None
        for node in nodes:
            if node.type == 'TEX_IMAGE':
                node_texture = node
                break

        # Find shader node
        node_shader = None
        for node in nodes:
            if node.type.startswith('BSDF'):
                node_shader = node
                break

        if texture == 'NONE':
            # Unlink texture node
            if node_texture is not None:
                for link in node_texture.outputs[0].links:
                    links.remove(link)

                nodes.remove(node_texture)

                # 3D Viewport still shows previous texture when texture link is removed via script.
                # As a workaround we trigger desired viewport update by setting color value.
                node_shader.inputs[0].default_value = node_shader.inputs[0].default_value
        else:
            if node_texture is None:
                node_texture = nodes.new(type="ShaderNodeTexImage")

            if (texture == 'UV_GRID') or (texture == 'COLOR_GRID'):
                if texture not in bpy.data.images:
                    bpy.ops.image.new(name=texture, generated_type=texture)
                image = bpy.data.images[texture]
            else:
                if texture not in bpy.data.images:
                    path = os.path.dirname(os.path.realpath(__file__))
                    texture_path = os.path.join(path, "data", texture)
                    image = bpy.data.images.load(texture_path)
                else:
                    image = bpy.data.images[texture]

            node_texture.image = image

            # Link texture node to shader node if not already linked
            if len(node_texture.outputs[0].links) == 0:
                links.new(node_texture.outputs[0], node_shader.inputs[0])

        # Switch viewport shading to Material Preview to show texture
        bpy.context.space_data.shading.type = 'MATERIAL'

        return {'FINISHED'}

class SMPLXRandomShapes(bpy.types.Operator):
    bl_idname = "object.smplx_random_shapes"
    bl_label = "Random"
    bl_description = ("Sets all shape blend shape keys to a random value")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                key_block.value = np.random.normal(0.0, 1.0)

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXResetShapes(bpy.types.Operator):
    bl_idname = "object.smplx_reset_shapes"
    bl_label = "Reset"
    bl_description = ("Resets all blend shape keys for shape")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                key_block.value = 0.0

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXRandomExpressionShapes(bpy.types.Operator):
    bl_idname = "object.smplx_random_expression_shapes"
    bl_label = "Random Face Expression"
    bl_description = ("Sets all face expression blend shape keys to a random value")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Exp"):
                key_block.value = np.random.uniform(-2, 2)

        return {'FINISHED'}

class SMPLXResetExpressionShapes(bpy.types.Operator):
    bl_idname = "object.smplx_reset_expression_shapes"
    bl_label = "Reset"
    bl_description = ("Resets all blend shape keys for face expression")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Exp"):
                key_block.value = 0.0

        return {'FINISHED'}

class SMPLXSnapGroundPlane(bpy.types.Operator):
    bl_idname = "object.smplx_snap_ground_plane"
    bl_label = "Snap To Ground Plane"
    bl_description = ("Snaps mesh to the XY ground plane")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return ((context.object.type == 'MESH') or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')

        obj = bpy.context.object
        if obj.type == 'ARMATURE':
                    armature = obj
                    obj = bpy.context.object.children[0]
        else:
            armature = obj.parent

        # Get vertices with applied skin modifier in object coordinates
        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh_from_eval = object_eval.to_mesh()

        # Get vertices in world coordinates
        matrix_world = obj.matrix_world
        vertices_world = [matrix_world @ vertex.co for vertex in mesh_from_eval.vertices]
        z_min = (min(vertices_world, key=lambda item: item.z)).z
        object_eval.to_mesh_clear() # Remove temporary mesh

        # Adjust height of armature so that lowest vertex is on ground plane.
        # Do not apply new armature location transform so that we are later able to show loaded poses at their desired height.
        armature.location.z = armature.location.z - z_min

        return {'FINISHED'}

class SMPLXUpdateJointLocations(bpy.types.Operator):
    bl_idname = "object.smplx_update_joint_locations"
    bl_label = "Update Joint Locations"
    bl_description = ("Update joint locations after shape/expression changes")
    bl_options = {'REGISTER', 'UNDO'}

    j_regressor_female = None
    j_regressor_male = None
    j_regressor_neutral = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')


        if self.j_regressor_female is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_joint_regressor_female.npz")
            with np.load(regressor_path) as data:
                self.j_regressor_female = data['joint_regressor']

        if self.j_regressor_male is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_joint_regressor_male.npz")
            with np.load(regressor_path) as data:
                self.j_regressor_male = data['joint_regressor']

        if self.j_regressor_neutral is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_joint_regressor_neutral.npz")
            with np.load(regressor_path) as data:
                self.j_regressor_neutral = data['joint_regressor']

        if "female" in obj.name:
            j_regressor = self.j_regressor_female
        elif "male" in obj.name:
            j_regressor = self.j_regressor_male
        else:
            j_regressor = self.j_regressor_neutral

        # Store current bone rotations
        armature = obj.parent

        bone_rotations = {}
        for pose_bone in armature.pose.bones:
            if pose_bone.rotation_mode != 'QUATERNION':
                pose_bone.rotation_mode = 'QUATERNION'
            quat = pose_bone.rotation_quaternion
            bone_rotations[pose_bone.name] = (quat[0], quat[1], quat[2], quat[3])

        # Set model to default pose
        for bone in armature.pose.bones:
            bone.rotation_quaternion = Quaternion()

        # Reset corrective poseshapes if used
        if context.window_manager.smplx_tool.smplx_corrective_poseshapes:
            bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')

        # Get vertices with applied skin modifier
        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh_from_eval = object_eval.to_mesh()

        # Get Blender vertices as numpy matrix
        vertices_np = np.zeros((len(mesh_from_eval.vertices)*3), dtype=np.float)
        mesh_from_eval.vertices.foreach_get("co", vertices_np)
        vertices_matrix = np.reshape(vertices_np, (len(mesh_from_eval.vertices), 3))
        object_eval.to_mesh_clear() # Remove temporary mesh

        # Note: Current joint regressor uses vertices as input which results in slow numpy operation
        joint_locations = j_regressor @ vertices_matrix

        # Set new bone joint locations
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        for index in range(NUM_SMPLX_JOINTS):
            bone = armature.data.edit_bones[SMPLX_JOINT_NAMES[index]]
            bone.head = (0.0, 0.0, 0.0)
            bone.tail = (0.0, 0.0, 0.1)

            bone_start = Vector(joint_locations[index])
            bone.translate(bone_start)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = obj

        # Restore pose
        for pose_bone in armature.pose.bones:
            pose_bone.rotation_quaternion = bone_rotations[pose_bone.name]

        # Restore corrective poseshapes if used
        if context.window_manager.smplx_tool.smplx_corrective_poseshapes:
            bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXSetPoseshapes(bpy.types.Operator):
    bl_idname = "object.smplx_set_poseshapes"
    bl_label = "Update Pose Shapes"
    bl_description = ("Sets and updates corrective poseshapes for current pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object and parent is armature
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Computes rotation matrix through Rodrigues formula as in cv2.Rodrigues
    def rodrigues_to_mat(self, rotvec):
        theta = np.linalg.norm(rotvec)
        r = (rotvec/theta).reshape(3, 1) if theta > 0. else rotvec
        cost = np.cos(theta)
        mat = np.asarray([[0, -r[2], r[1]],
                        [r[2], 0, -r[0]],
                        [-r[1], r[0], 0]])
        return(cost*np.eye(3) + (1-cost)*r.dot(r.T) + np.sin(theta)*mat)

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Calculate weights of pose corrective blend shapes
    # Input is pose of all 55 joints, output is weights for all joints except pelvis
    def rodrigues_to_posecorrective_weight(self, pose):
        joints_posecorrective = NUM_SMPLX_JOINTS
        rod_rots = np.asarray(pose).reshape(joints_posecorrective, 3)
        mat_rots = [self.rodrigues_to_mat(rod_rot) for rod_rot in rod_rots]
        bshapes = np.concatenate([(mat_rot - np.eye(3)).ravel() for mat_rot in mat_rots[1:]])
        return(bshapes)

    def execute(self, context):
        obj = bpy.context.object

        # Get armature pose in rodrigues representation
        if obj.type == 'ARMATURE':
            armature = obj
            obj = bpy.context.object.children[0]
        else:
            armature = obj.parent

        pose = [0.0] * (NUM_SMPLX_JOINTS * 3)

        for index in range(NUM_SMPLX_JOINTS):
            joint_name = SMPLX_JOINT_NAMES[index]
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        poseweights = self.rodrigues_to_posecorrective_weight(pose)

        # Set weights for pose corrective shape keys
        for index, weight in enumerate(poseweights):
            obj.data.shape_keys.key_blocks["Pose%03d" % index].value = weight

        # Set checkbox without triggering update function
        context.window_manager.smplx_tool["smplx_corrective_poseshapes"] = True

        return {'FINISHED'}

class SMPLXResetPoseshapes(bpy.types.Operator):
    bl_idname = "object.smplx_reset_poseshapes"
    bl_label = "Reset"
    bl_description = ("Resets corrective poseshapes for current pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object and parent is armature
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'ARMATURE':
            obj = bpy.context.object.children[0]

        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Pose"):
                key_block.value = 0.0

        return {'FINISHED'}

class SMPLXSetHandpose(bpy.types.Operator):
    bl_idname = "object.smplx_set_handpose"
    bl_label = "Set"
    bl_description = ("Set selected hand pose")
    bl_options = {'REGISTER', 'UNDO'}

    hand_poses = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object
        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        if self.hand_poses is None:
            path = os.path.dirname(os.path.realpath(__file__))
            data_path = os.path.join(path, "data", "smplx_handposes.npz")
            with np.load(data_path, allow_pickle=True) as data:
                self.hand_poses = data["hand_poses"].item()

        hand_pose_name = context.window_manager.smplx_tool.smplx_handpose
        print("Setting hand pose: " + hand_pose_name)

        if hand_pose_name not in self.hand_poses:
            self.report({"ERROR"}, f"Desired hand pose not existing: {hand_pose_name}")
            return {"CANCELLED"}

        (left_hand_pose, right_hand_pose) = self.hand_poses[hand_pose_name]

        hand_pose = np.concatenate( (left_hand_pose, right_hand_pose) ).reshape(-1, 3)

        hand_joint_start_index = 1 + NUM_SMPLX_BODYJOINTS + 3
        for index in range(2 * NUM_SMPLX_HANDJOINTS):
            pose_rodrigues = hand_pose[index]            
            bone_name = SMPLX_JOINT_NAMES[index + hand_joint_start_index]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

        # Update corrective poseshapes if used
        if context.window_manager.smplx_tool.smplx_corrective_poseshapes:
            bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXWritePose(bpy.types.Operator):
    bl_idname = "object.smplx_write_pose"
    bl_label = "Write Pose To Console"
    bl_description = ("Writes SMPL-X flat hand pose thetas to console window")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return (context.object.type == 'MESH') or (context.object.type == 'ARMATURE')
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        # Get armature pose in rodrigues representation
        pose = [0.0] * (NUM_SMPLX_JOINTS * 3)

        for index in range(NUM_SMPLX_JOINTS):
            joint_name = SMPLX_JOINT_NAMES[index]
            joint_pose = rodrigues_from_pose(armature, joint_name)
            pose[index*3 + 0] = joint_pose[0]
            pose[index*3 + 1] = joint_pose[1]
            pose[index*3 + 2] = joint_pose[2]

        print("\npose = " + str(pose))

        return {'FINISHED'}

class SMPLXResetPose(bpy.types.Operator):
    bl_idname = "object.smplx_reset_pose"
    bl_label = "Reset Pose"
    bl_description = ("Resets pose to default zero pose")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj

        for bone in armature.pose.bones:
            if bone.rotation_mode != 'QUATERNION':
                bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = Quaternion()

        # Reset corrective pose shapes
        bpy.ops.object.smplx_reset_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}

class SMPLXLoadPose(bpy.types.Operator, ImportHelper):
    bl_idname = "object.smplx_load_pose"
    bl_label = "Load Pose"
    bl_description = ("Load relaxed-hand model pose from file")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.pkl",
        options={'HIDDEN'}
    )

    update_shape: BoolProperty(
        name="Update shape parameters",
        description="Update shape parameters using the beta shape information in the loaded file",
        default=True
    )

    hand_pose_relaxed = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return ( ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or (context.object.type == 'ARMATURE'))
        except: return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj
            obj = armature.children[0]
            context.view_layer.objects.active = obj # mesh needs to be active object for recalculating joint locations

        if self.hand_pose_relaxed is None:
            path = os.path.dirname(os.path.realpath(__file__))
            data_path = os.path.join(path, "data", "smplx_handposes.npz")
            with np.load(data_path, allow_pickle=True) as data:
                hand_poses = data["hand_poses"].item()
                (left_hand_pose, right_hand_pose) = hand_poses["relaxed"]
                self.hand_pose_relaxed = np.concatenate( (left_hand_pose, right_hand_pose) ).reshape(-1, 3)

        print("Loading: " + self.filepath)

        translation = None
        global_orient = None
        body_pose = None
        jaw_pose = None
        #leye_pose = None
        #reye_pose = None
        left_hand_pose = None
        right_hand_pose = None
        betas = None
        expression = None
        with open(self.filepath, "rb") as f:
            data = pickle.load(f, encoding="latin1")

            if "transl" in data:
                translation = np.array(data["transl"]).reshape(3)

            if "global_orient" in data:
                global_orient = np.array(data["global_orient"]).reshape(3)

            body_pose = np.array(data["body_pose"])
            if body_pose.shape != (1, NUM_SMPLX_BODYJOINTS * 3):
                print(f"Invalid body pose dimensions: {body_pose.shape}")
                body_data = None
                return {'CANCELLED'}

            body_pose = np.array(data["body_pose"]).reshape(NUM_SMPLX_BODYJOINTS, 3)

            jaw_pose = np.array(data["jaw_pose"]).reshape(3)
            #leye_pose = np.array(data["leye_pose"]).reshape(3)
            #reye_pose = np.array(data["reye_pose"]).reshape(3)
            left_hand_pose = np.array(data["left_hand_pose"]).reshape(-1, 3)
            right_hand_pose = np.array(data["right_hand_pose"]).reshape(-1, 3)

            betas = np.array(data["betas"]).reshape(-1).tolist()
            expression = np.array(data["expression"]).reshape(-1).tolist()

        # Update shape if selected
        if self.update_shape:
            bpy.ops.object.mode_set(mode='OBJECT')
            for index, beta in enumerate(betas):
                key_block_name = f"Shape{index:03}"

                if key_block_name in obj.data.shape_keys.key_blocks:
                    obj.data.shape_keys.key_blocks[key_block_name].value = beta
                else:
                    print(f"ERROR: No key block for: {key_block_name}")

            bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        if global_orient is not None:
            set_pose_from_rodrigues(armature, "pelvis", global_orient)

        for index in range(NUM_SMPLX_BODYJOINTS):
            pose_rodrigues = body_pose[index]
            bone_name = SMPLX_JOINT_NAMES[index + 1] # body pose starts with left_hip
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

        set_pose_from_rodrigues(armature, "jaw", jaw_pose)

        # Left hand
        start_name_index = 1 + NUM_SMPLX_BODYJOINTS + 3
        for i in range(0, NUM_SMPLX_HANDJOINTS):
            pose_rodrigues = left_hand_pose[i]
            bone_name = SMPLX_JOINT_NAMES[start_name_index + i]
            pose_relaxed_rodrigues = self.hand_pose_relaxed[i]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, pose_relaxed_rodrigues)

        # Right hand
        start_name_index = 1 + NUM_SMPLX_BODYJOINTS + 3 + NUM_SMPLX_HANDJOINTS
        for i in range(0, NUM_SMPLX_HANDJOINTS):
            pose_rodrigues = right_hand_pose[i]
            bone_name = SMPLX_JOINT_NAMES[start_name_index + i]
            pose_relaxed_rodrigues = self.hand_pose_relaxed[NUM_SMPLX_HANDJOINTS + i]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues, pose_relaxed_rodrigues)

        if translation is not None:
            # Set translation
            armature.location = (translation[0], -translation[2], translation[1])

        # Activate corrective poseshapes
        bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

        # Set face expression
        for index, exp in enumerate(expression):
            key_block_name = f"Exp{index:03}"

            if key_block_name in obj.data.shape_keys.key_blocks:
                obj.data.shape_keys.key_blocks[key_block_name].value = exp
            else:
                print(f"ERROR: No key block for: {key_block_name}")

        return {'FINISHED'}

class SMPLXExportUnityFBX(bpy.types.Operator, ExportHelper):
    bl_idname = "object.smplx_export_unity_fbx"
    bl_label = "Export Unity FBX"
    bl_description = ("Export skinned mesh to Unity in FBX format")
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".fbx"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return (context.object.type == 'MESH')
        except: return False

    def execute(self, context):

        obj = bpy.context.object
        export_shape_keys = context.window_manager.smplx_tool.smplx_export_setting_shape_keys

        armature_original = obj.parent
        skinned_mesh_original = obj

        # Operate on temporary copy of skinned mesh and armature
        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh_original.select_set(True)
        armature_original.select_set(True)
        bpy.context.view_layer.objects.active = skinned_mesh_original
        bpy.ops.object.duplicate()
        skinned_mesh = bpy.context.object
        armature = skinned_mesh.parent

        # Apply armature object location to armature root bone and skinned mesh so that armature and skinned mesh are at origin before export
        context.view_layer.objects.active = armature
        context.view_layer.objects.active = armature
        armature_offset = Vector(armature.location)
        armature.location = (0, 0, 0)
        bpy.ops.object.mode_set(mode='EDIT')
        for edit_bone in armature.data.edit_bones:
            if edit_bone.name != "root":
                edit_bone.translate(armature_offset)

        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = skinned_mesh
        mesh_location = Vector(skinned_mesh.location)
        skinned_mesh.location = mesh_location + armature_offset
        bpy.ops.object.transform_apply(location = True)

        # Reset pose
        bpy.ops.object.smplx_reset_pose('EXEC_DEFAULT')

        if export_shape_keys != 'SHAPE_POSE':
            # Remove pose corrective shape keys
            print("Removing pose corrective shape keys")
            num_shape_keys = len(skinned_mesh.data.shape_keys.key_blocks.keys())

            current_shape_key_index = 0
            for index in range(0, num_shape_keys):
                bpy.context.object.active_shape_key_index = current_shape_key_index

                if bpy.context.object.active_shape_key is not None:
                    if bpy.context.object.active_shape_key.name.startswith('Pose'):
                        bpy.ops.object.shape_key_remove(all=False)
                    else:
                        current_shape_key_index = current_shape_key_index + 1        

        if export_shape_keys == 'NONE':
            # Bake and remove shape keys
            print("Baking shape and removing shape keys for shape")

            # Create shape mix for current shape
            bpy.ops.object.shape_key_add(from_mix=True)
            num_shape_keys = len(skinned_mesh.data.shape_keys.key_blocks.keys())

            # Remove all shape keys except newly added one
            bpy.context.object.active_shape_key_index = 0
            for count in range(0, num_shape_keys):
                bpy.ops.object.shape_key_remove(all=False)

        # Model (skeleton and skinned mesh) needs to have rotation of (90, 0, 0) when exporting so that it will have rotation (0, 0, 0) when imported into Unity
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        skinned_mesh.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = skinned_mesh
        bpy.ops.object.transform_apply(rotation = True)
        skinned_mesh.rotation_euler = (radians(90), 0, 0)
        skinned_mesh.select_set(False)

        armature.select_set(True)
        armature.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(rotation = True)
        armature.rotation_euler = (radians(90), 0, 0)

        # Select armature and skinned mesh for export
        skinned_mesh.select_set(True)

        # Rename armature and skinned mesh to not contain Blender copy suffix
        if "female" in skinned_mesh.name:
            gender = "female"
        else:
            gender = "male"

        target_mesh_name = "SMPLX-mesh-%s" % gender
        target_armature_name = "SMPLX-%s" % gender

        if target_mesh_name in bpy.data.objects:
            bpy.data.objects[target_mesh_name].name = "SMPLX-temp-mesh"
        skinned_mesh.name = target_mesh_name

        if target_armature_name in bpy.data.objects:
            bpy.data.objects[target_armature_name].name = "SMPLX-temp-armature"
        armature.name = target_armature_name

        bpy.ops.export_scene.fbx(filepath=self.filepath, use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)

        print("Exported: " + self.filepath)

        # Remove temporary copies of armature and skinned mesh
        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        armature.select_set(True)
        bpy.ops.object.delete()

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh_original.select_set(True)
        bpy.context.view_layer.objects.active = skinned_mesh_original

        if "SMPLX-temp-mesh" in bpy.data.objects:
            bpy.data.objects["SMPLX-temp-mesh"].name = target_mesh_name

        if "SMPLX-temp-armature" in bpy.data.objects:
            bpy.data.objects["SMPLX-temp-armature"].name = target_armature_name

        return {'FINISHED'}

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
        split.operator("scene.smplx_set_texture", text="Set")

class SMPLX_PT_Shape(bpy.types.Panel):
    bl_label = "Shape"
    bl_category = "SMPL-X"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.operator("object.smplx_random_shapes")
        split.operator("object.smplx_reset_shapes")
        col.separator()

        col.operator("object.smplx_snap_ground_plane")
        col.separator()

        col.operator("object.smplx_update_joint_locations")
        col.separator()
        row = col.row(align=True)
        split = row.split(factor=0.75, align=True)
        split.operator("object.smplx_random_expression_shapes")
        split.operator("object.smplx_reset_expression_shapes")

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

#        export_button = col.operator("export_scene.obj", text="Export OBJ [m]", icon='EXPORT')
#        export_button.global_scale = 1.0
#        export_button.use_selection = True
#        col.separator()

        row = col.row(align=True)
        row.operator("ed.undo", icon='LOOP_BACK')
        row.operator("ed.redo", icon='LOOP_FORWARDS')
        col.separator()

        (year, month, day) = bl_info["version"]
        col.label(text="Version: %s-%s-%s" % (year, month, day))

classes = [
    PG_SMPLXProperties,
    SMPLXAddGender,
    SMPLXSetTexture,
    SMPLXRandomShapes,
    SMPLXResetShapes,
    SMPLXRandomExpressionShapes,
    SMPLXResetExpressionShapes,
    SMPLXSnapGroundPlane,
    SMPLXUpdateJointLocations,
    SMPLXSetPoseshapes,
    SMPLXResetPoseshapes,
    SMPLXSetHandpose,
    SMPLXWritePose,
    SMPLXLoadPose,
    SMPLXResetPose,
    SMPLXExportUnityFBX,
    SMPLX_PT_Model,
    SMPLX_PT_Shape,
    SMPLX_PT_Pose,
    SMPLX_PT_Export
]

def register():
    from bpy.utils import register_class
    for cls in classes:
        bpy.utils.register_class(cls)

    # Store properties under WindowManager (not Scene) so that they are not saved in .blend files and always show default values after loading
    bpy.types.WindowManager.smplx_tool = PointerProperty(type=PG_SMPLXProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.WindowManager.smplx_tool

if __name__ == "__main__":
    register()
