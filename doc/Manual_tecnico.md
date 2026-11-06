# Manual técnico — Solución base G2 · Red

Proyecto semestral de Análisis y Diseño de Algoritmos (2026-2) · Primera entrega · Grupo 2.
Este manual acompaña a `doc/Formalización.tex` (informe), al código (`src/red.py`) y a las evidencias (`resultados/`). Todo corresponde a la misma versión del repositorio.

## Contenido
1. Propósito y alcance
2. Contexto e investigación previa
3. Problema formalizado (resumen)
4. Decisiones de modelado y su justificación
5. Algoritmos: diseño, pseudocódigo y corrección
6. Análisis de complejidad
7. Estructura del código
8. Formatos de entrada y salida
9. Pasos de ejecución
10. Ejemplo trabajado con el caso de la profesora
11. Validación realizada
12. Limitaciones y trabajo futuro
13. Referencias

---

## 1. Propósito y alcance
Esta solución base resuelve, para el caso entregado por la profesora (`entrada_G2_red_15_nodos.json`), las dos partes del problema:

- **Parte 1 — reparto del presupuesto de ruido:** dados los nodos ya elegidos y un presupuesto B, repartirlo para maximizar Σ u_i(x_i).
- **Parte 2 — selección de participantes:** elegir el subconjunto de nodos de cada ronda que maximiza una utilidad conjunta submodular, sujeto a un cupo k y a un presupuesto de costos de participación C.

Ambas se encadenan en T rondas: la selección decide quién participa, el reparto decide cuánto ruido gasta cada uno, y el presupuesto total de cada nodo P_i se va consumiendo entre rondas.

Queda fuera de esta entrega (se aborda en etapas posteriores del cronograma): fallos de nodos, externalidades de red en el reparto, el algoritmo exacto con su T(n), la cota de aproximación con costos y la validación experimental con instancias crecientes.

## 2. Contexto e investigación previa

### 2.1 Por qué el problema existe
En aprendizaje federado (McMahan et al., 2017) varios nodos entrenan un modelo común sin compartir sus datos crudos, y solo envían actualizaciones. Esas actualizaciones aún pueden filtrar información, por lo que se protegen con un mecanismo de **privacidad diferencial** que añade ruido calibrado (Dwork y Roth, 2014). Más ruido protege más pero reduce la utilidad de la actualización, y cada nodo tolera solo una cantidad total de ruido (su presupuesto de privacidad). De ahí salen dos decisiones por ronda: *quién* participa y *cuánto* de su presupuesto gasta.

### 2.2 Qué se sabe de cada parte
| Pregunta | Resultado conocido | Fuente |
|---|---|---|
| Repartir B unidades discretas entre N funciones separables, cóncavas y crecientes | Es un problema de asignación de recursos con solución exacta en tiempo polinomial: el voraz por ganancia marginal es óptimo | Ibaraki y Katoh (1988) |
| Elegir k elementos para maximizar una función monótona y submodular | NP-difícil; el voraz garantiza ≥ (1 − 1/e) ≈ 63,2 % del óptimo | Nemhauser, Wolsey y Fisher (1978) |
| ¿Se puede mejorar esa garantía? | No, salvo P = NP, ni siquiera para Cobertura Máxima | Feige (1998) |
| Con costos y presupuesto (*budgeted maximum coverage*) | El voraz simple pierde la garantía; hay algoritmos que la recuperan | Khuller, Moss y Naor (1999); Sviridenko (2004) |
| Dureza de la selección | Reducción desde Cobertura Máxima, a su vez desde Cobertura de Conjuntos | Karp (1972); `Formalización.tex`, Teorema de NP-dureza |

