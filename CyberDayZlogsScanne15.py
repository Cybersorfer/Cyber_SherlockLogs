import ftplib
import re
import sqlite3
import collections

# --- CONFIGURACIÓN CON TUS DATOS ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
# Nota: Si este camino falla, verifica en FileZilla si tu carpeta raíz es exactamente esta
LOG_REMOTE_PATH = "/dayzps/config/" 
CANTIDAD_LOGS = 100  # Cubre aproximadamente 1 semana de actividad (8 reinicios/día)

# --- 1. PREPARACIÓN DE LA BASE DE DATOS (SQLite) ---
def iniciar_db():
    conn = sqlite3.connect('dayz_logs_maestro.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo TEXT,
            evento TEXT,
            x REAL,
            z REAL,
            UNIQUE(archivo, evento, x, z) 
        )
    ''')
    conn.commit()
    return conn

# --- 2. DESCARGA Y PROCESAMIENTO ---
def procesar_servidor(conn):
    cursor = conn.cursor()
    try:
        print(f"Conectando a {FTP_HOST}...")
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(LOG_REMOTE_PATH)
        
        # Listar archivos y tomar los últimos 100
        files = [f for f in ftp.nlst() if f.endswith(".ADM")]
        files.sort()
        objetivos = files[-CANTIDAD_LOGS:] 

        # Patron para coordenadas: pos=<X, Y, Z>
        pattern = re.compile(r'pos=<(\d+\.\d+), \d+\.\d+, (\d+\.\d+)>')

        print(f"Iniciando descarga de {len(objetivos)} archivos...")
        for file_name in objetivos:
            lineas_temp = []
            try:
                ftp.retrbinary(f"RETR {file_name}", lambda data: lineas_temp.append(data.decode('latin-1', errors='ignore')))
                contenido = "".join(lineas_temp)

                for line in contenido.split('\n'):
                    # Filtramos eventos críticos para encontrar vehículos y bases
                    if any(key in line for key in ["Transport", "hit", "Placement", "built"]):
                        match = pattern.search(line)
                        if match:
                            x, z = match.groups()
                            evento_limpio = line.strip()[:150] # Guardamos los primeros 150 caracteres del evento
                            
                            cursor.execute('''
                                INSERT OR IGNORE INTO registros (archivo, evento, x, z)
                                VALUES (?, ?, ?, ?)
                            ''', (file_name, evento_limpio, float(x), float(z)))
            except Exception as e:
                print(f"Saltando archivo {file_name} por error: {e}")
                continue
        
        conn.commit()
        ftp.quit()
        print("Sincronización con Nitrado completada.")
    except Exception as e:
        print(f"Error de conexión: {e}")

# --- 3. EXPORTACIÓN PARA ISURVIVE ---
def generar_reporte_isurvive(conn):
    cursor = conn.cursor()
    # Esta consulta busca coordenadas donde hubo actividad en MÁS DE UN REINICIO
    # Esto filtra a la gente que solo iba pasando y te deja las bases/coches parqueados
    cursor.execute('''
        SELECT x, z, COUNT(DISTINCT archivo) as reinicios, MAX(archivo) as ultimo_visto
        FROM registros 
        GROUP BY x, z 
        HAVING reinicios > 1
        ORDER BY reinicios DESC
    ''')
    
    resultados = cursor.fetchall()
    with open("COORDINADAS_PARA_ISURVIVE.txt", "w") as f:
        f.write("REPORTE DE PUNTOS CALIENTES - DAYZ PS4\n")
        f.write("Copia las coordenadas (X, Z) en iSurvive para ver la ubicación\n")
        f.write("============================================================\n\n")
        for x, z, veces, ultimo in resultados:
            f.write(f"COORD: {x}, {z} | Visto en {veces} reinicios distintos | Último: {ultimo}\n")
    
    print(f"Reporte generado: COORDINADAS_PARA_ISURVIVE.txt ({len(resultados)} puntos sospechosos)")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    db_conn = iniciar_db()
    procesar_servidor(db_conn)
    generar_reporte_isurvive(db_conn)
    db_conn.close()
    print("\nProceso finalizado con éxito.")
