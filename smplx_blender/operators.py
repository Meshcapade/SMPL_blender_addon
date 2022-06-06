import bpy
import os
import numpy as np
import json
from bpy.props import (
    BoolProperty,
    StringProperty,
    CollectionProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
)
from .globals import (
    SMPLX_MODELFILE,
    NUM_SMPLX_BODYJOINTS,
    NUM_SMPLX_HANDJOINTS,
    NUM_SMPLX_JOINTS,
    SMPLX_JOINT_NAMES,
)
from .blender import (
    set_pose_from_rodrigues,
    rodrigues_from_pose,
)
from mathutils import Vector, Quaternion
from math import radians


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
        except Exception:
            return False

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
    bl_idname = "object.smplx_set_texture"
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
        except Exception:
            return False

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
        if bpy.context.space_data:
            if bpy.context.space_data.type == 'VIEW_3D':
                bpy.context.space_data.shading.type = 'MATERIAL'

        return {'FINISHED'}


class SMPLXMeasurementsToShape(bpy.types.Operator):
    bl_idname = "object.smplx_measurements_to_shape"
    bl_label = "Measurements To Shape"
    bl_description = ("Calculate and set shape parameters for specified measurements")
    bl_options = {'REGISTER', 'UNDO'}

    betas_regressor_female = None
    betas_regressor_male = None
    # betas_regressor_neutral = None

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE'))
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        if self.betas_regressor_female is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_measurements_to_betas_female.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.betas_regressor_female = (
                    np.asarray(data["A"]).reshape(-1, 2),
                    np.asarray(data["B"]).reshape(-1, 1),
                )

        if self.betas_regressor_male is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_measurements_to_betas_male.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.betas_regressor_male = (
                    np.asarray(data["A"]).reshape(-1, 2),
                    np.asarray(data["B"]).reshape(-1, 1),
                )

        if "female" in obj.name:
            (A, B) = self.betas_regressor_female
        elif "male" in obj.name:
            (A, B) = self.betas_regressor_male
        else:
            # (A, B) = self.betas_regressor_neutral
            self.report({"ERROR"}, "No measurements-to-betas regressor available for neutral model")
            return {"CANCELLED"}

        # Calculate beta values from measurements
        height_m = context.window_manager.smplx_tool.smplx_height
        height_cm = height_m * 100.0
        weight_kg = context.window_manager.smplx_tool.smplx_weight

        v_root = pow(weight_kg, 1.0/3.0)
        measurements = np.asarray([[height_cm], [v_root]])
        betas = A @ measurements + B

        num_betas = betas.shape[0]
        for i in range(num_betas):
            name = f"Shape{i:03d}"
            key_block = obj.data.shape_keys.key_blocks[name]
            value = betas[i, 0]

            # Adjust key block min/max range to value
            if value < key_block.slider_min:
                key_block.slider_min = value
            elif value > key_block.slider_max:
                key_block.slider_max = value

            key_block.value = value

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}


class SMPLXRandomShape(bpy.types.Operator):
    bl_idname = "object.smplx_random_shape"
    bl_label = "Random"
    bl_description = ("Sets all shape blend shape keys to a random value")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                key_block.value = np.random.normal(0.0, 1.0)

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}


class SMPLXResetShape(bpy.types.Operator):
    bl_idname = "object.smplx_reset_shape"
    bl_label = "Reset"
    bl_description = ("Resets all blend shape keys for shape")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                key_block.value = 0.0

        bpy.ops.object.smplx_update_joint_locations('EXEC_DEFAULT')

        return {'FINISHED'}


class SMPLXRandomExpressionShape(bpy.types.Operator):
    bl_idname = "object.smplx_random_expression_shape"
    bl_label = "Random Face Expression"
    bl_description = ("Sets all face expression blend shape keys to a random value")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Exp"):
                key_block.value = np.random.uniform(-2, 2)

        return {'FINISHED'}


