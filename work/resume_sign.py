import asyncio
from sign_session import ap, OUT, WORK

async def main():
    await ap("ap_project_open", path=str(OUT / "MOZU_Weathered_Illuminated.arm"))
    await asyncio.sleep(3)
    await ap("ap_set_config", rp_bloom=1.0, rp_grain=0.0)
    await ap("ap_pack_assets")
    await ap("ap_layer_select", name="03 - Red illuminated inset")
    await ap("ap_material_select", name="03 - Red illuminated inset")
    await ap("ap_material_update")
    await ap("ap_layer_update", name="03 - Red illuminated inset", visible=True)
    await ap("ap_view_set", view="front", orbit_x=0.13, orbit_y=-0.10)
    await asyncio.sleep(3)
    previews = OUT / "previews"
    previews.mkdir(exist_ok=True)
    await ap("ap_capture_viewport", path=str(previews / "ArmorPaint_Front.png"), width=1800,height=1000,include_image=False)
    await ap("ap_view_set", view="back", orbit_x=0.25, orbit_y=-0.12)
    await asyncio.sleep(2)
    await ap("ap_capture_viewport", path=str(previews / "ArmorPaint_Back.png"), width=1800,height=1000,include_image=False)
    await ap("ap_view_set", view="front", orbit_x=0.13, orbit_y=-0.1)
    await ap("ap_project_save")
    await asyncio.sleep(4)
    await ap("ap_project_get_info")
    await ap("ap_layer_list")

asyncio.run(main())
