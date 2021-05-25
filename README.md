# SMPL-X Blender Add-on

This add-on allows you to add [SMPL-X](https://smpl-x.is.tue.mpg.de) skinned meshes to your current Blender scene. Each imported SMPL-X mesh consists of a shape specific rig, as well as shape keys (blend shapes) for shape, expression and pose correctives.

+ Requirements: Blender 2.80+, tested with 2.92.0
+ Additional dependencies: None
+ Used SMPL-X model: SMPL-X v1.1 with 10 shape components, 10 expression components

# Features
+ Add female/male/neutral specific SMPL-X mesh to current scene
+ Set sample albedo texture
+ Position feet on ground plane (z=0)
+ Randomize/reset shape
+ Update joint locations
+ Randomize/reset face expression shape
+ Enable/disable corrective poseshapes
+ Change hand pose (flat, relaxed)
+ Write current pose in SMPL-X theta notation to console
+ Load pose from .pkl file (full pose with 55 joints in Rodrigues notation)
+ FBX export to Unity
    + Exports mesh in default T-Pose with flat hands
    + Imported FBX will show up in Unity inspector without rotations and without scaling
    + Shape key export options: 
        + Body shape and posecorrectives
        + Body shape without posecorrectives
        + None (bakes current body shape into mesh)
## Installation
1. Blender>Edit>Preferences>Add-ons>Install
2. Select downloaded SMPL-X for Blender add-on ZIP file (`smplx_blender_addon-YYYYMMDD.zip`) and install
3. Enable SMPL-X for Blender add-on
4. Enable sidebar in 3D Viewport>View>Sidebar
5. SMPL-X tool will show up in sidebar

## Notes
+ The add-on GUI (gender, texture, hand pose) does not reflect the state of the currently selected SMPL-X model if you work with multiple models in one scene.
+ To maintain editor responsiveness the add-on does not automatically recalculate joint locations when you change the shape manually via Blender shape keys. Use the `Update Joint Locations` button to update the joint locations after manual shape key change.
+ To maintain editor responsiveness the add-on does not automatically recalculate the corrective pose shape keys when edit the armature pose. Use the `Update Pose Shapes` button to update the joint locations after pose changes.

## License
+ Generated body mesh data using this add-on:
    + Licensed under SMPL-X Model License
        + https://smpl-x.is.tue.mpg.de/modellicense

+ See LICENSE.md for further license information including commercial licensing

+ Attribution for publications: 
    + You agree to cite the most recent paper describing the model as specified on the SMPL-X website: https://smpl-x.is.tue.mpg.de

## Acknowledgements
+ We thank [Meshcapade](https://meshcapade.com/) for providing the SMPL-X female/male sample textures (`smplx_texture_f_alb.png`, `smplx_texture_m_alb.png`) under [Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/) license.

+ Sergey Prokudin: rainbow texture data

## Changelog
+ 20210505: Initial release
+ 20210525: Replaced vertices-to-joints regressor with beta-to-joints regressor. Added rainbow texture (CC BY-NC 4.0).

## Contact
+ smplx-blender@tue.mpg.de