### 2.3 Qué decisiones tomamos a partir de eso
- **Parte 1** se resuelve de forma exacta con el voraz de montículo. No se justifica usar fuerza bruta ni metaheurísticas, porque existe un algoritmo óptimo y eficiente.
- **Parte 2** se resuelve con voraz porque la selección es NP-difícil y la función es submodular, que es justo la situación donde Nemhauser et al. dan garantía. Además se verifica contra el óptimo por fuerza bruta mientras N lo permite.
- Como el caso trae **costos distintos** además del cupo, se sabe que la cota (1 − 1/e) no aplica tal cual. Por eso se implementan dos variantes del voraz y se reporta la comparación con el óptimo solo como referencia (sección 12).

## 3. Problema formalizado (resumen)
La formalización completa (entradas, salidas, tamaño n, objetivo, restricciones, casos límite) está en `doc/Formalización.tex`. Para el caso G2, por ronda t:

- **Entrada:** N nodos, cupo k, costos c_i, presupuesto de participación C, ruido B, presupuestos totales P_i, grafo de influencia w_ij, funciones u_i y f.
- **Decisión:** S_t ⊆ V y x^t ∈ ℤ≥0^{S_t}.
- **Restricciones:** |S_t| ≤ k; Σ_{i∈S_t} c_i ≤ C; Σ_i x_i^t ≤ B; Σ_t x_i^t ≤ P_i.
- **Objetivo:** maximizar Σ_t [ f(S_t) + Σ_{i∈S_t} u_i(x_i^t) ].
- **Tamaño de la entrada:** n = N (el grafo del caso es completo, así que |E| = N(N−1)/2 = 105; k, B, C, T se reportan aparte).

Para el caso: N = 15, T = 3, k = 5, B = 30, C = 24, P_i = 18 para todos, costos entre 2 y 7.

## 4. Decisiones de modelado y su justificación
El JSON entrega coeficientes pero no las fórmulas de utilidad, así que se fijaron las siguientes. Hay que revisarlas si la profesora indicó otras.

### 4.1 Utilidad de reparto: u_i(x) = a_i · ln(1 + x)
- *a_i* es `coeficiente_utilidad`.
- Es creciente y cóncava, con u_i(0) = 0, como exige el modelo.
- Ganancia marginal de la unidad x+1: Δ_i(x+1) = a_i · ln((x+2)/(x+1)), estrictamente decreciente en x. Esto refleja rendimientos decrecientes: las primeras unidades de presupuesto aportan más que las siguientes.
- Se usa `log1p(1/(x+1))` para calcularlo con estabilidad numérica.

### 4.2 Utilidad conjunta: f(S) = Σ_j a_j · (1 − Π_{i∈S}(1 − w_ij)), con w_jj = 1
Es una **cobertura probabilística ponderada**: cada nodo seleccionado i «cubre» al nodo j con probabilidad w_ij (su influencia en el grafo), y cubrir a j vale a_j. Un nodo seleccionado se cubre a sí mismo (w_jj = 1).

*Por qué es monótona y submodular.* Sea m_S(j) = Π_{i∈S}(1 − w_ij) ∈ [0,1], la probabilidad de que j siga sin cubrir. Agregar un nodo i a S aporta

  f(S∪{i}) − f(S) = Σ_j a_j · m_S(j) · w_ij ≥ 0,

lo que prueba monotonía. Si A ⊆ B, entonces m_B(j) ≤ m_A(j) para todo j, porque se multiplican más factores en [0,1]. Por tanto la ganancia de i sobre A es ≥ la ganancia de i sobre B: submodularidad. Las ganancias son además calculables incrementalmente guardando el vector m(·).

Esta elección es coherente con la reducción de NP-dureza: la cobertura de conjuntos |⋃F_i| es el caso particular en que w_ij ∈ {0,1}. El grafo del caso entra en la selección a través de f.