class SMPLXResetExpressionShape(bpy.types.Operator):
    bl_idname = "object.smplx_reset_expression_shape"
    bl_label = "Reset"
    bl_description = ("Resets all blend shape keys for face expression")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh is active object
            return context.object.type == 'MESH'
        except Exception:
            return False

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
        except Exception:
            return False

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
        object_eval.to_mesh_clear()  # Remove temporary mesh

        # Adjust height of armature so that lowest vertex is on ground plane.
        # Do not apply new armature location transform so that we are later able to
        # show loaded poses at their desired height.
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
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        if self.j_regressor_female is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_betas_to_joints_female.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.j_regressor_female = (np.asarray(data["betasJ_regr"]), np.asarray(data["template_J"]))

        if self.j_regressor_male is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_betas_to_joints_male.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.j_regressor_male = (np.asarray(data["betasJ_regr"]), np.asarray(data["template_J"]))

        if self.j_regressor_neutral is None:
            path = os.path.dirname(os.path.realpath(__file__))
            regressor_path = os.path.join(path, "data", "smplx_betas_to_joints_neutral.json")
            with open(regressor_path) as f:
                data = json.load(f)
                self.j_regressor_neutral = (np.asarray(data["betasJ_regr"]), np.asarray(data["template_J"]))

        if "female" in obj.name:
            (betas_to_joints, template_j) = self.j_regressor_female
        elif "male" in obj.name:
            (betas_to_joints, template_j) = self.j_regressor_male
        else:
            (betas_to_joints, template_j) = self.j_regressor_neutral

        # Get beta shapes
        betas = []
        for key_block in obj.data.shape_keys.key_blocks:
            if key_block.name.startswith("Shape"):
                betas.append(key_block.value)
        betas = np.array(betas)

        joint_locations = betas_to_joints @ betas + template_j

        # Set new bone joint locations
        armature = obj.parent
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        for index in range(NUM_SMPLX_JOINTS):
            bone = armature.data.edit_bones[SMPLX_JOINT_NAMES[index]]
            bone.head = (0.0, 0.0, 0.0)
            bone.tail = (0.0, 0.0, 0.1)

            # Convert SMPL-X joint locations to Blender joint locations
            joint_location_smplx = joint_locations[index]
            bone_start = Vector((
                joint_location_smplx[0],
                -joint_location_smplx[2],
                joint_location_smplx[1],
            ))
            bone.translate(bone_start)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = obj

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
            return (
                ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or
                (context.object.type == 'ARMATURE')
            )
        except Exception:
            return False

    # https://github.com/gulvarol/surreal/blob/master/datageneration/main_part1.py
    # Computes rotation matrix through Rodrigues formula as in cv2.Rodrigues
    def rodrigues_to_mat(self, rotvec):
        theta = np.linalg.norm(rotvec)
        r = (rotvec/theta).reshape(3, 1) if theta > 0. else rotvec
        cost = np.cos(theta)
        mat = np.asarray([
            [0, -r[2], r[1]],
            [r[2], 0, -r[0]],
            [-r[1], r[0], 0],
        ])
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
            return (
                ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or
                (context.object.type == 'ARMATURE')
            )
        except Exception:
            return False

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
            return (
                ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or
                (context.object.type == 'ARMATURE')
            )
        except Exception:
            return False

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

        hand_pose = np.concatenate((left_hand_pose, right_hand_pose)).reshape(-1, 3)

        hand_joint_start_index = 1 + NUM_SMPLX_BODYJOINTS + 3
        for index in range(2 * NUM_SMPLX_HANDJOINTS):
            pose_rodrigues = hand_pose[index]
            bone_name = SMPLX_JOINT_NAMES[index + hand_joint_start_index]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

        # Update corrective poseshapes if used
        if context.window_manager.smplx_tool.smplx_corrective_poseshapes:
            bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

        return {'FINISHED'}


class SMPLXWritePose(bpy.types.Operator, ExportHelper):
    bl_idname = "object.smplx_write_pose"
    bl_label = "Write Pose To File"
    bl_description = ("Writes SMPL-X pose file")
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".json"

    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return (context.object.type == 'MESH') or (context.object.type == 'ARMATURE')
        except Exception:
            return False

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

        pose_data = {
            "pose": pose,
        }

        with open(self.filepath, "w") as f:
            json.dump(pose_data, f)

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
            return (
                ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or
                (context.object.type == 'ARMATURE')
            )
        except Exception:
            return False

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
    bl_label = "Load Pose From File"
    bl_description = ("Load SMPL-X pose from file")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'}
    )


    @classmethod
    def poll(cls, context):
        try:
            # Enable button only if mesh or armature is active object
            return (
                ((context.object.type == 'MESH') and (context.object.parent.type == 'ARMATURE')) or
                (context.object.type == 'ARMATURE')
            )
        except Exception:
            return False

    def execute(self, context):
        obj = bpy.context.object

        if obj.type == 'MESH':
            armature = obj.parent
        else:
            armature = obj
            obj = armature.children[0]
            context.view_layer.objects.active = obj  # mesh needs to be active object for recalculating joint locations

        print("Loading: " + self.filepath)

        with open(self.filepath, "rb") as f:
            pose_data = json.load(f)
            
        pose = np.array(pose_data["pose"]).reshape(NUM_SMPLX_JOINTS, 3)

        for index in range(NUM_SMPLX_JOINTS):
            pose_rodrigues = pose[index]
            bone_name = SMPLX_JOINT_NAMES[index]
            set_pose_from_rodrigues(armature, bone_name, pose_rodrigues)

        # Activate corrective poseshapes
        bpy.ops.object.smplx_set_poseshapes('EXEC_DEFAULT')

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
        except Exception:
            return False

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

        # Apply armature object location to armature root bone and skinned mesh so
        # that armature and skinned mesh are at origin before export
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
        bpy.ops.object.transform_apply(location=True)

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

        # Model (skeleton and skinned mesh) needs to have rotation of (90, 0, 0) when
        # exporting so that it will have rotation (0, 0, 0) when imported into Unity
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        skinned_mesh.select_set(True)
        skinned_mesh.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = skinned_mesh
        bpy.ops.object.transform_apply(rotation=True)
        skinned_mesh.rotation_euler = (radians(90), 0, 0)
        skinned_mesh.select_set(False)

        armature.select_set(True)
        armature.rotation_euler = (radians(-90), 0, 0)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(rotation=True)
        armature.rotation_euler = (radians(90), 0, 0)

        # Select armature and skinned mesh for export
        skinned_mesh.select_set(True)

        # Rename armature and skinned mesh to not contain Blender copy suffix
        if "female" in skinned_mesh.name:
            gender = "female"
        elif "male" in skinned_mesh.name:
            gender = "male"
        else:
            gender = "neutral"

        target_mesh_name = "SMPLX-mesh-%s" % gender
        target_armature_name = "SMPLX-%s" % gender

        if target_mesh_name in bpy.data.objects:
            bpy.data.objects[target_mesh_name].name = "SMPLX-temp-mesh"
        skinned_mesh.name = target_mesh_name

        if target_armature_name in bpy.data.objects:
            bpy.data.objects[target_armature_name].name = "SMPLX-temp-armature"
        armature.name = target_armature_name

        bpy.ops.export_scene.fbx(
            filepath=self.filepath,
            use_selection=True,
            apply_scale_options="FBX_SCALE_ALL",
            add_leaf_bones=False,
        )

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


