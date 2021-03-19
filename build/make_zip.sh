#!/bin/bash
pushd ../..
filedate=$(date '+%Y%m%d')
zip ./smplx_blender_addon-$filedate.zip smplx_blender_addon/*.py smplx_blender_addon/data/*.npz smplx_blender_addon/data/*.blend
popd