### 4.3 Otras decisiones
- La influencia se toma **simétrica** (w_ij = w_ji), como entrega el caso (aristas no dirigidas).
- **No hay fallos de nodos** (el caso no trae probabilidades q_i). Un nodo está disponible mientras le quede presupuesto.
- El presupuesto es **entero y discreto**; el reparto asigna unidades de a una.
- **Cupo y costos simultáneos:** el caso da k = 5 y C = 24; se exigen ambas restricciones.
- **El presupuesto P_i se consume entre rondas** y no se transfiere entre nodos.
- **Desempates** por menor índice de nodo, para que la ejecución sea determinista.

## 5. Algoritmos

### 5.1 Reparto voraz con montículo (Parte 1)
```
reparto(S, B, restante):
    x[i] ← 0  para i en S
    H ← montículo máximo con (Δ_i(1), i) para i en S con restante[i] > 0
    repetir B veces:
        si H vacío: parar
        (g, i) ← extraer máximo de H
        x[i] ← x[i] + 1
        si x[i] < restante[i]: insertar (Δ_i(x[i]+1), i) en H
    devolver x
```
**Corrección (argumento de intercambio).** Sea x* una solución óptima con Σ x_i* = B que respeta los topes, y supongamos que no es la del voraz. Existen i, j con x_i* > g_i y x_j* < g_j, donde g es la salida del voraz, tales que la última unidad de i en x* tiene ganancia Δ_i(x_i*) y la siguiente de j, Δ_j(x_j*+1). El voraz tomó antes la unidad x_j*+1 de j que la unidad x_i* de i, por lo que Δ_j(x_j*+1) ≥ Δ_i(x_i*). Mover una unidad de i a j (los topes se respetan, pues x_j*+1 ≤ g_j ≤ restante[j]) no disminuye la utilidad total. Repitiendo, se llega a g sin perder optimalidad. La concavidad (ganancias no crecientes) garantiza que el orden de ganancias de cada nodo es el orden en que se asignan las unidades. Los topes P_i (cotas superiores enteras) no rompen el argumento.

### 5.2 Selección voraz con cupo y costos (Parte 2)
```
seleccion(elegibles, modo):
    S ← ∅ ; costo ← 0 ; m[j] ← 1 para todo j
    mientras |S| < k:
        cand ← { i ∈ elegibles \ S : costo + c_i ≤ C }
        si cand vacío: parar
        para i en cand: g_i ← Σ_j a_j · m[j] · w_ij        # ganancia marginal
        elegir i* = argmax g_i              (modo "ganancia")
               o  argmax g_i / c_i          (modo "razón")
        S ← S ∪ {i*} ; costo ← costo + c_{i*}
        m[j] ← m[j] · (1 − w_{i*,j}) para todo j
    devolver S
```
En cada ronda se ejecutan los dos modos y se conserva el de mayor f(S).

**Qué garantiza y qué no.**
- Sin costos (c_i = 1, C = k), el voraz por ganancia cumple f(S) ≥ (1 − 1/e)·f(S_opt) (Nemhauser et al., 1978). La idea: en cada paso, la ganancia marginal del voraz es al menos (1/k) de lo que falta para llegar al óptimo, lo que da f(S_k) ≥ (1 − (1 − 1/k)^k) f(S_opt) ≥ (1 − 1/e) f(S_opt).
- Con costos distintos **no hay garantía**. Ejemplo: C = 10, un nodo A de ganancia 1 y costo 1, y un nodo B de ganancia 1,1 y costo 10. El voraz por ganancia toma B y agota el presupuesto, mientras que el óptimo toma A y otros nodos baratos por mucho más; con ganancias de ese estilo la razón puede hacerse tan mala como se quiera. El voraz por razón evita este caso pero tiene su propio contraejemplo (un nodo muy barato con ganancia pequeña le gana a uno de gran valor que sí cabía).
- La garantía (1 − 1/e) para *budgeted maximum coverage* se obtiene combinando el voraz por razón con el mejor elemento individual (Khuller et al., 1999, con razón (1 − 1/e)/2) o con enumeración de tripletes iniciales (Sviridenko, 2004, con razón (1 − 1/e)). La solución base **no** implementa esas correcciones; es un objetivo de la etapa del algoritmo aproximado.

