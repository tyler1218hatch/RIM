# Description: Create project folders and empty shapefiles for the first Data capture event

import os
import arcpy
import sys
from settings import ModelConfig
#import uuid
#from lib.project import RSProject, RSLayer
#from lib.util import safe_makedirs
from lib.loghelper import Logger
#import numpy
#import csv
#import pandas as pd
#import time
#import datetime
arcpy.CheckOutExtension('Spatial')

cfg = ModelConfig('http://xml.riverscapes.xyz/Projects/XSD/V1/Inundation.xsd')


##############################
# STEP 1 - CREATE PROJECT

# Inputs
def main(project_path, srs_template, image_path, DEM_path, hs_path, BRAT_path, VBET_path, site_name, huc, am_dc, am_inun, am_thal, am_vb, am_vbcen):
    BRAT_path = check_optional(BRAT_path)
    VBET_path = check_optional(VBET_path)
    am_dc = check_optional(am_dc)
    am_inun = check_optional(am_inun)
    am_thal = check_optional(am_thal)
    am_vb = check_optional(am_vb)
    am_vbcen = check_optional(am_vbcen)

    already_mapped = [am_dc, am_inun, am_thal, am_vb, am_vbcen]
    # create project folders and empty mapping shapefiles for first DCE
    make_project(project_path, srs_template, image_path, site_name, huc, BRAT_path, VBET_path, DEM_path, hs_path, already_mapped)

# Description: Create project folders and empty shapefiles for the first Data capture event



# Functions from BAAT

def check_optional(in_parameter):
    if in_parameter in ['#', '', None]:
        return False
    else:
        return in_parameter
def make_folder(path_to_location, new_folder_name):
    """
    Makes a folder and returns the path to it
    :param path_to_location: Where we want to put the folder
    :param new_folder_name: What the folder will be called
    :return: String
    """
    newFolder = os.path.join(path_to_location, new_folder_name)
    if not os.path.exists(newFolder):
        os.mkdir(newFolder)
    return newFolder

# RIM project creation functions


