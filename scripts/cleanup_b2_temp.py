import bpy
for c in list(bpy.data.collections):
    if c.name in {"CUSTOM_52869536_HENDERSON_B2", "CUSTOM_297109890_IFC1_B2", "13_Bespoke_Landmarks_B2_Hopewell", "13_Bespoke_The_Center_B2", "13_Bespoke_Exchange_Highcliff_B2"}:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c, do_unlink=True)
for o in list(bpy.data.objects):
    if o.name.startswith(("CUSTOM_590814694_HSBC_Main_Building", "CUSTOM_200915642_One_Island_East", "CUSTOM_52869536_The_Henderson_B2", "CUSTOM_297109890_IFC1_", "BESPOKE_B2_2762122396_Hopewell")):
        bpy.data.objects.remove(o, do_unlink=True)
print("B2 partial artifacts removed")
