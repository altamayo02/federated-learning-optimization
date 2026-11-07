"""Solución base: Proyecto Red (G2): selección de participantes + reparto de presupuesto.

Modelo (ver doc/Manual_tecnico.md, sección "Decisiones de modelado"):
	* u_i(x)  = a_i * ln(1 + x)            (creciente, cóncava, u_i(0)=0)
	* f(S)    = sum_j a_j * (1 - prod_{i in S} (1 - w_ij)),  con w_jj = 1
							(cobertura probabilística ponderada: monótona y submodular)
	* Restricciones por ronda: |S| <= k, sum c_i <= C, sum x_i <= B,
		y por nodo: sum_t x_i^t <= P_i.
Solo biblioteca estándar.
"""
import argparse
import heapq
import itertools
import json
import math
import os
import time
from datetime import datetime, UTC


# ----------------------------------------------------------------- modelo
class Instancia:
		def __init__(self, datos):
				p = datos["parametros"]
				self.N = p["numero_nodos"]
				self.T = p["numero_rondas"]
				self.k = p["cupo_participantes_por_ronda_k"]
				self.B = p["presupuesto_ruido_por_ronda_B"]
				self.C = p["presupuesto_costos_participacion_por_ronda"]
				self.ids = [n["id"] for n in datos["nodos"]]
				idx = {s: i for i, s in enumerate(self.ids)}
				self.a = [n["coeficiente_utilidad"] for n in datos["nodos"]]
				self.P = [n["presupuesto_total_nodo"] for n in datos["nodos"]]
				self.c = [n["costo_participacion"] for n in datos["nodos"]]
				self.w = [[0.0] * self.N for _ in range(self.N)]
				for e in datos["grafo"]:
						i, j = idx[e["u"]], idx[e["v"]]
						self.w[i][j] = self.w[j][i] = e["peso_influencia"]
				for i in range(self.N):
						self.w[i][i] = 1.0  # un nodo seleccionado se cubre a sí mismo
				if len(self.ids) != self.N:
						raise ValueError("numero_nodos no coincide con la lista de nodos")

		def ganancia_unidad(self, i, x):
				"""Δ_i(x+1) = u_i(x+1) - u_i(x)."""
				return self.a[i] * math.log1p(1.0 / (x + 1))

		def utilidad_nodo(self, i, x):
				return self.a[i] * math.log1p(x)

		def f(self, S):
				tot = 0.0
				for j in range(self.N):
						miss = 1.0
						for i in S:
								miss *= 1.0 - self.w[i][j]
						tot += self.a[j] * (1.0 - miss)
				return tot


# --------------------------------------------------------- Parte 2: selección
def _marginal(inst, miss, i):
		return sum(inst.a[j] * miss[j] * inst.w[i][j] for j in range(inst.N))


def seleccion_voraz(inst, elegibles, modo="ganancia"):
		"""Voraz con cupo k y presupuesto de costos C. modo: 'ganancia' o 'razon'
		(ganancia marginal / costo). Devuelve (S, traza)."""
		miss = [1.0] * inst.N
		S, costo, traza = [], 0, []
		while len(S) < inst.k:
				cand = []
				for i in elegibles:
						if i in S or costo + inst.c[i] > inst.C:
								continue
						g = _marginal(inst, miss, i)
						cand.append((g if modo == "ganancia" else g / inst.c[i], g, i))
				if not cand:
						break
				# máximo; desempate por menor índice
				_, g, i = max(cand, key=lambda t: (t[0], -t[2]))
				traza.append({
						"paso": len(S) + 1, "elegido": inst.ids[i], "ganancia_marginal": g,
						"costo": inst.c[i],
						"candidatos": {inst.ids[t[2]]: round(t[1], 6) for t in cand}})
				S.append(i)
				costo += inst.c[i]
				for j in range(inst.N):
						miss[j] *= 1.0 - inst.w[i][j]
		return S, traza


def seleccion_exacta(inst, elegibles, limite=300_000):
		"""Fuerza bruta (solo para verificar la cota en instancias pequeñas)."""
		total = sum(math.comb(len(elegibles), r) for r in range(inst.k + 1))
		if total > limite:
				return None
		mejor, mejorS = -1.0, []
		for r in range(inst.k + 1):
				for S in itertools.combinations(elegibles, r):
						if sum(inst.c[i] for i in S) <= inst.C:
								v = inst.f(S)
								if v > mejor:
										mejor, mejorS = v, list(S)
		return mejorS, mejor


# ------------------------------------------------- Parte 1: reparto voraz
def reparto_voraz(inst, S, B, restante):
		"""Asigna B unidades, de a una, al nodo de S con mayor ganancia marginal
		(montículo). Respeta el tope restante[i]. Devuelve (x, traza)."""
		x = {i: 0 for i in S}
		heap = [(-inst.ganancia_unidad(i, 0), i) for i in S if restante[i] > 0]
		heapq.heapify(heap)
		traza = []
		for u in range(B):
				if not heap:
						break
				g, i = heapq.heappop(heap)
				x[i] += 1
				traza.append({"unidad": u + 1, "nodo": inst.ids[i], "ganancia_marginal": -g})
				if x[i] < restante[i]:
						heapq.heappush(heap, (-inst.ganancia_unidad(i, x[i]), i))
		return x, traza


