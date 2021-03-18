# Import system modules
import os
import arcpy
import sys
import shutil
from settings import ModelConfig
import uuid
from lib.project import RSProject, RSLayer
from lib.util import safe_makedirs
from lib.loghelper import Logger
import time
import datetime
import argparse
import numpy
import csv
import pandas as pd
import matplotlib.pyplot as plt
from lib.loghelper import Logger
from create_project import make_folder
import numpy as np
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension('Spatial')

cfg = ModelConfig('http://xml.riverscapes.xyz/Projects/XSD/V1/Inundation.xsd')


def main(project_path,
         mapper_name,
         project_name,
         site_name,
         setting,
         huc8,
         list_dates,
         list_date_names,
         list_image_sources,
         list_flow_stages,
         list_actives,
         list_maintaineds,
         list_resolutions,
         ):

    RS_folder_name = os.path.join(project_path, '02_Mapping', 'RS_01')
    DEM = os.path.join(project_path, '01_Inputs', '02_Topo', 'DEM_01', 'DEM.tif')

    def split_multi(to_split):
        return to_split.split(';')

    has_brat = os.path.exists(os.path.join(project_path, '01_Inputs', '03_Context', 'BRAT_01'))
    has_vbet = os.path.exists(os.path.join(project_path, '01_Inputs', '03_Context', 'VBET_01'))
    list_dates = split_multi(list_dates)
    list_date_names = split_multi(list_date_names)
    list_image_sources = split_multi(list_image_sources)
    list_flow_stages = split_multi(list_flow_stages)
    list_actives = split_multi(list_actives)
    list_maintaineds = split_multi(list_maintaineds)
    list_resolutions = split_multi(list_resolutions)

    if len({len(i) for i in [list_dates, list_date_names, list_image_sources, list_flow_stages, list_actives, list_maintaineds, list_resolutions]}) != 1:
        arcpy.AddWarning('Mismatch in expected number of DCEs. Make sure all list inputs have the same length')

    class DCE_object:
        def __init__(self, name, number, date, date_name, image_source, flow_stage, active, maintained, resolution):
            self.name = name
            self.number = number
            self.date = date
            self.date_name = date_name
            self.image_source = image_source
            self.flow_stage = flow_stage
            self.active = active
            self.maintained = maintained
            self.resolution = resolution

    DCE_List = []

    for this_DCE, (this_date, this_date_name, this_image_source, this_flow_stage, this_active, this_maintained, this_resoultion) \
            in enumerate(zip(list_dates, list_date_names, list_image_sources, list_flow_stages, list_actives, list_maintaineds, list_resolutions)):
        if this_DCE + 1 < 10:
            DCE_name = 'DCE_0' + str(this_DCE+1)
            DCE_number = '0' + str(this_DCE+1)
        else:
            DCE_name = 'DCE_' + str(this_DCE + 1)
            DCE_number = str(this_DCE + 1)

        new_DCE = DCE_object(DCE_name, DCE_number, this_date, this_date_name, this_image_source, this_flow_stage, this_active,this_maintained, this_resoultion)
        DCE_List.append(new_DCE)

    # Add VB and VBCL to xml
    log = Logger('build_xml')
    log.info('Starting the build of the XML')
    # Load up a new RSProject class
    project = RSProject(cfg, project_path)

    # DCEs = [DCE1_name, DCE2_name]
    LayerTypes = {
        # RSLayer(name, id, tag, rel_path)

        'CD01': RSLayer('Percent Valley Bottom Inundation', 'CD_totPct', 'PDF', '03_Analysis/CDs/tot_pct.pdf'),
        'CD02': RSLayer('Inundated Area', 'CD_area', 'PDF', '03_Analysis/CDs/area_types.pdf'),
        'CD03': RSLayer('Percent Valley Bottom Inundation by Type', 'CD_typePct', 'PDF', '03_Analysis/CDs/pct_types.pdf'),
        'BRAT': RSLayer('BRAT', 'BRAT', 'Vector', '01_Inputs/03_Context/BRAT_01/BRAT.shp'),
        'VBET': RSLayer('VBET', 'VBET', 'Vector', '01_Inputs/03_Context/VBET_01/VBET.shp'),
        'VB': RSLayer('Valley Bottom', 'VB_01', 'Vector', '02_Mapping/RS_01/valley_bottom.shp'),
        'VB_CL': RSLayer('VB Centerline', 'vbCL_01', 'Vector', '02_Mapping/RS_01/vb_centerline.shp'),

        # Assumes That all DEMs and Hillshades are the same as the first
        'DEM': RSLayer('NED 10m DEM', 'DEM', 'DEM', '01_Inputs/02_Topo/DEM_01/DEM.tif'),
        'HILLSHADE': RSLayer('DEM Hillshade', 'HILLSHADE', 'Raster', '01_Inputs/02_Topo/DEM_01/hlsd.tif'),
    }

    for this_DCE in DCE_List:
        LayerTypes['VB_{}'.format(this_DCE.number)] = \
            RSLayer('Valley Bottom', 'VB_{}'.format(this_DCE.number), 'Vector',
                    '03_Analysis/{}/Shapefiles/valley_bottom.shp'.format(this_DCE.name))

        LayerTypes['VB_CL_{}'.format(this_DCE.number)] = \
            RSLayer('VB Centerline', 'vbCL_{}'.format(this_DCE.number), 'Vector',
                    '03_Analysis/{}/Shapefiles/vb_centerline.shp'.format(this_DCE.name))

        LayerTypes['PIE_{}'.format(this_DCE.number)] = \
            RSLayer('{} Inundation Types'.format(this_DCE.name), 'PIE_{}'.format(this_DCE.number), 'PDF',
                    '03_Analysis/{}/inun_types.pdf'.format(this_DCE.name))

        LayerTypes['Min_{}'.format(this_DCE.number)] = \
            RSLayer('Minimum Inundation Extent', 'Min{}'.format(this_DCE.number), 'Vector',
                    '03_Analysis/{}/Shapefiles/error_min.shp'.format(this_DCE.name))

        LayerTypes['Max_{}'.format(this_DCE.number)] = \
            RSLayer('Maximum Inundation Extent', 'Max{}'.format(this_DCE.number), 'Vector',
                    '03_Analysis/{}/Shapefiles/error_max.shp'.format(this_DCE.name))

        LayerTypes['AP_{}'.format(this_DCE.number)] = \
            RSLayer(this_DCE.date_name, 'AP_{}'.format(this_DCE.number), 'Raster',
                    '01_Inputs/01_Imagery/AP_{}/orthomosaic.png'.format(this_DCE.number))

        LayerTypes['INUN_{}'.format(this_DCE.number)] = \
            RSLayer('Inundation', 'DCE_{}_inun'.format(this_DCE.number), 'Vector',
                    '03_Analysis/{}/Shapefiles/inundation.shp'.format(this_DCE.name))

        LayerTypes['DAM_CREST_{}'.format(this_DCE.number)] = \
            RSLayer('Dam Crests', 'DCE_{}_damcrests'.format(this_DCE.number), 'Vector',
                    '03_Analysis/{}/Shapefiles/dam_crests.shp'.format(this_DCE.name))

        LayerTypes['TWG_{}'.format(this_DCE.number)] = \
            RSLayer('Thalwegs', 'DCE_{}_thalwegs'.format(this_DCE.number), 'Vector',
                    '03_Analysis/{}/Shapefiles/thalwegs.shp'.format(this_DCE.name))

    project_name = project_name
    project = RSProject(cfg, project_path.replace('\\', '/'))
    project.create(project_name, 'Inundation')

    # Add the root metadata
    project.add_metadata({
        'ModelVersion': cfg.version,
        'HUC8': huc8,
        'InundationVersion': cfg.version,
        'site_name': site_name,
        'mapper_name': mapper_name
    })

    # Create the inputs container node
    inputs = project.XMLBuilder.add_sub_element(project.XMLBuilder.root, 'Inputs', None, {
    })

    # Create the realizations container node
    realizations = project.XMLBuilder.add_sub_element(project.XMLBuilder.root, 'Realizations', None, {
    })

    log = Logger('build_xml')
    log.info('adding inputs to xml...')

    # Create the InundationContext (vb and vb centerline) container node
    RS01_node = project.XMLBuilder.add_sub_element(realizations, 'InundationContext', None, {
        'id': 'RS_01',
        'dateCreated': datetime.datetime.now().isoformat(),
        'guid': str(uuid.uuid1()),
        'productVersion': cfg.version,
    })
    project.XMLBuilder.add_sub_element(RS01_node, 'Name', 'Site Extent and Centerline')
    RS01_inputs_node = project.XMLBuilder.add_sub_element(RS01_node, 'Inputs', None)
    project.XMLBuilder.add_sub_element(RS01_node, 'Outputs', None)
    project.add_project_raster(inputs, LayerTypes['DEM'])
    project.add_project_raster(inputs, LayerTypes['HILLSHADE'])

    # add the input vectors to xml
    if has_brat:
        project.add_project_vector(inputs, LayerTypes['BRAT'])
    if has_vbet:
        project.add_project_vector(inputs, LayerTypes['VBET'])

    # Add RS01 files to xml
    project.add_project_vector(RS01_inputs_node, LayerTypes['VB'])
    project.add_project_vector(RS01_inputs_node, LayerTypes['VB_CL'])

    for this_DCE in DCE_List:

        log = Logger(this_DCE.name)
        # Create the InundationDCE container node and metadata
        DCE_Node = project.XMLBuilder.add_sub_element(realizations, 'InundationDCE', None, {
          'id': this_DCE.name,
          'dateCreated': datetime.datetime.now().isoformat(),
          'guid': str(uuid.uuid1()),
          'productVersion': cfg.version
        })
        project.XMLBuilder.add_sub_element(DCE_Node, 'Name', this_DCE.date_name)
        inputs_node = project.XMLBuilder.add_sub_element(DCE_Node, 'Inputs', None)
        outputs_node = project.XMLBuilder.add_sub_element(DCE_Node, 'Outputs', None)


        project.add_project_raster(inputs, LayerTypes['AP_{}'.format(this_DCE.number)])
        ap_node = project.XMLBuilder.find_by_id('AP_{}'.format(this_DCE.number))
        project.add_metadata({
          'image_date': this_DCE.date,
          'source': this_DCE.image_source,
          'flow_stage': this_DCE.flow_stage,
          'image_res': this_DCE.resolution,
        }, ap_node)

        #Add DCE files to xml
        project.add_project_vector(inputs_node, LayerTypes['INUN_{}'.format(this_DCE.number)])
        project.add_project_vector(inputs_node, LayerTypes['DAM_CREST_{}'.format(this_DCE.number)])
        project.add_project_vector(inputs_node, LayerTypes['TWG_{}'.format(this_DCE.number)])

        # Existing code
        project.add_project_vector(inputs_node, LayerTypes['VB_{}'.format(this_DCE.number)])
        project.add_project_vector(inputs_node, LayerTypes['VB_CL_{}'.format(this_DCE.number)])
        project.add_project_vector(inputs_node, LayerTypes['Min_{}'.format(this_DCE.number)])
        project.add_project_vector(inputs_node, LayerTypes['Max_{}'.format(this_DCE.number)])
        project.add_project_pdf(outputs_node, LayerTypes['PIE_{}'.format(this_DCE.number)])


    #TODO not sure if this needs to also iterate
    CD01_node = project.XMLBuilder.add_sub_element(realizations, 'InundationCD', None, {
        'id': 'DCE_0102CD',
        'dateCreated': datetime.datetime.now().isoformat(),
        'guid': str(uuid.uuid1()),
        'productVersion': cfg.version
    })
    project.XMLBuilder.add_sub_element(CD01_node, 'Name', 'DCE Comparison')
    CD01_inputs_node = project.XMLBuilder.add_sub_element(CD01_node, 'Inputs', None)

    # project.XMLBuilder.add_sub_element(CD01_inputs_node, 'DCE1', DCE1_date_name)
    # project.XMLBuilder.add_sub_element(CD01_inputs_node, 'DCE2', DCE2_date_name)

    # Add CD output pie charts and csv
    CD01_outputs_node = project.XMLBuilder.add_sub_element(CD01_node, 'Outputs', None)
    project.add_project_pdf(CD01_outputs_node, LayerTypes['CD01'])
    project.add_project_pdf(CD01_outputs_node, LayerTypes['CD02'])
    project.add_project_pdf(CD01_outputs_node, LayerTypes['CD03'])

    log = Logger('set paths')

    # Set internal paths
    map_folder = os.path.join(project_path, '02_Mapping')
    RS_folder = os.path.join(map_folder, RS_folder_name)
    out_folder = os.path.join(project_path, '03_Analysis')

    # Copy all RS and DCE mapped shapefiles and save copy to output folder for analysis

    DCE_path_list = []

    for this_DCE in DCE_List:

        DCE_location = os.path.join(map_folder, this_DCE.name)
        make_folder(os.path.join(out_folder, this_DCE.name), '01_Metrics')

        DCE_out = make_folder(os.path.join(out_folder, this_DCE.name), 'shapefiles')
        DCE_path_list.append(DCE_out)

        arcpy.CopyFeatures_management(os.path.join(RS_folder, 'valley_bottom.shp'), os.path.join(DCE_out, 'valley_bottom.shp'))
        arcpy.CopyFeatures_management(os.path.join(RS_folder, 'vb_centerline.shp'), os.path.join(DCE_out, 'vb_centerline.shp'))
        arcpy.CopyFeatures_management(os.path.join(DCE_location, 'thalwegs.shp'), os.path.join(DCE_out, 'thalwegs.shp'))
        arcpy.CopyFeatures_management(os.path.join(DCE_location, 'dam_crests.shp'), os.path.join(DCE_out, 'dam_crests.shp'))
        arcpy.CopyFeatures_management(os.path.join(DCE_location, 'inundation.shp'), os.path.join(DCE_out, 'inundation.shp'))


    # Add DCE parameters to valley bottom shapefile
    for DCE, DCE_Object in zip(DCE_path_list, DCE_List):
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'site_name', "TEXT")
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'date', "TEXT")
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'flow_stage', "TEXT")
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'active', "TEXT")
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'maintnd', "TEXT")
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'img_res', "DOUBLE")

        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['site_name', 'date', 'flow_stage', 'active', 'maintnd', 'img_res']) as cursor:
            for row in cursor:
                row[0] = site_name
                row[1] = DCE_Object.date
                row[2] = DCE_Object.flow_stage
                row[3] = DCE_Object.active
                row[4] = DCE_Object.maintained
                row[5] = DCE_Object.resolution
                cursor.updateRow(row)


    log.info('paths set for DCEs of interest and DEM and input parameters added to VB output shapefile')

    #######

    # Calculate reach and valley slope with DEM, Thalweg, and VB_Centerline
    log = Logger('CL_attributes')
    # Create a thalweg file with just the main thalweg
    for DCE in DCE_path_list:
        arcpy.MakeFeatureLayer_management(os.path.join(DCE, 'thalwegs.shp'), 'twg_main', "type = 'main'")
        arcpy.SelectLayerByAttribute_management('twg_main', "NEW_SELECTION")
        arcpy.CopyFeatures_management('twg_main', os.path.join(DCE, 'twg_main.shp'))

    def CL_attributes(polyline, DEM, scratch):
        """
        calculates min and max elevation, length, slope for each flowline segment
        :param polyline: The output netwrok to add fields to.
        :param DEM: The DEM raster.
        :param midpoint_buffer: The buffer created from midpoints
        :param scratch: The current workspace
        """
        # if fields lready exist, delete them
        fields = [f.name for f in arcpy.ListFields(polyline)]
        drop = ["el_1", "el_2", "length", "slope"]
        for field in fields:
            if field in drop:
                arcpy.DeleteField_management(polyline, field)

        # function to attribute start/end elevation (dem z) to each flowline segment
        def zSeg(vertex_type, out_field):
            # create start/end points for each flowline reach segment
            tmp_pts = os.path.join(scratch, 'tmp_pts.shp')
            arcpy.FeatureVerticesToPoints_management(polyline, tmp_pts, vertex_type)
            # create 20 meter buffer around each start/end point
            tmp_buff = os.path.join(scratch, 'tmp_buff.shp')
            arcpy.Buffer_analysis(tmp_pts, tmp_buff, '30 Meters')
            # get min dem z value within each buffer
            arcpy.AddField_management(polyline, out_field, "DOUBLE")
            try:
                out_ZS = arcpy.sa.ZonalStatistics(tmp_buff, "FID", DEM, "MINIMUM", "NODATA")
            except:
                raise Exception("Zonal Statistics could not be completed. Please make sure that all of your Thalwegs and Valley Bottom Centerlines have been edited and saved.")
            out_ZS.save(os.path.join(scratch, "out_ZS"))
            tmp_pts2 = os.path.join(scratch, 'tmp_pts2.shp')
            arcpy.sa.ExtractValuesToPoints(tmp_pts, os.path.join(scratch, "out_ZS"), tmp_pts2)
            # populate polyline with elevation value from out_ZS
            with arcpy.da.UpdateCursor(polyline, out_field) as Ucursor:
                for Urow in Ucursor:
                    with arcpy.da.SearchCursor(tmp_pts2, 'RASTERVALU') as Scursor:
                        for Srow in Scursor:
                            Urow[0] = Srow[0]
                            Ucursor.updateRow(Urow)

            # delete temp fcs, tbls, etc.
            items = [tmp_pts, tmp_pts2, tmp_buff, out_ZS]
            for item in items:
                arcpy.Delete_management(item)

        # run zSeg function for start/end of each network segment
        log.info('extracting elevation at start of polyline...')
        zSeg('START', 'el_1')
        log.info('extracting elevation at end of polyline...')
        zSeg('END', 'el_2')

        # calculate slope
        log.info('calculating length...')
        arcpy.AddField_management(polyline, "length", "DOUBLE")
        arcpy.CalculateField_management(polyline, "length", '!shape.length@meters!', "PYTHON_9.3")
        log.info('calculating slope...')
        arcpy.AddField_management(polyline, "slope", "DOUBLE")
        with arcpy.da.UpdateCursor(polyline, ["el_1", "el_2", "length", "slope"]) as cursor:
            for row in cursor:
                row[3] = (abs(row[0] - row[1])) / row[2]
                if row[3] == 0.0:
                    row[3] = 0.0001
                cursor.updateRow(row)

        log.info('added min and max elevation, length, and slope to polyline')

    # Run CL_attributes for thalweg to get channel slope and valley bottom centerline to get valley slope
    for DCE in DCE_path_list:
        log = Logger('DCE CL_attributes')
        CL_attributes(os.path.join(DCE, 'twg_main.shp'), DEM, project_path)
        log.info('channel slope and length calculated')
        log = Logger('RS CL_attributes')
        CL_attributes(os.path.join(DCE, "vb_centerline.shp"), DEM, project_path)
        log.info('valley slope and length calculated')

    log = Logger('calculate attributes')
    # Add and calculate fields for valley bottom shapefile
    for DCE in DCE_path_list:
        log.info('calculating valley area...')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'area', 'DOUBLE')
        fields = ['area', 'SHAPE@AREA']
        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), fields) as cursor:
            for row in cursor:
                row[0] = row[1]
                cursor.updateRow(row)

    # Add and calculate fields for thalwegs lengths

    # Add and calculate fields for DCE shapefiles
    for DCE in DCE_path_list:
        # inundation
        log.info('calculating inundatioin areas and perimeters...')
        inundation = os.path.join(DCE, 'inundation.shp')
        arcpy.AddField_management(inundation, 'area', 'DOUBLE')
        arcpy.AddField_management(inundation, 'perimeter', 'DOUBLE')
        fields = ['area', 'perimeter', 'SHAPE@AREA', 'SHAPE@LENGTH']
        with arcpy.da.UpdateCursor(inundation, fields) as cursor:
            for row in cursor:
                row[0] = row[2]
                row[1] = row[3]
                cursor.updateRow(row)
        # dam crests
        log.info('calculating dam crest lengths...')
        dam_crests = os.path.join(DCE, 'dam_crests.shp')
        arcpy.AddField_management(dam_crests, 'length', 'DOUBLE')
        fields = ['length', 'SHAPE@LENGTH']
        with arcpy.da.UpdateCursor(dam_crests, fields) as cursor:
            for row in cursor:
                row[0] = row[1]
                cursor.updateRow(row)

        # thalwegs (all)
        log.info('calculating all thalweg lengths...')
        thalwegs = os.path.join(DCE, 'thalwegs.shp')
        # calculate thalweg length for all types
        twgArr = arcpy.da.FeatureClassToNumPyArray(thalwegs, ['SHAPE@LENGTH'])
        twgTotLen = twgArr['SHAPE@LENGTH'].sum()
        # calculate other thalweg types
        # main
        mainTwgArr = arcpy.da.FeatureClassToNumPyArray(thalwegs, ['SHAPE@LENGTH', 'type'], "type = 'main'")
        mainTwgLen = mainTwgArr['SHAPE@LENGTH'].sum()
        mainTwgPct = round(mainTwgLen / twgTotLen, 1)
        # anabranch
        anaTwgArr = arcpy.da.FeatureClassToNumPyArray(thalwegs, ['SHAPE@LENGTH', 'type'], "type = 'anabranch'")
        anaTwgLen = anaTwgArr['SHAPE@LENGTH'].sum()
        anaTwgPct = round(anaTwgLen / twgTotLen, 1)
        # split
        splitTwgArr = arcpy.da.FeatureClassToNumPyArray(thalwegs, ['SHAPE@LENGTH', 'type'], "type = 'split'")
        splitTwgLen = splitTwgArr['SHAPE@LENGTH'].sum()
        splitTwgPct = round(splitTwgLen / twgTotLen, 1)
        # braid
        braidTwgArr = arcpy.da.FeatureClassToNumPyArray(thalwegs, ['SHAPE@LENGTH', 'type'], "type = 'braid'")
        braidTwgLen = braidTwgArr['SHAPE@LENGTH'].sum()
        braidTwgPct = round(braidTwgLen / twgTotLen, 1)
        # add fields to attribyte table
        arcpy.AddField_management(thalwegs, 'length', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgLenTot', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgLenMain', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgPctMain', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgLenAna', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgPctAna', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgLenSplt', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgPctSplt', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgLenBrd', 'DOUBLE')
        arcpy.AddField_management(thalwegs, 'twgPctBrd', 'DOUBLE')

        with arcpy.da.UpdateCursor(thalwegs, ['length', 'twgLenTot', 'twgLenMain', 'twgPctMain', 'twgLenAna', 'twgPctAna', 'twgLenSplt', 'twgPctSplt', 'twgLenBrd', 'twgPctBrd', 'SHAPE@LENGTH']) as cursor:
            for row in cursor:
                row[0] = row[10]
                row[1] = twgTotLen
                row[2] = mainTwgLen
                row[3] = mainTwgPct
                row[4] = anaTwgLen
                row[5] = anaTwgPct
                row[6] = splitTwgLen
                row[7] = splitTwgPct
                row[8] = braidTwgLen
                row[9] = braidTwgPct
                cursor.updateRow(row)

    # Calculate integrated valley width and integrated wetted width

    def intWidth_fn(polygon, polyline):
        arrPoly = arcpy.da.FeatureClassToNumPyArray(polygon, ['SHAPE@AREA'])
        arrPolyArea = arrPoly['SHAPE@AREA'].sum()
        arrCL = arcpy.da.FeatureClassToNumPyArray(polyline, ['SHAPE@LENGTH'])
        arrCLLength = arrCL['SHAPE@LENGTH'].sum()
        intWidth = round(arrPolyArea / arrCLLength, 1)
        arcpy.AddMessage("integrated width ={}".format(intWidth))
        arcpy.AddField_management(polygon, 'intWidth', 'DOUBLE')
        with arcpy.da.UpdateCursor(polygon, ['intWidth']) as cursor:
            for row in cursor:
                row[0] = intWidth
                cursor.updateRow(row)

    for DCE in DCE_path_list:
        log.info('calculating integrated valley width...')
        intWidth_fn(os.path.join(DCE, 'valley_bottom.shp'), os.path.join(DCE, "vb_centerline.shp"))
        log.info('calculating integrated wetted width...')
        intWidth_fn(os.path.join(DCE, 'inundation.shp'), os.path.join(DCE, 'twg_main.shp'))

    # Calculate total inundated area and percent and inundated area and percent by inundation type

    def inun_fn(inun_poly, site_poly):
        # calculate inundation areas
        tot_arrPoly = arcpy.da.FeatureClassToNumPyArray(inun_poly, ['SHAPE@AREA', 'type'])
        tot_area = tot_arrPoly['SHAPE@AREA'].sum()
        ff_arrPoly = arcpy.da.FeatureClassToNumPyArray(inun_poly, ['SHAPE@AREA', 'type'], "type = 'free_flowing'")
        ff_area = ff_arrPoly['SHAPE@AREA'].sum()
        pd_arrPoly = arcpy.da.FeatureClassToNumPyArray(inun_poly, ['SHAPE@AREA', 'type'], "type = \'ponded'")
        pd_area = pd_arrPoly['SHAPE@AREA'].sum()
        ov_arrPoly = arcpy.da.FeatureClassToNumPyArray(inun_poly, ['SHAPE@AREA', 'type'], "type = \'overflow'")
        ov_area = ov_arrPoly['SHAPE@AREA'].sum()
        vb_arrArea = arcpy.da.FeatureClassToNumPyArray(site_poly, 'SHAPE@AREA')
        vb_area = vb_arrArea['SHAPE@AREA'].sum()
        # calculate inundation percents
        tot_pct = round((tot_area / vb_area) * 100, 1)
        arcpy.AddMessage("% valley bottom inundation (all types) = {}".format(tot_pct))
        ff_pct = round((ff_area / vb_area) * 100, 1)
        arcpy.AddMessage("% free flowing =".format(ff_pct))
        pd_pct = round((pd_area / vb_area) * 100, 1)
        arcpy.AddMessage("% ponded =".format(pd_pct))
        ov_pct = round((ov_area / vb_area) * 100, 1)
        arcpy.AddMessage("% overflow =".format(ov_pct))

        # Plot pie chart
        (head, tail) = os.path.split(DCE)
        (head, tail) = os.path.split(head)

        labels = 'Free Flowing', 'Ponded', 'Overflow'
        sizes = [ff_pct, pd_pct, ov_pct]
        colors = ['deeppink', 'blue', 'cyan']

        fig1, ax1 = plt.subplots()
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.axis('equal')

        pdf_save_location = os.path.join(out_folder, tail, 'inun_types.pdf')

        if os.path.exists(pdf_save_location):
            os.remove(pdf_save_location)

        plt.savefig(pdf_save_location)

        png_save_location = os.path.join(out_folder, tail, 'inun_types.png')

        if os.path.exists(png_save_location):
            os.remove(png_save_location)

        plt.savefig(png_save_location)


        # Find number of exposed bars/ islands
        arcpy.Dissolve_management(in_features=os.path.join(DCE, 'inundation.shp'), out_feature_class=os.path.join(DCE, 'inun_diss.shp'))
        arcpy.Union_analysis(in_features=os.path.join(DCE, 'inun_diss.shp'), out_feature_class=os.path.join(DCE, 'inun_union.shp'), join_attributes="ALL", cluster_tolerance="", gaps="NO_GAPS")
        arcpy.AddField_management(os.path.join(DCE, 'inun_union.shp'), 'area', 'DOUBLE')
        with arcpy.da.UpdateCursor(os.path.join(DCE, 'inun_union.shp'), ['SHAPE@AREA', 'area']) as cursor:
            for row in cursor:
                row[1] = row[0]
                cursor.updateRow(row)
        arcpy.MakeFeatureLayer_management(os.path.join(DCE, 'inun_union.shp'), 'inun_union')
        arcpy.SelectLayerByAttribute_management(in_layer_or_view='inun_union', where_clause='\"FID_inun_d\" = -1')
        arcpy.SelectLayerByAttribute_management(in_layer_or_view='inun_union', selection_type="SUBSET_SELECTION", where_clause='\"area\" > 1')
        holes = int(arcpy.GetCount_management('inun_union').getOutput(0))
        arcpy.CopyFeatures_management('inun_union', os.path.join(DCE, 'inun_holes.shp'))
        arcpy.AddMessage("{} holes".format(holes))
        island_num = holes

        # add fields to inundation shapefile
        arcpy.AddField_management(inun_poly, 'tot_area', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'ff_area', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'pd_area', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'ov_area', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'vb_area', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'tot_pct', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'ff_pct', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'pd_pct', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'ov_pct', 'DOUBLE')
        arcpy.AddField_management(inun_poly, 'island_num', 'DOUBLE')
        with arcpy.da.UpdateCursor(inun_poly, ['tot_area', 'ff_area', 'pd_area', 'ov_area', 'vb_area', 'tot_pct', 'ff_pct', 'pd_pct', 'ov_pct', 'island_num']) as cursor:
            for row in cursor:
                row[0] = tot_area
                row[1] = ff_area
                row[2] = pd_area
                row[3] = ov_area
                row[4] = vb_area
                row[5] = tot_pct
                row[6] = ff_pct
                row[7] = pd_pct
                row[8] = ov_pct
                row[9] = island_num
                cursor.updateRow(row)

    for DCE in DCE_path_list:
        log.info('calculating inundation area and percent...')
        arcpy.AddMessage("calculating inundation percents for {}...".format(DCE))
        inun_fn(os.path.join(DCE, 'inundation.shp'), os.path.join(DCE, 'valley_bottom.shp'))

    # Calculate number of islands and perimeter:area ratio

    # Calculate dam crest metrics

    def dam_crests_fn(crests_line, CL_line):
        # Calculate valley length
        arrCL = arcpy.da.FeatureClassToNumPyArray(CL_line, ['SHAPE@LENGTH'])
        arrCL_len = arrCL['SHAPE@LENGTH'].sum()

        # Calculate dam crest to valley length ratio
        crestArr = arcpy.da.FeatureClassToNumPyArray(crests_line, ['SHAPE@LENGTH'])
        crest_lenArr = crestArr['SHAPE@LENGTH'].sum()
        crest_CL_rat = round(crest_lenArr / arrCL_len, 1)
        arcpy.AddMessage("dam crest length (all) : valley length = {}".format(crest_CL_rat))
        # active dam crest to valley length ratio
        act_crestArr = arcpy.da.FeatureClassToNumPyArray(crests_line, ['SHAPE@LENGTH', 'crest_type'], "crest_type = 'active'")
        act_crest_len = act_crestArr['SHAPE@LENGTH'].sum()
        pct_act = (act_crest_len / crest_lenArr) * 100
        act_crest_rat = round(act_crest_len / arrCL_len, 1)
        arcpy.AddMessage("active dam crest length : valley length = {}".format(act_crest_rat))
        # intact dam crest to valley length ratio
        intact_crestArr = arcpy.da.FeatureClassToNumPyArray(crests_line, ['SHAPE@LENGTH', 'dam_state'], "dam_state = 'intact'")
        intact_crest_len = intact_crestArr['SHAPE@LENGTH'].sum()
        intact_crest_rat = round(intact_crest_len / arrCL_len, 1)
        arcpy.AddMessage("intact dam crest length : valley length = {}".format(intact_crest_rat))

        # Calculate number of dams and dam density
        # Make a layer from the feature class
        arcpy.CopyFeatures_management(crests_line, os.path.join(project_path, 'tmp_dams.shp'))
        tmp_dams = os.path.join(project_path, 'tmp_dams.shp')
        arcpy.MakeFeatureLayer_management(tmp_dams, os.path.join(project_path, 'damsCount_lyr'))
        # Delete identical dam_ID so there is just 1 row per dam
        arcpy.DeleteIdentical_management(os.path.join(project_path, 'damsCount_lyr'), 'dam_id')
        # all dams
        dams_num = int(arcpy.GetCount_management(os.path.join(project_path, 'damsCount_lyr')).getOutput(0))
        arcpy.AddMessage( "number of dams = {}".format(dams_num))
        # dam density in dams/km
        dam_dens = round((dams_num / arrCL_len) * 1000, 1)
        arcpy.AddMessage( "dam density (dams/km) = {}".format(dam_dens))
        # intact
        arcpy.SelectLayerByAttribute_management(os.path.join(project_path, 'damsCount_lyr'), 'NEW_SELECTION', "dam_state = 'intact'")
        intact_num = int(arcpy.GetCount_management(os.path.join(project_path, 'damsCount_lyr')).getOutput(0))
        arcpy.AddMessage( "number of intact dams = {}".format(intact_num))
        # breached
        arcpy.SelectLayerByAttribute_management(os.path.join(project_path, 'damsCount_lyr'), 'NEW_SELECTION', "dam_state = 'breached'")
        breached_num = int(arcpy.GetCount_management(os.path.join(project_path, 'damsCount_lyr')).getOutput(0))
        arcpy.AddMessage( "number of breached dams = {}".format(breached_num))
        # blown_out
        arcpy.SelectLayerByAttribute_management(os.path.join(project_path, 'damsCount_lyr'), 'NEW_SELECTION', "dam_state = 'blown_out'")
        blown_out_num = int(arcpy.GetCount_management(os.path.join(project_path, 'damsCount_lyr')).getOutput(0))
        arcpy.AddMessage( "number of blown out dams = {}".format(blown_out_num))
        # delete temporary dams layer
        arcpy.Delete_management(tmp_dams)

        # Add values to dam_crests attribute table
        arcpy.AddField_management(crests_line, 'width', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'dams_num', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'dam_dens', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'intact_num', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'breach_num', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'blown_num', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'ratio_all', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'ratio_act', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'ratio_int', 'DOUBLE')
        arcpy.AddField_management(crests_line, 'crstPctAct', 'DOUBLE')

        with arcpy.da.UpdateCursor(crests_line, ['width', 'dams_num', 'dam_dens', 'intact_num', 'breach_num', 'blown_num', 'ratio_all', 'ratio_act', 'ratio_int', 'SHAPE@LENGTH', 'crstPctAct']) as cursor:
            for row in cursor:
                row[0] = row[9]
                row[1] = dams_num
                row[2] = dam_dens
                row[3] = intact_num
                row[4] = breached_num
                row[5] = blown_out_num
                row[6] = crest_CL_rat
                row[7] = act_crest_rat
                row[8] = intact_crest_rat
                row[10] = pct_act
                cursor.updateRow(row)

    for DCE in DCE_path_list:
        dam_crests_fn(os.path.join(DCE, 'dam_crests.shp'), os.path.join(DCE, 'vb_centerline.shp'))

    # Pull attributes from BRAT table
    # Create a BRAT output file clipped to VB poly
    if has_brat:
        for DCE in DCE_path_list:
            arcpy.Clip_analysis(os.path.join(project_path, '01_Inputs', '03_Context', 'BRAT_01', 'BRAT.shp'), os.path.join(DCE, 'valley_bottom.shp'), os.path.join(DCE, 'BRAT_clip.shp'))

    # Estimate bankfull with Beechie equation

    # Estimate Error for inundation area

    def poly_error_buf(polygon, error_val, out_folder):
        buf_pos = float(error_val)
        buf_neg = (buf_pos * -1)
        arcpy.Buffer_analysis(polygon, os.path.join(out_folder, 'error_max.shp'), buf_pos)
        arcpy.Buffer_analysis(polygon, os.path.join(out_folder, 'error_min.shp'), buf_neg)

    for DCE, DCE_Object in zip(DCE_path_list, DCE_List):
        err = float(DCE_Object.resolution) * 3
        poly_error_buf(os.path.join(DCE, 'inundation.shp'), err, DCE)

    # Create min and max extent polygons for each DCE
    for DCE in DCE_path_list:
        log.info('calculating inundation area and percent error...')
        arcpy.AddMessage( "calculating inundation error calcs for {}...".format(DCE))
        inun_fn(os.path.join(DCE, 'error_min.shp'), os.path.join(DCE, 'valley_bottom.shp'))
        inun_fn(os.path.join(DCE, 'error_max.shp'), os.path.join(DCE, 'valley_bottom.shp'))

    # Add desired site scale variables to valley bottom shapefile
    # BRAT
    if has_brat:
        for DCE in DCE_path_list:
            arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'iGeo_DA', 'DOUBLE')
            arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'iHyd_QLow', 'DOUBLE')
            arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'iHyd_Q2', 'DOUBLE')
            arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'iHyd_SPLow', 'DOUBLE')
            arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'iHyd_SP2', 'DOUBLE')
            arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'iGeo_Slope', 'DOUBLE')
            # statsFields = [['iGeo_DA', "MEAN"], ['iHyd_QLow', "MEAN"], ['iHyd_Q2', "MEAN"], ['iHyd_SPLow', "MEAN"], ['iHyd_SP2', "MEAN"]]
            # arcpy.Statistics_analysis(os.path.join(DCE, 'BRAT_clip.shp'), os.path.join(DCE, 'BRAT_TAB'), statsFields)
            arcpy.Dissolve_management(in_features=os.path.join(DCE, "BRAT_clip.shp"), out_feature_class=os.path.join(DCE, "BRAT_diss"), dissolve_field="iGeo_DA;iHyd_QLow;iHyd_Q2;iHyd_SPLow;iHyd_SP2;iGeo_Slope", statistics_fields="", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
            field_names = ['iGeo_DA', 'iHyd_QLow', 'iHyd_Q2', 'iHyd_SPLow', 'iHyd_SP2', 'iGeo_Slope']
            with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['iGeo_DA', 'iHyd_QLow', 'iHyd_Q2', 'iHyd_SPLow', 'iHyd_SP2', 'iGeo_Slope']) as Ucursor:
                for Urow in Ucursor:
                    with arcpy.da.SearchCursor(os.path.join(DCE, 'BRAT_diss.shp'), field_names) as Scursor:
                        for Srow in Scursor:
                            Urow[0] = Srow[0]
                            Urow[1] = Srow[1]
                            Urow[2] = Srow[2]
                            Urow[3] = Srow[3]
                            Urow[4] = Srow[4]
                            Urow[5] = Srow[5]
                            Ucursor.updateRow(Urow)
    # main thalweg/ channel slope and length
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'grad_chan', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'len_chan', 'DOUBLE')
        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['grad_chan', 'len_chan']) as Ucursor:
            for Urow in Ucursor:
                with arcpy.da.SearchCursor(os.path.join(DCE, 'twg_main.shp'), ['slope', 'length']) as Scursor:
                    for Srow in Scursor:
                        Urow[0] = Srow[0]
                        Urow[1] = Srow[1]
                        Ucursor.updateRow(Urow)
    # thalwegs (all)
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'twgLenTot', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'twgLenMain', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'twgPctMain', 'DOUBLE')
        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['twgLenTot', 'twgLenMain', 'twgPctMain']) as Ucursor:
            for Urow in Ucursor:
                with arcpy.da.SearchCursor(os.path.join(DCE, 'thalwegs.shp'), ['twgLenTot', 'twgLenMain', 'twgPctMain']) as Scursor:
                    for Srow in Scursor:
                        Urow[0] = Srow[0]
                        Urow[1] = Srow[1]
                        Urow[2] = Srow[2]
                        Ucursor.updateRow(Urow)
    # valley bottom centerline
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'grad_vall', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'len_vall', 'DOUBLE')
        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['grad_vall', 'len_vall']) as Ucursor:
            for Urow in Ucursor:
                with arcpy.da.SearchCursor(os.path.join(DCE, 'vb_centerline.shp'), ['slope', 'length']) as Scursor:
                    for Srow in Scursor:
                        Urow[0] = Srow[0]
                        Urow[1] = Srow[1]
                        Ucursor.updateRow(Urow)
    # dam crests
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'dams_num', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'dam_dens', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'intact_num', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'breach_num', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'blown_num', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'ratio_all', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'ratio_act', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'ratio_int', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'crstPctAct', 'DOUBLE')

        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['dams_num', 'dam_dens', 'intact_num', 'breach_num', 'blown_num', 'ratio_all', 'ratio_act', 'ratio_int', 'crstPctAct']) as Ucursor:
            for Urow in Ucursor:
                with arcpy.da.SearchCursor(os.path.join(DCE, 'dam_crests.shp'), ['dams_num', 'dam_dens', 'intact_num', 'breach_num', 'blown_num', 'ratio_all', 'ratio_act', 'ratio_int', 'crstPctAct']) as Scursor:
                    for Srow in Scursor:
                        Urow[0] = Srow[0]
                        Urow[1] = Srow[1]
                        Urow[2] = Srow[2]
                        Urow[3] = Srow[3]
                        Urow[4] = Srow[4]
                        Urow[5] = Srow[5]
                        Urow[6] = Srow[6]
                        Urow[7] = Srow[7]
                        Urow[8] = Srow[8]
                        Ucursor.updateRow(Urow)
    # inundation
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'intWid_wet', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'tot_area', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'ff_area', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'pd_area', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'ov_area', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'tot_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'ff_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'pd_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'ov_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'island_num', 'DOUBLE')

        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['intWid_wet', 'tot_area', 'ff_area', 'pd_area', 'ov_area', 'tot_pct', 'ff_pct', 'pd_pct', 'ov_pct', 'island_num']) as Ucursor:
            for Urow in Ucursor:
                with arcpy.da.SearchCursor(os.path.join(DCE, 'inundation.shp'), ['intWidth', 'tot_area', 'ff_area', 'pd_area', 'ov_area', 'tot_pct', 'ff_pct', 'pd_pct', 'ov_pct', 'island_num']) as Scursor:
                    for Srow in Scursor:
                        Urow[0] = Srow[0]
                        Urow[1] = Srow[1]
                        Urow[2] = Srow[2]
                        Urow[3] = Srow[3]
                        Urow[4] = Srow[4]
                        Urow[5] = Srow[5]
                        Urow[6] = Srow[6]
                        Urow[7] = Srow[7]
                        Urow[8] = Srow[8]
                        Urow[9] = Srow[9]
                        Ucursor.updateRow(Urow)
    # minimum inundation
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'minWid_wet', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'minTot_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'minFF_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'minPD_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'minOV_pct', 'DOUBLE')

        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['minWid_wet', 'minTot_pct', 'minFF_pct', 'minPD_pct', 'minOV_pct']) as Ucursor:
            for Urow in Ucursor:
                with arcpy.da.SearchCursor(os.path.join(DCE, 'error_min.shp'), ['intWidth', 'tot_pct', 'ff_pct', 'pd_pct', 'ov_pct']) as Scursor:
                    for Srow in Scursor:
                        Urow[0] = Srow[0]
                        Urow[1] = Srow[1]
                        Urow[2] = Srow[2]
                        Urow[3] = Srow[3]
                        Urow[4] = Srow[4]
                        Ucursor.updateRow(Urow)
    # max inundation
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'maxWid_wet', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'maxTot_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'maxFF_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'maxPD_pct', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'maxOV_pct', 'DOUBLE')

        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['maxWid_wet', 'maxTot_pct', 'maxFF_pct', 'maxPD_pct', 'maxOV_pct']) as Ucursor:
            for Urow in Ucursor:
                with arcpy.da.SearchCursor(os.path.join(DCE, 'error_max.shp'), ['intWidth', 'tot_pct', 'ff_pct', 'pd_pct', 'ov_pct']) as Scursor:
                    for Srow in Scursor:
                        Urow[0] = Srow[0]
                        Urow[1] = Srow[1]
                        Urow[2] = Srow[2]
                        Urow[3] = Srow[3]
                        Urow[4] = Srow[4]
                        Ucursor.updateRow(Urow)

    # Additional site calcs
    for DCE in DCE_path_list:
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'sinAllTwg', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'sinMainTwg', 'DOUBLE')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'setting', 'TEXT')
        arcpy.AddField_management(os.path.join(DCE, 'valley_bottom.shp'), 'huc8', 'TEXT')

        with arcpy.da.UpdateCursor(os.path.join(DCE, 'valley_bottom.shp'), ['len_vall', 'twgLenTot', 'twgLenMain', 'sinAllTwg', 'sinMainTwg', 'setting', 'huc8']) as cursor:
            for row in cursor:
                row[3] = row[1] / row[0]
                row[4] = row[2] / row[0]
                row[5] = setting
                row[6] = huc8
                cursor.updateRow(row)

    # Add data to csv
    for DCE in DCE_path_list:
        # create output folder
        output = os.path.dirname(DCE)

        # valley bottom
        nparr = arcpy.da.FeatureClassToNumPyArray(os.path.join(DCE, 'valley_bottom.shp'), ['*'])
        field_names = [f.name for f in arcpy.ListFields(os.path.join(DCE, 'valley_bottom.shp'))]
        fields_str = ','.join(str(i) for i in field_names)
        numpy.savetxt(output + '/' + '01_Metrics' + '/' + 'valley_bottom' + '_metrics.csv', nparr, fmt="%s", delimiter=",", header=str(fields_str), comments='')
        # valley bottom centerline
        nparr = arcpy.da.FeatureClassToNumPyArray(os.path.join(DCE, 'vb_centerline.shp'), ['*'])
        field_names = [f.name for f in arcpy.ListFields(os.path.join(DCE, 'vb_centerline.shp'))]
        fields_str = ','.join(str(i) for i in field_names)
        numpy.savetxt(output + '/' + '01_Metrics' + '/' + 'vb_centerline' + '_metrics.csv', nparr, fmt="%s", delimiter=",", header=str(fields_str), comments='')
        # main thalweg - channel slope and length
        nparr = arcpy.da.FeatureClassToNumPyArray(os.path.join(DCE, 'twg_main.shp'), ['*'])
        field_names = [f.name for f in arcpy.ListFields(os.path.join(DCE, 'twg_main.shp'))]
        fields_str = ','.join(str(i) for i in field_names)
        numpy.savetxt(output + '/' + '01_Metrics' + '/' + 'twg_main' + '_metrics.csv', nparr, fmt="%s", delimiter=",", header=str(fields_str), comments='')
        # inundation
        nparr = arcpy.da.FeatureClassToNumPyArray(os.path.join(DCE, 'inundation.shp'), ['*'])
        field_names = [f.name for f in arcpy.ListFields(os.path.join(DCE, 'inundation.shp'))]
        fields_str = ','.join(str(i) for i in field_names)
        numpy.savetxt(output + '/' + '01_Metrics' + '/' + 'inundation' + '_metrics.csv', nparr, fmt="%s", delimiter=",", header=str(fields_str), comments='')
        # dam crests
        nparr = arcpy.da.FeatureClassToNumPyArray(os.path.join(DCE, 'dam_crests.shp'), ['*'])
        field_names = [f.name for f in arcpy.ListFields(os.path.join(DCE, 'dam_crests.shp'))]
        fields_str = ','.join(str(i) for i in field_names)
        numpy.savetxt(output + '/' + '01_Metrics' + '/' + 'dam_crests' + '_metrics.csv', nparr, fmt="%s", delimiter=",", header=str(fields_str), comments='')

    ####################################################

    # Join metrics from both DCE into 1 csv
    # List of all csvs
    outputs = []

    for DCE_Object in DCE_List:
        outputs.append(os.path.join(project_path, '03_Analysis/{}/01_Metrics/valley_bottom_metrics.csv'.format(DCE_Object.name)))

    metrics = pd.concat([pd.read_csv(f) for f in outputs])
    # Output csv
    csv_out = os.path.join(project_path, '03_Analysis/CDs', 'metrics.csv')
    metrics.to_csv(csv_out)
    create_detailed_metrics(csv_out)



    # Make Plots
    data = pd.read_csv(os.path.join(project_path, '03_Analysis/CDs/metrics.csv'))
    # plot with total percent inun and error bars
    date = data.date.tolist()
    tot_pct = data.tot_pct.tolist()
    maxPct = data.maxTot_pct.tolist()
    minPct = data.minTot_pct.tolist()
    Uerror = []
    Uzip = zip(maxPct, tot_pct)
    for list1_i, list2_i in Uzip:
        Uerror.append(list1_i - list2_i)
    Lerror = []
    Lzip = zip(tot_pct, minPct)
    for list1_i, list2_i in Lzip:
        Lerror.append(list1_i - list2_i)
    # The position of the bars on the x-axis
    r = []
    for index, _ in enumerate(DCE_List):
        r.append(index)
    # Names of group and bar width
    names = date
    barWidth = 1
    # Create brown bars
    arcpy.AddMessage(tot_pct)
    plt.bar(r, tot_pct, color='black', edgecolor='white', width=barWidth)
    # Custom X axis
    plt.xticks(r, names)
    # asym error
    a_error = [Lerror, Uerror]
    plt.errorbar(r, tot_pct, yerr=a_error, fmt='o')
    plt.ylabel('% Valley Bottom Inundation')
    plt.ylim(0, 100)
    plt.savefig(os.path.join(project_path, '03_Analysis/CDs', 'tot_pct.pdf'))
    plt.savefig(os.path.join(project_path, '03_Analysis/CDs', 'tot_pct.png'))

    # Plot with total inun area symbolized by type
    ff_area = data.ff_area.tolist()
    pd_area = data.pd_area.tolist()
    ov_area = data.ov_area.tolist()
    # heights of ff + pd
    ffpd_area = np.add(ff_area, pd_area).tolist()
    # The position of the bars on the x-axis
    r = []
    for index, _ in enumerate(DCE_List):
        r.append(float(index)/2)
    # Names of group and bar width
    names = date
    barWidth = .5
    # Create pink ff bars
    plt.bar(r, ff_area, color='deeppink', edgecolor='white', width=barWidth, label='free flowing')
    # Create blue pd bars
    plt.bar(r, pd_area, bottom=ff_area, color='blue', edgecolor='white', width=barWidth, label='ponded')
    # Create cyan ov bars
    plt.bar(r, ov_area, bottom=ffpd_area, color='cyan', edgecolor='white', width=barWidth, label='overflow')
    # Custom X axis
    plt.xticks(r, names)
    plt.ylabel('Inundated area (m^2)')
    plt.savefig(os.path.join(project_path, '03_Analysis/CDs', 'area_types.pdf'))
    plt.savefig(os.path.join(project_path, '03_Analysis/CDs', 'area_types.png'))
    # Plot with total inun % symbolized by type
    ff_pct = data.ff_pct.tolist()
    pd_pct = data.pd_pct.tolist()
    ov_pct = data.ov_pct.tolist()
    # heights of ff + pd
    ffpd_pct = np.add(ff_pct, pd_pct).tolist()
    # The position of the bars on the x-axis
    r = []
    for index, _ in enumerate(DCE_List):
        r.append(float(index)/2)
    # Names of group and bar width
    names = date
    barWidth = .5
    # Create pink ff bars
    plt.bar(r, ff_pct, color='deeppink', edgecolor='white', width=barWidth, label='free flowing')
    # Create blue pd bars
    plt.bar(r, pd_pct, bottom=ff_pct, color='blue', edgecolor='white', width=barWidth, label='ponded')
    # Create cyan ov bars
    plt.bar(r, ov_pct, bottom=ffpd_pct, color='cyan', edgecolor='white', width=barWidth, label='overflow')
    # Custom X axis
    plt.xticks(r, names)
    plt.ylim(0, 100)
    plt.ylabel('% Valley Bottom Inundation')
    plt.savefig(os.path.join(project_path, '03_Analysis/CDs', 'pct_types.pdf'))
    plt.savefig(os.path.join(project_path, '03_Analysis/CDs', 'pct_types.png'))

