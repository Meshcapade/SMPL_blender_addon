from zipfile import ZipFile, ZIP_DEFLATED
from os import walk, listdir
from datetime import date
from pathlib import Path
build_script_dir = Path(__file__).parent
today = date.today()
filedate = today.strftime("%Y%m%d")
filename = '{}_{}.zip'.format("smplx_blender", filedate)
root_folder = build_script_dir.parent
addon_folder = root_folder / "smplx_blender"
data_folder = addon_folder / "data"

with ZipFile(filename, 'w') as z:

    # Adding python and data files
    for root, _, files in walk(addon_folder):
        for file in files:
            # Python files or data files
            if Path(file).suffix in ['.py', '.pyd'] or Path(root) == data_folder:
                filepath = Path(root) / Path(file)
                print("Adding '{}'".format(filepath))
                z.write(filepath, compress_type=ZIP_DEFLATED)

    # Adding README, LICENSE, and other root .md files
    for file in listdir(root_folder):
        if Path(file).suffix == ".md":
            filepath = Path(root_folder) / Path(file)
            print("Adding '{}'".format(filepath))
            z.write(filepath, compress_type=ZIP_DEFLATED)

print("Finished making release '{}', saved to current directory".format(filename))