## 6. Análisis de complejidad
Notación: N nodos, k cupo, B presupuesto de ruido por ronda, T rondas.

**Reparto (por ronda).** Construir el montículo: O(|S|) con |S| ≤ k. Cada una de las B extracciones y reinserciones cuesta O(log |S|). Total: **O(k + B log k)**. Es polinomial en B y N, y pseudo-polinomial en la longitud de la codificación binaria de B (el `.tex` lo deja explícito). En la formulación del curso, con S = N: T(N,B) = O(B log N).

**Selección (por ronda).**
- Ganancia marginal de un candidato con esta f: recorre los N nodos j → O(N).
- Un paso evalúa hasta N candidatos → O(N²); actualizar m(·) cuesta O(N).
- k pasos → **O(k·N²)**; dos modos → factor constante 2.
- Con un oráculo de ganancia marginal O(1) (supuesto del `.tex`), el costo sería O(k·N). El factor N adicional viene de que aquí f se evalúa de forma explícita. Para la validación experimental hay que contrastar contra la T(n) de *esta* implementación.

**Total.** T rondas: **O(T·(k·N² + k + B log k))**. Con los parámetros fijos del caso es O(N²), y el caso real se resuelve en alrededor de un milisegundo.

**Fuerza bruta de verificación.** Enumera Σ_{r≤k} C(N, r) subconjuntos y evalúa f en O(r·N) cada uno. Para N = 15, k = 5 son 4 944 subconjuntos por ronda. Se omite si superan 300 000 (opción `--sin-exacto` para omitirla siempre).

## 7. Estructura del código
```
src/red.py            solución base (un solo módulo, sin dependencias)
tests/test_red.py     pruebas automáticas
entrada_G2_red_15_nodos.json   caso de la profesora
resultados/           resultado.json y traza.txt por caso
doc/                  informe (.tex) y este manual
```
Funciones de `src/red.py`:

| Elemento | Responsabilidad |
|---|---|
| `Instancia` | Lee el JSON; construye la matriz de influencia (simétrica, w_ii = 1); expone `ganancia_unidad`, `utilidad_nodo` y `f` |
| `seleccion_voraz(inst, elegibles, modo)` | Voraz con cupo y costos; devuelve S y traza de cada paso con todos los candidatos |
| `seleccion_exacta(inst, elegibles)` | Fuerza bruta de verificación |
| `reparto_voraz(inst, S, B, restante)` | Voraz de montículo respetando topes; devuelve x y traza por unidad |
| `resolver(inst)` | Orquesta las T rondas, actualiza presupuestos restantes y calcula la utilidad total |
| `verificar(...)` | Comprueba restricciones y, si hay exacto, la razón al óptimo |
| `texto(...)`, `main()` | Traza legible y línea de comandos |

## 8. Formatos de entrada y salida

### 8.1 Entrada (JSON)
```json
{
  "parametros": {
    "numero_nodos": 15, "numero_rondas": 3,
    "cupo_participantes_por_ronda_k": 5,
    "presupuesto_ruido_por_ronda_B": 30,
    "presupuesto_costos_participacion_por_ronda": 24
  },
  "grafo": [ {"u": "N01", "v": "N02", "peso_influencia": 0.25}, ... ],
  "nodos": [ {"id": "N01", "coeficiente_utilidad": 8.5,
              "presupuesto_total_nodo": 18, "costo_participacion": 3}, ... ]
}
```
Todos los campos son obligatorios. El programa comprueba que `numero_nodos` coincida con la lista de nodos; los demás errores de formato terminan con la excepción de Python correspondiente (limitación: no hay validación de esquema más fina).

### 8.2 Salida
`resultados/<caso>_resultado.json`:

