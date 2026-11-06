import itertools, json, math, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import red

RUTA = os.path.join(os.path.dirname(__file__), "..", "entrada_G2_red_15_nodos.json")


class T(unittest.TestCase):
    def setUp(self):
        self.inst = red.Instancia(json.load(open(RUTA)))

    def test_reparto_optimo_vs_fuerza_bruta(self):
        inst, S, B = self.inst, [0, 3, 9], 8
        x, _ = red.reparto_voraz(inst, S, B, [99] * inst.N)
        v = sum(inst.utilidad_nodo(i, x[i]) for i in S)
        mejor = max(sum(inst.utilidad_nodo(i, c) for i, c in zip(S, comb))
                    for comb in itertools.product(range(B + 1), repeat=3) if sum(comb) == B)
        self.assertAlmostEqual(v, mejor)

    def test_submodular_monotona(self):
        inst = self.inst
        A, Bs, i = [0], [0, 1, 2], 5
        self.assertGreaterEqual(inst.f(A + [i]) - inst.f(A), inst.f(Bs + [i]) - inst.f(Bs))
        self.assertGreaterEqual(inst.f(Bs), inst.f(A))

    def test_restricciones_y_cota(self):
        rondas, _ = red.resolver(self.inst)
        for r in rondas:
            self.assertTrue(all(r["verificacion"].values()), r["verificacion"])
        tot = {}
        for r in rondas:
            for n, v in r["reparto"].items():
                tot[n] = tot.get(n, 0) + v
        self.assertTrue(all(v <= 18 for v in tot.values()))


if __name__ == "__main__":
    unittest.main()
