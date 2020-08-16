# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 15:04:43 2020

@author: karen
"""

# Name: new_DCE.py
# Description: Create shapefiles for inundation work

# Import system modules
import arcpy
from arcpy import env
import os
import argparse
from lib.loghelper import Logger


# define inputs to the create_DCE function
# path to a shapefile with the desired output coordinate system
#srs_template = r"C:\Users\karen\Box\0_ET_AL\NonProject\etal_Drone\2019\Inundation_sites\Utah\Mill_Creek\08042019\GIS\dam_crests.shp"
# path to project folder
#project_path = r"C:\Users\karen\Box\0_ET_AL\NonProject\etal_Drone\2019\Inundation_sites\Utah\Mill_Creek\test"

# name of desired new DCE folder
DCE_fold = 'DCE_02'

# function for create files


def new_DCE(srs_template, project_path, DCE_fold):

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
    image_folder = os.path.join(project_path, '01_Imagery')

    # create new AP folder
    if not os.path.exists(os.path.join(image_folder, AP_fold)):
        AP_path = os.makedirs(os.path.join(image_folder, AP_fold))

    log.info('copying image to project folder...')

    def add_image(image_path, AP_folder):
        # put input imagery in folder
        if not os.path.exists(os.path.join(AP_folder, 'imagery.tif')):
            arcpy.CopyRaster_management(image_path, os.path.join(AP_folder, 'imagery.tif'))
            else print('existing image already exists in this AP folder')
    add_image(image_path, AP_path)

    # set pathway to mapping folder
    map_path = os.path.join(project_path, '02_Mapping')

    #  check if RS folder exists, if not make one
    if not os.path.exists(os.path.join(map_path, 'RS_01')):
        os.makedirs(os.path.join(map_path, 'RS_01'))

    # create new DCE folder
    if not os.path.exists(os.path.join(map_path, DCE_fold)):
        os.makedirs(os.path.join(map_path, DCE_fold))

    # create a folder in Analysis for this DCE
    analysis_path = os.path.join(project_path, '03_Analysis')
    if not os.path.exists(os.path.join(analysis_path, DCE_fold)):
        os.makedirs(os.path.join(analysis_path, DCE_fold))

    # inundation
    arcpy.CreateFeatureclass_management(os.path.join(map_path, DCE_fold), "inundation.shp", "POLYGON", "", has_m, has_z, spatial_reference)
    # add field for inundation type
    arcpy.AddField_management(os.path.join(map_path, DCE_fold, 'inundation.shp'), 'type', "TEXT")

    # dam crests
    arcpy.CreateFeatureclass_management(os.path.join(map_path, DCE_fold), "dam_crests.shp", "POLYLINE", "", has_m, has_z, spatial_reference)
    # add fields for dam state and crest type
    arcpy.AddField_management(os.path.join(map_path, DCE_fold, 'dam_crests.shp'), 'dam_state', "TEXT")
    arcpy.AddField_management(os.path.join(map_path, DCE_fold, 'dam_crests.shp'), 'crest_type', "TEXT")
    arcpy.AddField_management(os.path.join(map_path, DCE_fold, 'dam_crests.shp'), 'dam_id', "DOUBLE")

    # thalwegs
    arcpy.CreateFeatureclass_management(os.path.join(map_path, DCE_fold), "thalwegs.shp", "POLYLINE", "", has_m, has_z, spatial_reference)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('srs_template', help='path to a shapefile with desired output coordinate system', type=str)
    parser.add_argument('project_path', help='path to output folder', type=str)
    args = parser.parse_args()

    new_DCE(args.srs_template, args.project_path, DCE_fold)


# path to a shapefile with the desired output coordinate system
#srs_template = r"C:\Users\karen\Box\0_ET_AL\NonProject\etal_Drone\2019\Inundation_sites\Utah\Mill_Creek\08042019\GIS\dam_crests.shp"
# path to project folder
#project_path = r"C:\Users\karen\Box\0_ET_AL\NonProject\etal_Drone\2019\Inundation_sites\Utah\Mill_Creek\test"
#new_DCE(srs_template, project_path, DCE_fold)