| Campo | Contenido |
|---|---|
| `tiempo_segundos`, `utilidad_total` | Tiempo del algoritmo (sin la fuerza bruta) y Σ_t [f(S_t) + Σ u_i] |
| `rondas[].seleccion`, `f_S`, `modo_seleccion`, `f_por_modo` | Nodos elegidos, su utilidad, el modo ganador y el valor de ambos modos |
| `rondas[].traza_seleccion` | Por paso: nodo elegido, ganancia marginal, costo y ganancia de **todos** los candidatos |
| `rondas[].reparto`, `utilidad_reparto` | Unidades por nodo y utilidad Σ u_i(x_i) |
| `rondas[].traza_reparto` | Por unidad: nodo que la recibe y su ganancia marginal |
| `rondas[].presupuesto_restante_por_nodo` | P_i menos lo gastado hasta esa ronda |
| `rondas[].exacto` | Óptimo por fuerza bruta, razón voraz/óptimo y la cota 1 − 1/e |
| `rondas[].verificacion` | Cada restricción con OK/FALLA |

`resultados/<caso>_traza.txt` contiene lo mismo en texto legible.

## 9. Pasos de ejecución
Requisitos: Python 3.8 o superior (probado en 3.14). No hay que instalar nada (`requirements.txt` no tiene dependencias).

```bash
git clone <repositorio> && cd federated-learning-optimization
python3 src/red.py entrada_G2_red_15_nodos.json      # un caso
python3 src/red.py caso1.json caso2.json -o salida   # varios casos, otra carpeta
python3 src/red.py caso.json --sin-exacto            # sin fuerza bruta (instancias grandes)
python3 tests/test_red.py                            # pruebas
```
Cada ejecución imprime la traza y escribe los dos archivos por caso en la carpeta de salida (por defecto `resultados/`). El resultado no depende del directorio desde donde se lance. Se comprobó que dos ejecuciones producen trazas idénticas.

## 10. Ejemplo trabajado con el caso de la profesora
Datos de la ronda 1 (los valores salen de `resultados/`).

**Selección.**

| Paso | Elegido | Ganancia marginal | Costo acumulado | Observación |
|---|---|---|---|---|
| 1 | N11 | 103,490 | 4 | Mayor influencia sobre los demás (pesos de hasta 0,8), pese a tener el menor coeficiente propio (7,6) |
| 2 | N14 | 24,278 | 7 | |
| 3 | N09 | 9,933 | 10 | |
| 4 | N15 | 5,531 | 16 | |
| 5 | N13 | 2,348 | 23 | Se alcanza k = 5; costo 23 ≤ 24 |

Las ganancias decrecen paso a paso, como corresponde a una función submodular. La verificación manual del paso 1: f({N11}) = a_N11 + Σ_{j≠N11} a_j·w_{N11,j} = 103,49. El voraz por razón ganancia/costo da f = 145,106 y el voraz por ganancia da 145,580, por lo que se conserva este último. La fuerza bruta (4 944 subconjuntos) encuentra el mismo conjunto óptimo, con f* = 145,580 y razón 1,0.

**Reparto de B = 30.** La primera unidad va a N14 con ganancia 10,1·ln 2 = 7,0008 (la mayor posible entre los cinco), la segunda a N09 con 9,9·ln 2 = 6,8622, y así sucesivamente. Resultado: N11 = 5, N14 = 7, N09 = 7, N15 = 6, N13 = 5 (suma 30), con utilidad 88,564.

**Efecto del presupuesto total.** Tras la ronda 1, N09 y N14 conservan 11 unidades de 18. Tras la ronda 2 conservan 4. En la ronda 3 solo pueden recibir 4, por lo que el reparto cambia a N11 = 8, N14 = 4, N09 = 4, N15 = 6, N13 = 8 (utilidad 85,611, menor que en las rondas anteriores porque los topes obligan a mover unidades a nodos de menor ganancia). Al terminar, los cinco nodos elegidos quedan con 0 de presupuesto.

