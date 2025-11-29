# OllamaChat for QGIS

A QGIS plugin that integrates **Ollama AI models** with **PostgreSQL/PostGIS** databases, enabling natural language queries to generate and execute SQL commands directly within QGIS.

## Features

- 🤖 **AI-Powered SQL Generation**: Use natural language to create complex SQL queries
- 🗄️ **PostgreSQL Integration**: Connect directly to PostgreSQL/PostGIS databases
- 📊 **Schema-Aware**: Automatically includes database schema context for accurate SQL generation
- ⚡ **Execute & Visualize**: Run generated SQL queries and view results instantly
- 🎯 **Table Selection**: Choose specific tables to include in your context
- 💬 **Streaming Responses**: See AI responses in real-time

---

## Prerequisites

### 1. Install Ollama

Download and install Ollama from [ollama.ai](https://ollama.ai/)

### 2. Pull an AI Model

Open your terminal and pull a model (recommended: `llama3`, `mistral`, or `llava` for vision):

```bash
ollama pull llama3
```

Or for vision capabilities:

```bash
ollama pull llava
```

### 3. Check Python Dependencies (Optional)

The plugin requires `psycopg2` for PostgreSQL connections. **Most QGIS installations already include this**, so you likely don't need to install anything!

**How to check:**
1. Try connecting to your PostgreSQL database using the plugin
2. If you see an error about "psycopg2 is not installed", then install it:

**On Windows (OSGeo4W Shell):**
```bash
pip install psycopg2
```

**On Linux/Mac:**
```bash
pip3 install psycopg2-binary
```

After installation, restart QGIS.

---

## Installation

1. Download or clone this repository
2. Copy the `OllamaChat` folder to your QGIS plugins directory:
   - **Windows**: `C:\Users\<YourName>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Mac**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Open QGIS
4. Go to `Plugins` → `Manage and Install Plugins`
5. Enable **OllamaChat** from the Installed tab

---

## Quick Start Guide - PostgreSQL

### Step 1: Start Ollama

Make sure Ollama is running in the background. Open a terminal and run:

```bash
ollama serve
```

Keep this terminal window open while using the plugin.

### Step 2: Open the Plugin

In QGIS, the **Ollama Chat** panel should appear on the right side. If not visible:
- Go to `View` → `Panels` → Check **Ollama Chat**

### Step 3: Connect to PostgreSQL Database

1. Fill in your PostgreSQL connection details:
   - **Host**: `localhost` (or your server IP)
   - **Port**: `5432` (default PostgreSQL port)
   - **Database**: Your database name
   - **User**: Your PostgreSQL username
   - **Password**: Your PostgreSQL password

2. Click **Connect**

3. You should see: `● Connected to: [your_database]` in green

### Step 4: Configure Schema Context (Recommended)

1. Check **"Include Database Schema (for SQL queries)"**
2. Click **Fetch Tables from Database**
3. Select the tables you want to work with from the list (hold Ctrl/Cmd to select multiple)
4. This helps the AI understand your database structure

### Step 5: Choose Your AI Model

In the **Ollama Model Configuration** section, enter your model name:
- For general SQL: `llama3`, `mistral`, `codellama`
- For images: `llava`

### Step 6: Ask a Question

Type your question in natural language. Examples:

**Simple Query:**
```
Show all cities with population greater than 100000
```

**Complex Query:**
```
Create a query that finds the top 10 countries by area, 
including their name, population, and GDP
```

**Spatial Query:**
```
Find all buildings within 500 meters of main roads
```

**Create Views:**
```
Create a view called 'large_cities' that shows cities 
with population over 1 million
```

### Step 7: Execute SQL

1. Click **Send to Ollama**
2. Wait for the AI response (shown in the **Response** tab)
3. If SQL is detected, it appears in the **SQL Code** tab
4. Click **Execute SQL** to run the query on your database
5. Results will be displayed in the Response tab

---

## Usage Examples for PostgreSQL

### Example 1: Basic SELECT Query

**Prompt:**
```
Select all records from the cities table where population is above 500000
```

**Generated SQL:**
```sql
SELECT * FROM cities WHERE population > 500000;
```

### Example 2: JOIN Query

**Prompt:**
```
Show country names and their total number of cities
```

**Generated SQL:**
```sql
SELECT countries.name, COUNT(cities.id) as city_count
FROM countries
LEFT JOIN cities ON countries.id = cities.country_id
GROUP BY countries.name;
```

### Example 3: PostGIS Spatial Query

**Prompt:**
```
Find all points within 1000 meters of a specific location (lon: -122.4194, lat: 37.7749)
```

**Generated SQL:**
```sql
SELECT * FROM locations
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(-122.4194, 37.7749), 4326)::geography,
    1000
);
```

### Example 4: Create a View

**Prompt:**
```
Create a view that shows all European countries with their capital cities
```

**Generated SQL:**
```sql
CREATE VIEW european_capitals AS
SELECT c.name as country, ci.name as capital
FROM countries c
JOIN cities ci ON c.capital_id = ci.id
WHERE c.continent = 'Europe';
```

### Example 5: Aggregation Query

**Prompt:**
```
Calculate average, min, and max population by continent
```

**Generated SQL:**
```sql
SELECT 
    continent,
    AVG(population) as avg_population,
    MIN(population) as min_population,
    MAX(population) as max_population
