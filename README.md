# About
This addon is an extension of the [SMPL-X Blender addon](https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon) created by Joachim Tesch and owned by the Max Planck Institute for Intelligent Systems. Meshcapade has licensed the SMPL model and its updates (including SMPL+H, SMPL-X and STAR) from Max Planck Institute, and is making this extension of the blender add-on available for commercial users who have an active license for the SMPL Model. 

For acadmemic uses, please visit: https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon. Or contact us at support@meshcapade.com

# SMPL-X and Meshcape Utilities Blender Add-on

This add-on allows you to add [SMPL-X](https://smpl-x.is.tue.mpg.de) skinned meshes to your current Blender scene. Each imported SMPL-X mesh consists of a shape specific rig, as well as shape keys (blend shapes) for shape, expression and pose correctives.

- Requirements:
  - Blender 2.92+ (tested with 2.93.0)
- Dev Requirements:
  - Python (for testing and building releases)
  - [Git LFS](https://git-lfs.github.com/) (for assets to build releases)
  - Flake8 (linting)
- Additional dependencies: None
- Used SMPL-X model: SMPL-X v1.1 with 10 shape components, 10 expression components

# Features

## SMPL-X

- Add female/male/neutral specific SMPL-X mesh to current scene
- Set sample albedo texture
- Set body shape from height and weight measurements
- Randomize/reset shape
- Update joint locations
- Position feet on ground plane (z=0)
- Randomize/reset face expression shape
- Enable/disable corrective poseshapes
- Change hand pose (flat, relaxed)
- Write current pose in SMPL-X theta notation to console
- Load pose from .pkl file (full pose with 55 joints in Rodrigues notation)
- FBX export to Unity

  - Exports mesh in default T-Pose with flat hands
  - Imported FBX will show up in Unity inspector without rotations and without scaling
  - Shape key export options:

    - Body shape and posecorrectives
    - Body shape without posecorrectives
    - None (bakes current body shape into mesh)

## Meshcapade Utilities

- Batch convert OBJ or FBX UV formats

## Installation
- Download [the latest release](https://github.com/Meshcapade/SMPL_blender_addon/releases/latest) zip file, `smplx_blender_YYYYMMDD.zip`. Do not unzip.
- Within Blender (2.92+), under Edit -> Preferences navigate to the Add-ons tab
- Click the Install button on the upper right, navigate to and select the downloaded zip file, and click 'Install Add-on'
- Once loaded, check the box next to the now appeared add-on title to activate.

![image](https://user-images.githubusercontent.com/538382/131877148-3d65f453-13ef-4c47-b56f-fd008930937a.png)

Enable sidebar in 3D Viewport>View>Sidebar, the tabs SMPL-X and Meshcapade Utilities should show along the sidebar.

![image](https://user-images.githubusercontent.com/538382/131878699-df5b7fd1-9bbc-47ae-9cb4-8fd319727c9d.png)


## Make Addon Release

Run:

```sh
python build/make_addon.py
```

This wraps all python files and assets in the `smplx_blender/data` folder into a zip that can be installed by Blender as an addon.

Be sure to have had Git LFS installed, and pulled, in order to obtain said assets.

## Notes

### SMPL-X

- The add-on GUI (gender, texture, hand pose) does not reflect the state of the currently selected SMPL-X model if you work with multiple models in one scene.
- To maintain editor responsiveness the add-on does not automatically recalculate joint locations when you change the shape manually via Blender shape keys. Use the `Update Joint Locations` button to update the joint locations after manual shape key change.
- To maintain editor responsiveness the add-on does not automatically recalculate the corrective pose shape keys when edit the armature pose. Use the `Update Pose Shapes` button to update the joint locations after pose changes.

### Meshcapade Utilities

- Launching Blender in a terminal will allow one to see the output of any running script. Particularly helpful for displaying progress of lengthier operations, as the UI does not show any info.

## Licenses

- The blender code available in this repo is licensed under the GPL 3.0 license:
https://www.gnu.org/licenses/gpl-3.0.en.html


- The SMPL, SMPL+H or SMPL-X model files used in or by this repo are available only under the SMPL-Commercial use license. Before using this product, please make sure you have an active SMPL Model commercial-use license. See models_license.md for further license information about SMPL & SMPL-X.


- Body meshes generated using this add-on are covered under the SMPL-Body Creative-Commons-BY license: https://smpl.is.tue.mpg.de/bodylicense.html

- Attribution for publications:
  - You agree to cite the most recent paper describing the model as specified on the SMPL-X website: <https://smpl-x.is.tue.mpg.de>

## Acknowledgements

- [Joachim Tesch](https://gitlab.tuebingen.mpg.de/jtesch), creator of the original blender addon for SMPL-X. This repo is a commercial-use extension for his addon which is available for academic use here: https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon

- Sergey Prokudin (rainbow texture data)

- Vassilis Choutas (betas-to-joints regressor)

- Lea Müller and Vassilis Choutas (measurements-to-betas regressor)

## Changelog

- 20210505: Initial release
- 20210525: Replaced vertices-to-joints regressor with beta-to-joints regressor. Added rainbow texture (CC BY-NC 4.0).
- 20210611: Added option to set shape from height and weight values for female and male models
- 20210820: Created Meshcapade fork

## Contact

- support@meshcapade.com
- tyler@meshcapade.com
