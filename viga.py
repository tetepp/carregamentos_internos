import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


class Viga:

    def __init__(self, comprimento):

        self.L = comprimento

        self.reacoes = []
        self.cargas_pontuais = []
        self.cargas_distribuidas = []
        self.momentos = []

    # =====================================================
    # REAÇÕES
    # =====================================================

    def adicionar_reacao(self, posicao, valor):

        self.reacoes.append({
            "pos": posicao,
            "valor": valor
        })

    # =====================================================
    # CARGAS PONTUAIS
    # =====================================================

    def adicionar_carga_pontual(self, posicao, valor):

        self.cargas_pontuais.append({
            "pos": posicao,
            "valor": valor
        })

    # =====================================================
    # DISTRIBUÍDA CONSTANTE
    # =====================================================

    def adicionar_carga_distribuida_constante(
        self,
        intensidade,
        inicio,
        fim
    ):

        self.cargas_distribuidas.append({
            "tipo": "constante",
            "q": intensidade,
            "inicio": inicio,
            "fim": fim
        })

    # =====================================================
    # DISTRIBUÍDA LINEAR
    # =====================================================

    def adicionar_carga_distribuida_linear(
        self,
        q_inicial,
        q_final,
        inicio,
        fim
    ):

        self.cargas_distribuidas.append({
            "tipo": "linear",
            "q_inicial": q_inicial,
            "q_final": q_final,
            "inicio": inicio,
            "fim": fim
        })

    # =====================================================
    # MOMENTO CONCENTRADO
    # =====================================================

    def adicionar_momento(
        self,
        posicao,
        valor
    ):

        self.momentos.append({
            "pos": posicao,
            "valor": valor
        })

    # =====================================================
    # CÁLCULO
    # =====================================================

    def calcular(self, dx=0.01):

        xs = np.arange(0, self.L + dx, dx)

        cortante = []
        momento = []

        # =================================================
        # FORÇA CORTANTE
        # =================================================

        for x in xs:

            v = 0

            # REAÇÕES
            for r in self.reacoes:

                if x >= r["pos"]:
                    v += r["valor"]

            # CARGAS PONTUAIS
            for p in self.cargas_pontuais:

                if x >= p["pos"]:
                    v += p["valor"]

            # DISTRIBUÍDAS
            for c in self.cargas_distribuidas:

                # -----------------------------------------
                # CONSTANTE
                # -----------------------------------------

                if c["tipo"] == "constante":

                    if x > c["inicio"]:

                        limite = min(x, c["fim"])

                        comprimento = limite - c["inicio"]

                        if comprimento > 0:

                            v += c["q"] * comprimento

                # -----------------------------------------
                # LINEAR
                # -----------------------------------------

                elif c["tipo"] == "linear":

                    if x > c["inicio"]:

                        limite = min(x, c["fim"])

                        s = limite - c["inicio"]

                        if s > 0:

                            L_total = c["fim"] - c["inicio"]

                            t = s / L_total

                            q_s = (
                                c["q_inicial"] +
                                t * (c["q_final"] - c["q_inicial"])
                            )

                            area = s * (c["q_inicial"] + q_s) / 2

                            v += area

            cortante.append(v)

        # =================================================
        # MOMENTO FLETOR
        # =================================================

        momento.append(0)

        for i in range(1, len(xs)):

            m = momento[i - 1] + cortante[i] * dx

            x0 = xs[i - 1]
            x1 = xs[i]

            for mc in self.momentos:

                if x0 < mc["pos"] <= x1:
                    m += mc["valor"]

            momento.append(m)

        resultado = {

            "x": xs.tolist(),

            "forca_cortante": cortante,

            "momento_fletor": momento,

            "forca_cortante_max": max(cortante),

            "forca_cortante_min": min(cortante),

            "momento_fletor_max": max(momento),

            "momento_fletor_min": min(momento)
        }

        return resultado


# =========================================================
# API FLASK
# =========================================================

@app.route("/calcular", methods=["POST"])
def calcular():

    dados = request.get_json()

    viga = Viga(dados["comprimento"])

    for r in dados.get("reacoes", []):
        viga.adicionar_reacao(r["pos"], r["valor"])

    for p in dados.get("cargas_pontuais", []):
        viga.adicionar_carga_pontual(p["pos"], p["valor"])

    for c in dados.get("cargas_distribuidas", []):

        if c["tipo"] == "constante":
            viga.adicionar_carga_distribuida_constante(
                c["q"], c["inicio"], c["fim"]
            )

        elif c["tipo"] == "linear":
            viga.adicionar_carga_distribuida_linear(
                c["q_inicial"], c["q_final"],
                c["inicio"], c["fim"]
            )

    for m in dados.get("momentos", []):
        viga.adicionar_momento(m["pos"], m["valor"])

    resultado = viga.calcular(dx=0.01)

    return jsonify(resultado)


# =========================================================
# FUNÇÃO PARA IMPRIMIR RESULTADOS
# =========================================================

def imprimir_resultados(resultado):

    print("\n==============================")
    print("RESULTADOS")
    print("==============================")

    print("\nFORÇA CORTANTE")

    print(
        f"Máximo: "
        f"{resultado['forca_cortante_max']:.2f}"
    )

    print(
        f"Mínimo: "
        f"{resultado['forca_cortante_min']:.2f}"
    )

    print("\nMOMENTO FLETOR")

    print(
        f"Máximo: "
        f"{resultado['momento_fletor_max']:.2f}"
    )

    print(
        f"Mínimo: "
        f"{resultado['momento_fletor_min']:.2f}"
    )


# =========================================================
# INICIALIZAÇÃO
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)
