import ayon_maya.api.action
from ayon_core.pipeline.publish import (
    PublishValidationError,
    ValidateContentsOrder,
)
from ayon_maya.api import plugin


class ValidateAnimationProductTypePublish(plugin.MayaInstancePlugin):
    """Validate at least a single product type is exported for the instance.
    
    Validate either fbx animation collector or collect animation output 
    geometry(Alembic) enabled for publishing otherwise no products
    would be generated for the instance - publishing nothing valid.
    """

    order = ValidateContentsOrder
    families = ["animation"]
    label = "Animation Product Type Publish"
    actions = [ayon_maya.api.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        publish_attributes = instance.data["publish_attributes"]
        if "animation.fbx" in instance.data["families"]:
            return invalid
        elif publish_attributes["ExtractAnimation"]["active"]:
            return invalid
        elif publish_attributes["ExtractMayaUsdAnim"]["active"]:
            return invalid
        else:
            invalid.append(instance.name)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            message = (
                f"Invalid Animation Product Type in {invalid}\n"
                "Users must turn on either 'Collect Fbx Animation'\n"
                "or 'Collect Animation Output Geometry(Alembic)'\n"
                "for publishing\n"
            )
            raise PublishValidationError(message)
