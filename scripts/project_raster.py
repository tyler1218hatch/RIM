import os
import arcpy
import sys
from create_project import make_folder

arcpy.env.overwriteOutput = True

# path to folder with unprojected rasters
in_folder = r"C:\Users\karen\Box\Thesis_sites\16010203\temple_a\DroneDeploy"

# create folder for projected outputs
out_folder = make_folder(in_folder, 'Projected')

srs_template = r"C:\Users\karen\Box\0_ET_AL\NonProject\etal_Drone\2019\Inundation_sites\Utah\TempleFork\site_trib_b\10262019\GIS\dam_crests.shp"

# Project drone deploy output rasters
def project_rasters(in_folder, out_folder, srs_template):

    spatial_reference = arcpy.Describe(srs_template).spatialReference

    # Orthomosaic
    arcpy.ProjectRaster_management(os.path.join(in_folder, 'orthomosaic150ft.tif'), os.path.join(out_folder, 'orthomosaic.tif'), spatial_reference, 'NEAREST', '.02')

    # DEM
    arcpy.ProjectRaster_management(os.path.join(in_folder, 'DEM_150ft.tif'), os.path.join(out_folder, 'DEM.tif'), spatial_reference, 'NEAREST', '.02')

    # Orthomosaic
    arcpy.ProjectRaster_management(os.path.join(in_folder, 'NDVI_150ft.tif'), os.path.join(out_folder, 'NDVI.tif'), spatial_reference, 'NEAREST', '.02')

project_rasters(in_folder, out_folder, srs_template)