class SMPLExecuteConvertUV(bpy.types.Operator):
    bl_idname = "object.smpl_execute_convert_uv"
    bl_label = "Convert UVs"
    bl_description = ("Convert the source SMPL files with target UV")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        num_source_objs = len(context.window_manager.smpl_tool.smpl_uv_source_objs)
        num_source_fbxs = len(context.window_manager.smpl_tool.smpl_uv_source_fbxs)
        num_source_items = num_source_objs + num_source_fbxs
        output_dir = context.window_manager.smpl_tool.smpl_uv_output_dir
        try:
            return num_source_items > 0 and output_dir
        except Exception:
            return False

    def execute(self, context):
        from .blender import (
            import_obj,
            import_fbx,
            create_collection,
            move_object_to_collection,
            destroy_collection,
            transfer_uv,
            change_active_collection,
            export_object,
        )
        from .globals import (
            RESOLUTIONS,
            FBX_TYPE,
            OBJ_TYPE,
        )
        from .utils import (
            get_uv_obj_path,
        )

        # Context variables
        wm = bpy.context.window_manager
        smpl_tool = wm.smpl_tool

        uv_type = smpl_tool.smpl_uv_type
        output_dir = smpl_tool.smpl_uv_output_dir

        # Gathering the source items into one list
        source_objs = smpl_tool.smpl_uv_source_objs
        source_fbxs = smpl_tool.smpl_uv_source_fbxs
        source_items = (
            list((o, OBJ_TYPE) for o in source_objs) +
            list((f, FBX_TYPE) for f in source_fbxs)
        )

        # Get required uv template paths
        uv_template_type_res_path_tuples = [
            (uv_type, res, get_uv_obj_path(uv_type=uv_type, resolution=res))
            for res in RESOLUTIONS
        ]

        # Load template OBJs into collection
        uv_template_collection = create_collection(name="UV Templates")

        # Create lookup dictionaries for the UV mesh templates
        UV_RES_OBJS = {}
        UV_RES_VERTEX_MAPPING = {}
        for (uv_type, res, uv_obj_path) in uv_template_type_res_path_tuples:
            uv_obj = import_obj(uv_obj_path)
            move_object_to_collection(uv_obj, uv_template_collection)
            UV_RES_OBJS[res] = uv_obj
            num_verts = len(uv_obj.data.vertices)
            UV_RES_VERTEX_MAPPING[num_verts] = res

        # Percentage progress on mouse
        step_size = 100.0 / len(source_items)
        wm.progress_begin(0.0, 100.0)

        for i, (item, item_type) in enumerate(source_items):
            # Progress mouse indicator
            wm.progress_update(i * step_size)

            src_path = item.name
            src_dir, src_filename = os.path.split(src_path)
            dst_path = os.path.join(output_dir, src_filename)

            # For cleanup purposes, having these operations take place in a new collection
            scratch_collection = create_collection(name="Scratch")
            change_active_collection(collection=scratch_collection)

            # Load src object and get resolution
            if item_type == OBJ_TYPE:
                src_obj = import_obj(src_path)
                src_mesh_obj = src_obj
            elif item_type == FBX_TYPE:
                src_obj = import_fbx(src_path)
                # If root object is an armature (typical for a rigged FBX asset), get the associated mesh
                if src_obj.type == 'ARMATURE':
                    src_mesh_obj = next(child for child in src_obj.children if child.type == 'MESH')
                elif src_obj.type == 'MESH':
                    src_mesh_obj = src_obj
                else:
                    # Imported FBX not valid
                    print("Imported FBX does not have a mesh object, skipping")
                    destroy_collection(collection=scratch_collection)
                    continue

            # Determine the resolution of the imported asset
            num_src_vertices = len(src_mesh_obj.data.vertices)
            if num_src_vertices in UV_RES_VERTEX_MAPPING:
                resolution = UV_RES_VERTEX_MAPPING[num_src_vertices]
            else:
                # Imported object not valid
                print("Imported object '{}' has invalid vertex count of {}, skipping".format(
                    src_obj.name,
                    num_src_vertices,
                ))
                destroy_collection(collection=scratch_collection)
                continue

            # Target UV mesh with matching resolution
            target_uv_mesh_obj = UV_RES_OBJS[resolution]

            print("Transferring {} resolution '{}' type UV map to {} '{}'".format(
                resolution,
                uv_type,
                item_type,
                src_obj.name,
            ))
            transfer_uv(mesh_from=target_uv_mesh_obj, mesh_to=src_mesh_obj)

            # Exporting
            print("Exporting UV updated object '{}' to {}".format(src_obj.name, dst_path))
            export_object(obj=src_obj, export_type=item_type, path=dst_path)
            # Destroying the scratch collection to cleanup the scene
            destroy_collection(collection=scratch_collection)

        destroy_collection(collection=uv_template_collection)
        wm.progress_end()
        return {'FINISHED'}


