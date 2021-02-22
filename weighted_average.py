"""
Model exported as python.
Name : Weighted Average
Group : Tests
With QGIS : 31601
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class WeightedAverage(QgsProcessingAlgorithm):
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
        self.addParameter(
            QgsProcessingParameterField(
                "IDFieldMustnothaveduplicates",
                "ID Field [Must not have duplicates]",
                optional=True,
                type=QgsProcessingParameterField.Any,
                parentLayerParameterName="inputlayer",
                allowMultiple=False,
                defaultValue="",
            )
        )
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
        self.addParameter(
            QgsProcessingParameterField(
                "AdditionalFields",
                "Additional Fields to keep for HTML Table",
                optional=True,
                type=QgsProcessingParameterField.Any,
                parentLayerParameterName="overlaylayer",
                allowMultiple=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                "VERBOSE_LOG", "Verbose logging", optional=True, defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "result",
                "Result",
                type=QgsProcessing.TypeVectorAnyGeometry,
                createByDefault=True,
                supportsAppend=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "Intersected",
                "Intersected",
                type=QgsProcessing.TypeVectorAnyGeometry,
                createByDefault=True,
                supportsAppend=True,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "NameorID",  # to do: reduce name length
                "Name or ID Field [Must not have duplicates]",
                optional=True,
                type=QgsProcessingParameterField.Any,
                parentLayerParameterName="inputlayer",
                allowMultiple=False,
                defaultValue="",
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
            "FIELD_NAME": "__Unique_ID__",
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
            "FIELD_NAME": "__Area_SPW__",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 0,
            "FORMULA": "area($geometry)",
            "INPUT": outputs["Add_id_field"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Add_area_field"] = processing.run(
            "native:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # intersection between input and overlay layer
        alg_params = {
            "INPUT": outputs["Add_area_field"]["OUTPUT"],
            "INPUT_FIELDS": [""],
            "OVERLAY": parameters["overlaylayer"],
            "OVERLAY_FIELDS": [str(parameters["fieldtoaverage"])]
            + parameters["AdditionalFields"],
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
            "OUTPUT": parameters["Intersected"]
            #'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs["Add_Weight"] = processing.run(
            "native:fieldcalculator",
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
            '","__Unique_ID__")/"__Area_SPW__"',
            "INPUT": outputs["Add_Weight"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["area_average"] = processing.run(
            "native:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Dissolve
        alg_params = {
            "FIELD": ["__Unique_ID__"],
            "INPUT": outputs["area_average"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["Dissolve"] = processing.run(
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

        # in input layer for 'Drop field(s) for Report' add Area and area as %

        # Drop field(s) for Report
        alg_params = {
            "COLUMN": ["__Unique_ID__", "__Area_SPW__"]
            + [
                parameters["fieldtoaverage"]
            ]  # to do: drop all fields in input layer except id field
            + [parameters["fieldtoaverage"] + "_Area"],
            "INPUT": outputs["Add_Weight"]["OUTPUT"],
            "OUTPUT": parameters["result"],
        }
        outputs[result_name] = processing.run(
            "qgis:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        outputs[result_name]["OUTPUT"] = result_name
        results["result"] = outputs[result_name]["OUTPUT"]

        # Drop field(s) for Result
        alg_params = {
            "COLUMN": ["__Unique_ID__", "__Area_SPW__"]
            + [parameters["fieldtoaverage"]]
            + parameters["AdditionalFields"]
            + [parameters["fieldtoaverage"] + "_Area"],
            "INPUT": outputs["Dissolve"]["OUTPUT"],
            "OUTPUT": parameters["result"],
        }
        outputs[result_name] = processing.run(
            "qgis:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        outputs[result_name]["OUTPUT"] = result_name
        results["result"] = outputs[result_name]["OUTPUT"]

        return results

    def name(self):
        return "Weighted Average"

    def displayName(self):
        return "Weighted Average"

    def group(self):
        return "Tests"

    def groupId(self):
        return "Tests"

    def createInstance(self):
        return WeightedAverage()
