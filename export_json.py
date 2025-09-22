import subprocess
import json
import os
import re

# -------------------------
# CONFIGURACIÓN
# -------------------------
fecha = "01.10.1959"       # dd.mm.yyyy
hora = "11.45"             # decimal
geopos = "2.16992,41.3879,0"
swetest_exe = "swetest64.exe"

# -------------------------
# FUNCIÓN PARA VERIFICAR SWETEST
# -------------------------
def verificar_swetest():
    """Muestra las opciones disponibles de swetest"""
    try:
        print("🔍 Verificando opciones de swetest...")
        resultado = subprocess.check_output([swetest_exe, "-h"], text=True, stderr=subprocess.STDOUT, timeout=10)
        print("📋 Opciones disponibles:")
        print("-" * 50)
        print(resultado[:500])  # Mostrar solo los primeros 500 caracteres
        print("-" * 50)
        return True
    except Exception as e:
        print(f"⚠️  No se pudo obtener ayuda de swetest: {e}")
        return False

# -------------------------
# VALIDACIONES PREVIAS
# -------------------------
def validar_configuracion():
    """Valida que el ejecutable existe y los parámetros son correctos"""
    if not os.path.exists(swetest_exe):
        raise FileNotFoundError(f"No se encuentra el ejecutable: {swetest_exe}")
    
    # Validar formato de fecha
    if not re.match(r'\d{2}\.\d{2}\.\d{4}', fecha):
        raise ValueError(f"Formato de fecha incorrecto: {fecha}. Use dd.mm.yyyy")
    
    # Validar formato de hora
    try:
        float(hora)
    except ValueError:
        raise ValueError(f"Formato de hora incorrecto: {hora}. Use formato decimal")

# -------------------------
# PARSEO MEJORADO
# -------------------------
def parsear_salida_swetest(salida):
    """Parsea la salida de swetest de forma más robusta"""
    data = {
        "planets": {},
        "houses": {},
        "points": {},  # Para nodos, apogeos, etc.
        "angles": {}   # Para ángulos como Ascendente, MC, etc.
    }
    
    lineas = salida.strip().splitlines()
    
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("warning:") or linea.startswith("using"):
            continue
            
        # Buscar patrón: texto seguido de número (CORREGIDO)
        match = re.match(r'^(.+?)\s+(-?\d+\.?\d*)$', linea)
        
        if match:
            nombre_completo = match.group(1).strip()
            try:
                valor = float(match.group(2))
                
                # Clasificar el tipo de objeto
                nombre_lower = nombre_completo.lower()
                
                # Detectar casas por número
                if re.match(r'^\d+$', nombre_completo):
                    # Es una casa numerada (1, 2, 3, etc.)
                    data["houses"][f"house{nombre_completo}"] = valor
                    
                elif nombre_lower.startswith("house"):
                    # Casas astrológicas con prefijo "house"
                    data["houses"][nombre_completo] = valor
                    
                elif any(keyword in nombre_lower for keyword in ["node", "apogee", "perigee"]):
                    # Puntos especiales (nodos, apogeos, etc.)
                    data["points"][nombre_completo] = valor
                    
                elif any(keyword in nombre_lower for keyword in ["asc", "mc", "armc", "vertex", "equat", "polar"]):
                    # Ángulos astrológicos
                    data["angles"][nombre_completo] = valor
                    
                else:
                    # Planetas tradicionales
                    data["planets"][nombre_completo] = valor
                    
            except ValueError:
                print(f"⚠️  No se pudo convertir: {linea}")
                continue
        else:
            # Si no coincide el patrón, intentar parseo simple
            partes = re.split(r'\s+', linea)
            if len(partes) >= 2:
                try:
                    valor = float(partes[-1])  # Último elemento como valor
                    nombre = " ".join(partes[:-1])  # Todo lo anterior como nombre
                    data["planets"][nombre] = valor
                except ValueError:
                    print(f"⚠️  Línea no reconocida: {linea}")
    
    return data

