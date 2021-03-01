# -*- coding: utf-8 -*-

"""
/***************************************************************************
 AreaWeightedAverage
                                 A QGIS plugin
 Area Area Weighted Average.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-02-21
        copyright            : (C) 2021 by Abdul Raheem Siddiqui
        email                : ars.work.ce@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = "Abdul Raheem Siddiqui"
__date__ = "2021-02-21"
__copyright__ = "(C) 2021 by Abdul Raheem Siddiqui"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"

import os
import inspect
import processing
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterBoolean,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterFileDestination,
)


class AreaWeightedAverageAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = "OUTPUT"
    INPUT = "INPUT"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "inputlayer",
                "Input Layer",
                types=[QgsProcessing.TypeVectorPolygon],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "overlaylayer",
                "Overlay Layer",
                types=[QgsProcessing.TypeVectorPolygon],
                defaultValue=None,
            )
        )

        param = QgsProcessingParameterField(
            "identifierfieldforreport",
            "Identifier Field for Report",
            optional=True,
            type=QgsProcessingParameterField.Any,
            parentLayerParameterName="inputlayer",
            allowMultiple=False,
            defaultValue="",
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterField(
                "fieldtoaverage",
                "Field to Average",
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="overlaylayer",
                allowMultiple=False,
                defaultValue=None,
            )
        )

        param = QgsProcessingParameterField(
            "additionalfields",
            "Additional Fields to Keep for Report",
            optional=True,
            type=QgsProcessingParameterField.Any,
            parentLayerParameterName="overlaylayer",
            allowMultiple=True,
        )
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "result",
                "Result",
                type=QgsProcessing.TypeVectorAnyGeometry,
                createByDefault=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "reportaslayer",
                "Report as Layer",
                type=QgsProcessing.TypeVectorAnyGeometry,
                createByDefault=True,
                defaultValue=None,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                "ReportasHTML",
                self.tr("Report as HTML"),
                self.tr("HTML files (*.html)"),
                None,
                True,
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(7, model_feedback)
        results = {}
        outputs = {}

        # add_ID_field to input layer
        alg_params = {
            "FIELD_NAME": "F_ID",
            "GROUP_FIELDS": [""],
            "INPUT": parameters["inputlayer"],
            "SORT_ASCENDING": True,
            "SORT_EXPRESSION": "",
            "SORT_NULLS_FIRST": False,
            "START": 0,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Add_id_field"] = processing.run(
            "native:addautoincrementalfield",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # add_area_field to input layer
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Area_AWA",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 0,
            "FORMULA": "area($geometry)",
            "INPUT": outputs["Add_id_field"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Add_area_field"] = processing.run(
            "qgis:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # dissolve all overlay fields so as not to repeat record in reporting
        alg_params = {
            "FIELD": [parameters["fieldtoaverage"]]
            + [
                field
                for field in parameters["additionalfields"]
                if field != str(parameters["fieldtoaverage"])
            ],
            "INPUT": parameters["overlaylayer"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Dissolve"] = processing.run(
            "native:dissolve",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        # intersection between input and overlay layer
        # delete no field in input layer and all fields in overlay layer
        # except field to average and additional fields
        alg_params = {
            "INPUT": outputs["Add_area_field"]["OUTPUT"],
            "INPUT_FIELDS": [""],
            "OVERLAY": outputs["Dissolve"]["OUTPUT"],
            "OVERLAY_FIELDS": [str(parameters["fieldtoaverage"])]
            + parameters["additionalfields"],
            "OVERLAY_FIELDS_PREFIX": "",
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Intersection"] = processing.run(
            "native:intersection",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # add_Weight
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": parameters["fieldtoaverage"] + "_Area",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 0,
            "FORMULA": ' "' + parameters["fieldtoaverage"] + '"  *  area($geometry)',
            "INPUT": outputs["Intersection"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Add_Weight"] = processing.run(
            "qgis:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # area_average
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Weighted_" + parameters["fieldtoaverage"],
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 0,
            "FORMULA": ' sum("' + parameters["fieldtoaverage"] + "_Area"
            '","F_ID")/"Area_AWA"',
            "INPUT": outputs["Add_Weight"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["area_average"] = processing.run(
            "qgis:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # remerge input layer elements
        alg_params = {
            "FIELD": ["F_ID"],
            "INPUT": outputs["area_average"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Dissolve2"] = processing.run(
            "native:dissolve",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        input_layer = self.parameterAsVectorLayer(parameters, "inputlayer", context)
        result_name = input_layer.name() + "_" + parameters["fieldtoaverage"]
        parameters["result"].destinationName = result_name

        # drop field(s) for Result
        #
        alg_params = {
            "COLUMN": ["F_ID", "Area_AWA"]
            + [parameters["fieldtoaverage"]]
            + [
                field
                for field in parameters["additionalfields"]
                if field != str(parameters["fieldtoaverage"])
            ]
            + [parameters["fieldtoaverage"] + "_Area"],
            "INPUT": outputs["Dissolve2"]["OUTPUT"],
            "OUTPUT": parameters["result"],
        }
        outputs["Drop1"] = processing.run(
            "qgis:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        results["result"] = outputs["Drop1"]["OUTPUT"]

        # Reporting

        # in input layer for 'Drop field(s) for Report' add Area and area as %

        # # Drop field(s) for Report

        int_layer = context.takeResultLayer(outputs["Add_Weight"]["OUTPUT"])
        all_fields = [f.name() for f in int_layer.fields()]
        fields_to_keep = (
            ["F_ID"]
            + [
                field
                for field in parameters["additionalfields"]
                if field != str(parameters["fieldtoaverage"])
            ]
            + [parameters["fieldtoaverage"]]
            + [parameters["identifierfieldforreport"]]
        )
        fields_to_drop = [f for f in all_fields if f not in fields_to_keep]
        alg_params = {
            "COLUMN": fields_to_drop,
            "INPUT": int_layer,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Drop2"] = processing.run(
            "qgis:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # update area
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Area_CRS_Units",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 0,
            "FORMULA": "area($geometry)",
            "INPUT": outputs["Drop2"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["update_area"] = processing.run(
            "qgis:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        parameters["reportaslayer"].destinationName = "Report as Layer"
        # add area %
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Area_Prcnt",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 0,
            "FORMULA": ' "Area_CRS_Units" *100/  sum(  "Area_CRS_Units" ,  "F_ID" )',
            "INPUT": outputs["update_area"]["OUTPUT"],
            "OUTPUT": parameters["reportaslayer"],
        }
        outputs["area_prcnt"] = processing.run(
            "qgis:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        results["reportaslayer"] = outputs["area_prcnt"]["OUTPUT"]

        # Drop geometries

        alg_params = {
            "INPUT": outputs["Add_Weight"]["OUTPUT"],
            "OUTPUT": parameters["ReportasTable"],
        }
        outputs["DropGeometries"] = processing.run(
            "native:dropgeometries",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        results["ReportasTable"] = outputs["DropGeometries"]["OUTPUT"]

        return results

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "Area Weighted Average"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ""

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return AreaWeightedAverageAlgorithm()

    def icon(self):
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        icon = QIcon(os.path.join(os.path.join(cmd_folder, "logo.png")))
        return icon