**Utilidad total del caso:** 699,477 en 0,0009 s.

## 11. Validación realizada
1. **Verificaciones dentro de cada ejecución** (aparecen en la traza): |S| ≤ k, Σ c_i ≤ C, Σ x_i ≤ B, x_i ≤ presupuesto restante, x_i enteros no negativos y, como referencia, f(S_voraz) ≥ (1 − 1/e)·f(S_opt). Todas dan OK en las tres rondas.
2. **Pruebas automáticas** (`tests/test_red.py`):
   - el reparto voraz coincide con la enumeración exhaustiva de todos los repartos de 8 unidades entre 3 nodos;
   - f es monótona y submodular en un ejemplo concreto;
   - se cumplen las restricciones en las 3 rondas y ningún nodo supera su presupuesto total de 18.
3. **Comparación con el óptimo exacto:** razón voraz/óptimo = 1,0 en las tres rondas. Con costos esto es una observación sobre esta instancia, no una garantía.
4. **Reproducibilidad:** ejecución desde otro directorio y con otra carpeta de salida produjo la misma traza.

## 12. Limitaciones y trabajo futuro
| Limitación | Consecuencia | Etapa donde se aborda |
|---|---|---|
| u_i y f son una elección propia (sección 4) | Los valores numéricos dependen de ella; la corrección del algoritmo no | Confirmar con la profesora |
| Con costos distintos no hay garantía (1 − 1/e) | La razón al óptimo es solo referencial; se necesita el voraz con mejor elemento individual o enumeración de tripletes | Algoritmo aproximado (semanas 7-8) |
| Sin fallos de nodos | No se modela la variante de rondas con fallos | Variantes |
| El reparto ignora las externalidades de red | Con utilidades dependientes de vecinos, el voraz del reparto puede dejar de ser óptimo | Variantes |
| Selección O(k·N²) por evaluar f de forma explícita | La T(n) experimental debe compararse con esta, no con O(N·k) | Experimentación (semanas 9-10) |
| Fuerza bruta solo para N pequeño | No sirve como referencia con instancias grandes | Algoritmo exacto (semanas 5-6) |
| Selección miope entre rondas | No se planifica el uso del presupuesto P_i a lo largo de las T rondas: el voraz elige igual todas las rondas | Variantes |
| Validación de entrada mínima | Un JSON mal formado produce una excepción de Python | — |
| Una sola medición de tiempo | Es válida como evidencia de ejecución, pero es ruidosa | Experimentación |

## 13. Referencias
- B. McMahan, E. Moore, D. Ramage, S. Hampson y B. Agüera y Arcas. *Communication-Efficient Learning of Deep Networks from Decentralized Data.* AISTATS, 2017.
- C. Dwork y A. Roth. *The Algorithmic Foundations of Differential Privacy.* Foundations and Trends in Theoretical Computer Science 9(3–4), 2014.
- T. Ibaraki y N. Katoh. *Resource Allocation Problems: Algorithmic Approaches.* MIT Press, 1988.
- G. L. Nemhauser, L. A. Wolsey y M. L. Fisher. *An analysis of approximations for maximizing submodular set functions — I.* Mathematical Programming 14, 1978.
- U. Feige. *A threshold of ln n for approximating set cover.* Journal of the ACM 45(4), 1998.
- S. Khuller, A. Moss y J. Naor. *The budgeted maximum coverage problem.* Information Processing Letters 70(1), 1999.
- M. Sviridenko. *A note on maximizing a submodular set function subject to a knapsack constraint.* Operations Research Letters 32(1), 2004.
- R. M. Karp. *Reducibility among combinatorial problems.* En *Complexity of Computer Computations*, 1972.
- T. H. Cormen, C. E. Leiserson, R. L. Rivest y C. Stein. *Introduction to Algorithms* (montículos y algoritmos voraces).