# -------------------------
# PRUEBAS DIFERENTES DE COMANDOS
# -------------------------
def probar_comandos():
    """Prueba diferentes variaciones del comando swetest"""
    
    comandos_a_probar = [
        # Opción 1: Planetas + Casas completas
        {
            "nombre": "Planetas + Casas completas",
            "comando": [
                swetest_exe,
                f"-b{fecha}",
                f"-ut{hora}",
                f"-geopos{geopos}",
                f"-housep{geopos}",
                "-house12",  # Sistema de casas Placidus
                "-fPl",
                "-head"
            ]
        },
        # Opción 2: Con sistema de casas Koch
        {
            "nombre": "Planetas + Casas Koch",
            "comando": [
                swetest_exe,
                f"-b{fecha}",
                f"-ut{hora}",
                f"-geopos{geopos}",
                f"-housek{geopos}",  # Sistema Koch
                "-fPl",
                "-head"
            ]
        },
        # Opción 3: Original que funcionaba
        {
            "nombre": "Solo planetas (original)",
            "comando": [
                swetest_exe,
                f"-b{fecha}",
                f"-ut{hora}",
                f"-geopos{geopos}",
                f"-housep{geopos}",
                "-fPl",
                "-head"
            ]
        },
        # Opción 4: Formato diferente para casas
        {
            "nombre": "Casas formato alternativo",
            "comando": [
                swetest_exe,
                f"-b{fecha}",
                f"-ut{hora}",
                f"-geopos{geopos}",
                f"-housep{geopos}",
                "-fPls",  # Formato con casas
                "-head"
            ]
        }
    ]
    
    for i, test in enumerate(comandos_a_probar, 1):
        print(f"\n🧪 Prueba {i}: {test['nombre']}")
        print(f"🔧 Comando: {' '.join(test['comando'])}")
        
        try:
            resultado = subprocess.check_output(
                test['comando'], 
                text=True, 
                stderr=subprocess.STDOUT,
                timeout=15
            )
            
            print("✅ ¡Éxito! Salida obtenida:")
            print("-" * 30)
            print(resultado[:500])  # Mostrar primeros 500 caracteres
            print("-" * 30)
            
            # Si llegamos aquí, este comando funcionó
            return test['comando'], resultado
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error (código {e.returncode}): {e.output}")
        except subprocess.TimeoutExpired:
            print("❌ Timeout - comando tardó demasiado")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    return None, None

# -------------------------
# EJECUCIÓN PRINCIPAL
# -------------------------
def main():
    try:
        # Validar configuración básica
        validar_configuracion()
        print("✅ Configuración básica validada")
        
        # Verificar qué opciones acepta swetest
        verificar_swetest()
        
        # Probar diferentes comandos
        print("\n" + "="*60)
        print("🚀 PROBANDO DIFERENTES COMANDOS")
        print("="*60)
        
        comando_exitoso, salida_exitosa = probar_comandos()
        
        if comando_exitoso and salida_exitosa:
            print("\n🎉 ¡Comando exitoso encontrado!")
            print(f"✨ Comando final: {' '.join(comando_exitoso)}")
            
            # Parsear y guardar datos
            data = parsear_salida_swetest(salida_exitosa)
            
            if not data["planets"] and not data["houses"] and not data["points"] and not data["angles"]:
                print("⚠️  Advertencia: No se pudieron extraer datos válidos")
                print("📋 Salida completa para análisis:")
                print(salida_exitosa)
            else:
                # Guardar JSON
                with open("carta.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                print("✅ JSON generado correctamente: carta.json")
                print(f"📊 Planetas encontrados: {len(data['planets'])}")
                print(f"🏠 Casas encontradas: {len(data['houses'])}")
                print(f"📍 Puntos especiales: {len(data['points'])}")
                print(f"📐 Ángulos encontrados: {len(data['angles'])}")
                
                # Mostrar muestra de los datos
                if data["planets"]:
                    print("\n🌟 Planetas:")
                    for planeta, grado in data["planets"].items():
                        print(f"  {planeta}: {grado}°")
                
                if data["points"]:
                    print("\n📍 Puntos especiales:")
                    for punto, grado in data["points"].items():
                        print(f"  {punto}: {grado}°")
                
                if data["angles"]:
                    print("\n📐 Ángulos:")
                    for angulo, grado in data["angles"].items():
                        print(f"  {angulo}: {grado}°")
                
                if data["houses"]:
                    print("\n🏠 Casas:")
                    for casa, grado in sorted(data["houses"].items()):
                        print(f"  {casa}: {grado}°")
        else:
            print("\n❌ Ningún comando funcionó.")
            print("💡 Sugerencias:")
            print("   1. Verifica que swetest64.exe esté en el directorio actual")
            print("   2. Verifica que tengas los archivos de efemérides")
            print("   3. Prueba ejecutar manualmente: swetest64.exe -h")
                
    except Exception as e:
        print(f"⚠️  Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()