# Métodos de optimización de aprendizaje federado
El presente proyecto representa un trabajo semestral que consolida los saberes adquiridos en el curso de Análisis y Diseño de Algoritmos.

## Solución base, Grupo 2 · Red

Elige los nodos participantes de cada ronda con un voraz submodular y reparte el presupuesto de ruido con un voraz de montículo, a lo largo de T rondas.

### Ejecución
```bash
python3 src/red.py data/N15.json          # genera resultados/ y muestra la traza
python3 src/red.py caso1.json caso2.json -o resultados   # varios casos
python3 src/red.py caso.json --sin-exacto                # omite la verificación por fuerza bruta
python3 tests/test_red.py                                # pruebas
```
Requiere Python 3 y ninguna dependencia (`requirements.txt`).
Por cada caso escribe `resultados/<caso>_resultado.json` (resultado, tiempo y traza completa) y `resultados/<caso>_traza.txt` (la misma traza en texto legible).

Documentación: `doc/Manual_tecnico.md` (algoritmo, formatos y limitaciones) y `doc/Formalización.pdf` (informe: formalización y prueba de NP-dureza; fuente en `doc/Formalización.tex`, compilar con pdfLaTeX).