def make_project(project_path, srs_template, image_path, site_name, huc, BRAT_path, VBET_path, DEM_path, hs_path, already_mapped):
    """
    Creates project folders
    :param project_path: where we want project to be located
    """

    am_dc = already_mapped[0]
    am_inun = already_mapped[1]
    am_thal = already_mapped[2]
    am_vb = already_mapped[3]
    am_vbcen = already_mapped[4]

    # set workspace to desired project location
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = project_path

    if not os.path.exists(project_path):
        os.mkdir(project_path)

    # build project folder structure in project path
    # inputs folders

    log = Logger('create_project')
    log.info('creating project folders...')
    arcpy.AddMessage('creating project folders...')

    inputs_folder = make_folder(project_path, "01_Inputs")

    image_folder = make_folder(inputs_folder, "01_Imagery")
    AP01_folder = make_folder(image_folder, "AP_01")

    topo_folder = make_folder(inputs_folder, "02_Topo")
    DEM01_folder = make_folder(topo_folder, "DEM_01")

    context_folder = make_folder(inputs_folder, "03_Context")
    if BRAT_path:
        BRAT01_folder = make_folder(context_folder, "BRAT_01")
    if VBET_path:
        VBET01_folder = make_folder(context_folder, "VBET_01")
    make_folder(context_folder, 'WBD')

    log.info('copying input files into new project folder...')
    arcpy.AddMessage('Copying input files into new project folder...')

    def add_image(image_path, AP_folder):
        # put input imagery in folder
        arcpy.CopyRaster_management(image_path, os.path.join(AP_folder, 'orthomosaic.png'))

    arcpy.AddMessage('\tCopying imagery...')
    add_image(image_path, AP01_folder)
    # copy DEM, hillshade to project folder
    arcpy.AddMessage('\tCopying DEM...')
    arcpy.CopyRaster_management(DEM_path, os.path.join(DEM01_folder, 'DEM.tif'))
    arcpy.AddMessage('\tCopying Hillshade...')
    arcpy.CopyRaster_management(hs_path, os.path.join(DEM01_folder, 'hlsd.tif'))

    # copy BRAT, VBET to project folder
    if BRAT_path:
        arcpy.AddMessage('\tCopying BRAT...')
        arcpy.CopyFeatures_management(BRAT_path, os.path.join(BRAT01_folder, 'BRAT.shp'))
    if VBET_path:
        arcpy.AddMessage('\tCopying VBET...')
        arcpy.CopyFeatures_management(VBET_path, os.path.join(VBET01_folder, 'VBET.shp'))

    # mapping folder
    # subsequent DCE and RS folders are created when a new DCE is made using new dce script
    mapping_folder = make_folder(project_path, "02_Mapping")
    DCE01_folder = make_folder(mapping_folder, "DCE_01")

    log = Logger('create_project')
    log.info('creating blank RS and DCE shapefiles...')
    arcpy.AddMessage('creating blank RS and DCE shapefiles...')

    # make empty shapefiles for first DCE
    # Use Describe to get a SpatialReference object
    spatial_reference = arcpy.Describe(srs_template).spatialReference
    # inundation
    if not os.path.exists(os.path.join(DCE01_folder, "inundation.shp")) and not am_inun:
        arcpy.CreateFeatureclass_management(DCE01_folder, "inundation.shp", "POLYGON", "", "DISABLED", "DISABLED", spatial_reference)
    # add field for inundation type
        arcpy.AddField_management(os.path.join(DCE01_folder, 'inundation.shp'), 'type', "TEXT")
    # dam crests
    if not os.path.exists(os.path.join(DCE01_folder, "dam_crests.shp")) and not am_dc:
        arcpy.CreateFeatureclass_management(DCE01_folder, "dam_crests.shp", "POLYLINE", "", "DISABLED", "DISABLED", spatial_reference)
    # add fields for dam state and crest type
        arcpy.AddField_management(os.path.join(DCE01_folder, 'dam_crests.shp'), 'dam_state', "TEXT")
        arcpy.AddField_management(os.path.join(DCE01_folder, 'dam_crests.shp'), 'crest_type', "TEXT")
        arcpy.AddField_management(os.path.join(DCE01_folder, 'dam_crests.shp'), 'dam_id', "DOUBLE")
    # thalwegs
    if not os.path.exists(os.path.join(DCE01_folder, "thalwegs.shp")) and not am_thal:
        arcpy.CreateFeatureclass_management(DCE01_folder, "thalwegs.shp", "POLYLINE", "", "DISABLED", "DISABLED", spatial_reference)
    # add fields for thalweg type
        arcpy.AddField_management(os.path.join(DCE01_folder, 'thalwegs.shp'), 'type', "TEXT")
    # make first RS folder
    RS01_folder = make_folder(mapping_folder, "RS_01")
    # create empty shapefiles for valley bottom and valley bottom centerline
    # valley bottom
    if not os.path.exists(os.path.join(RS01_folder, "valley_bottom.shp")) and not am_vb:
        arcpy.CreateFeatureclass_management(RS01_folder, "valley_bottom.shp", "POLYGON", "", "DISABLED", "DISABLED", spatial_reference)
        arcpy.AddField_management(os.path.join(RS01_folder, 'valley_bottom.shp'), 'site_name', "TEXT")
        arcpy.AddField_management(os.path.join(RS01_folder, 'valley_bottom.shp'), 'huc', "DOUBLE")
        with arcpy.da.UpdateCursor(os.path.join(RS01_folder, 'valley_bottom.shp'), ['site_name', 'huc']) as cursor:
            for row in cursor:
                row[0] = site_name
                row[1] = huc
                cursor.updateRow(row)
    # valley bottom centerline
    if not os.path.exists(os.path.join(RS01_folder, "vb_centerline.shp")) and not am_vbcen:
        arcpy.CreateFeatureclass_management(RS01_folder, "vb_centerline.shp", "POLYLINE", "", "DISABLED", "DISABLED", spatial_reference)

    if am_dc:
        arcpy.Copy_management(am_vb, os.path.join(DCE01_folder, 'dam_crests.shp'))
    if am_thal:
        arcpy.Copy_management(am_vb, os.path.join(DCE01_folder, "inundation.shp"))
    if am_inun:
        arcpy.Copy_management(am_vb, os.path.join(DCE01_folder, "thalwegs.shp"))
    if am_vb:
        arcpy.Copy_management(am_vb, os.path.join(RS01_folder, "valley_bottom.shp"))
    if am_vbcen:
        arcpy.Copy_management(am_vb, os.path.join(RS01_folder, "vb_centerline.shp"))


    # analysis folder
    analysis_folder = make_folder(project_path, "03_Analysis")
    DCEout = make_folder(analysis_folder, "DCE_01")
    make_folder(DCEout, "Shapefiles")
    make_folder(analysis_folder, "CDs")
    make_folder(analysis_folder, "Summary")

    arcpy.AddMessage('---DONE!---')


if __name__ == "__main__":
    main(sys.argv[1],
         sys.argv[2],
         sys.argv[3],
         sys.argv[4],
         sys.argv[5],
         sys.argv[6],
         sys.argv[7],
         sys.argv[8],
         sys.argv[9],
         sys.argv[10],
         sys.argv[11],
         sys.argv[12],
         sys.argv[13],
         sys.argv[14],
    )