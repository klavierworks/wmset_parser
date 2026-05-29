from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image  # Make sure Pillow is installed
from typing import Optional, List, Tuple
from io import BytesIO
import os
from utils.binary_reader import BinaryReader

@dataclass
class TIMHeader:
    bpp: int
    has_palette: bool
    img_size: int
    img_x: int
    img_y: int
    img_w: int
    img_h: int
    pal_size: Optional[int]
    pal_x: Optional[int]
    pal_y: Optional[int]
    pal_w: Optional[int]
    pal_h: Optional[int]
    nb_pal: Optional[int]



@dataclass
class TIM:
    name: str
    stream: BytesIO

    header: TIMHeader = field(init=False)
    image_data: bytes = field(init=False)
    palette_data: Optional[bytes] = field(init=False)
    palette_colors: Optional[List[Tuple[float, float, float, float]]] = field(init=False)  # RGBA colors


    MAGIC_NUMBER = b'\x10\x00\x00\x00'
    
    def __post_init__(self):
        success = self.parse()
        
        #self.save_png(f"{self.name}.png")

        if not success:
            raise ValueError(f"Failed to parse TIM data for {self.name}")

        if self.header.has_palette and self.palette_data is None:
            raise ValueError("Palette data is missing")
        
    def __str__(self):
        if not self.header:
            return f"Model {self.name} (unparsed)"
            
        result = [f"Model {self.name}"]
        result.append(f"  BPP: {self.header.bpp}")
        result.append(f"  Has Palette: {self.header.has_palette}")
        result.append(f"  Image: {self.header.img_w}x{self.header.img_h} at ({self.header.img_x},{self.header.img_y})")
        
        if self.header.has_palette:
            result.append(f"  Palette: {self.header.pal_w}x{self.header.pal_h} at ({self.header.pal_x},{self.header.pal_y})")
            result.append(f"  Num Palettes: {self.header.nb_pal}")
            
        return "\n".join(result)

    def parse(self) -> bool:
        """
        Parse TIM data
        Returns:
            bool: True if successful
        """        
        # Check magic number
        if self.stream.read(4) != self.MAGIC_NUMBER:
            print("Invalid TIM magic number")
            return False
        
        # Read flags byte
        flags = ord(self.stream.read(1))
        bpp = flags & 0x03
        has_palette = bool((flags >> 3) & 1)
        
        # Skip 3 bytes
        self.stream.read(3)
        
        if has_palette and bpp > 1:
            print(f"Invalid TIM flags: bpp={bpp}, has_palette={has_palette}")
            return False
            
        # Parse palette if present
        pal_size = None
        pal_x = pal_y = pal_w = pal_h = nb_pal = None
        palette_data = None
        
        if has_palette:
            pal_size = BinaryReader.read_uint32(self.stream)
            
            # Read palette header
            pal_x = BinaryReader.read_uint16(self.stream)
            pal_y = BinaryReader.read_uint16(self.stream)
            pal_w = BinaryReader.read_uint16(self.stream)
            pal_h = BinaryReader.read_uint16(self.stream)
            
            # Calculate palette entries
            one_pal_size = 16 if bpp == 0 else 256
            nb_pal = (pal_size - 12) // (one_pal_size * 2)
            if (pal_size - 12) % (one_pal_size * 2) != 0:
                nb_pal *= 2
                
            if nb_pal <= 0:
                return False
                
            # Read palette data
            palette_data = self.stream.read(pal_size - 12)
            
            # Parse palette colors with proper alpha handling
            self.palette_colors = []
            for i in range(0, len(palette_data), 2):
                if i + 1 >= len(palette_data):
                    break
                    
                word = palette_data[i] | (palette_data[i+1] << 8)

                # Extract BGR555 components
                b = ((word >> 10) & 0x1F) / 31.0
                g = ((word >>  5) & 0x1F) / 31.0
                r = ( word        & 0x1F) / 31.0
                # Paletted TIMs (object/model textures): STP bit marks transparent entries.
                # The FF8 word==0 rule applies to 16bpp direct-color images (world atlas).
                a = 0.0 if (word >> 15) else 1.0
                
                self.palette_colors.append((r, g, b, a))

        # Read image header
        img_size = BinaryReader.read_uint32(self.stream)
        img_x = BinaryReader.read_uint16(self.stream)
        img_y = BinaryReader.read_uint16(self.stream)
        img_w = BinaryReader.read_uint16(self.stream)
        img_h = BinaryReader.read_uint16(self.stream)
        
        # Adjust width based on bpp
        if bpp == 0:
            img_w *= 4
        elif bpp == 1:
            img_w *= 2
            
        # Store the header information
        self.header = TIMHeader(
            bpp=bpp,
            has_palette=has_palette,
            img_size=img_size,
            img_x=img_x,
            img_y=img_y,
            img_w=img_w,
            img_h=img_h,
            pal_size=pal_size,
            pal_x=pal_x,
            pal_y=pal_y,
            pal_w=pal_w,
            pal_h=pal_h,
            nb_pal=nb_pal
        )
        
        # Read image data
        self.image_data = self.stream.read(img_size - 12)

        if has_palette:
          self.palette_data = palette_data
        
        return True
      
      
    def to_image(self) -> Image.Image:
        """Render the TIM to an RGBA PIL Image at its native image-pixel resolution."""
        width = self.header.img_w
        height = self.header.img_h
        img = Image.new("RGBA", (width, height))
        pixels = img.load()

        bpp = self.header.bpp
        data = self.image_data

        if self.header.has_palette:
            idx = 0
            if bpp == 0:
                # 4bpp: 2 pixels per byte
                for y in range(height):
                    for x in range(0, width, 2):
                        if idx >= len(data):
                            break
                        byte = data[idx]
                        high = (byte >> 4) & 0xF
                        low = byte & 0xF
                        if x < width:
                            r, g, b, a = self.palette_colors[high]
                            pixels[x, y] = (int(r*255), int(g*255), int(b*255), int(a*255))
                        if x+1 < width:
                            r, g, b, a = self.palette_colors[low]
                            pixels[x+1, y] = (int(r*255), int(g*255), int(b*255), int(a*255))
                        idx += 1
            elif bpp == 1:
                # 8bpp: 1 pixel per byte
                for y in range(height):
                    for x in range(width):
                        if idx >= len(data):
                            break
                        color_idx = data[idx]
                        r, g, b, a = self.palette_colors[color_idx]
                        pixels[x, y] = (int(r*255), int(g*255), int(b*255), int(a*255))
                        idx += 1
        else:
            # Direct 16-bit color image (BGR555)
            idx = 0
            for y in range(height):
                for x in range(width):
                    if idx+1 >= len(data):
                        break
                    word = data[idx] | (data[idx+1] << 8)
                    b = ((word >> 10) & 0x1F) / 31.0
                    g = ((word >> 5) & 0x1F) / 31.0
                    r = (word & 0x1F) / 31.0
                    a = 0 if word == 0 else 255
                    pixels[x, y] = (int(r*255), int(g*255), int(b*255), a)
                    idx += 2
        return img

    def save_png(self, path: str):
        """Save the TIM image as a PNG."""
        img = self.to_image()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path)
        print(f"Saved TIM as PNG: {path}")
        
  
    @staticmethod
    def export_as_mtl(tim: "TIM", mtl_filename: str, png_filename: str):
        """
        Export a TIM texture as a simple MTL file for OBJ.
        :param tim: TIM instance
        :param mtl_filename: output .mtl filename
        :param png_filename: texture PNG filename referenced in the MTL
        """
        mtl_path = Path(mtl_filename)
        with open(mtl_path, "w") as f:
            f.write(f"# Material for {tim.name}\n")
            f.write(f"newmtl Textured\n")
            f.write("Ka 1.000 1.000 1.000\n")  # ambient color
            f.write("Kd 1.000 1.000 1.000\n")  # diffuse color
            f.write("Ks 0.000 0.000 0.000\n")  # specular
            f.write("d 1.0\n")                 # opacity
            f.write("illum 2\n")               # illumination model
            f.write(f"map_Kd {Path(png_filename).name}\n")  # diffuse texture
        print(f"Saved MTL file: {mtl_filename}")
        
        tim.save_png(png_filename)