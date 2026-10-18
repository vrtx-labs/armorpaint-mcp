import asyncio
import json
from pathlib import Path
from sign_session import ap, OUT, WORK

SOURCE = OUT / "source_maps"
PROJECT = OUT / "MOZU_Weathered_Illuminated.arm"

async def value(node, socket, v):
    await ap("ap_node_set_value", id=node, kind="float", socket=socket, value=v)

async def main():
    await ap("ap_texture_resolution", size=4096)
    await ap("ap_view_set", view="front")
    images = ["steel_base", "steel_roughness", "steel_normal", "oxidation_base", "oxidation_roughness",
              "red_diffuser_base", "red_diffuser_roughness", "red_diffuser_normal"]
    image_index = {}
    for index, name in enumerate(images):
        await ap("ap_import_asset", path=str(SOURCE / f"{name}.png"))
        image_index[name] = index

    async def image_node(name, x, y, linear=False):
        result = await ap("ap_node_add", type="TEX_IMAGE", x=x, y=y)
        node = result["id"]
        await ap("ap_node_set_value", id=node, kind="button", button=0, value=image_index[name])
        if linear:
            await ap("ap_node_set_value", id=node, kind="button", button=1, value=1)
        return node

    async def material(name, base, rough, normal, metal, emission, alpha):
        await ap("ap_material_create", name=name)
        nodes = await ap("ap_node_list")
        output = next(int(n.split(",")[0]) for n in nodes["nodes"].split(";") if ",OUTPUT_MATERIAL_PBR," in n)
        base_node = await image_node(base, -500, 0)
        rough_node = await image_node(rough, -500, 300, linear=True)
        normal_node = await image_node(normal, -500, 600, linear=True)
        for node, target in [(base_node,0),(rough_node,3),(normal_node,5)]:
            await ap("ap_node_connect", from_id=node, from_socket=0, to_id=output, to_socket=target)
        if alpha:
            await ap("ap_node_connect", from_id=base_node, from_socket=1, to_id=output, to_socket=1)
        await value(output,2,1)
        await value(output,4,metal)
        await value(output,6,emission)
        await value(output,7,0)
        await ap("ap_material_update")
        await ap("ap_layer_create", name=name, kind="fill")
        await asyncio.sleep(1)

    await material("01 - Galvanized body and zinc lip", "steel_base", "steel_roughness", "steel_normal", 0.88,0,False)
    await material("02 - Oxidation and rain patina", "oxidation_base", "oxidation_roughness", "steel_normal",0.03,0,True)
    await material("03 - Red illuminated inset", "red_diffuser_base", "red_diffuser_roughness", "red_diffuser_normal",0,1,True)
    await ap("ap_layer_delete", name="Layer 1")
    await ap("ap_layer_list")
    await asyncio.sleep(3)
    await ap("ap_project_save_as", path=str(PROJECT))
    await asyncio.sleep(4)
    assert PROJECT.exists() and PROJECT.stat().st_size > 100000
    await ap("ap_capture_viewport", path=str(WORK / "sign-front.png"), width=1800, height=1000, include_image=False)
    exports = OUT / "textures"
    exports.mkdir(exist_ok=True)
    await ap("ap_export_pbr", directory=str(exports), name="MOZU_Sign")
    await asyncio.sleep(3)
    print("Exported:", [p.name for p in exports.iterdir()])

asyncio.run(main())