class SMPLSetSourceObjs(bpy.types.Operator, ImportHelper):
    bl_idname = "object.smpl_set_source_objs"
    bl_label = "Set Source OBJs"
    bl_description = ("Set source obj files of SMPL bodies to convert UVs")
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".obj"

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
    )

    files: CollectionProperty(type=bpy.types.PropertyGroup)

    def execute(self, context):
        context.window_manager.smpl_tool.smpl_uv_source_objs.clear()
        folder = (os.path.dirname(self.filepath))
        for f in self.files:
            so = context.window_manager.smpl_tool.smpl_uv_source_objs.add()
            so.name = os.path.join(folder, f.name)
        return {'FINISHED'}


class SMPLClearSourceObjs(bpy.types.Operator):
    bl_idname = "object.smpl_clear_source_objs"
    bl_label = "Clear Source OBJs"
    bl_description = ("Clear source obj files of SMPL bodies to convert UVs")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.window_manager.smpl_tool.smpl_uv_source_objs.clear()
        return {'FINISHED'}


class SMPLSetSourceFbxs(bpy.types.Operator, ImportHelper):
    bl_idname = "object.smpl_set_source_fbxs"
    bl_label = "Set Source FBXs"
    bl_description = ("Set source fbx files of SMPL bodies to convert UVs")
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".fbx"

    filter_glob: StringProperty(
        default="*.fbx",
        options={'HIDDEN'},
    )

    files: CollectionProperty(type=bpy.types.PropertyGroup)

    def execute(self, context):
        context.window_manager.smpl_tool.smpl_uv_source_fbxs.clear()
        folder = (os.path.dirname(self.filepath))
        for f in self.files:
            so = context.window_manager.smpl_tool.smpl_uv_source_fbxs.add()
            so.name = os.path.join(folder, f.name)
        return {'FINISHED'}


class SMPLClearSourceFbxs(bpy.types.Operator):
    bl_idname = "object.smpl_clear_source_fbxs"
    bl_label = "Clear Source FBXs"
    bl_description = ("Clear source fbx files of SMPL bodies to convert UVs")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.window_manager.smpl_tool.smpl_uv_source_fbxs.clear()
        return {'FINISHED'}


OPERATORS = [
    SMPLXAddGender,
    SMPLXSetTexture,
    SMPLXMeasurementsToShape,
    SMPLXRandomShape,
    SMPLXResetShape,
    SMPLXRandomExpressionShape,
    SMPLXResetExpressionShape,
    SMPLXSnapGroundPlane,
    SMPLXUpdateJointLocations,
    SMPLXSetPoseshapes,
    SMPLXResetPoseshapes,
    SMPLXSetHandpose,
    SMPLXWritePose,
    SMPLXResetPose,
    SMPLXLoadPose,
    SMPLXExportUnityFBX,
    SMPLExecuteConvertUV,
    SMPLSetSourceObjs,
    SMPLClearSourceObjs,
    SMPLSetSourceFbxs,
    SMPLClearSourceFbxs,
]