FROM countries
GROUP BY continent
ORDER BY avg_population DESC;
```

---

## Important Notes

### Case-Sensitive Column Names

If your PostgreSQL database has column or table names with uppercase letters, the AI will automatically enclose them in double quotes:

```sql
-- Correct (auto-generated):
SELECT "CityName", "POPULATION" FROM "MyTable"

-- Wrong (will fail):
SELECT CityName, POPULATION FROM MyTable
```

### Schema Selection

- **All Tables**: If no tables are selected, the entire schema is sent to the AI
- **Specific Tables**: Select only relevant tables for faster, more focused results
- **Large Databases**: For databases with 50+ tables, select only the tables you need

### SQL Validation

The plugin performs basic SQL validation:
- Checks for incomplete statements
- Verifies minimum query length
- Warns about common errors

### Execution Safety

- Review generated SQL before executing
- The plugin supports: SELECT, INSERT, UPDATE, DELETE, CREATE VIEW, ALTER, DROP
- Database commits are automatic
- Use caution with DROP and DELETE statements

---

## Troubleshooting

### "Cannot connect to Ollama"
- Ensure Ollama is running: `ollama serve`
- Check if accessible at: http://localhost:11434
- Restart Ollama if needed

### "Model not available"
- Pull the model: `ollama pull llama3`
- Check available models: `ollama list`

### "psycopg2 is not installed"
- **This error only appears if psycopg2 is actually missing** (rare with modern QGIS installations)
- Install: `pip install psycopg2` (in OSGeo4W Shell on Windows)
- Or: `pip3 install psycopg2-binary` (Linux/Mac)
- Restart QGIS after installation

### "Connection Failed" to PostgreSQL
- Verify host, port, database name
- Check username and password
- Ensure PostgreSQL is running
- Check firewall settings
- Verify user has connection privileges

### Generated SQL has errors
- Make sure you selected relevant tables
- Try rephrasing your question more specifically
- Check that column names match your database schema
- Review the Response tab for AI explanations

### SQL execution fails with "column does not exist"
- Your database may have case-sensitive column names
- Check the exact column names in your database
- Try fetching tables again to refresh schema

---

## Tips for Best Results

1. **Be Specific**: Include table names, column names, or conditions
   - Good: "Select name and age from users where age > 25"
   - Vague: "Show me some data"

2. **Enable Schema Context**: Always check "Include Database Schema" for SQL queries

3. **Select Relevant Tables**: Don't send 100 tables when you only need 3

4. **Use Examples**: Show the AI what you want
   - "Create a query similar to SELECT * FROM cities WHERE population > X, but for countries"

5. **Iterate**: If the first query isn't perfect, ask follow-up questions
   - "Modify the previous query to also include the GDP column"

6. **Review Before Executing**: Always check the generated SQL in the SQL Code tab

---

## Advanced Features

### Copy SQL to Clipboard
Click **Copy SQL** to copy the generated query for use elsewhere.

### Multi-Query Responses
If the AI generates multiple SQL statements, they'll all appear in the SQL Code tab.

### Streaming Responses
Watch the AI generate responses in real-time in the Response tab.

### Connection Persistence
Your database connection stays active until you click **Disconnect** or close QGIS.

---

## Model Recommendations

| Model | Best For | Size | Speed |
|-------|----------|------|-------|
| `llama3` | General SQL queries | ~4GB | Fast |
| `mistral` | Complex reasoning | ~4GB | Fast |
| `codellama` | Code generation | ~4GB | Fast |
| `llava` | Image + SQL queries | ~4GB | Medium |

---

## System Requirements

- **QGIS**: 3.0 or higher
- **Python**: 3.6+
- **Ollama**: Latest version
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 5GB+ for AI models

---

## Support

For issues, questions, or feature requests:
- Check the Troubleshooting section above
- Review Ollama documentation: https://ollama.ai/
- Check PostgreSQL connection settings

---

## License

This plugin is open source. Feel free to modify and distribute.

---

## Changelog

### Version 0.1
- Initial release
- PostgreSQL/PostGIS support
- AI-powered SQL generation
- Real-time query execution
- Schema context inclusion
- Table selection feature

