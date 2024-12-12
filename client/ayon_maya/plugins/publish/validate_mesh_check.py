import inspect

import pyblish.api

import ayon_maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError
)
from ayon_maya.api import plugin

from maya import cmds


class ValidateMeshPolyCheck(plugin.MayaInstancePlugin):
    """Validate mesh for errors using `maya.cmds.polyCheck`"""

    order = pyblish.api.ValidatorOrder
    families = ["model", "pointcache", "animation"]
    label = "Mesh Check"
    actions = [
        ayon_maya.api.action.SelectInvalidAction
    ]

    @classmethod
    def get_invalid(cls, instance):
        meshes = cmds.ls(instance, type="mesh", long=True)
        return [mesh for mesh in meshes if cmds.polyCheck(mesh)]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                f"Meshes found with errors: {invalid}",
                description=self.get_description()
            )

    @staticmethod
    def get_description():
        inspect.cleandoc(
            """### Meshes found with errors

            According to Maya's `polyCheck` command some meshes have errors.
            
            The errors are reported to the Maya Output Window.
            """
        )