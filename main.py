from dxfimport.importer import ReadDXF
from globals.config import MyConfig
import globals.globals as g

from copy import copy, deepcopy
from core.shape import Shape
from core.point import Point
from core.holegeo import HoleGeo
from core.layercontent import LayerContent, Layers, Shapes
from core.entitycontent import EntityContent
from core.linegeo import LineGeo

from postpro.postprocessor import MyPostProcessor

import logging
import os, sys


class Main():
    '''
    MAin class
    '''
    def __init__(self, dxf_filename):
        '''
        initialization
        '''
        self.dxf_filename = dxf_filename
        self.valuesDXF = None
        self.shapes = Shapes([])
        self.entityRoot = None
        self.layerContents = Layers([])
        self.newNumber = 1

        self.cont_dx = 0.0
        self.cont_dy = 0.0
        self.cont_rotate = 0.0
        self.cont_scale = 1.0

        self.filename = ""
        self.MyPostProcessor = MyPostProcessor()

    def load(self):
        """
        Loads the file given by self.filename.  Also calls the command to
        make the plot.
        @param plot: if it should plot
        """
        g.config = MyConfig()
        self.valuesDXF = ReadDXF(self.dxf_filename)

        # Output the information in the text window
        logger.info(('Loaded layers: %s') % len(self.valuesDXF.layers))
        logger.info(('Loaded blocks: %s') % len(self.valuesDXF.blocks.Entities))
        for i in range(len(self.valuesDXF.blocks.Entities)):
            layers = self.valuesDXF.blocks.Entities[i].get_used_layers()
            logger.info(('Block %i includes %i Geometries, reduced to %i Contours, used layers: %s') % (i, len(self.valuesDXF.blocks.Entities[i].geo), len(self.valuesDXF.blocks.Entities[i].cont), layers))
        layers = self.valuesDXF.entities.get_used_layers()
        insert_nr = self.valuesDXF.entities.get_insert_nr()
        logger.info(('Loaded %i entity geometries; reduced to %i contours; used layers: %s; number of inserts %i') % (len(self.valuesDXF.entities.geo), len(self.valuesDXF.entities.cont), layers, insert_nr))

        if g.config.metric == 0:
            logger.info("Drawing units: inches")
            distance = ("[in]")
            speed = ("[IPM]")
        else:
            logger.info("Drawing units: millimeters")
            distance = ("[mm]")
            speed = ("[mm/min]")
        self.makeShapes()
        self.sort_default()
        self.exportShapes()

    def makeShapes(self):
        self.entityRoot = EntityContent(nr=0, name='Entities', parent=None,
                                        p0=Point(self.cont_dx, self.cont_dy), pb=Point(),
                                        sca=[self.cont_scale, self.cont_scale, self.cont_scale], rot=self.cont_rotate)
        self.layerContents = Layers([])
        self.shapes = Shapes([])

        self.makeEntityShapes(self.entityRoot)

        for layerContent in self.layerContents:
            layerContent.overrideDefaults()
        self.layerContents.sort(key=lambda x: x.nr)
        self.newNumber = len(self.shapes)

    def makeEntityShapes(self, parent, layerNr=-1):
        """
        Instance is called prior to plotting the shapes. It creates
        all shape classes which are plotted into the canvas.

        @param parent: The parent of a shape is always an Entity. It may be the root
        or, if it is a Block, this is the Block.
        """
        if parent.name == "Entities":
            entities = self.valuesDXF.entities
        else:
            ent_nr = self.valuesDXF.Get_Block_Nr(parent.name)
            entities = self.valuesDXF.blocks.Entities[ent_nr]

        # Assigning the geometries in the variables geos & contours in cont
        ent_geos = entities.geo

        # Loop for the number of contours
        for cont in entities.cont:
            # Query if it is in the contour of an insert or of a block
            if ent_geos[cont.order[0][0]].Typ == "Insert":
                ent_geo = ent_geos[cont.order[0][0]]

                # Assign the base point for the block
                new_ent_nr = self.valuesDXF.Get_Block_Nr(ent_geo.BlockName)
                new_entities = self.valuesDXF.blocks.Entities[new_ent_nr]
                pb = new_entities.basep

                # Scaling, etc. assign the block
                p0 = ent_geos[cont.order[0][0]].Point
                sca = ent_geos[cont.order[0][0]].Scale
                rot = ent_geos[cont.order[0][0]].rot

                # Creating the new Entitie Contents for the insert
                newEntityContent = EntityContent(nr=0,
                                                 name=ent_geo.BlockName,
                                                 parent=parent,
                                                 p0=p0,
                                                 pb=pb,
                                                 sca=sca,
                                                 rot=rot)

                parent.append(newEntityContent)

                self.makeEntityShapes(newEntityContent, ent_geo.Layer_Nr)

            else:
                # Loop for the number of geometries
                tmp_shape = Shape(len(self.shapes),
                                  (True if cont.closed else False),
                                  parent)

                for ent_geo_nr in range(len(cont.order)):
                    ent_geo = ent_geos[cont.order[ent_geo_nr][0]]
                    if cont.order[ent_geo_nr][1]:
                        ent_geo.geo.reverse()
                        for geo in ent_geo.geo:
                            geo = copy(geo)
                            geo.reverse()
                            self.append_geo_to_shape(tmp_shape, geo)
                        ent_geo.geo.reverse()
                    else:
                        for geo in ent_geo.geo:
                            self.append_geo_to_shape(tmp_shape, copy(geo))

                if len(tmp_shape.geos) > 0:
                    # All shapes have to be CW direction.
                    tmp_shape.AnalyseAndOptimize()

                    self.shapes.append(tmp_shape)
                    if g.config.vars.Import_Parameters['insert_at_block_layer'] and layerNr != -1:
                        self.addtoLayerContents(tmp_shape, layerNr)
                    else:
                        self.addtoLayerContents(tmp_shape, ent_geo.Layer_Nr)
                    parent.append(tmp_shape)

    def append_geo_to_shape(self, shape, geo):
        if -1e-5 <= geo.length < 1e-5:  # TODO adjust import for this
            return

        # if self.ui.actionSplitLineSegments.isChecked(): RW
        if isinstance(geo, LineGeo):
            diff = (geo.Pe - geo.Ps) / 2.0
            geo_b = deepcopy(geo)
            geo_a = deepcopy(geo)
            geo_b.Pe -= diff
            geo_a.Ps += diff
            shape.append(geo_b)
            shape.append(geo_a)
        else:
            shape.append(geo)
        #else: RW
            #shape.append(geo) RW

        if isinstance(geo, HoleGeo):
            shape.type = 'Hole'
            shape.closed = True  # TODO adjust import for holes?
            if g.config.machine_type == 'drag_knife':
                shape.disabled = True
                shape.allowedToChange = False
    
    def addtoLayerContents(self, shape, lay_nr):
        # Check if the layer already exists and add shape if it is.
        for LayCon in self.layerContents:
            if LayCon.nr == lay_nr:
                LayCon.shapes.append(shape)
                shape.parentLayer = LayCon
                return

        # If the Layer does not exist create a new one.
        LayerName = self.valuesDXF.layers[lay_nr].name
        self.layerContents.append(LayerContent(lay_nr, LayerName, [shape]))
        shape.parentLayer = self.layerContents[-1]

    def exportShapes(self, status=False, saveas=None):
        """
        This function is called by the menu "Export/Export Shapes". It may open
        a Save Dialog if used without LinuxCNC integration. Otherwise it's
        possible to select multiple postprocessor files, which are located
        in the folder.
        """

        logger.debug('Export the enabled shapes') # save debug line into the logger file

        # Get the export order from the QTreeView
        # self.TreeHandler.updateExportOrder()
        #self.updateExportRoute()

        logger.debug("Sorted layers:") # save debug line into the logger file
        for i, layer in enumerate(self.layerContents.non_break_layer_iter()):
            logger.debug("LayerContents[%i] = %s" % (i, layer)) #save layers from class layerContents into the logger file

        for i, layer in enumerate(self.layerContents.non_break_layer_iter()):
            print("LayerContents[%i] = %s" % (i, layer))    #testing line

        if not g.config.vars.General['write_to_stdout']:

            # Get the name of the File to export
            if not saveas:
                MyFormats = ""
                for i in range(len(self.MyPostProcessor.output_format)):
                    name = "%s " % (self.MyPostProcessor.output_text[i])
                    format_ = "(*%s);;" % (self.MyPostProcessor.output_format[i])
                    MyFormats = MyFormats + name + format_
                filename = ['C:\\PythonScripts\\1.Programming\\dxf2g\\config\\test.ngc','G-CODE for LinuxCNC (*.ngc)']
                save_filename = filename[0]

            else:
                filename = [None, None]
                save_filename = saveas

            # If Cancel was pressed
            if not save_filename:
                self.unsetCursor()
                return

            (beg, ende) = os.path.split(save_filename) #path and file name with extension

            (fileBaseName, fileExtension) = os.path.splitext(ende)#file name and extension

            pp_file_nr = 0
            for i in range(len(self.MyPostProcessor.output_format)):
                name = "%s " % (self.MyPostProcessor.output_text[i])
                format_ = "(*%s)" % (self.MyPostProcessor.output_format[i])
                MyFormats = name + format_
                if filename[1] == MyFormats:
                    pp_file_nr = i
            if fileExtension != self.MyPostProcessor.output_format[pp_file_nr]:
                if not QtCore.QFile.exists(save_filename):
                    save_filename += self.MyPostProcessor.output_format[pp_file_nr]

            self.MyPostProcessor.getPostProVars(pp_file_nr)
        else:
            save_filename = ""
            self.MyPostProcessor.getPostProVars(0)

        """
        Export will be performed according to LayerContents and their order
        is given in this variable too.
        """

        self.MyPostProcessor.exportShapes(self.filename,
                                          save_filename,
                                          self.layerContents)

        self.unsetCursor()

        if g.config.vars.General['write_to_stdout']:
            self.close()

    def sort_default(self):
        '''
        The function is setting order from dxf
        '''
        self.layerContents.sort(key=lambda x: x.nr, reverse=False)

    @staticmethod
    def log_file_path():
        '''
        Return a path for a log file
        '''
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)  # from exe
        elif __file__:
            script_dir = os.path.dirname(__file__)  # running live
        return script_dir

    @staticmethod
    def log_config(script_dir):
        '''
        Setting up logger configuration
        '''
        LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
        logging.basicConfig(filename=script_dir + "\\LogFile.log",
                            level=logging.DEBUG, format=LOG_FORMAT,
                            filemode='w')  # filemode=w clean the log file
        logger = logging.getLogger()
        return logger


script_dir = Main.log_file_path()
logger = Main.log_config(script_dir)
dxf_object = Main('C:\\PythonScripts\\1.Programming\\dxf2g\\4.dxf')
Main.load(dxf_object)
