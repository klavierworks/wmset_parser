from dataclasses import dataclass
from typing import List
from sections.models.parse import Model
from sections.textures.tim import TIM
from utils.binary_reader import BinaryReader
from io import BytesIO

@dataclass(init=False)
class Section15:
  offsets: List[int]
  models: List[Model]

  def __init__(self, stream: BytesIO):
    self.offsets = self.parse_offsets(stream)
    self.models = self.parse_models(stream, self.offsets)
  
  def parse_offsets(self, stream: BytesIO) -> List[int]:
    offsets: List[int] = []
    while True:
        offset = BinaryReader.read_uint16(stream)
        blank_space = BinaryReader.read_uint16(stream) ## padding, I see a 15 is one of the values here, unsure why
        if offset == 0:
            break
        if blank_space != 0:
          if blank_space == 15:
            print(f"Note: Found expected padding value 15 at offset {stream.tell()-2}. This is possibly a legacy model as it is also unable to be parsed the same way.")
          else:
            print(f"Warning: Expected padding to be 0, got {blank_space} at offset {stream.tell()-2}. Offset: {offset}")
          
          print("Ignoring.")
          continue
        offsets.append(offset)
    return offsets

  def parse_models(self, stream: BytesIO, offsets: List[int]) -> List[Model]:
    models: List[Model] = []
    for i, offset in enumerate(offsets):
      start_offset = offset
      end_offset = offsets[i + 1] if i + 1 < len(offsets) else len(stream.getbuffer())
      chunk_size = end_offset - start_offset
      stream.seek(start_offset)
      model_bytes = stream.read(chunk_size)
      model_stream = BytesIO(model_bytes)
      model = Model(model_stream)
      models.append(model)  
  
    return models
  
  @staticmethod
  def export_model_to_obj(model: Model, obj_filename: str, tim: TIM):
      """
      Export a Model to a Wavefront OBJ using a TIM texture.
      Writes .obj, .mtl, and ensures TIM PNG is saved.
      """
      import os

      # Ensure TIM texture is saved
      png_filename = os.path.splitext(obj_filename)[0] + ".png"
      tim.save_png(png_filename)

      mtl_filename = os.path.splitext(obj_filename)[0] + ".mtl"
      material_name = "Textured"

      # --- Write MTL ---
      with open(mtl_filename, "w") as mtl_file:
          mtl_file.write(f"# Material for {os.path.basename(mtl_filename)}\n")
          mtl_file.write(f"newmtl {material_name}\n")
          mtl_file.write("Ka 1.000 1.000 1.000\n")
          mtl_file.write("Kd 1.000 1.000 1.000\n")
          mtl_file.write("Ks 0.000 0.000 0.000\n")
          mtl_file.write("d 1.0\n")
          mtl_file.write("illum 2\n")
          mtl_file.write(f"map_Kd {os.path.basename(png_filename)}\n")

      width = tim.header.img_w
      height = tim.header.img_h

      # --- Write OBJ ---
      os.makedirs(os.path.dirname(obj_filename), exist_ok=True)
      with open(obj_filename, "w") as obj_file:
          obj_file.write(f"# Exported OBJ: {os.path.basename(obj_filename)}\n")
          obj_file.write(f"mtllib {os.path.basename(mtl_filename)}\n")
          obj_file.write(f"usemtl {material_name}\n\n")

          # --- Vertices ---
          for vertex in model.vertices:
              x = vertex.x / 100.0
              y = -vertex.y / 100.0  # Y-flip
              z = vertex.z / 100.0
              obj_file.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
          obj_file.write("\n")

          # --- UVs ---
          uv_counter = 1
          uv_indices = []

          # Triangles
          for tri in model.triangles:
              for i in range(3):
                  u = tri.texcoords1[i] if i < len(tri.texcoords1) else 0
                  v = tri.texcoords2[i] if i < len(tri.texcoords2) else 0
                  # Correct PS1 UV normalization
                  uu = u / width
                  vv = 1.0 - (v / height)
                  uv_indices.append(uv_counter)
                  obj_file.write(f"vt {uu:.6f} {vv:.6f}\n")
                  uv_counter += 1

          # Quads
          for quad in model.quads:
              tex_coords = [quad.texcoords1, quad.texcoords2, quad.texcoords3, quad.texcoords4]
              for tex in tex_coords:
                  if isinstance(tex, list) and len(tex) >= 2:
                      u, v = tex[:2]
                  else:
                      u, v = 0, 0
                  uu = u / width
                  vv = 1.0 - (v / height)
                  uv_indices.append(uv_counter)
                  obj_file.write(f"vt {uu:.6f} {vv:.6f}\n")
                  uv_counter += 1

          obj_file.write("\n")

          # --- Faces ---
          uv_index_counter = 1

          # Triangles
          for tri in model.triangles:
              v_idx = [i + 1 for i in tri.vertex_indices]
              obj_file.write(
                  f"f {v_idx[0]}/{uv_index_counter} {v_idx[1]}/{uv_index_counter+1} {v_idx[2]}/{uv_index_counter+2}\n"
              )
              uv_index_counter += 3

          # Quads
          for quad in model.quads:
              v_idx = [i + 1 for i in quad.vertex_indices]
              # Swap 2 and 3 for PS1 quad winding
              obj_file.write(
                  f"f {v_idx[0]}/{uv_index_counter} {v_idx[1]}/{uv_index_counter+1} "
                  f"{v_idx[3]}/{uv_index_counter+3} {v_idx[2]}/{uv_index_counter+2}\n"
              )
              uv_index_counter += 4
