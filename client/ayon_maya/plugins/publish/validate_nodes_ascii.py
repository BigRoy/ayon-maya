import inspect

import ayon_maya.api.action
from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateContentsOrder,
    RepairAction
)
from ayon_maya.api import plugin, lib
from maya import cmds


class ValidateNodeNamesASCII(plugin.MayaInstancePlugin,
                             OptionalPyblishPluginMixin):
    """Ensure node names contain only ASCII characters.

    This avoids problematic characters in e.g. Alembic exports with names
    like `BÃ_zierCircle_001` which can cause issues in export and import
    to other software.

    It may also introduce issues with PyAlembic, see:
        - https://github.com/alembic/alembic/issues/462

    """

    order = ValidateContentsOrder
    families = ["model", "rig", "animation", "camera", "pointcache"]
    label = "Node names ASCII"
    actions = [ayon_maya.api.action.SelectInvalidAction, RepairAction]
    optional = False

    @classmethod
    def get_invalid(cls, instance) -> "list[str]":

        invalid = []
        for node in cmds.ls(instance):
            name = node.rsplit("|", 1)[-1]
            if not name.isascii():
                cls.log.warning(f"Invalid node name: {name}")

                # We only mark the node invalid if is an editable node and
                # the user can actually do something about it.
                if cmds.referenceQuery(node, isNodeReferenced=True):
                    cls.log.debug(
                        f"Node is referenced, skipping: {name}")
                    continue
                if cmds.lockNode(node, query=True, lock=True)[0]:
                    cls.log.debug(
                        f"Node is locked, skipping: {name}")
                    continue

                invalid.append(node)

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Detected non-ASCII characters in node names.",
                description=self.get_description())

    @classmethod
    @lib.undo_chunk()
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        # Fix children first to avoid full paths going invalid
        invalid = sorted(invalid, key=len, reverse=True)
        for node in invalid:
            name = node.rsplit("|", 1)[-1]
            # Strip non-ASCII characters
            ascii_name = name.encode("ascii", "ignore").decode("ascii")
            cmds.rename(node, ascii_name)

    @staticmethod
    def get_description():
        return inspect.cleandoc(
            """### Node names must contain only ASCII characters.
            
            Your scene contains nodes with non-ASCII characters which can cause
            issues when exporting and importing between different software.
            
            Use the Repair action to automatically strip the non-ASCII from the
            node names.
            """
        )
