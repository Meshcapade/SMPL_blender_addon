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

## License

- Generated body mesh data using this add-on:

  - Licensed under SMPL-X Model License

    - <https://smpl-x.is.tue.mpg.de/modellicense>

- See LICENSE.md for further license information including commercial licensing

- Attribution for publications:

  - You agree to cite the most recent paper describing the model as specified on the SMPL-X website: <https://smpl-x.is.tue.mpg.de>

## Acknowledgements

- We thank [Meshcapade](https://meshcapade.com/) for providing the SMPL-X female/male sample textures (`smplx_texture_f_alb.png`, `smplx_texture_m_alb.png`) under [Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/) license.

- Sergey Prokudin (rainbow texture data)

- Vassilis Choutas (betas-to-joints regressor)

- Lea Müller and Vassilis Choutas (measurements-to-betas regressor)

## Changelog

- 20210505: Initial release
- 20210525: Replaced vertices-to-joints regressor with beta-to-joints regressor. Added rainbow texture (CC BY-NC 4.0).
- 20210611: Added option to set shape from height and weight values for female and male models
- 20210820: Created Meshcapade fork

## Contact

- smplx-blender@tue.mpg.de
- tyler@meshcapade.com
