import inspect

import pyblish.api

import ayon_maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from ayon_maya.api import plugin

from maya import cmds


class ValidateMeshPolyCheck(plugin.MayaInstancePlugin,
                            OptionalPyblishPluginMixin):
    """Validate mesh for errors using `maya.cmds.polyCheck`"""

    order = pyblish.api.ValidatorOrder
    families = ["model", "pointcache", "animation"]
    label = "Mesh Check"
    optional = True
    optional_tooltip = (
        "Validate a mesh for internal errors."
        "\n\n"
        "This validation may be slow to run on large meshes or scenes and can "
        "then be disabled.\nOtherwise it's best to leave it on since it "
        "captures some hard to find errors that may generate issues later on."
        "\n\n"
        "For example, there were cases where upon exporting a mesh to Alembic "
        "it would lose its UVs, due to some 'hidden' errors in the mesh."
    )

    actions = [
        ayon_maya.api.action.SelectInvalidAction
    ]

    @classmethod
    def get_invalid(cls, instance):
        meshes = cmds.ls(instance, type="mesh", long=True)
        return [mesh for mesh in meshes if cmds.polyCheck(mesh)]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

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