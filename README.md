# SMPL-X Blender Add-on

This add-on allows you to add gender specific [SMPL-X](https://smpl-x.is.tue.mpg.de) skinned meshes to your current Blender scene. Each imported SMPL-X mesh consist of a shape specific rig, as well as shape keys (blend shapes) for shape, expression and pose correctives.

Add-on features:
+ Add gender specific SMPL-X mesh to current scene
+ ~~Set mesh texture~~
+ Position feet on ground plane (z=0)
+ Randomize/reset shape
+ ~~Update joint locations~~
+ ~~Enable/disable corrective poseshapes~~
+ ~~Write current pose in SMPL-X theta notation to console~~
+ ~~FBX export to Unity~~
    + Imported FBX will show up in Unity inspector without rotations and without scaling
    + Shape key export options: 
        + Body shape + posecorrectives
        + Body shape only
        + None (bakes current body shape into mesh)

Requirements: Blender 2.80+

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
    + SMPL-X Blender model: `smplx_model_20210319.blend`
    + SMPL-X joint regressors:
        + `smplx_joint_regressor_female.npz`
        + `smplx_joint_regressor_male.npz`
        + `smplx_joint_regressor_neutral.npz`

+ Clone the repository and go to the `smplx_blender_addon` folder
+ Make `data` subfolder and copy the `.blend` and `.npz` files into the subfolder

### Creation of Blender add-on ZIP file
+ Go to `build` subfolder
+ Run `./make_zip.sh`
    + This will generate a new ZIP file with the plugin code and model files in the folder above `smplx_blender_addon`
    + Windows 10 users can use Windows Subsystem for Linux (WSL) for this step

## Usage

## TODO
+ Add npz joint regressor
+ Add pose correctives
+ Add sample body texture
    + Body part segmentation
    + Body texture
+ Use optimized joint regressor (beta_to_joints) for faster numpy joint recalc
+ Add Virtual Caliper (Regressor 2, 4 and 5)
+ Add Rigify control rig
+ FBX export to Unreal (Send to Unreal?)

## DONE
+ Position root node on floor when positioning on ground
+ Not needed: Add "Game Engine" model with separate blend shapes for positive and negative directions
  + Note: Unity 2018.3+ allows positive and negative blendshape weights and weights > 100
    + https://forum.unity.com/threads/removing-clamping-of-blendshapes-to-the-range-0-100.504973/
+ Remove scipy dependency from joint regressor .pkl by switching to compressed .npz
+ Use model with UV coordinates
+ Preserve current model transform and shape key state by using duplicate armature and skinned mesh for Unity export
    + Armature and mesh are exported without Blender number suffix for consistent display