from collections import defaultdict
from typing import List
import inspect

from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateContentsOrder,
)
import ayon_maya.api.action
from ayon_maya.api import plugin

import maya.cmds as cmds
import pyblish.api


def strip_namespace(path: str) -> str:
    """Return maya node path without namespaces

    Example:
        >>> strip_namespace("|aa:bb:cc|hello:world|foo:bar")
        "cc|world|bar"
        >>> strip_namespace("|namespace:grp|namespace:foobar")
        "grp|foobar"

    """
    return "|".join(
        # Strip of namespace from each name in the path's hierarchy
        name.rsplit(":", 1)[-1] for name in path.split("|")
    )


class ValidateStripNamespacesUniqueness(plugin.MayaInstancePlugin,
                                        OptionalPyblishPluginMixin):
    """Ensure no node names clash if namespaces are stripped on export"""

    order = ValidateContentsOrder
    families = ["animation", "pointcache", "usd"]
    label = "Strip Namespaces Uniqueness"
    actions = [ayon_maya.api.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        nodes = cmds.ls(instance, long=True)

        # Group nodes by their path without namespaces
        node_by_path = defaultdict(list)
        for node in nodes:
            node_by_path[strip_namespace(node)].append(node)

        # Any entry that has more than one path is invalid
        invalid: List[str] = []
        for path, invalid_nodes in node_by_path.items():
            if len(invalid_nodes) > 1:
                # Clashes found
                # For brevity of the warnings exclude warning logs for any
                # child that also has a clash on its direct parent so that
                # e.g. shapes aren't reported separately
                parent = path.rsplit("|", 1)[0]
                if len(node_by_path.get(parent, [])) < 2:
                    cls.log.warning("Clashing nodes at path: %s", path)
                for invalid_node in invalid_nodes:
                    cls.log.debug("\t%s", invalid_node)

                invalid.extend(invalid_nodes)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""
        if not self.is_active(instance.data):
            return

        if self.is_stripping_namespaces(instance):
            return

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                message="Clashing sibling node names found.",
                title="Clashing sibling node names",
                description=self.get_description()
            )

    def is_stripping_namespaces(self, instance: pyblish.api.Instance) -> bool:
        """Return whether strip namespaces is enabled or not for the export"""
        # TODO: Preferably we have a less hacky way to find whether
        #  strip namespaces will be enabled or not for the export
        # The strip namespaces toggle is exposed on these plug-ins for
        # publishing. We check on the instance whether it's enabled/disabled
        # when attribute values are found for the plug-ins.
        settings = [
            ("ExtractAnimation", "stripNamespaces"),
            ("ExtractAlembic", "stripNamespaces"),
            ("ExtractMayaUsdAnim", "stripNamespaces"),
            ("ExtractMayaUsdModel", "stripNamespaces"),
            ("ExtractMayaUsdPointcache", "stripNamespaces"),
            ("ExtractMayaUsd", "stripNamespaces"),
        ]
        publish_attributes = instance.data.get("publish_attributes", {})
        for plugin_name, attr_name in settings:
            if plugin_name in publish_attributes:
                state = publish_attributes[plugin_name].get(attr_name, True)
                self.log.debug("Found plug-in attribute values for %s.%s = %s",
                               plugin_name, attr_name, state)
                return state
        return False

    def get_description(self):
        return inspect.cleandoc("""
        ### Clashing node names found
        
        Sibling nodes were found that clash by node name when the namespace
        is stripped off. Choose to either **not** strip the namespaces or
        correct the hierarchy so siblings have unique node names.
        
        For example this is a conflict:
        ```
        - /grp/namespace:bar
        - /grp/other:bar
        ```
        Because each of the entries, when namespaces are stripped result
        in the same destination path: `/grp/bar`.
        """)
