"""Export the embedded Assimp scene, retaining positions, normals, and UVs."""
import ctypes as C
import sys
from pathlib import Path

library = Path('C:/Program Files/Allegorithmic/Substance Painter/assimp.dll')
import os
with os.add_dll_directory(str(library.parent)):
    assimp = C.CDLL(str(library))
assimp.aiImportFile.argtypes = [C.c_char_p, C.c_uint]
assimp.aiImportFile.restype = C.c_void_p
assimp.aiGetErrorString.restype = C.c_char_p
assimp.aiExportScene.argtypes = [C.c_void_p, C.c_char_p, C.c_char_p, C.c_uint]
assimp.aiExportScene.restype = C.c_int
assimp.aiReleaseImport.argtypes = [C.c_void_p]
scene = assimp.aiImportFile(os.fsencode(sys.argv[1]), 0)
if not scene:
    raise RuntimeError(assimp.aiGetErrorString())
try:
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    result = assimp.aiExportScene(scene, b'obj', os.fsencode(output), 0)
    if result:
        raise RuntimeError(assimp.aiGetErrorString())
    print('Exported embedded mesh:', output)
finally:
    assimp.aiReleaseImport(scene)