def create_detailed_metrics(csv_in):

    df = pd.read_csv(csv_in)
    dce_nums = [x + 1 for x in range(len(df.index))]
    for first in dce_nums:
        for second in dce_nums:
            if first < second:

                first_string = 'DCE_{}'.format(first)
                second_string = 'DCE_{}'.format(second)
                new_csv = csv_in.replace('metrics.csv', '{}_to_{}_metrics.csv'.format(first_string, second_string))
                shutil.copy(csv_in, new_csv)
                with open(new_csv, 'ab') as fp:
                    writer = csv.writer(fp)
                    first_index = first - 1
                    second_index = second - 1
                    writer.writerow([''])
                    new_row = ['{} to {}'.format(first_string, second_string)]
                    columns = df.columns.tolist()
                    columns.pop(0)
                    for column in columns:
                        new_row.append(column)
                    writer.writerow(new_row)

                    new_row = ['{} x {}'.format(first_string, second_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[first_index] * column[second_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['{} + {}'.format(first_string, second_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[first_index] + column[second_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['{} - {}'.format(first_string, second_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[first_index] - column[second_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['{} - {}'.format(second_string, first_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[second_index] - column[first_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['{} / {}'.format(first_string, second_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[first_index] / column[second_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['{} / {}'.format(second_string, first_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[second_index] / column[first_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['{} % of Sum'.format(first_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[first_index] / (column[first_index] + column[second_index]))
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['{} % of Sum'.format(second_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            new_row.append(column[second_index] / (column[first_index] + column[second_index]))
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['% Change {} to {}'.format(first_string, second_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            increase = column[second_index] - column[first_index]
                            new_row.append(increase / column[first_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

                    new_row = ['% Change {} to {}'.format(first_string, first_string)]
                    to_loop = df.iteritems()
                    next(to_loop)
                    for name, column in to_loop:
                        if type(column[0]) is not str:
                            increase = column[first_index] - column[second_index]
                            new_row.append(increase / column[second_index])
                        else:
                            new_row.append('NA')
                    writer.writerow(new_row)

    new_csv = csv_in.replace('metrics.csv', 'Overall_metrics.csv')
    shutil.copy(csv_in, new_csv)
    with open(new_csv, 'ab') as fp:
        writer = csv.writer(fp)
        writer.writerow('')
        new_row = ['Minimum']
        to_loop = df.iteritems()
        next(to_loop)
        for name, column in to_loop:
            if type(column[0]) is not str:
                new_row.append(min(column))
            else:
                new_row.append('NA')
        writer.writerow(new_row)

        new_row = ['Maximum']
        to_loop = df.iteritems()
        next(to_loop)
        for name, column in to_loop:
            if type(column[0]) is not str:
                new_row.append(max(column))
            else:
                new_row.append('NA')
        writer.writerow(new_row)

        new_row = ['Mean']
        to_loop = df.iteritems()
        next(to_loop)
        for name, column in to_loop:
            if type(column[0]) is not str:
                new_row.append(numpy.mean(column))
            else:
                new_row.append('NA')
        writer.writerow(new_row)

        new_row = ['Median']
        to_loop = df.iteritems()
        next(to_loop)
        for name, column in to_loop:
            if type(column[0]) is not str:
                new_row.append(numpy.median(column))
            else:
                new_row.append('NA')
        writer.writerow(new_row)

        new_row = ['Standard Deviation']
        to_loop = df.iteritems()
        next(to_loop)
        for name, column in to_loop:
            if type(column[0]) is not str:
                new_row.append(numpy.std(column))
            else:
                new_row.append('NA')
        writer.writerow(new_row)

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
    )