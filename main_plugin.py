from qgis.PyQt.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QTextEdit,
                                 QPushButton, QFileDialog, QLabel, QMessageBox, 
                                 QCheckBox, QComboBox, QHBoxLayout, QListWidget,
                                 QTabWidget, QPlainTextEdit, QListWidgetItem, 
                                 QApplication, QLineEdit, QGroupBox, QGridLayout)
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsDataSourceUri, QgsVectorLayerExporter
import requests
import base64
import os
import json
import re
import sqlite3

class OllamaChat:
    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        self.image_data = None
        self.include_db_schema = False
        self.extracted_sql = None
        self.selected_tables = []
        self.available_tables = []
        
        # PostgreSQL connection
        self.db_connection = None
        self.db_host = ""
        self.db_port = "5432"
        self.db_name = ""
        self.db_user = ""
        self.db_password = ""
        
        # Ollama model name
        self.ollama_model = "llava"

    def initGui(self):
        """Initialize the GUI when the plugin is loaded"""
        self.dock_widget = QDockWidget("Ollama Chat")
        self.dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        self.dock_widget.setWidget(widget)

        # PostgreSQL Connection Group
        db_group = QGroupBox("PostgreSQL Database Connection")
        db_layout = QGridLayout()
        db_group.setLayout(db_layout)
        
        # Connection fields
        db_layout.addWidget(QLabel("Host:"), 0, 0)
        self.db_host_edit = QLineEdit()
        self.db_host_edit.setPlaceholderText("localhost")
        self.db_host_edit.setText("localhost")
        db_layout.addWidget(self.db_host_edit, 0, 1)
        
        db_layout.addWidget(QLabel("Port:"), 0, 2)
        self.db_port_edit = QLineEdit()
        self.db_port_edit.setPlaceholderText("5432")
        self.db_port_edit.setText("5432")
        self.db_port_edit.setMaximumWidth(60)
        db_layout.addWidget(self.db_port_edit, 0, 3)
        
        db_layout.addWidget(QLabel("Database:"), 1, 0)
        self.db_name_edit = QLineEdit()
        self.db_name_edit.setPlaceholderText("database_name")
        db_layout.addWidget(self.db_name_edit, 1, 1, 1, 3)
        
        db_layout.addWidget(QLabel("User:"), 2, 0)
        self.db_user_edit = QLineEdit()
        self.db_user_edit.setPlaceholderText("postgres")
        db_layout.addWidget(self.db_user_edit, 2, 1)
        
        db_layout.addWidget(QLabel("Password:"), 2, 2)
        self.db_password_edit = QLineEdit()
        self.db_password_edit.setEchoMode(QLineEdit.Password)
        self.db_password_edit.setPlaceholderText("password")
        db_layout.addWidget(self.db_password_edit, 2, 3)
        
        # Connect/Disconnect buttons
        db_btn_layout = QHBoxLayout()
        self.connect_db_btn = QPushButton("Connect")
        self.connect_db_btn.clicked.connect(self.connect_to_database)
        db_btn_layout.addWidget(self.connect_db_btn)
        
        self.disconnect_db_btn = QPushButton("Disconnect")
        self.disconnect_db_btn.clicked.connect(self.disconnect_from_database)
        self.disconnect_db_btn.setEnabled(False)
        db_btn_layout.addWidget(self.disconnect_db_btn)
        
        self.db_status_label = QLabel("● Not connected")
        self.db_status_label.setStyleSheet("color: red;")
        db_btn_layout.addWidget(self.db_status_label)
        db_btn_layout.addStretch()
        
        db_layout.addLayout(db_btn_layout, 3, 0, 1, 4)
        
        layout.addWidget(db_group)

        # Ollama Model Selection Group
        model_group = QGroupBox("Ollama Model Configuration")
        model_layout = QHBoxLayout()
        model_group.setLayout(model_layout)
        
        model_layout.addWidget(QLabel("Model Name:"))
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("e.g., llava, llama2, mistral")
        self.model_name_edit.setText("llava")
        model_layout.addWidget(self.model_name_edit)
        
        layout.addWidget(model_group)

        # Prompt input
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Enter your prompt here (e.g., 'Generate SQL to find all cities with population > 100000')...")
        layout.addWidget(self.prompt_edit)

        # Database schema checkbox
        self.db_schema_checkbox = QCheckBox("Include Database Schema (for SQL queries)")
        self.db_schema_checkbox.setChecked(False)
        self.db_schema_checkbox.stateChanged.connect(self.toggle_db_schema)
        layout.addWidget(self.db_schema_checkbox)
        
        # Table selection for schema (multi-select list)
        table_label = QLabel("Select Tables (click a table to select it)")
        table_label.setEnabled(False)
        self.table_label = table_label
        layout.addWidget(table_label)
        
        self.table_list = QListWidget()
        self.table_list.setSelectionMode(QListWidget.MultiSelection)
        self.table_list.setEnabled(False)
        self.table_list.setMaximumHeight(100)
        self.table_list.itemSelectionChanged.connect(self.on_table_selection_changed)
        layout.addWidget(self.table_list)
        
        # Button to refresh tables
        self.refresh_tables_btn = QPushButton("Fetch Tables from Database")
        self.refresh_tables_btn.clicked.connect(self.fetch_tables)
        self.refresh_tables_btn.setEnabled(False)
        layout.addWidget(self.refresh_tables_btn)

        # Attach image
        self.image_label = QLabel("No image attached")
        layout.addWidget(self.image_label)

        self.attach_btn = QPushButton("Attach Image")
        self.attach_btn.clicked.connect(self.attach_image)
        layout.addWidget(self.attach_btn)

        # Send button
        self.send_btn = QPushButton("Send to Ollama")
        self.send_btn.clicked.connect(self.send_to_ollama)
        layout.addWidget(self.send_btn)

        # Tabbed output
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Response tab
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.tab_widget.addTab(self.output_edit, "Response")
        
        # SQL tab
        sql_tab = QWidget()
        sql_layout = QVBoxLayout()
        sql_tab.setLayout(sql_layout)
        
        self.sql_edit = QPlainTextEdit()
        self.sql_edit.setReadOnly(True)
        self.sql_edit.setPlaceholderText("SQL code will appear here when detected in response...")
        sql_layout.addWidget(self.sql_edit)
        
        # SQL execution buttons
        sql_btn_layout = QHBoxLayout()
        self.execute_sql_btn = QPushButton("Execute SQL")
        self.execute_sql_btn.clicked.connect(self.execute_sql)
        self.execute_sql_btn.setEnabled(False)
        sql_btn_layout.addWidget(self.execute_sql_btn)
        
        self.copy_sql_btn = QPushButton("Copy SQL")
        self.copy_sql_btn.clicked.connect(self.copy_sql)
        self.copy_sql_btn.setEnabled(False)
        sql_btn_layout.addWidget(self.copy_sql_btn)
        
        sql_layout.addLayout(sql_btn_layout)
        self.tab_widget.addTab(sql_tab, "SQL Code")

        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)

    def unload(self):
        """Remove the plugin and clean up"""
        # Disconnect from database if connected
        if self.db_connection:
            self.disconnect_from_database()
        
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def connect_to_database(self):
        """Connect to PostgreSQL database"""
        try:
            import psycopg2
        except ImportError:
            QMessageBox.critical(
                None,
                "Missing Dependency",
                "psycopg2 is not installed.\n\n"
                "To install it:\n"
                "1. Open OSGeo4W Shell (or your Python environment)\n"
                "2. Run: pip install psycopg2\n"
                "3. Restart QGIS"
            )
            return
        
        # Get connection parameters
        host = self.db_host_edit.text().strip() or "localhost"
        port = self.db_port_edit.text().strip() or "5432"
        database = self.db_name_edit.text().strip()
        user = self.db_user_edit.text().strip()
        password = self.db_password_edit.text()
        
        # Validate inputs
        if not database or not user:
            QMessageBox.warning(
                None,
                "Missing Information",
                "Please enter at least Database name and User."
            )
            return
        
        # Try to connect
        try:
            self.iface.messageBar().pushMessage(
                "Ollama Chat",
                f"Connecting to database '{database}'...",
                level=Qgis.Info,
                duration=2
            )
            
            self.db_connection = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            
            # Save connection parameters
            self.db_host = host
            self.db_port = port
            self.db_name = database
            self.db_user = user
            self.db_password = password
            
            # Update UI
            self.connect_db_btn.setEnabled(False)
            self.disconnect_db_btn.setEnabled(True)
            self.db_status_label.setText(f"● Connected to: {database}")
            self.db_status_label.setStyleSheet("color: green;")
            
            # Disable connection fields
            self.db_host_edit.setEnabled(False)
            self.db_port_edit.setEnabled(False)
            self.db_name_edit.setEnabled(False)
            self.db_user_edit.setEnabled(False)
            self.db_password_edit.setEnabled(False)
            
            self.iface.messageBar().pushMessage(
                "Ollama Chat",
                f"Successfully connected to PostgreSQL database: {database}",
                level=Qgis.Success,
                duration=4
            )
            
            # Enable table fetching
            self.refresh_tables_btn.setEnabled(True)
            
            # Auto-fetch tables if schema checkbox is enabled
            if self.include_db_schema:
                self.fetch_tables()
            
        except Exception as e:
            QMessageBox.critical(
                None,
                "Connection Failed",
                f"Failed to connect to PostgreSQL database.\n\n"
                f"Error: {str(e)}\n\n"
                f"Please check your connection parameters."
            )
            self.db_connection = None

    def disconnect_from_database(self):
        """Disconnect from PostgreSQL database"""
        if self.db_connection:
            try:
                self.db_connection.close()
            except:
                pass
            self.db_connection = None
        
        # Update UI
        self.connect_db_btn.setEnabled(True)
        self.disconnect_db_btn.setEnabled(False)
        self.db_status_label.setText("● Not connected")
        self.db_status_label.setStyleSheet("color: red;")
        
        # Enable connection fields
        self.db_host_edit.setEnabled(True)
        self.db_port_edit.setEnabled(True)
        self.db_name_edit.setEnabled(True)
        self.db_user_edit.setEnabled(True)
        self.db_password_edit.setEnabled(True)
        
        # Disable and clear table list
        self.refresh_tables_btn.setEnabled(False)
        self.table_list.clear()
        self.available_tables = []
        self.selected_tables = []
        
        self.iface.messageBar().pushMessage(
            "Ollama Chat",
            "Disconnected from PostgreSQL database",
            level=Qgis.Info,
            duration=2
        )

    def toggle_db_schema(self, state):
        """Enable/disable database schema inclusion"""
        self.include_db_schema = (state == Qt.Checked)
        self.table_list.setEnabled(self.include_db_schema)
        self.table_label.setEnabled(self.include_db_schema)
        
        if self.include_db_schema:
            # Auto-fetch tables if connected
            if self.db_connection:
                self.fetch_tables()
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                "Database schema will be included in prompts", 
                level=Qgis.Info, 
                duration=2
            )
    
    def on_table_selection_changed(self):
        """Handle table selection changes"""
        self.selected_tables = []
        for item in self.table_list.selectedItems():
            table_name = item.text()
            if table_name:
                self.selected_tables.append(table_name)

    def fetch_tables(self):
        """Fetch list of tables from the connected PostgreSQL database"""
        if not self.db_connection:
            QMessageBox.warning(
                None,
                "Not Connected",
                "Please connect to a PostgreSQL database first."
            )
            return
        
        try:
            self.iface.messageBar().pushMessage(
                "Ollama Chat",
                "Fetching tables from database...",
                level=Qgis.Info,
                duration=2
            )
            
            cursor = self.db_connection.cursor()
            
            # Query to get all tables from public schema
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            # Clear and populate table list
            self.table_list.clear()
            self.available_tables = []
            
            for row in results:
                table_name = row[0]
                self.available_tables.append(table_name)
                item = QListWidgetItem(table_name)
                self.table_list.addItem(item)
            
            if len(self.available_tables) == 0:
                self.iface.messageBar().pushMessage(
                    "Ollama Chat",
                    "No tables found in database",
                    level=Qgis.Warning,
                    duration=3
                )
            else:
                self.iface.messageBar().pushMessage(
                    "Ollama Chat",
                    f"Found {len(self.available_tables)} tables in database",
                    level=Qgis.Success,
                    duration=3
                )
                
        except Exception as e:
            QMessageBox.critical(
                None,
                "Error Fetching Tables",
                f"Failed to fetch tables from database.\n\n"
                f"Error: {str(e)}"
            )

    def get_layer_schema(self, layer):
        """Extract schema information from a QGIS vector layer"""
        if not layer or not isinstance(layer, QgsVectorLayer):
            return None
            
        schema_info = {
            "table_name": layer.name(),
            "geometry_type": layer.geometryType(),
            "fields": []
        }
        
        for field in layer.fields():
            field_info = {
                "name": field.name(),
                "type": field.typeName(),
                "length": field.length(),
                "precision": field.precision()
            }
            schema_info["fields"].append(field_info)
        
        return schema_info

    def get_database_schema_context(self):
        """Generate a text description of the database schema for the LLM"""
        # Fetch schema from connected PostgreSQL database
        if self.db_connection:
            return self.get_postgres_schema_direct()
        else:
            return ""
    
    def get_postgres_schema_direct(self):
        """Fetch PostgreSQL schema directly from the database connection"""
        if not self.db_connection:
            return ""
        
        try:
            cursor = self.db_connection.cursor()
            
            # Determine which tables to include
            tables_to_include = self.selected_tables if self.selected_tables else None
            
            # Query to get tables and their columns from public schema
            if tables_to_include:
                # Only selected tables
                placeholders = ','.join(['%s'] * len(tables_to_include))
                query = f"""
                    SELECT 
                        t.table_name,
                        c.column_name,
                        c.data_type,
                        c.character_maximum_length,
                        c.numeric_precision
                    FROM information_schema.tables t
                    JOIN information_schema.columns c ON t.table_name = c.table_name
                    WHERE t.table_schema = 'public' 
                        AND t.table_type = 'BASE TABLE'
                        AND t.table_name IN ({placeholders})
                    ORDER BY t.table_name, c.ordinal_position
                """
                cursor.execute(query, tables_to_include)
            else:
                # All tables
                query = """
                    SELECT 
                        t.table_name,
                        c.column_name,
                        c.data_type,
                        c.character_maximum_length,
                        c.numeric_precision
                    FROM information_schema.tables t
                    JOIN information_schema.columns c ON t.table_name = c.table_name
                    WHERE t.table_schema = 'public' 
                        AND t.table_type = 'BASE TABLE'
                    ORDER BY t.table_name, c.ordinal_position
                """
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            if not results:
                return ""
            
            # Organize results by table and track case-sensitive identifiers
            tables = {}
            has_uppercase_columns = False
            has_uppercase_tables = False
            
            for row in results:
                table_name, column_name, data_type, char_length, numeric_precision = row
                
                if table_name not in tables:
                    tables[table_name] = []
                
                # Check if column or table name contains uppercase letters
                if any(c.isupper() for c in column_name):
                    has_uppercase_columns = True
                if any(c.isupper() for c in table_name):
                    has_uppercase_tables = True
                
                # Add quotes around identifiers that need them (contain uppercase)
                quoted_column = f'"{column_name}"' if any(c.isupper() for c in column_name) else column_name
                
                col_info = f"{quoted_column} ({data_type}"
                if char_length:
                    col_info += f", length: {char_length}"
                if numeric_precision:
                    col_info += f", precision: {numeric_precision}"
                col_info += ")"
                
                tables[table_name].append(col_info)
            
            # Build schema text
            schema_text = "\n\n--- POSTGRESQL DATABASE SCHEMA ---\n"
            schema_text += f"Database: {self.db_name}\n\n"
            
            # Add SQL syntax rules if there are case-sensitive identifiers
            if has_uppercase_columns or has_uppercase_tables:
                schema_text += "IMPORTANT SQL SYNTAX RULES:\n"
                schema_text += "- Column and table names with uppercase letters MUST be enclosed in double quotes\n"
                schema_text += "- Example: WHERE \"POPULATION\" > 10000 (NOT WHERE POPULATION > 10000)\n"
                schema_text += "- Example: SELECT \"CityName\", \"POPULATION\" FROM \"MyTable\"\n"
                schema_text += "- Column names shown with quotes below REQUIRE quotes in SQL queries\n"
                schema_text += "- Column names without quotes can be used without quotes\n\n"
            
            if tables_to_include:
                schema_text += f"Selected tables ({len(tables)}):\n\n"
            else:
                schema_text += f"All available tables ({len(tables)}):\n\n"
            
            for table_name, columns in tables.items():
                # Quote table name if it contains uppercase
                quoted_table = f'"{table_name}"' if any(c.isupper() for c in table_name) else table_name
                schema_text += f"Table: {quoted_table}\n"
                schema_text += "Columns:\n"
                for col in columns:
                    schema_text += f"  - {col}\n"
                schema_text += "\n"
            
            schema_text += "--- END DATABASE SCHEMA ---\n\n"
            schema_text += "Based on the schema above, please help with the following request:\n\n"
            
            return schema_text
            
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "Ollama Chat",
                f"Failed to fetch database schema: {str(e)}",
                level=Qgis.Warning,
                duration=3
            )
            return ""

    def extract_sql_from_text(self, text):
        """Extract SQL code from response text"""
        # Pattern to match SQL code blocks - more flexible with whitespace
        # Matches ```sql or ```SQL followed by any whitespace, then content, then ```
        sql_pattern = r'```[Ss][Qq][Ll]\s*\n?(.*?)```'
        matches = re.findall(sql_pattern, text, re.DOTALL)
        
        if matches:
            # Get the first non-empty match
            for match in matches:
                if match.strip():
                    # Clean up the SQL - remove trailing/leading whitespace
                    cleaned_sql = match.strip()
                    # Don't add semicolon if already present
                    return cleaned_sql
        
        # Fallback: look for SELECT, INSERT, UPDATE, DELETE, CREATE statements
        fallback_pattern = r'((?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+.+?;)'
        fallback_matches = re.findall(fallback_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if fallback_matches:
            return '\n\n'.join(fallback_matches)
        
        return None

    def copy_sql(self):
        """Copy SQL to clipboard"""
        if self.extracted_sql:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.extracted_sql)
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                "SQL copied to clipboard!", 
                level=Qgis.Success, 
                duration=2
            )

    def execute_sql(self):
        """Execute the extracted SQL on the PostgreSQL database"""
        if not self.extracted_sql:
            QMessageBox.warning(None, "No SQL", "No SQL code to execute.")
            return
        
        # Check if connected to database
        if not self.db_connection:
            QMessageBox.warning(
                None,
                "Not Connected",
                "Please connect to a PostgreSQL database first.\n\n"
                "Fill in the connection details at the top and click 'Connect'."
            )
            return
        
        # Validate SQL before execution
        sql_upper = self.extracted_sql.strip().upper()
        
        # Check for incomplete SQL (common patterns)
        if 'SELECT * FROM' in sql_upper and sql_upper.endswith('FROM'):
            QMessageBox.warning(
                None,
                "Incomplete SQL",
                "The SQL statement appears to be incomplete.\n"
                "It's missing the table name after 'FROM'.\n\n"
                "Please edit the SQL and try again."
            )
            return
        
        # Check for very short/incomplete statements
        if len(self.extracted_sql.strip()) < 10:
            QMessageBox.warning(
                None,
                "Invalid SQL",
                "The SQL statement appears to be too short or incomplete.\n"
                "Please check the SQL and try again."
            )
            return
        
        try:
            # Show execution message
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                f"Executing SQL on database: {self.db_name}", 
                level=Qgis.Info, 
                duration=3
            )
            
            # Execute SQL query on the database
            result = self.execute_direct_sql(self.extracted_sql)
            
            # Check if it's a DDL statement for better messaging
            sql_upper = self.extracted_sql.strip().upper()
            is_ddl = any(sql_upper.startswith(cmd) for cmd in ['CREATE', 'ALTER', 'DROP'])
            
            if result:
                self.iface.messageBar().pushMessage(
                    "Ollama Chat", 
                    f"SQL executed successfully! {len(result)} rows returned.", 
                    level=Qgis.Success, 
                    duration=4
                )
                
                # Show results in output tab
                result_text = "SQL Execution Results:\n\n"
                result_text += f"Rows returned: {len(result)}\n\n"
                
                if result:
                    # Show first 10 rows
                    for i, row in enumerate(result[:10]):
                        result_text += f"Row {i+1}: {row}\n"
                    
                    if len(result) > 10:
                        result_text += f"\n... and {len(result) - 10} more rows"
                
                self.output_edit.append("\n\n" + "="*50 + "\n" + result_text)
                self.tab_widget.setCurrentIndex(0)  # Switch to Response tab
            else:
                # Different message for DDL vs DML
                if is_ddl:
                    ddl_type = "DDL statement"
                    if sql_upper.startswith('CREATE VIEW'):
                        ddl_type = "View created"
                    elif sql_upper.startswith('CREATE TABLE'):
                        ddl_type = "Table created"
                    elif sql_upper.startswith('ALTER'):
                        ddl_type = "Table altered"
                    elif sql_upper.startswith('DROP'):
                        ddl_type = "Object dropped"
                    
                    success_msg = f"{ddl_type} successfully!"
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        success_msg, 
                        level=Qgis.Success, 
                        duration=4
                    )
                    
                    # Add to output
                    self.output_edit.append("\n\n" + "="*50 + f"\n{success_msg}\n" + "="*50)
                    self.tab_widget.setCurrentIndex(0)
                else:
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        "SQL executed successfully (no rows returned)", 
                        level=Qgis.Success, 
                        duration=3
                    )
                
        except Exception as e:
            error_msg = f"SQL Execution Error: {str(e)}"
            QMessageBox.critical(None, "SQL Error", error_msg)
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                error_msg, 
                level=Qgis.Critical, 
                duration=5
            )

    def execute_direct_sql(self, sql):
        """Execute SQL directly on the connected PostgreSQL database"""
        if not self.db_connection:
            raise Exception("No database connection available")
        
        try:
            cursor = self.db_connection.cursor()
            
            # Check if it's a DDL statement
            sql_upper = sql.strip().upper()
            is_ddl = any(sql_upper.startswith(cmd) for cmd in ['CREATE', 'ALTER', 'DROP', 'INSERT', 'UPDATE', 'DELETE'])
            
            cursor.execute(sql)
            
            # Try to fetch results only for SELECT queries
            results = None
            if not is_ddl:
                try:
                    results = cursor.fetchall()
                except:
                    results = None
            
            self.db_connection.commit()
            
            # For DDL statements, provide helpful feedback
            if is_ddl and sql_upper.startswith('CREATE VIEW'):
                view_name = "view"
                # Try to extract view name
                try:
                    import re
                    match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)', sql, re.IGNORECASE)
                    if match:
                        view_name = match.group(1)
                except:
                    pass
                
                self.iface.messageBar().pushMessage(
                    "Ollama Chat", 
                    f"View '{view_name}' created successfully in PostgreSQL database!", 
                    level=Qgis.Success, 
                    duration=5
                )
            
            cursor.close()
            
            return results
            
        except Exception as e:
            self.db_connection.rollback()
            raise Exception(f"PostgreSQL Error: {str(e)}")

    def execute_db_query(self, layer, sql):
        """Execute SQL query on database layer and return results"""
        provider = layer.dataProvider()
        provider_type = provider.name()
        
        if provider_type == 'postgres':
            # PostgreSQL/PostGIS
            uri = QgsDataSourceUri(provider.dataSourceUri())
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=uri.host(),
                    port=uri.port() if uri.port() else '5432',
                    database=uri.database(),
                    user=uri.username(),
                    password=uri.password()
                )
                cursor = conn.cursor()
                
                # Check if it's a DDL statement (CREATE, ALTER, DROP) or DML that doesn't return rows
                sql_upper = sql.strip().upper()
                is_ddl = any(sql_upper.startswith(cmd) for cmd in ['CREATE', 'ALTER', 'DROP', 'INSERT', 'UPDATE', 'DELETE'])
                
                cursor.execute(sql)
                
                # Try to fetch results only for SELECT queries
                results = None
                if not is_ddl:
                    try:
                        results = cursor.fetchall()
                    except:
                        results = None
                
                conn.commit()
                
                # For DDL statements, provide helpful feedback
                if is_ddl and sql_upper.startswith('CREATE VIEW'):
                    view_name = "view"
                    # Try to extract view name
                    try:
                        import re
                        match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)', sql, re.IGNORECASE)
                        if match:
                            view_name = match.group(1)
                    except:
                        pass
                    
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        f"View '{view_name}' created successfully in PostgreSQL database!", 
                        level=Qgis.Success, 
                        duration=5
                    )
                
                cursor.close()
                conn.close()
                
                return results
            except ImportError:
                raise Exception("psycopg2 not installed. Install it to execute PostgreSQL queries.")
            except Exception as e:
                raise Exception(f"PostgreSQL Error: {str(e)}")
                
        elif provider_type == 'spatialite':
            # SpatiaLite/SQLite
            uri = QgsDataSourceUri(provider.dataSourceUri())
            db_path = uri.database()
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if it's a DDL statement
                sql_upper = sql.strip().upper()
                is_ddl = any(sql_upper.startswith(cmd) for cmd in ['CREATE', 'ALTER', 'DROP', 'INSERT', 'UPDATE', 'DELETE'])
                
                cursor.execute(sql)
                
                # Try to fetch results only for SELECT queries
                results = None
                if not is_ddl:
                    try:
                        results = cursor.fetchall()
                    except:
                        results = None
                
                conn.commit()
                
                # For DDL statements, provide helpful feedback
                if is_ddl and sql_upper.startswith('CREATE VIEW'):
                    view_name = "view"
                    # Try to extract view name
                    try:
                        import re
                        match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)', sql, re.IGNORECASE)
                        if match:
                            view_name = match.group(1)
                    except:
                        pass
                    
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        f"View '{view_name}' created successfully in SQLite/GeoPackage!", 
                        level=Qgis.Success, 
                        duration=5
                    )
                
                cursor.close()
                conn.close()
                
                return results
            except Exception as e:
                raise Exception(f"SQLite/SpatiaLite Error: {str(e)}")
            
        elif provider_type == 'ogr':
            # OGR provider (GeoPackage, Shapefile, GeoJSON, etc.)
            source = provider.dataSourceUri()
            
            # Extract the file path from the data source URI
            # Format can be: "/path/to/file.gpkg|layername=layer"
            if '|' in source:
                file_path = source.split('|')[0]
            else:
                file_path = source
            
            # Check if it's a SQLite-based format (GeoPackage, SQLite)
            if file_path.lower().endswith(('.gpkg', '.sqlite', '.db')):
                try:
                    # Use sqlite3 to execute SQL on GeoPackage/SQLite
                    conn = sqlite3.connect(file_path)
                    cursor = conn.cursor()
                    
                    # Check if it's a DDL statement
                    sql_upper = sql.strip().upper()
                    is_ddl = any(sql_upper.startswith(cmd) for cmd in ['CREATE', 'ALTER', 'DROP', 'INSERT', 'UPDATE', 'DELETE'])
                    
                    cursor.execute(sql)
                    
                    # Try to fetch results only for SELECT queries
                    results = None
                    if not is_ddl:
                        try:
                            results = cursor.fetchall()
                        except:
                            results = None
                    
                    conn.commit()
                    
                    # For DDL statements, provide helpful feedback
                    if is_ddl and sql_upper.startswith('CREATE VIEW'):
                        view_name = "view"
                        # Try to extract view name
                        try:
                            import re
                            match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)', sql, re.IGNORECASE)
                            if match:
                                view_name = match.group(1)
                        except:
                            pass
                        
                        self.iface.messageBar().pushMessage(
                            "Ollama Chat", 
                            f"View '{view_name}' created successfully in GeoPackage!", 
                            level=Qgis.Success, 
                            duration=5
                        )
                    
                    conn.close()
                    
                    return results
                except Exception as e:
                    raise Exception(f"Error executing SQL on GeoPackage/SQLite: {str(e)}")
            else:
                # For other OGR formats (Shapefile, GeoJSON, etc.), use GDAL ExecuteSQL
                try:
                    from osgeo import ogr, gdal
                    
                    # Clean SQL for OGR - remove trailing semicolon as OGR doesn't expect it
                    sql_cleaned = sql.strip()
                    if sql_cleaned.endswith(';'):
                        sql_cleaned = sql_cleaned[:-1].strip()
                    
                    # Check for unsupported SQL operations with OGR
                    sql_upper = sql_cleaned.upper()
                    unsupported_commands = ['CREATE VIEW', 'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE', 'DROP VIEW']
                    
                    for cmd in unsupported_commands:
                        if sql_upper.startswith(cmd):
                            raise Exception(
                                f"{cmd} is not supported with OGR/GDAL ExecuteSQL.\n\n"
                                f"OGR SQL dialect only supports:\n"
                                f"  - SELECT statements\n"
                                f"  - Simple spatial queries\n\n"
                                f"For {cmd} operations, use a proper database (PostgreSQL, GeoPackage, etc.)\n"
                                f"or edit the SQL to use a SELECT statement instead."
                            )
                    
                    # Open the data source
                    ds = ogr.Open(file_path, 1)  # 1 = update mode
                    if ds is None:
                        raise Exception(f"Could not open data source: {file_path}")
                    
                    # Execute SQL (without semicolon)
                    result_layer = ds.ExecuteSQL(sql_cleaned, dialect='OGRSQL')
                    
                    if result_layer is None:
                        ds.Destroy()
                        # Return empty result for successful DDL commands
                        return None
                    
                    # Fetch results
                    results = []
                    for feature in result_layer:
                        # Get all field values
                        row = []
                        for i in range(feature.GetFieldCount()):
                            row.append(feature.GetField(i))
                        results.append(tuple(row))
                    
                    ds.ReleaseResultSet(result_layer)
                    ds.Destroy()
                    
                    return results if results else None
                    
                except ImportError:
                    raise Exception("GDAL/OGR not available. Cannot execute SQL on this file format.")
                except Exception as e:
                    error_str = str(e)
                    # Provide more helpful error messages for common OGR SQL issues
                    if "syntax error" in error_str.lower() and "unexpected" in error_str.lower():
                        # Get layer info for better error message
                        try:
                            from osgeo import ogr
                            ds = ogr.Open(file_path, 0)
                            if ds and ds.GetLayerCount() > 0:
                                lyr = ds.GetLayer(0)
                                layer_name = lyr.GetName()
                                layer_defn = lyr.GetLayerDefn()
                                field_names = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]
                                ds.Destroy()
                                
                                raise Exception(
                                    f"SQL Expression Parsing Error: {error_str}\n\n"
                                    f"Common issues with OGR SQL:\n"
                                    f"  - Field names are CASE-SENSITIVE\n"
                                    f"  - Table name might be wrong\n"
                                    f"  - Check your field names match exactly\n\n"
                                    f"Available layer: '{layer_name}'\n"
                                    f"Available fields: {', '.join(field_names)}\n\n"
                                    f"Your SQL:\n{sql_cleaned}"
                                )
                        except:
                            pass
                        
                        raise Exception(
                            f"SQL Expression Parsing Error: {error_str}\n\n"
                            f"Common issues with OGR SQL:\n"
                            f"  - Field names are CASE-SENSITIVE (use exact case as in layer)\n"
                            f"  - Table names must match the layer name exactly\n"
                            f"  - CREATE VIEW is not supported\n"
                            f"  - Check that your SQL is complete\n\n"
                            f"Your SQL:\n{sql_cleaned}"
                        )
                    else:
                        raise Exception(f"Error executing SQL with OGR: {error_str}")
        else:
            raise Exception(f"Provider type '{provider_type}' not yet supported for SQL execution")

    def check_ollama_model(self, model_name):
        """Check if the specified model is available in Ollama"""
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            available_models = [model['name'] for model in data.get('models', [])]
            
            # Check if the model name matches any available model
            # Ollama models can have tags like "llava:latest"
            for available_model in available_models:
                if model_name in available_model or available_model.startswith(model_name + ":"):
                    return True, None
            
            # Model not found
            if available_models:
                models_list = "\n  - ".join(available_models)
                error_msg = (
                    f"Model '{model_name}' is not available in Ollama.\n\n"
                    f"Available models:\n  - {models_list}\n\n"
                    f"To pull a model, run in terminal:\n"
                    f"  ollama pull {model_name}"
                )
            else:
                error_msg = (
                    f"Model '{model_name}' is not available in Ollama.\n\n"
                    f"No models found. To pull a model, run in terminal:\n"
                    f"  ollama pull {model_name}"
                )
            
            return False, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = (
                "Cannot connect to Ollama.\n\n"
                "Make sure Ollama is running on http://localhost:11434"
            )
            return False, error_msg
        except Exception as e:
            error_msg = f"Error checking Ollama models: {str(e)}"
            return False, error_msg

    def attach_image(self):
        """Attach an image file for sending to Ollama"""
        path, _ = QFileDialog.getOpenFileName(
            None, 
            "Select Image", 
            "", 
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if path:
            try:
                with open(path, "rb") as f:
                    image_bytes = f.read()
                    b64 = base64.b64encode(image_bytes).decode("utf-8")
                self.image_data = b64
                self.image_label.setText(f"Attached: {os.path.basename(path)}")
                self.iface.messageBar().pushMessage(
                    "Ollama Chat", 
                    f"Image attached: {os.path.basename(path)}", 
                    level=Qgis.Success, 
                    duration=2
                )
            except Exception as e:
                self.image_label.setText("Error attaching image")
                self.iface.messageBar().pushMessage(
                    "Ollama Chat", 
                    f"Failed to attach image: {str(e)}", 
                    level=Qgis.Warning, 
                    duration=3
                )

    def send_to_ollama(self):
        """Send prompt and optional image to Ollama API"""
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(None, "Empty Prompt", "Please enter a prompt first.")
            return
        
        # Get and validate model name
        model_name = self.model_name_edit.text().strip()
        if not model_name:
            QMessageBox.warning(
                None, 
                "No Model Specified", 
                "Please enter an Ollama model name (e.g., llava, llama2, mistral)."
            )
            return
        
        # Check if the model is available
        self.iface.messageBar().pushMessage(
            "Ollama Chat", 
            f"Checking if model '{model_name}' is available...", 
            level=Qgis.Info, 
            duration=2
        )
        
        is_available, error_msg = self.check_ollama_model(model_name)
        if not is_available:
            QMessageBox.critical(
                None, 
                "Model Not Available", 
                error_msg
            )
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                f"Model '{model_name}' is not available", 
                level=Qgis.Critical, 
                duration=5
            )
            return

        # Disable send button during request
        self.send_btn.setEnabled(False)
        
        # Show progress message in QGIS message bar
        self.iface.messageBar().pushMessage(
            "Ollama Chat", 
            "Preparing request...", 
            level=Qgis.Info, 
            duration=2
        )
        
        self.output_edit.setText("Connecting to Ollama...")
        
        try:
            # Add database schema context if enabled
            full_prompt = prompt
            if self.include_db_schema:
                schema_context = self.get_database_schema_context()
                if schema_context:
                    full_prompt = schema_context + prompt
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        "Including database schema in request...", 
                        level=Qgis.Info, 
                        duration=2
                    )
                else:
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        "No layers available for schema", 
                        level=Qgis.Warning, 
                        duration=3
                    )
            
            # Build the payload
            payload = {
                "model": model_name,
                "prompt": full_prompt,
                "stream": True
            }
            
            # Add image if attached
            if self.image_data:
                payload["images"] = [self.image_data]
                self.iface.messageBar().pushMessage(
                    "Ollama Chat", 
                    "Sending request with image to Ollama...", 
                    level=Qgis.Info, 
                    duration=3
                )
            else:
                self.iface.messageBar().pushMessage(
                    "Ollama Chat", 
                    "Sending request to Ollama...", 
                    level=Qgis.Info, 
                    duration=3
                )

            # Make the API request
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                stream=True,
                timeout=1200
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Show message that we're receiving response
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                "Receiving response from Ollama...", 
                level=Qgis.Info, 
                duration=3
            )

            full_text = ""
            self.output_edit.setText("")
            
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse JSON response
                        chunk_data = json.loads(line.decode("utf-8"))
                        
                        # Extract the response text
                        if "response" in chunk_data:
                            response_text = chunk_data["response"]
                            full_text += response_text
                            self.output_edit.setPlainText(full_text)
                        
                        # Check if done
                        if chunk_data.get("done", False):
                            break
                            
                    except json.JSONDecodeError as e:
                        # Skip malformed JSON lines
                        continue
            
            # Check if we got any response
            if not full_text:
                self.output_edit.setText("No response received from Ollama. The model might not be available.")
                self.iface.messageBar().pushMessage(
                    "Ollama Chat", 
                    "No response received from Ollama", 
                    level=Qgis.Warning, 
                    duration=4
                )
            else:
                # Extract SQL from response
                self.extracted_sql = self.extract_sql_from_text(full_text)
                
                if self.extracted_sql:
                    self.sql_edit.setPlainText(self.extracted_sql)
                    self.execute_sql_btn.setEnabled(True)
                    self.copy_sql_btn.setEnabled(True)
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        "Response completed! SQL code detected and extracted.", 
                        level=Qgis.Success, 
                        duration=3
                    )
                    # Highlight the SQL tab
                    self.tab_widget.setTabText(1, "SQL Code ✓")
                else:
                    self.sql_edit.setPlainText("No SQL code detected in response.")
                    self.execute_sql_btn.setEnabled(False)
                    self.copy_sql_btn.setEnabled(False)
                    self.iface.messageBar().pushMessage(
                        "Ollama Chat", 
                        "Response completed successfully!", 
                        level=Qgis.Success, 
                        duration=3
                    )
                    self.tab_widget.setTabText(1, "SQL Code")

        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to Ollama. Make sure Ollama is running on http://localhost:11434"
            self.output_edit.setText(error_msg)
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                error_msg, 
                level=Qgis.Critical, 
                duration=5
            )
        
        except requests.exceptions.Timeout:
            error_msg = "Request timed out. The model might be taking too long to respond."
            self.output_edit.setText(error_msg)
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                error_msg, 
                level=Qgis.Critical, 
                duration=5
            )
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code} - {e.response.reason}"
            self.output_edit.setText(error_msg)
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                error_msg, 
                level=Qgis.Critical, 
                duration=5
            )
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.output_edit.setText(error_msg)
            self.iface.messageBar().pushMessage(
                "Ollama Chat", 
                error_msg, 
                level=Qgis.Critical, 
                duration=5
            )
        
        finally:
            # Re-enable send button
            self.send_btn.setEnabled(True)

