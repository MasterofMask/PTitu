"""
Script de verificación de instalación
"""
import sys

def test_imports():
    """Verifica que todas las librerías se importan correctamente"""
    
    print("Verificando instalación...\n")
    errors = []
    
    # Lista de librerías a verificar
    libraries = [
        ('cv2', 'OpenCV'),
        ('PIL', 'Pillow'),
        ('skimage', 'scikit-image'),
        ('torch', 'PyTorch'),
        ('torchvision', 'torchvision'),
        ('mtcnn', 'MTCNN'),
        ('facenet_pytorch', 'facenet-pytorch'),
        ('sklearn', 'scikit-learn'),
        ('numpy', 'NumPy'),
        ('scipy', 'SciPy'),
        ('exifread', 'ExifRead'),
        ('PyQt5', 'PyQt5'),
        ('tqdm', 'tqdm'),
        ('dateutil', 'python-dateutil'),
    ]
    
    # Verificar sqlite3 (incluido en Python)
    try:
        import sqlite3
        print(f"✓ SQLite3 (v{sqlite3.sqlite_version}) - Incluido en Python")
    except ImportError:
        print(f"✗ SQLite3 NO disponible")
        errors.append('sqlite3')
    
    print()
    
    for module, name in libraries:
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'instalado')
            print(f"✓ {name:20} - v{version}")
        except ImportError as e:
            print(f"✗ {name:20} - NO instalado")
            errors.append(name)
    
    print("\n" + "="*60)
    if not errors:
        print("¡Todas las librerías instaladas correctamente!")
    else:
        print(f"⚠ Errores en: {', '.join(errors)}")
    print("="*60)
    return not errors

def test_directories():
    """Verifica que la estructura de carpetas existe"""
    from pathlib import Path
    
    print("\nVerificando estructura de carpetas...\n")
    
    required_dirs = [
        'src',
        'src/core',
        'src/models',
        'src/processors',
        'src/clustering',
        'src/ui',
        'tests',
        'data',
        'data/models',
    ]
    
    errors = []
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/ - NO EXISTE")
            errors.append(dir_path)
    
    print("\n" + "="*60)
    if not errors:
        print("¡Estructura de carpetas correcta!")
    else:
        print(f"⚠ Faltan carpetas: {', '.join(errors)}")
    print("="*60)
    return not errors

def test_python_version():
    """Verifica la versión de Python"""
    import platform
    
    print("\nInformación del sistema:\n")
    print(f"Python: {sys.version}")
    print(f"Plataforma: {platform.platform()}")
    print(f"Arquitectura: {platform.machine()}")
    print("="*60)
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("   VERIFICACIÓN DE INSTALACIÓN - PTITU")
    print("="*60 + "\n")
    
    test0 = test_python_version()
    test1 = test_imports()
    test2 = test_directories()
    
    print("\n" + "="*60)
    if test1 and test2:
        print("✓ ¡Sistema listo para comenzar el desarrollo!")
        print("="*60)
        sys.exit(0)
    else:
        print("✗ Hay problemas que resolver antes de continuar")
        print("="*60)
        sys.exit(1)