# ------------------------------------------------------------- orquestación
def resolver(inst, verificar_exacto=True):
		"""Resuelve las T rondas. Devuelve (rondas, utilidad_total, segundos del
		algoritmo), sin contar la fuerza bruta de verificación."""
		restante = list(inst.P)
		rondas, util_total, seg = [], 0.0, 0.0
		for t in range(1, inst.T + 1):
				eleg = [i for i in range(inst.N) if restante[i] > 0]
				t0 = time.perf_counter()
				# el mejor entre voraz por ganancia y voraz por razón ganancia/costo
				resultados = []
				for modo in ("ganancia", "razon"):
						S, tr = seleccion_voraz(inst, eleg, modo)
						resultados.append((inst.f(S), modo, S, tr))
				fS, modo, S, trS = max(resultados, key=lambda r: r[0])
				x, trX = reparto_voraz(inst, S, inst.B, restante)
				seg += time.perf_counter() - t0
				for i, v in x.items():
						restante[i] -= v
				u = sum(inst.utilidad_nodo(i, v) for i, v in x.items())
				ronda = {
						"ronda": t, "modo_seleccion": modo,
						"f_por_modo": {r[1]: r[0] for r in resultados},
						"seleccion": [inst.ids[i] for i in S], "f_S": fS,
						"traza_seleccion": trS,
						"reparto": {inst.ids[i]: v for i, v in x.items()},
						"utilidad_reparto": u, "traza_reparto": trX,
						"presupuesto_restante_por_nodo": {inst.ids[i]: restante[i] for i in range(inst.N)},
				}
				if verificar_exacto:
						ex = seleccion_exacta(inst, eleg)
						if ex:
								ronda["exacto"] = {"seleccion": [inst.ids[i] for i in ex[0]], "f": ex[1],
																	"razon_voraz_sobre_optimo": fS / ex[1] if ex[1] else 1.0,
																	"cota_1_menos_1_sobre_e": 1 - 1 / math.e}
				ronda["verificacion"] = verificar(inst, ronda, S, x, restante)
				util_total += fS + u
				rondas.append(ronda)
		return rondas, util_total, seg


def verificar(inst, ronda, S, x, restante):
		gastado = sum(x.values())
		v = {
				f"|S| <= k ({len(S)} <= {inst.k})": len(S) <= inst.k,
				f"sum c_i <= C ({sum(inst.c[i] for i in S)} <= {inst.C})": sum(inst.c[i] for i in S) <= inst.C,
				f"sum x_i <= B ({gastado} <= {inst.B})": gastado <= inst.B,
				"x_i <= presupuesto restante del nodo": all(r >= 0 for r in restante),
		}
		if "exacto" in ronda:
				v["f(S_voraz) >= (1-1/e) f(S_opt) (referencial: con costos la cota no aplica)"] = (
						ronda["exacto"]["razon_voraz_sobre_optimo"] >= ronda["exacto"]["cota_1_menos_1_sobre_e"])
		return v


# ------------------------------------------------------------------- salida
def texto(nombre, rondas, util, seg):
		L = [f"=== Caso: {nombre} | tiempo: {seg:.6f} s | utilidad total: {util:.6f} ==="]
		for r in rondas:
				L += [f"\n-- Ronda {r['ronda']} (selección: voraz por '{r['modo_seleccion']}') --",
							f"Nodos: {', '.join(r['seleccion'])}   f(S)={r['f_S']:.4f}"]
				for p in r["traza_seleccion"]:
						L.append(f"  paso {p['paso']}: +{p['elegido']} ganancia={p['ganancia_marginal']:.4f} costo={p['costo']}")
				L.append("Reparto: " + ", ".join(f"{k}={v}" for k, v in r["reparto"].items())
						+ f"   utilidad={r['utilidad_reparto']:.4f}")
				L.append("  orden de unidades: " + " ".join(p["nodo"] for p in r["traza_reparto"]))
				if "exacto" in r:
						e = r["exacto"]
						L.append(f"Óptimo exacto f*={e['f']:.4f} ({', '.join(e['seleccion'])}); razón voraz/óptimo={e['razon_voraz_sobre_optimo']:.4f}")
				for k, ok in r["verificacion"].items():
						L.append(f"  [{'OK' if ok else 'FALLA'}] {k}")
		return "\n".join(L) + "\n"


def main():
		ap = argparse.ArgumentParser(description="Solución base G2 · Red")
		ap.add_argument("entrada", nargs="+", help="archivo(s) JSON de casos")
		ap.add_argument("-o", "--salida", default="data")
		ap.add_argument("--sin-exacto", action="store_true", help="omite la fuerza bruta de verificación")
		a = ap.parse_args()
		os.makedirs(a.salida, exist_ok=True)
		for ruta in a.entrada:
				nombre = os.path.splitext(os.path.basename(ruta))[0]
				with open(ruta, encoding="utf-8") as fh:
						inst = Instancia(json.load(fh))
				rondas, util, seg = resolver(inst, verificar_exacto=not a.sin_exacto)
				with open(
					a.salida + "/results/" + f"{nombre}.json",
					"w",
					encoding="utf-8"
				) as fh:
						json.dump({
							"caso": nombre,
							"tiempo_segundos": seg,
							"utilidad_total": util,
							"rondas": rondas
						}, fh, indent=2, ensure_ascii=False)
				txt = texto(nombre, rondas, util, seg)
				tstamp = datetime.now(UTC).strftime("%Y-%m-%d-%H-%M-%S")
				with open(
					a.salida + "/trace/" + f"{nombre}_{tstamp}.txt",
					"w",
					encoding="utf-8"
				) as fh:
						fh.write(txt)
				print(txt)


if __name__ == "__main__":
		main()
