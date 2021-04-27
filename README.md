# SMPL-X Blender Add-on

This add-on allows you to add [SMPL-X](https://smpl-x.is.tue.mpg.de) skinned meshes to your current Blender scene. Each imported SMPL-X mesh consist of a shape specific rig, as well as shape keys (blend shapes) for shape, expression and pose correctives.

Add-on features:
+ Add female/male/neutral specific SMPL-X mesh to current scene
+ Set sample albedo texture
+ Position feet on ground plane (z=0)
+ Randomize/reset shape
+ Update joint locations
+ Randomize/reset face expression shape
+ Enable/disable corrective poseshapes
+ Change hand pose (flat, relaxed)
+ Write current pose in SMPL-X theta notation to console
+ Load pose from .pkl file
+ ~~FBX export to Unity~~
    + Imported FBX will show up in Unity inspector without rotations and without scaling
    + Shape key export options: 
        + Body shape + posecorrectives
        + Body shape only
        + None (bakes current body shape into mesh)
+ ~~FBX export to Unreal Engine~~

Requirements: Blender 2.80+, tested with 2.92.0

Additional dependencies: None

## Installation
1. Blender>Edit>Preferences>Add-ons>Install
2. Select SMPL-X for Blender add-on ZIP file and install
3. Enable SMPL-X for Blender add-on
4. Enable sidebar in 3D Viewport>View>Sidebar
5. SMPL-X tool will show up in sidebar

## Developer information

The information in this section is only needed when you clone the repository to make changes to the plugin code and want to build a new add-on installer.

### Installation of model
+ Requirements
    + SMPL-X Blender model: `smplx_model_20210415.blend`
    + SMPL-X joint regressors:
        + `smplx_joint_regressor_female.npz`
        + `smplx_joint_regressor_male.npz`
        + `smplx_joint_regressor_neutral.npz`
    + SMPL-X handposes:
        + `smplx_handposes.npz`

+ Clone the repository and go to the `smplx_blender_addon` folder
+ Copy the `.blend` and `.npz` files into the `data` subfolder

### Creation of Blender add-on ZIP file
+ Go to `build` subfolder
+ Run `./make_zip.sh`
    + This will generate a new ZIP file with the plugin code and model files in the folder above `smplx_blender_addon`
    + Windows 10 users can use Windows Subsystem for Linux (WSL) for this step

## Usage
+ TODO
## Acknowledgements
+ We thank [Meshcapade](https://meshcapade.com/) for providing the SMPL-X female/male sample textures (`smplx_texture_f_alb.png`, `smplx_texture_m_alb.png`) under [Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/) license.

## TODO
+ FBX export to Unreal (Send to Unreal)
+ Test Unity export
+ Add sample body texture
    + Body part segmentation
+ Use optimized joint regressor (beta_to_joints) for faster numpy joint recalc
+ Add Virtual Caliper (Regressor 2, 4 and 5)
+ Add Rigify control rig

## DONE
+ Position root node on floor when positioning on ground
+ Not needed: Add "Game Engine" model with separate blend shapes for positive and negative directions
  + Note: Unity 2018.3+ allows positive and negative blendshape weights and weights > 100
    + https://forum.unity.com/threads/removing-clamping-of-blendshapes-to-the-range-0-100.504973/
+ Remove torch dependency from joint regressor .pkl by switching to compressed .npz
+ Use model with UV coordinates
+ Preserve current model transform and shape key state by using duplicate armature and skinned mesh for Unity export
    + Armature and mesh are exported without Blender number suffix for consistent display
+ Add sample body texture
    + Body texture
+ Set hand pose when loading .pkl which has hand pose
+ Fix hand poses when relative to relaxed hand pose
