# Generador SLR para YALex + YAPar

Este proyecto implementa un generador de analizadores léxicos y sintácticos en Python sin librerías externas.

## Características principales

- Lectura de especificaciones `.yal` (léxico) y `.yalp` (sintáctico).
- Construcción de AFN por Thompson y conversión a AFD por subconjuntos.
- Simulación de AFD para tokenizar entrada de texto.
- Construcción de autómata LR(0) y tabla SLR (ACTION/GOTO).
- Generación de archivos Python independientes para:
  - Analizador léxico generado.
  - Analizador sintáctico generado.
- Interfaz gráfica amigable usando `tkinter` (librería estándar).
- Exportación textual de:
  - Diagrama de transiciones del AFD.
  - Estados LR(0) y transiciones.
- Ejecución del análisis completo con traza de acciones (`shift/reduce/accept`) y reporte de errores léxicos/sintácticos.

## Restricciones cumplidas

- No se usan librerías externas.
- No se usa módulo `re` para el procesamiento léxico.
- El reconocimiento léxico se realiza con autómatas finitos.
- El lexer y parser generados son independientes del generador.
- Se incluyen tres grupos de pruebas: baja, media y alta complejidad.

## Estructura del proyecto

```text
Proyecto2_Compis/
├── src/
│   ├── main.py
│   ├── ui_app.py
│   ├── generator/
│       ├── __init__.py
│       ├── models.py
│       ├── yalex_parser.py
│       ├── regex_engine.py
│       ├── yalp_parser.py
│       ├── grammar_tools.py
│       ├── slr_builder.py
│       ├── codegen.py
│       └── pipeline.py
├── tests_data/
│   ├── low/
│   │   ├── lexer_low.yal
│   │   ├── parser_low.yalp
│   │   └── input_low.txt
│   ├── medium/
│   │   ├── lexer_medium.yal
│   │   ├── parser_medium.yalp
│   │   └── input_medium.txt
│   └── high/
│       ├── lexer_high.yal
│       ├── parser_high.yalp
│       └── input_high.txt
├── outputs/
├── .gitignore
└── README.md
```

## Ejecución

```bash
python3 src/main.py
```

También se puede ejecutar por CLI:

```bash
python3 -m src.generator.pipeline \
  --yal tests_data/medium/lexer_medium.yal \
  --yalp tests_data/medium/parser_medium.yalp \
  --input tests_data/medium/input_medium.txt \
  --out outputs/medium_run
```

## Diseño resumido

1. **Módulo léxico**: parsea reglas YALex, convierte regex a postfix (shunting-yard), construye AFN y AFD, y tokeniza con criterio de mayor avance y prioridad por orden de reglas.
2. **Módulo sintáctico**: parsea YAPar, construye gramática aumentada, conjuntos FIRST/FOLLOW, colección LR(0), tabla SLR y algoritmo de parsing.
3. **Generación de código**: escribe `generated_lexer.py` y `generated_parser.py` autocontenidos con tablas serializadas.
4. **UI**: flujo guiado para elegir archivos, generar analizadores, ver autómatas y ejecutar análisis sobre un archivo de entrada.

