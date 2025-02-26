from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2.extras
import psycopg2

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="1",
        user="postgres",
        password="12345"
    )
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"Conexión exitosa. Versión de PostgreSQL: {db_version[0]}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error al conectar: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        edad = request.form['edad']
        ciudad_origen = request.form['ciudad_origen']
        estado = request.form['estado']
        fecha_contrato = request.form['fecha_contrato']

        if not nombre or not edad or not ciudad_origen or not estado or not fecha_contrato:
            error = "Todos los campos son obligatorios."
            return render_template('registro.html', error=error)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM chicas_magicas WHERE nombre = %s', (nombre,))
            if cursor.fetchone():
                error = "Esta chica mágica ya está registrada."
                cursor.close()
                conn.close()
                return render_template('registro.html', error=error)

            cursor.execute('INSERT INTO chicas_magicas (nombre, edad, ciudad_origen) VALUES (%s, %s, %s) RETURNING id',
                           (nombre, edad, ciudad_origen))
            chica_id = cursor.fetchone()[0]


            cursor.execute('INSERT INTO contrato (chica_id, estado, fecha_contrato) VALUES (%s, %s, %s)',
                           (chica_id, estado, fecha_contrato))

            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for('registro'))

        except Exception as e:
            error = f"Error al registrar: {e}"
            return render_template('registro.html', error=error)

    return render_template('registro.html')

@app.route('/busqueda')
def busqueda():
    estado = request.args.get('estado')
    chicas = get_chicas_filtradas(estado)  
    return render_template('busqueda.html', chicas=chicas)

def get_chicas_filtradas(estado=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if estado:
        query = """
            SELECT cm.id, cm.nombre, cm.edad, cm.ciudad_origen
            FROM chicas_magicas cm
            LEFT JOIN contrato c ON cm.id = c.chica_id
            WHERE c.estado = %s
        """
        cursor.execute(query, (estado,))
    else:
        query = """
            SELECT cm.id, cm.nombre, cm.edad, cm.ciudad_origen
            FROM chicas_magicas cm
            LEFT JOIN contrato c ON cm.id = c.chica_id
        """
        cursor.execute(query)

    chicas = cursor.fetchall()
    chicas_list = [{'id': c[0], 'nombre': c[1], 'edad': c[2], 'ciudad_origen': c[3]} for c in chicas]

    cursor.close()
    conn.close()
    return chicas_list

@app.route('/infochica/<int:chica_id>')
def infochica(chica_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cm.id, cm.nombre, cm.edad, cm.ciudad_origen, c.estado, c.fecha_contrato 
            FROM chicas_magicas cm 
            LEFT JOIN contrato c ON cm.id = c.chica_id
            WHERE cm.id = %s
        """, (chica_id,))
        result = cursor.fetchone()
        if result is None:
            return "Chica no encontrada", 404

        chica = {
            'id': result[0],
            'nombre': result[1],
            'edad': result[2],
            'ciudad_origen': result[3],
            'estado': result[4],
            'fecha_contrato': result[5]
        }
    except Exception as e:
        return f"Error al obtener la información: {e}", 500
    finally:
        cursor.close()
        conn.close()

    return render_template('infochica.html', chica=chica)

@app.route('/actualizar_estado/<int:chica_id>', methods=['POST'])
def actualizar_estado(chica_id):
    nuevo_estado = request.form.get("nuevo_estado")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT estado FROM contrato WHERE chica_id = %s", (chica_id,))
    estado_actual = cursor.fetchone()

    cursor.execute("UPDATE contrato SET estado = %s WHERE chica_id = %s", (nuevo_estado, chica_id))
    cursor.execute("INSERT INTO historial_cambios (chica_id, estado_anterior, estado_nuevo) VALUES (%s, %s, %s)", 
                   (chica_id, estado_actual[0], nuevo_estado))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('infochica', chica_id=chica_id))

@app.route('/eliminar_chica/<int:chica_id>', methods=['POST'])
def eliminar_chica(chica_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        
        cursor.execute("DELETE FROM contrato WHERE chica_id = %s", (chica_id,))
        cursor.execute("DELETE FROM chicas_magicas WHERE id = %s", (chica_id,))
        
        conn.commit()
        flash('Chica mágica eliminada exitosamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al eliminar: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    
    return redirect(url_for('busqueda'))

if __name__ == "_main_":
    app.run(debug=True)
