# Métodos de optimización de aprendizaje federado
El presente proyecto representa un trabajo semestral que consolida los saberes adquiridos en el curso de Análisis y Diseño de Algoritmos.

## Solución base — Grupo 2 · Red

Selección de nodos participantes (voraz submodular) y reparto de presupuesto de ruido (voraz con montículo), en T rondas.

### Ejecución
```bash
python3 src/red.py entrada_G2_red_15_nodos.json          # genera resultados/ y muestra la traza
python3 src/red.py caso1.json caso2.json -o resultados   # varios casos
python3 src/red.py caso.json --sin-exacto                # omite la verificación por fuerza bruta
python3 tests/test_red.py                                # pruebas
```
Requisitos: Python 3, sin dependencias (`requirements.txt`).
Por cada caso se escribe `resultados/<caso>_resultado.json` (resultado, tiempo, traza completa) y `resultados/<caso>_traza.txt` (traza legible).

Documentación: `doc/Manual_tecnico.md` (algoritmo, formatos, limitaciones) y `doc/Formalización.tex` (formalización).
