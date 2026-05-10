def validar_posicao(valor, L, nome):

    if 0 <= valor <= L:
        return True

    print(f"Erro: {nome} deve estar entre 0 e {L}.")
    return False

# ==========================================================
# CARGAS CONCENTRADAS
# ==========================================================

def adicionar_carga(L):

    print("\n--- NOVA CARGA CONCENTRADA ---")

    while True:

        try:

            direcao = int(
                input("Direção: (1) Para cima (2) Para baixo: ")
            )

            if direcao in (1, 2):
                break

        except:
            pass

        print("Valor inválido!")

    while True:

        try:

            P = float(input("Intensidade (N): "))

            if P > 0:
                break

        except:
            pass

        print("Valor inválido!")

    while True:

        try:

            x = float(input(f"Posição (m) [0 a {L}]: "))

            if validar_posicao(x, L, "Carga"):
                break

        except:
            pass

        print("Valor inválido!")

    return (P, x, direcao)


# ==========================================================
# MOMENTOS CONCENTRADOS
# ==========================================================

def adicionar_momento(L):

    print("\n--- NOVO MOMENTO CONCENTRADO ---")

    while True:

        try:

            sentido = int(
                input("Sentido: (1) Horário (-) (2) Anti-horário (+): ")
            )

            if sentido in (1, 2):
                break

        except:
            pass

        print("Valor inválido!")

    while True:

        try:

            M = float(input("Intensidade (N.m): "))

            if M > 0:
                break

        except:
            pass

        print("Valor inválido!")

    while True:

        try:

            x = float(input(f"Posição (m) [0 a {L}]: "))

            if validar_posicao(x, L, "Momento"):
                break

        except:
            pass

        print("Valor inválido!")

    return (M, x, sentido)


# ==========================================================
# REAÇÕES - PINO E ROLETE
# ==========================================================

def calcular_reacoes_pino_rolete(
    x_pino,
    x_rolete,
    cargas,
    momentos
):

    d = x_rolete - x_pino

    if abs(d) < 1e-9:
        raise ValueError("Pino e rolete coincidem.")

    soma_F = 0.0

    for P, x, direcao in cargas:

        if direcao == 1:
            soma_F += P
        else:
            soma_F -= P

    soma_M = 0.0

    # Cargas
    for P, x, direcao in cargas:

        if direcao == 1:
            soma_M -= P * (x - x_pino)

        else:
            soma_M += P * (x - x_pino)

    # Momentos externos
    for M, x_m, sentido in momentos:

        if sentido == 1:      # horário
            soma_M += M

        else:                 # anti-horário
            soma_M -= M

    RB = soma_M / d

    RA = -soma_F - RB

    return RA, 0.0, RB


# ==========================================================
# REAÇÕES - ENGASTE
# ==========================================================

def calcular_reacoes_engaste(
    cargas,
    momentos,
    x_eng
):

    soma_F = 0.0

    for P, x, direcao in cargas:

        if direcao == 1:
            soma_F += P
        else:
            soma_F -= P

    Ry = -soma_F

    soma_M = 0.0

    for P, x, direcao in cargas:

        if direcao == 1:
            soma_M -= P * (x - x_eng)

        else:
            soma_M += P * (x - x_eng)

    for M, x_m, sentido in momentos:

        if sentido == 1:
            soma_M -= M
        else:
            soma_M += M

    M_eng = -soma_M

    return Ry, 0.0, M_eng


# ==========================================================
# ESFORÇOS INTERNOS
# ==========================================================

def calcular_esforcos(
    x,
    cargas,
    momentos,
    reacoes,
    tipo,
    x_pino=None,
    x_rolete=None,
    x_eng=None
):

    V = 0.0
    M = 0.0

    eventos = []

    # ======================================================
    # REAÇÕES
    # ======================================================

    if tipo == '1':

        if x_pino <= x:
            eventos.append((x_pino, 'forca', reacoes['RA']))

        if x_rolete <= x:
            eventos.append((x_rolete, 'forca', reacoes['RB']))

    else:

        if x_eng <= x:

            eventos.append((x_eng, 'forca', reacoes['Ry']))
            eventos.append((x_eng, 'momento', reacoes['M']))

    # ======================================================
    # CARGAS
    # ======================================================

    for P, x_carga, direcao in cargas:

        if x_carga <= x:

            if direcao == 1:
                deltaV = +P
            else:
                deltaV = -P

            eventos.append((x_carga, 'forca', deltaV))

    # ======================================================
    # MOMENTOS
    # ======================================================

    for M_ext, x_m, sentido in momentos:

        if x_m <= x:

            if sentido == 1:
                deltaM = +M_ext
            else:
                deltaM = -M_ext

            eventos.append((x_m, 'momento', deltaM))

    eventos.sort(key=lambda e: e[0])

    x_anterior = 0.0

    for pos, tipo_evento, valor in eventos:

        dx = pos - x_anterior

        M += V * dx

        if tipo_evento == 'forca':
            V += valor

        elif tipo_evento == 'momento':
            M += valor

        x_anterior = pos

    dx_final = x - x_anterior

    M += V * dx_final

    return V, M, 0.0


