"""
Procesador de metadatos EXIF de fotografías.

Este módulo extrae información EXIF de archivos de imagen incluyendo:
- Información de cámara (marca, modelo)
- Configuración de captura (ISO, apertura, tiempo de exposición)
- Datos temporales (timestamp)
- Coordenadas GPS
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import exifread
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


class MetadataProcessor:
    """
    Procesador de metadatos EXIF.
    
    Extrae y procesa metadatos embebidos en archivos de imagen
    usando tanto exifread como PIL para máxima compatibilidad.
    """
    
    def __init__(self):
        """Inicializa el procesador de metadatos"""
        self.supported_formats = ['.jpg', '.jpeg', '.tiff', '.png']
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Procesa un archivo de imagen y extrae todos sus metadatos.
        
        Args:
            file_path: Ruta al archivo de imagen
            
        Returns:
            Diccionario con metadatos extraídos
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        if file_path.suffix.lower() not in self.supported_formats:
            logger.warning(f"Formato no soportado: {file_path.suffix}")
            return {}
        
        metadata = {}
        
        try:
            # Extraer con PIL (más confiable para timestamps y GPS)
            pil_metadata = self._extract_with_pil(file_path)
            metadata.update(pil_metadata)
            
            # Complementar con exifread (más datos técnicos)
            exif_metadata = self._extract_with_exifread(file_path)
            
            # Combinar, dando prioridad a PIL
            for key, value in exif_metadata.items():
                if key not in metadata or metadata[key] is None:
                    metadata[key] = value
            
            logger.info(f"Metadatos extraídos de {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error procesando {file_path}: {e}")
        
        return metadata
    
    def _extract_with_pil(self, file_path: Path) -> Dict[str, Any]:
        """
        Extrae metadatos usando PIL/Pillow.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Diccionario con metadatos
        """
        metadata = {}
        
        try:
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                
                if exif_data is None:
                    return metadata
                
                # Procesar EXIF básico
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    if tag == 'Make':
                        metadata['camera_make'] = str(value).strip()
                    
                    elif tag == 'Model':
                        metadata['camera_model'] = str(value).strip()
                    
                    elif tag == 'DateTimeOriginal':
                        metadata['timestamp'] = self._parse_datetime(value)
                    
                    elif tag == 'FocalLength':
                        metadata['focal_length'] = self._parse_focal_length(value)
                    
                    elif tag == 'FNumber':
                        metadata['aperture'] = self._parse_fnumber(value)
                    
                    elif tag == 'ExposureTime':
                        metadata['exposure_time'] = self._parse_exposure_time(value)
                    
                    elif tag == 'ISOSpeedRatings':
                        metadata['iso'] = int(value) if value else None
                    
                    elif tag == 'Flash':
                        metadata['flash'] = int(value) if value else None
                    
                    elif tag == 'GPSInfo':
                        gps_data = self._parse_gps(value)
                        metadata.update(gps_data)
        
        except Exception as e:
            logger.debug(f"Error extrayendo con PIL: {e}")
        
        return metadata
    
    def _extract_with_exifread(self, file_path: Path) -> Dict[str, Any]:
        """
        Extrae metadatos usando exifread.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Diccionario con metadatos
        """
        metadata = {}
        
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                
                if not tags:
                    return metadata
                
                # Información de cámara
                if 'Image Make' in tags:
                    metadata['camera_make'] = str(tags['Image Make']).strip()
                
                if 'Image Model' in tags:
                    metadata['camera_model'] = str(tags['Image Model']).strip()
                
                # Timestamp
                if 'EXIF DateTimeOriginal' in tags:
                    metadata['timestamp'] = self._parse_datetime(
                        str(tags['EXIF DateTimeOriginal'])
                    )
                elif 'Image DateTime' in tags:
                    metadata['timestamp'] = self._parse_datetime(
                        str(tags['Image DateTime'])
                    )
                
                # Configuración de captura
                if 'EXIF FocalLength' in tags:
                    metadata['focal_length'] = self._parse_focal_length(
                        str(tags['EXIF FocalLength'])
                    )
                
                if 'EXIF FNumber' in tags:
                    metadata['aperture'] = self._parse_fnumber(
                        str(tags['EXIF FNumber'])
                    )
                
                if 'EXIF ExposureTime' in tags:
                    metadata['exposure_time'] = str(tags['EXIF ExposureTime'])
                
                if 'EXIF ISOSpeedRatings' in tags:
                    try:
                        metadata['iso'] = int(str(tags['EXIF ISOSpeedRatings']))
                    except ValueError:
                        pass
                
                if 'EXIF Flash' in tags:
                    try:
                        metadata['flash'] = int(str(tags['EXIF Flash']))
                    except ValueError:
                        pass
                
                # GPS
                gps_data = self._extract_gps_exifread(tags)
                metadata.update(gps_data)
        
        except Exception as e:
            logger.debug(f"Error extrayendo con exifread: {e}")
        
        return metadata
    
    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """
        Convierte string de fecha EXIF a objeto datetime.
        
        Formato EXIF: "YYYY:MM:DD HH:MM:SS"
        
        Args:
            dt_string: String con fecha/hora
            
        Returns:
            Objeto datetime o None
        """
        if not dt_string:
            return None
        
        try:
            # Formato estándar EXIF
            return datetime.strptime(
                str(dt_string).strip(),
                "%Y:%m:%d %H:%M:%S"
            )
        except ValueError:
            try:
                # Formato alternativo con guiones
                return datetime.strptime(
                    str(dt_string).strip(),
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                logger.warning(f"No se pudo parsear fecha: {dt_string}")
                return None
    
    def _parse_focal_length(self, focal_str) -> Optional[float]:
        """
        Convierte focal length a float.
        
        Args:
            focal_str: String o tupla con focal length
            
        Returns:
            Focal length en mm
        """
        try:
            if isinstance(focal_str, tuple) and len(focal_str) == 2:
                # Formato: (numerador, denominador)
                return float(focal_str[0]) / float(focal_str[1])
            elif isinstance(focal_str, str):
                # Formato: "50" o "50/1"
                if '/' in focal_str:
                    num, den = focal_str.split('/')
                    return float(num) / float(den)
                return float(focal_str)
            else:
                return float(focal_str)
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    
    def _parse_fnumber(self, fn_str) -> Optional[float]:
        """
        Convierte f-number a float.
        
        Args:
            fn_str: String o tupla con f-number
            
        Returns:
            F-number (apertura)
        """
        try:
            if isinstance(fn_str, tuple) and len(fn_str) == 2:
                return float(fn_str[0]) / float(fn_str[1])
            elif isinstance(fn_str, str):
                if '/' in fn_str:
                    num, den = fn_str.split('/')
                    return float(num) / float(den)
                return float(fn_str)
            else:
                return float(fn_str)
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    
    def _parse_exposure_time(self, exp_str) -> Optional[str]:
        """
        Formatea el tiempo de exposición.
        
        Args:
            exp_str: String o tupla con tiempo de exposición
            
        Returns:
            String formateado (ej: "1/500")
        """
        try:
            if isinstance(exp_str, tuple) and len(exp_str) == 2:
                num, den = exp_str
                if num == 1:
                    return f"1/{den}"
                return f"{num}/{den}"
            return str(exp_str)
        except (ValueError, TypeError):
            return None
    
    def _parse_gps(self, gps_info: dict) -> Dict[str, Optional[float]]:
        """
        Extrae coordenadas GPS de PIL GPSInfo.
        
        Args:
            gps_info: Diccionario con información GPS
            
        Returns:
            Diccionario con lat, lon, alt
        """
        result = {
            'gps_latitude': None,
            'gps_longitude': None,
            'gps_altitude': None
        }
        
        try:
            # Latitud
            if 1 in gps_info and 2 in gps_info:
                lat = self._convert_to_degrees(gps_info[2])
                if gps_info[1] == 'S':
                    lat = -lat
                result['gps_latitude'] = lat
            
            # Longitud
            if 3 in gps_info and 4 in gps_info:
                lon = self._convert_to_degrees(gps_info[4])
                if gps_info[3] == 'W':
                    lon = -lon
                result['gps_longitude'] = lon
            
            # Altitud
            if 6 in gps_info:
                alt = gps_info[6]
                if isinstance(alt, tuple) and len(alt) == 2:
                    result['gps_altitude'] = float(alt[0]) / float(alt[1])
                else:
                    result['gps_altitude'] = float(alt)
        
        except Exception as e:
            logger.debug(f"Error parseando GPS: {e}")
        
        return result
    
    def _extract_gps_exifread(self, tags: dict) -> Dict[str, Optional[float]]:
        """
        Extrae GPS usando tags de exifread.
        
        Args:
            tags: Diccionario de tags EXIF
            
        Returns:
            Diccionario con coordenadas GPS
        """
        result = {
            'gps_latitude': None,
            'gps_longitude': None,
            'gps_altitude': None
        }
        
        try:
            # Latitud
            if 'GPS GPSLatitude' in tags and 'GPS GPSLatitudeRef' in tags:
                lat = self._convert_to_degrees_exifread(
                    tags['GPS GPSLatitude'].values
                )
                if str(tags['GPS GPSLatitudeRef']) == 'S':
                    lat = -lat
                result['gps_latitude'] = lat
            
            # Longitud
            if 'GPS GPSLongitude' in tags and 'GPS GPSLongitudeRef' in tags:
                lon = self._convert_to_degrees_exifread(
                    tags['GPS GPSLongitude'].values
                )
                if str(tags['GPS GPSLongitudeRef']) == 'W':
                    lon = -lon
                result['gps_longitude'] = lon
            
            # Altitud
            if 'GPS GPSAltitude' in tags:
                alt = tags['GPS GPSAltitude'].values[0]
                result['gps_altitude'] = float(alt.num) / float(alt.den)
        
        except Exception as e:
            logger.debug(f"Error extrayendo GPS con exifread: {e}")
        
        return result
    
    def _convert_to_degrees(self, value) -> float:
        """
        Convierte coordenadas GPS a grados decimales (PIL format).
        
        Args:
            value: Tupla con (grados, minutos, segundos)
            
        Returns:
            Coordenada en grados decimales
        """
        d, m, s = value
        
        # Convertir tuplas a float
        if isinstance(d, tuple):
            d = float(d[0]) / float(d[1])
        if isinstance(m, tuple):
            m = float(m[0]) / float(m[1])
        if isinstance(s, tuple):
            s = float(s[0]) / float(s[1])
        
        return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)
    
    def _convert_to_degrees_exifread(self, values) -> float:
        """
        Convierte coordenadas GPS a grados decimales (exifread format).
        
        Args:
            values: Lista con [grados, minutos, segundos]
            
        Returns:
            Coordenada en grados decimales
        """
        d = float(values[0].num) / float(values[0].den)
        m = float(values[1].num) / float(values[1].den)
        s = float(values[2].num) / float(values[2].den)
        
        return d + (m / 60.0) + (s / 3600.0)