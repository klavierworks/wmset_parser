import json
import os
from dataclasses import is_dataclass, asdict
from typing import Any, Dict, List

from sections.generic_script_section import GenericScriptSection
from sections.models.parse import Model
from sections.section_15 import Section15
from sections.textures.tim import TIM


class Exporter:
    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_models(self, models: List[Model], object_textures: List[TIM]) -> None:
        models_dir = os.path.join(self.output_dir, "models")
        os.makedirs(models_dir, exist_ok=True)
        for i, model in enumerate(models):
            texture = object_textures[i]
            obj_path = os.path.join(models_dir, f"model_{i}.obj")
            Section15.export_model_to_obj(model, obj_path, texture)
            print(f"Exported model_{i}.obj")

    def export_textures(self, subfolder: str, textures: List[TIM]) -> None:
        textures_dir = os.path.join(self.output_dir, "textures", subfolder)
        os.makedirs(textures_dir, exist_ok=True)
        for i, texture in enumerate(textures):
            texture.save_png(os.path.join(textures_dir, f"{subfolder}_{i}.png"))

    def export_sections_json(self, sections: Dict[str, Any]) -> None:
        path = os.path.join(self.output_dir, "sections.json")
        with open(path, "w") as f:
            json.dump(sections, f, indent=4, default=self._json_default)

    @staticmethod
    def convert_script_section(section: GenericScriptSection) -> List[List[List[int]]]:
        return [
            [[op.code_id, op.param1, op.param2] for op in script.opcodes]
            for script in section.scripts
        ]

    @staticmethod
    def _json_default(obj: object) -> object:
        if is_dataclass(obj) and not isinstance(obj, type):
            return {k: v for k, v in asdict(obj).items() if k != "offsets"}
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in vars(obj).items() if k != "offsets"}
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