def main():

    print("=" * 50)
    print("ANÁLISE DE VIGAS ISOSTÁTICAS")
    print("=" * 50)

    # ======================================================
    # COMPRIMENTO
    # ======================================================

    while True:

        try:

            L = float(input("\nComprimento da viga (m): "))

            if L > 0:
                break

        except:
            pass

        print("Valor inválido!")

    # ======================================================
    # APOIO
    # ======================================================

    print("\nTipo de apoio:")
    print("1 - Pino e Rolete")
    print("2 - Engaste")

    while True:

        tipo = input("Escolha: ").strip()

        if tipo in ('1', '2'):
            break

        print("Valor inválido!")

    # ======================================================
    # PINO E ROLETE
    # ======================================================

    if tipo == '1':

        while True:

            try:

                x_pino = float(input("\nPosição do PINO: "))

                if validar_posicao(x_pino, L, "Pino"):
                    break

            except:
                pass

            print("Valor inválido!")

        while True:

            try:

                x_rolete = float(input("Posição do ROLETE: "))

                if validar_posicao(x_rolete, L, "Rolete"):
                    break

            except:
                pass

            print("Valor inválido!")

        while x_pino == x_rolete:

            print("\nErro: Pino e rolete não podem estar na mesma posição!")

            while True:

                try:

                    x_pino = float(input("\nPosição do PINO: "))

                    if validar_posicao(x_pino, L, "Pino"):
                        break

                except:
                    pass

                print("Valor inválido!")

            while True:

                try:

                    x_rolete = float(input("Posição do ROLETE: "))

                    if validar_posicao(x_rolete, L, "Rolete"):
                        break

                except:
                    pass

                print("Valor inválido!")

    # ======================================================
    # ENGASTE
    # ======================================================

    else:

        while True:

            try:

                x_eng = float(input("\nPosição do ENGASTE: "))

                if validar_posicao(x_eng, L, "Engaste"):
                    break

            except:
                pass

            print("Valor inválido!")

    # ======================================================
    # CARGAS
    # ======================================================

    cargas = []

    while True:

        print("\nAdicionar carga concentrada?")
        print("(1) Sim")
        print("(2) Não")

        op = input("Escolha: ").strip()

        if op == '1':
            cargas.append(adicionar_carga(L))

        elif op == '2':
            break

    # ======================================================
    # MOMENTOS
    # ======================================================

    momentos = []

    while True:

        print("\nAdicionar momento concentrado?")
        print("(1) Sim")
        print("(2) Não")

        op = input("Escolha: ").strip()

        if op == '1':
            momentos.append(adicionar_momento(L))

        elif op == '2':
            break

    # ======================================================
    # REAÇÕES
    # ======================================================

    if tipo == '1':

        RA, RAh, RB = calcular_reacoes_pino_rolete(
            x_pino,
            x_rolete,
            cargas,
            momentos
        )

        print("\n" + "=" * 40)
        print("REAÇÕES")
        print("=" * 40)

        print(f"\nPINO x={x_pino:.2f}")
        print(f"Vertical: {RA:+.2f} N")

        print(f"\nROLETE x={x_rolete:.2f}")
        print(f"Vertical: {RB:+.2f} N")

        reacoes = {
            'RA': RA,
            'RB': RB
        }

    else:

        Ry, Rx, M_eng = calcular_reacoes_engaste(
            cargas,
            momentos,
            x_eng
        )

        print("\n" + "=" * 40)
        print("REAÇÕES")
        print("=" * 40)

        print(f"\nENGASTE x={x_eng:.2f}")

        print(f"Vertical: {Ry:+.2f} N")
        print(f"Momento: {M_eng:+.2f} N.m")

        reacoes = {
            'Ry': Ry,
            'M': M_eng
        }

    # ======================================================
    # ESFORÇOS INTERNOS
    # ======================================================

    while True:

        print("\n" + "-" * 40)
        print("ESFORÇOS INTERNOS")
        print("1 - Calcular em um ponto")
        print("4 - Sair")

        op = input("Escolha: ").strip()

        if op == '4':
            break

        if op == '1':

            while True:

                try:

                    x = float(input("Posição x (m): "))

                    if 0 <= x <= L:
                        break

                except:
                    pass

                print("Valor inválido!")

            if tipo == '1':

                V, M, N = calcular_esforcos(
                    x,
                    cargas,
                    momentos,
                    reacoes,
                    tipo,
                    x_pino=x_pino,
                    x_rolete=x_rolete
                )

            else:

                V, M, N = calcular_esforcos(
                    x,
                    cargas,
                    momentos,
                    reacoes,
                    tipo,
                    x_eng=x_eng
                )

            print(f"\nResultados em x={x:.3f} m")

            print(f"Cortante: {V:+.2f} N")
            print(f"Momento:  {M:+.2f} N.m")
            print(f"Normal:   {N:+.2f} N")

    print("\n" + "=" * 50)
    print("FIM DA ANÁLISE")
    print("=" * 50)


if __name__ == "__main__":
    main()