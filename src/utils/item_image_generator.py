"""
Générateur d'images d'items pour les embeds Discord
"""
import aiohttp
import asyncio
from PIL import Image, ImageDraw
import io
import structlog
from typing import List, Optional

logger = structlog.get_logger()

class ItemImageGenerator:
    """Générateur d'images composites pour les items"""
    
    def __init__(self):
        self.item_size = 64  # Taille de chaque item en pixels
        self.item_spacing = 4  # Espacement entre les items
    
    async def create_items_image(self, item_ids: List[int]) -> Optional[io.BytesIO]:
        """
        Créer une image composite avec tous les items
        Retourne un BytesIO contenant l'image pour upload Discord
        """
        try:
            # Filtrer les items valides (non-zéro)
            valid_items = [item_id for item_id in item_ids if item_id > 0]
            
            if not valid_items:
                return None
            
            # Télécharger les images des items
            item_images = await self._download_item_images(valid_items)
            
            if not item_images:
                return None
            
            # Créer l'image composite
            composite_image = self._create_composite_image(item_images)
            
            # Convertir en BytesIO pour Discord
            return self._image_to_bytes(composite_image)
            
        except Exception as e:
            logger.error(f"Erreur création image items: {e}")
            return None
    
    async def _download_item_images(self, item_ids: List[int]) -> List[Image.Image]:
        """Télécharger les images des items depuis l'API Riot"""
        images = []
        
        async with aiohttp.ClientSession() as session:
            for item_id in item_ids:
                try:
                    url = f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/item/{item_id}.png"
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            image = Image.open(io.BytesIO(image_data))
                            # Redimensionner à la taille voulue
                            image = image.resize((self.item_size, self.item_size), Image.Resampling.LANCZOS)
                            images.append(image)
                        else:
                            # Image placeholder si l'item n'existe pas
                            placeholder = self._create_placeholder_image()
                            images.append(placeholder)
                            
                except Exception as e:
                    logger.warning(f"Erreur téléchargement item {item_id}: {e}")
                    placeholder = self._create_placeholder_image()
                    images.append(placeholder)
        
        return images
    
    def _create_composite_image(self, item_images: List[Image.Image]) -> Image.Image:
        """Créer une image composite avec tous les items en ligne"""
        if not item_images:
            return self._create_placeholder_image()
        
        # Calculer les dimensions de l'image finale
        total_width = len(item_images) * self.item_size + (len(item_images) - 1) * self.item_spacing
        total_height = self.item_size
        
        # Créer l'image de base (transparente)
        composite = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))
        
        # Coller chaque item
        x_offset = 0
        for item_image in item_images:
            composite.paste(item_image, (x_offset, 0))
            x_offset += self.item_size + self.item_spacing
        
        return composite
    
    def _create_placeholder_image(self) -> Image.Image:
        """Créer une image placeholder pour les items manquants"""
        placeholder = Image.new('RGBA', (self.item_size, self.item_size), (50, 50, 50, 255))
        draw = ImageDraw.Draw(placeholder)
        
        # Dessiner un "?" au centre
        text = "?"
        # Note: Pour un vrai placeholder, il faudrait une police
        # draw.text((self.item_size//2, self.item_size//2), text, fill=(255, 255, 255), anchor="mm")
        
        return placeholder
    
    def _image_to_bytes(self, image: Image.Image) -> io.BytesIO:
        """Convertir une image PIL en BytesIO pour Discord"""
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
