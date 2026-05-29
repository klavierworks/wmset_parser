import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple
from sections.models.parse import Model
from sections.textures.tim import TIM
from utils.binary_reader import BinaryReader
from io import BytesIO

@dataclass(init=False)
class Section15:
  entries: List[Tuple[int, int]]  # (stored_offset, blank) per table entry
  models: List[Optional[Model]]

  def __init__(self, stream: BytesIO):
    self.entries = self.parse_entries(stream)
    self.models = self.parse_models(stream, self.entries)

  def parse_entries(self, stream: BytesIO) -> List[Tuple[int, int]]:
    entries: List[Tuple[int, int]] = []
    while True:
        offset = BinaryReader.read_uint16(stream)
        blank = BinaryReader.read_uint16(stream)
        if offset == 0 and blank == 0:
            break
        entries.append((offset, blank))
    return entries

  def parse_models(self, stream: BytesIO, entries: List[Tuple[int, int]]) -> List[Optional[Model]]:
    """Parse models. For entries where `blank` is nonzero, the stored offset is
    garbage and `blank` is the alignment mask (e.g. 0x0F → 16-byte align);
    derive the real offset from end-of-previous-model aligned to `blank+1`."""
    models: List[Optional[Model]] = []
    section_len = len(stream.getbuffer())
    prev_end: Optional[int] = None

    for i, (stored_offset, blank) in enumerate(entries):
      if blank != 0:
        if prev_end is None:
          print(f"Model {i}: nonzero blank=0x{blank:02x} with no prior model — skipping.")
          models.append(None)
          continue
        actual_offset = (prev_end + blank) & ~blank
        print(f"Model {i}: blank=0x{blank:02x}, using aligned offset {actual_offset} (stored={stored_offset} ignored).")
      else:
        actual_offset = stored_offset

      if actual_offset + 8 > section_len:
        print(f"Model {i}: offset {actual_offset} past section end — skipping.")
        models.append(None)
        continue

      stream.seek(actual_offset)
      tri, quad, _tex_page, vtx = struct.unpack('<HHHH', stream.read(8))
      size = 8 + tri * 12 + quad * 16 + vtx * 8

      if actual_offset + size > section_len:
        print(f"Model {i}: header at {actual_offset} gives size {size} which exceeds section — skipping.")
        models.append(None)
        continue

      stream.seek(actual_offset)
      try:
        model = Model(BytesIO(stream.read(size)))
        models.append(model)
        prev_end = actual_offset + size
      except Exception as e:
        print(f"Failed to parse model {i} at offset {actual_offset}: {e}. Inserting None.")
        models.append(None)

    return models
  
  # Canvas is at 4bpp-pixel density (4 image pixels per VRAM 16bpp pixel horizontally).
  # PS1 VRAM is 1024×512 16bpp-pixels, so canvas is 4096×512 image-pixels.
  ATLAS_W = 4096
  ATLAS_H = 512

  @staticmethod
  def export_model_to_obj(model: Model, obj_filename: str, atlas_png_basename: str):
      """Write OBJ+MTL referencing a shared VRAM-atlas PNG. UVs are remapped from
      page-relative (model.texture_page + u/v) into atlas-relative coords."""
      import os

      tp = model.texture_page
      tx = tp & 0xF
      ty = (tp >> 4) & 1
      fmt = (tp >> 7) & 3  # 0=4bpp, 1=8bpp, 2=16bpp
      # u scale: image-pixels-per-VRAM-16bpp-pixel for the page's bpp, then
      # converted to canvas density (4× per 16bpp pixel).
      u_scale = {0: 1, 1: 2, 2: 4}[fmt]
      page_cx = tx * 256
      page_cy = ty * 256

      def to_uv(u: int, v: int):
          cx = page_cx + u * u_scale
          cy = page_cy + v
          return cx / Section15.ATLAS_W, 1.0 - (cy / Section15.ATLAS_H)

      mtl_filename = os.path.splitext(obj_filename)[0] + ".mtl"
      material_name = "Textured"

      with open(mtl_filename, "w") as mtl_file:
          mtl_file.write(f"# Material for {os.path.basename(mtl_filename)}\n")
          mtl_file.write(f"newmtl {material_name}\n")
          mtl_file.write("Ka 1.000 1.000 1.000\n")
          mtl_file.write("Kd 1.000 1.000 1.000\n")
          mtl_file.write("Ks 0.000 0.000 0.000\n")
          mtl_file.write("d 1.0\n")
          mtl_file.write("illum 2\n")
          mtl_file.write(f"map_Kd {atlas_png_basename}\n")

      os.makedirs(os.path.dirname(obj_filename), exist_ok=True)
      with open(obj_filename, "w") as obj_file:
          obj_file.write(f"# Exported OBJ: {os.path.basename(obj_filename)}\n")
          obj_file.write(f"mtllib {os.path.basename(mtl_filename)}\n")
          obj_file.write(f"usemtl {material_name}\n\n")

          for vertex in model.vertices:
              x = vertex.x / 100.0
              y = -vertex.y / 100.0
              z = vertex.z / 100.0
              obj_file.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
          obj_file.write("\n")

          for tri in model.triangles:
              for tex in (tri.texcoords1, tri.texcoords2, tri.texcoords3):
                  u, v = tex[0], tex[1]
                  uu, vv = to_uv(u, v)
                  obj_file.write(f"vt {uu:.6f} {vv:.6f}\n")

          for quad in model.quads:
              for tex in (quad.texcoords1, quad.texcoords2, quad.texcoords3, quad.texcoords4):
                  u, v = tex[0], tex[1]
                  uu, vv = to_uv(u, v)
                  obj_file.write(f"vt {uu:.6f} {vv:.6f}\n")

          obj_file.write("\n")

          uv_index_counter = 1
          for tri in model.triangles:
              v_idx = [i + 1 for i in tri.vertex_indices]
              obj_file.write(
                  f"f {v_idx[0]}/{uv_index_counter} {v_idx[1]}/{uv_index_counter+1} {v_idx[2]}/{uv_index_counter+2}\n"
              )
              uv_index_counter += 3

          for quad in model.quads:
              v_idx = [i + 1 for i in quad.vertex_indices]
              obj_file.write(
                  f"f {v_idx[0]}/{uv_index_counter} {v_idx[1]}/{uv_index_counter+1} "
                  f"{v_idx[3]}/{uv_index_counter+3} {v_idx[2]}/{uv_index_counter+2}\n"
              )
              uv_index_counter += 4

  @staticmethod
  def build_vram_atlas(tims: List[TIM]):
      """Composite TIMs onto a 4096×512 (4bpp-density) PS1-VRAM atlas."""
      from PIL import Image
      atlas = Image.new("RGBA", (Section15.ATLAS_W, Section15.ATLAS_H), (0, 0, 0, 0))
      for tim in tims:
          img = tim.to_image()
          # image-pixels-per-VRAM-16bpp-pixel for this TIM's bpp:
          tim_pix_per_16bpp = {0: 4, 1: 2, 2: 1}[tim.header.bpp]
          # canvas is at 4× density of 16bpp, so stretch by:
          x_stretch = 4 // tim_pix_per_16bpp
          if x_stretch != 1:
              img = img.resize((img.width * x_stretch, img.height), Image.NEAREST)
          cx = tim.header.img_x * 4
          cy = tim.header.img_y
          atlas.alpha_composite(img, (cx, cy))
      return atlas
