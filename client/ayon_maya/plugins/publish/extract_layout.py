import json
import os

from ayon_api import get_representation_by_id
from ayon_maya.api import plugin, lib
from maya import cmds
from maya.api import OpenMaya as om


class ExtractLayout(plugin.MayaExtractorPlugin):
    """Extract a layout."""

    label = "Extract Layout"
    families = ["layout"]
    project_container = "AVALON_CONTAINERS"
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.debug("Performing extraction..")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        json_data = []
        # TODO representation queries can be refactored to be faster
        project_name = instance.context.data["projectName"]

        for asset in cmds.sets(str(instance), query=True):
            # Find the container
            project_container = self.project_container
            container_list = cmds.ls(project_container)
            if len(container_list) == 0:
                self.log.warning("Project container is not found!")
                self.log.warning("The asset(s) may not be properly loaded after published") # noqa
                continue

            grp_loaded_ass = instance.data.get("groupLoadedAssets", False)
            if grp_loaded_ass:
                asset_list = cmds.listRelatives(asset, children=True)
                # WARNING This does override 'asset' variable from parent loop
                #   is it correct?
                for asset in asset_list:
                    grp_name = asset.split(':')[0]
            else:
                grp_name = asset.split(':')[0]
            containers = cmds.ls("{}*_CON".format(grp_name))
            if len(containers) == 0:
                self.log.warning("{} isn't from the loader".format(asset))
                self.log.warning("It may not be properly loaded after published") # noqa
                continue
            container = containers[0]

            representation_id = cmds.getAttr(
                "{}.representation".format(container))

            representation = get_representation_by_id(
                project_name,
                representation_id,
                fields={"versionId", "context"}
            )

            self.log.debug(representation)

            version_id = representation["versionId"]
            # TODO use product entity to get product type rather than
            #    data in representation 'context'
            repre_context = representation["context"]
            product_type = repre_context.get("product", {}).get("type")
            if not product_type:
                product_type = repre_context.get("family")

            json_element = {
                "product_type": product_type,
                "instance_name": cmds.getAttr(
                    "{}.namespace".format(container)),
                "representation": str(representation_id),
                "version": str(version_id)
            }


            row_length = 4
            t_matrix_list = cmds.xform(asset, query=True, matrix=True)
            maya_transform_mm = om.MMatrix(t_matrix_list)
            convert_transform_mm = om.MMatrix()
            for i in range(0, row_length):
                first_row = maya_transform_mm.getElement(i, 0)
                second_row = maya_transform_mm.getElement(i, 1)
                third_row = maya_transform_mm.getElement(i, 2)
                fourth_row = maya_transform_mm.getElement(i, 3)
                if i == 1:
                    convert_transform_mm.setElement(i, 0, -first_row)
                    convert_transform_mm.setElement(i, 1, second_row)
                    convert_transform_mm.setElement(i, 2, -third_row)
                    convert_transform_mm.setElement(i, 3, -fourth_row)
                else:
                    convert_transform_mm.setElement(i, 0, first_row)
                    convert_transform_mm.setElement(i, 1, -second_row)
                    convert_transform_mm.setElement(i, 2, third_row)
                    convert_transform_mm.setElement(i, 3, fourth_row)

            json_filename = "{}.json".format(instance.name)
            json_path = os.path.join(stagingdir, json_filename)
            t_matrix = []
            with lib.maintained_selection():
                cmds.select(asset, noExpand=True)
                sel = om.MGlobal.getActiveSelectionList()
                dagpath = sel.getDependNode(0)
                ue_transform = om.MFnTransform(dagpath)
                with lib.maintained_transformation(ue_transform):
                    # make sure the data doesn't change during context
                    convert_transform = om.MTransformationMatrix(convert_transform_mm)
                    final_ue_transform = ue_transform.setTransformation(convert_transform)
                    t_matrix_list = list(final_ue_transform.transformation().asMatrix())

                    for i in range(0, len(t_matrix_list), row_length):
                        t_matrix.append(t_matrix_list[i:i + row_length])

            json_element["transform_matrix"] = [
                list(row)
                for row in t_matrix
            ]

            json_element["basis"] = [
                [1, 0, 0, 0],
                [0, 0, 1, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 1]
            ]

            json_data.append(json_element)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        json_representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(json_representation)

        self.log.debug("Extracted instance '%s' to: %s",
                       instance.name, json_representation)
