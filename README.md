# CRM Bragi — Fase 1 (Buscar + ver venues)

App web sencilla para **buscar venues con Google Places** y **verlos en una lista**.
Operador único: Alejandro. Todo es local en tu computador.

> Esta es la Fase 1. Todavía NO envía correos ni busca emails: solo busca lugares,
> los guarda y te los muestra. Eso llega en fases siguientes.

---

## Qué hay aquí

| Archivo | Qué hace |
|---|---|
| `database.py` | Crea y maneja la base de datos (un archivo SQLite). Incluye respaldo. |
| `places_search.py` | El buscador: le pregunta a Google Places y guarda los venues. |
| `app.py` | La app web: la lista y la ficha de cada venue. |
| `templates/` | Las pantallas (HTML). |
| `.env.example` | Plantilla de las llaves. Copias a `.env` y pegas tu llave real. |

---

## Primera vez: preparar (se hace UNA sola vez)

### 1. Instalar los "ingredientes" de Python
En la terminal, dentro de esta carpeta:

```bash
python3 -m venv venv          # crea un entorno aislado
source venv/bin/activate      # lo activa (veras (venv) al inicio de la linea)
pip install -r requirements.txt
```

> Cada vez que abras una terminal nueva para trabajar, vuelve a correr
> `source venv/bin/activate` antes de los comandos.

### 2. Poner tu llave de Google
Copia la plantilla y edita el nuevo archivo:

```bash
cp .env.example .env
```

Abre `.env` y reemplaza `pega_aqui_tu_llave` por tu llave real de Google Places.
**El archivo `.env` nunca se sube a Git** (ya está protegido en `.gitignore`).

---

## Uso del día a día

### A) Buscar venues (lo corres tú, por tandas)
Ejemplos:

```bash
# Davikane en Texas (venue directo)
python3 places_search.py --query "salas de conciertos en Pharr, TX" \
    --artista Davikane --categoria A --ciudad Pharr --estado TX

# Dani en Florida (promotor/intermediario)
python3 places_search.py --query "promotores de eventos en Miami, FL" \
    --artista Dani --categoria B --ciudad Miami --estado FL
```

Opciones:
- `--artista` → `Dani` o `Davikane`
- `--categoria` → `A` (venue directo) o `B` (intermediario/promotor)
- `--max` → cuántos resultados traer (por defecto 20)

Si un lugar ya estaba guardado, **no se duplica**.

### B) Ver los venues en el navegador
```bash
python3 app.py
```
Abre **http://localhost:5001**. Veras la lista con filtros (ciudad, artista, categoría,
estado). Haz clic en un nombre para ver su **ficha** completa. Para parar la app: `Ctrl+C`.

---

## Cuidar tus datos (importante)

- La base de datos es **un solo archivo** (`bragi_crm.db`). Son tus datos reales.
- Para respaldarla (copiarla a la carpeta `backups/`):
  ```bash
  python3 -c "import database; database.respaldar()"
  ```
- **Nunca** se borra ni se recrea la base. Antes de cualquier cambio de estructura,
  primero se respalda.
