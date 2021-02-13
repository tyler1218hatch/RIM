# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 15:04:43 2020

@author: karen
"""

# Name: new_DCE.py
# Description: Create shapefiles for inundation work

# Import system modules
import os
import arcpy
import sys
from settings import ModelConfig
import uuid
from lib.project import RSProject, RSLayer
from lib.util import safe_makedirs
from lib.loghelper import Logger
import time
import datetime

cfg = ModelConfig('http://xml.riverscapes.xyz/Projects/XSD/V1/Inundation.xsd')

def main(project_path, image_path):

    # create project folders and empty mapping shapefiles for first DCE
    arcpy.AddMessage('Creating New DCE...')
    srs_template = os.path.join(project_path, '03_Analyses', 'DCE_01', "inundation.shp")
    AP_fold = create_next_folder(os.path.join(project_path, '01_Inputs', '01_Imagery'), 'AP')
    DCE_fold = create_next_folder(os.path.join(project_path, '02_Mapping'), 'DCE')
    create_next_folder(os.path.join(project_path, '03_Analysis'), 'DCE')
    new_DCE(srs_template, project_path, AP_fold, DCE_fold, image_path)


def create_next_folder(source_folder, prefix):

    if not prefix.endswith('_'):
        prefix += '_'

    all_folders = [dI for dI in os.listdir(source_folder) if os.path.isdir(os.path.join(source_folder, dI))]
    next_folder_num = max([int(f.replace(prefix, '')) for f in all_folders]) + 1

    if next_folder_num < 10:
        next_folder_name = prefix + '0' + str(next_folder_num)
    else:
        next_folder_name = prefix + str(next_folder_num)

    next_folder_path = os.path.join(source_folder, next_folder_name)
    os.mkdir(next_folder_path)

    return next_folder_path


# function for create files
def new_DCE(srs_template, project_path, AP_fold, DCE_fold, image_path):

    #    LayerTypes = {
        # RSLayer(name, id, tag, rel_path)
        # 'AP_new': RSLayer(date_name, AP_fold, 'Raster', os.path.join('01_Inputs/01_Imagery', AP_fold, 'imagery.tif')),
        # 'INUN_new': RSLayer('Inundation', 'DCE_01_inun', 'Vector', os.path.join('03_Analysis', DCE_fold, 'Shapefiles/inundation.shp')),
        # 'DAM_CREST_new': RSLayer('Dam Crests', 'DCE_01_damcrests', 'Vector', os.path.join('03_Analysis', DCE_fold, 'Shapefiles/dam_crests.shp')),
        # 'TWG_new': RSLayer('Thalwegs', 'DCE_01_thalwegs', 'Vector', os.path.join('03_Analysis', DCE_fold, 'Shapefiles/thalwegs.shp'))
    # }

    #log = Logger('edit_xml')
    #log.info('Loading the XML to make edits...')
    # Load up a new RSProject class
    #project = RSProject(cfg, project_path)

    log = Logger('new_DCE')

    # Set local variables
    has_m = "DISABLED"
    has_z = "DISABLED"

    log.info('before getting spatial reference')
    # Use Describe to get a SpatialReference object
    spatial_reference = arcpy.Describe(srs_template).spatialReference

    log.info('checking if project folders exist')
    # check if Inputs, Mapping, and Analysis folders exist, if not create them
    folder_list = ['01_Inputs', '02_Mapping', '03_Analysis']
    for folder in folder_list:
        if not os.path.exists(os.path.join(project_path, folder)):
            os.makedirs(os.path.join(project_path, folder))

    log.info('Inputs, Mapping, Analysis folders exist')

    # set pathway to imagery folder
    image_folder = os.path.join(project_path, '01_Inputs/01_Imagery')


    log.info('copying image to project folder...')

    def add_image(image_path, AP_folder):
        # put input imagery in folder
        if not os.path.exists(os.path.join(AP_folder, 'imagery.png')):
            arcpy.CopyRaster_management(image_path, os.path.join(AP_folder, 'imagery.tif'))
        else:
            print("existing image already exists in this AP folder")

    add_image(image_path, AP_fold)

    # set pathway to mapping folder
    map_path = os.path.join(project_path, '02_Mapping')

    #  check if RS folder exists, if not make one
    if not os.path.exists(os.path.join(map_path, 'RS_01')):
        os.makedirs(os.path.join(map_path, 'RS_01'))

    # populate new DCE folder

    log.info('creating new DCE shapefiles...')

    # inundation
    arcpy.CreateFeatureclass_management(DCE_fold, "inundation.shp", "POLYGON", "", has_m, has_z, spatial_reference)
    # add field for inundation type
    arcpy.AddField_management(os.path.join(DCE_fold, 'inundation.shp'), 'type', "TEXT")

    # dam crests
    arcpy.CreateFeatureclass_management(DCE_fold, "dam_crests.shp", "POLYLINE", "", has_m, has_z, spatial_reference)
    # add fields for dam state and crest type
    arcpy.AddField_management(os.path.join(DCE_fold, 'dam_crests.shp'), 'dam_state', "TEXT")
    arcpy.AddField_management(os.path.join(DCE_fold, 'dam_crests.shp'), 'crest_type', "TEXT")
    arcpy.AddField_management(os.path.join(DCE_fold, 'dam_crests.shp'), 'dam_id', "DOUBLE")

    # thalwegs
    arcpy.CreateFeatureclass_management(DCE_fold, "thalwegs.shp", "POLYLINE", "", has_m, has_z, spatial_reference)
    arcpy.AddField_management(os.path.join(DCE_fold, 'thalwegs.shp'), 'type', "TEXT")

    log.info('updating xml with new DCE...')


if __name__ == "__main__":
    main(sys.argv[1],
         sys.argv[2],
         sys.argv[3],
         sys.argv[4],
         sys.argv[5]
    )