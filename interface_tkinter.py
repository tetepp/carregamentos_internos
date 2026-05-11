import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import traceback

def parse_float(val_str):
    """Trata a entrada do utilizador permitindo o uso de vírgula decimal."""
    try:
        return float(str(val_str).replace(',', '.'))
    except ValueError:
        raise ValueError("Formato numérico inválido.")

def clean_zero(val):
    """Evita a exibição de '-0.00' por imprecisão de ponto flutuante."""
    return 0.0 if abs(val) < 1e-9 else val

# ==========================================================
# 1. MOTOR FÍSICO (Back-end e Cálculo Numérico)
# ==========================================================
class VigaEngine:
    def __init__(self, comprimento):
        self.L = comprimento
        self.cargas_pontuais = []
        self.cargas_distribuidas = []
        self.momentos = []
        self.reacoes_calculadas = []

    def adicionar_carga_pontual(self, pos, valor):
        self.cargas_pontuais.append({"pos": pos, "valor": valor})

    def adicionar_carga_distribuida(self, q_ini, q_fim, inicio, fim):
        self.cargas_distribuidas.append({"q_inicial": q_ini, "q_final": q_fim, "inicio": inicio, "fim": fim})

    def adicionar_momento(self, pos, valor):
        self.momentos.append({"pos": pos, "valor": valor})

    def calcular_reacoes(self, tipo_apoio, x_a, x_b=None):
        soma_Fy = 0.0
        soma_M_A = 0.0

        for p in self.cargas_pontuais:
            soma_Fy += p["valor"]
            soma_M_A += p["valor"] * (p["pos"] - x_a)

        for c in self.cargas_distribuidas:
            L_c = c["fim"] - c["inicio"]
            if L_c <= 0: continue
            
            F_ret = c["q_inicial"] * L_c
            x_ret = c["inicio"] + L_c / 2.0
            
            F_tri = (c["q_final"] - c["q_inicial"]) * L_c / 2.0
            x_tri = c["inicio"] + (2.0 / 3.0) * L_c

            F_eq = F_ret + F_tri
            if abs(F_eq) > 1e-9:
                x_eq = (F_ret * x_ret + F_tri * x_tri) / F_eq
                soma_Fy += F_eq
                soma_M_A += F_eq * (x_eq - x_a)

        for m in self.momentos:
            soma_M_A += m["valor"]

        self.reacoes_calculadas = []

        if tipo_apoio == 'engaste':
            Ry = -soma_Fy
            M_eng = -soma_M_A
            self.reacoes_calculadas.append({"tipo": "forca", "pos": x_a, "valor": clean_zero(Ry), "nome": "Ry"})
            self.reacoes_calculadas.append({"tipo": "momento", "pos": x_a, "valor": clean_zero(M_eng), "nome": "M_eng"})
        else:
            if abs(x_b - x_a) < 1e-6:
                raise ValueError("Atenção: Os apoios (Pino e Rolete) não podem coincidir na mesma posição física.")
            
            Rb = -soma_M_A / (x_b - x_a)
            Ra = -soma_Fy - Rb
            self.reacoes_calculadas.append({"tipo": "forca", "pos": x_a, "valor": clean_zero(Ra), "nome": "Ra"})
            self.reacoes_calculadas.append({"tipo": "forca", "pos": x_b, "valor": clean_zero(Rb), "nome": "Rb"})

    def _get_shear_at(self, x):
        v = 0.0
        for r in self.reacoes_calculadas:
            if x >= r["pos"] - 1e-9: v += r["valor"]
        for p in self.cargas_pontuais:
            if x >= p["pos"] - 1e-9: v += p["valor"]
        for c in self.cargas_distribuidas:
            if x > c["inicio"] + 1e-9:
                limite = min(x, c["fim"])
                s = limite - c["inicio"]
                if s > 0:
                    L_total = c["fim"] - c["inicio"]
                    t = s / L_total
                    q_s = c["q_inicial"] + t * (c["q_final"] - c["q_inicial"])
                    v += s * (c["q_inicial"] + q_s) / 2.0
        return v

    def calcular_esforcos(self, dx=0.01):
        pontos = [0.0, self.L]
        for p in self.cargas_pontuais: pontos.append(p["pos"])
        for m in self.momentos: pontos.append(m["pos"])
        for c in self.cargas_distribuidas: pontos.extend([c["inicio"], c["fim"]])
        for r in self.reacoes_calculadas: pontos.append(r["pos"])

        xs = np.arange(0, self.L + dx, dx)
        xs = np.concatenate((xs, pontos))
        xs = np.round(xs, decimals=5)
        xs = np.unique(xs)
        xs = xs[(xs >= 0) & (xs <= self.L)]

        cortante = np.zeros_like(xs)
        momento = np.zeros_like(xs)

        for i, x in enumerate(xs):
            cortante[i] = self._get_shear_at(x)

        m0 = 0.0
        for mc in self.momentos:
            if abs(mc["pos"]) < 1e-6: m0 -= mc["valor"]
        for r in self.reacoes_calculadas:
            if r["tipo"] == "momento" and abs(r["pos"]) < 1e-6: m0 -= r["valor"]
        momento[0] = m0

        for i in range(1, len(xs)):
            delta_x = xs[i] - xs[i - 1]
            x_mid = (xs[i - 1] + xs[i]) / 2.0
            
            v_mid = self._get_shear_at(x_mid)
            m = momento[i - 1] + (v_mid * delta_x)
            
            x0, x1 = xs[i - 1], xs[i]
            for mc in self.momentos:
                if x0 + 1e-6 < mc["pos"] <= x1 + 1e-6: m -= mc["valor"]
            for r in self.reacoes_calculadas:
                if r["tipo"] == "momento" and x0 + 1e-6 < r["pos"] <= x1 + 1e-6: m -= r["valor"]
            
            momento[i] = m

        return {
            "x": xs, "V": cortante, "M": momento,
            "V_max": clean_zero(np.max(cortante)), "V_min": clean_zero(np.min(cortante)),
            "M_max": clean_zero(np.max(momento)), "M_min": clean_zero(np.min(momento))
        }


# ==========================================================
# 2. MODAL DE CARREGAMENTOS (UI isolada)
# ==========================================================
class ModalNovaCarga(tk.Toplevel):
    def __init__(self, parent, theme, L_max, callback_salvar):
        super().__init__(parent)
        self.theme = theme
        self.L_max = L_max
        self.callback = callback_salvar

        self.title("Adicionar Nova Carga")
        self.geometry("450x380")
        self.configure(bg=self.theme["bg_panel"])

        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self._drag_data = {"x": 0, "y": 0}
        self.bind("<ButtonPress-1>", self._iniciar_arrasto)
        self.bind("<B1-Motion>", self._arrastar_janela)

        self._build_ui()
        self._centralizar_no_parent(parent)

    def _centralizar_no_parent(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def _iniciar_arrasto(self, event):
        if isinstance(event.widget, (ttk.Entry, ttk.Combobox, ttk.Button)): return
        self._drag_data["x"] = event.x_root
        self._drag_data["y"] = event.y_root

    def _arrastar_janela(self, event):
        if isinstance(event.widget, (ttk.Entry, ttk.Combobox, ttk.Button)): return
        deltax = event.x_root - self._drag_data["x"]
        deltay = event.y_root - self._drag_data["y"]
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")
        self._drag_data["x"] = event.x_root
        self._drag_data["y"] = event.y_root

    def _build_ui(self):
        f_main = ttk.Frame(self, padding=25, style="Panel.TFrame")
        f_main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f_main, text="Configuração de Carga", font=self.theme["font_title"], foreground=self.theme["primary"]).pack(anchor=tk.W, pady=(0, 15))
        ttk.Label(f_main, text="Selecione o tipo de carregamento:").pack(anchor=tk.W, pady=(0, 5))

        self.var_tipo = tk.StringVar(value="Pontual (Força)")
        cb = ttk.Combobox(f_main, textvariable=self.var_tipo,
                          values=["Pontual (Força)", "Momento Concentrado", "Distribuída Constante", "Distribuída Linear"],
                          state="readonly", font=self.theme["font_body"])
        cb.pack(fill=tk.X, pady=(0, 15))

        self.f_inputs = ttk.Frame(f_main, style="Panel.TFrame")
        self.f_inputs.pack(fill=tk.BOTH, expand=True)
        self.f_inputs.columnconfigure(1, weight=1)

        self.var_tipo.trace_add("write", self._atualizar_campos)
        cb.current(0)

        f_botoes = ttk.Frame(f_main, style="Panel.TFrame")
        f_botoes.pack(fill=tk.X, pady=(20, 0))

        btn_cancelar = ttk.Button(f_botoes, text="Cancelar", command=self.destroy)
        btn_cancelar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        btn_cancelar.config(cursor="hand2")

        btn_salvar = ttk.Button(f_botoes, text="✔ Confirmar", style="Acao.TButton", command=self._validar_e_salvar)
        btn_salvar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        btn_salvar.config(cursor="hand2")

    def _atualizar_campos(self, *args):
        for w in self.f_inputs.winfo_children(): w.destroy()

        tipo = self.var_tipo.get()
        if tipo in ["Pontual (Força)", "Momento Concentrado"]:
            lbl_u = "N" if tipo == "Pontual (Força)" else "N.m"
            instrucao = "[- p/ Baixo]" if tipo == "Pontual (Força)" else "[- p/ Horário]"

            ttk.Label(self.f_inputs, text=f"Intensidade ({lbl_u})\n{instrucao}:", justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W, pady=8)
            ent_val = ttk.Entry(self.f_inputs, justify="center", font=self.theme["font_body"])
            ent_val.grid(row=0, column=1, sticky="ew", pady=8, padx=(10, 0))

            ttk.Label(self.f_inputs, text="Posição x [m]:").grid(row=1, column=0, sticky=tk.W, pady=8)
            ent_pos = ttk.Entry(self.f_inputs, justify="center", font=self.theme["font_body"])
            ent_pos.grid(row=1, column=1, sticky="ew", pady=8, padx=(10, 0))

            self.f_inputs.entries = {"val": ent_val, "pos": ent_pos}

        else:
            ttk.Label(self.f_inputs, text="Intens. Início [N/m]\n[- p/ Baixo]:", justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W, pady=5)
            ent_qi = ttk.Entry(self.f_inputs, justify="center", font=self.theme["font_body"])
            ent_qi.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))

            ent_qf = None
            if tipo == "Distribuída Linear":
                ttk.Label(self.f_inputs, text="Intens. Final [N/m]:").grid(row=1, column=0, sticky=tk.W, pady=5)
                ent_qf = ttk.Entry(self.f_inputs, justify="center", font=self.theme["font_body"])
                ent_qf.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))

            r_offset = 2 if tipo == "Distribuída Linear" else 1
            ttk.Label(self.f_inputs, text="Posição Inicial x [m]:").grid(row=r_offset, column=0, sticky=tk.W, pady=5)
            ent_xi = ttk.Entry(self.f_inputs, justify="center", font=self.theme["font_body"])
            ent_xi.grid(row=r_offset, column=1, sticky="ew", pady=5, padx=(10, 0))

            ttk.Label(self.f_inputs, text="Posição Final x [m]:").grid(row=r_offset + 1, column=0, sticky=tk.W, pady=5)
            ent_xf = ttk.Entry(self.f_inputs, justify="center", font=self.theme["font_body"])
            ent_xf.grid(row=r_offset + 1, column=1, sticky="ew", pady=5, padx=(10, 0))

            self.f_inputs.entries = {"qi": ent_qi, "qf": ent_qf, "xi": ent_xi, "xf": ent_xf}

    def _validar_e_salvar(self):
        tipo = self.var_tipo.get()
        try:
            dados = {"tipo_str": tipo}

            if tipo == "Pontual (Força)" or tipo == "Momento Concentrado":
                pos = parse_float(self.f_inputs.entries["pos"].get())
                if not (0 <= pos <= self.L_max): raise ValueError(f"Posição fora da viga (0 a {self.L_max} m)")
                dados.update({
                    "tipo": "pontual" if tipo == "Pontual (Força)" else "momento",
                    "val": parse_float(self.f_inputs.entries["val"].get()),
                    "pos": pos
                })
            else:
                qi = parse_float(self.f_inputs.entries["qi"].get())
                qf = parse_float(self.f_inputs.entries["qf"].get()) if tipo == "Distribuída Linear" else qi
                xi = parse_float(self.f_inputs.entries["xi"].get())
                xf = parse_float(self.f_inputs.entries["xf"].get())
                if not (0 <= xi < xf <= self.L_max): raise ValueError(f"Intervalo de x inválido (limites 0 a {self.L_max} m).")
                dados.update({"tipo": "distrib", "qi": qi, "qf": qf, "xi": xi, "xf": xf})

            self.callback(dados)
            self.destroy()
        except ValueError as e:
            msg = str(e) if "Posição" in str(e) or "Intervalo" in str(e) else "Insira apenas números (use vírgula ou ponto)."
            DialogoErro(self, "Dados Inválidos", msg)


# ==========================================================
# 3. RENDERIZADOR (Gráficos Turbinados)
# ==========================================================
class VigaRenderer:
    def __init__(self, fig, ax_viga, ax_v, ax_m, canvas):
        self.fig = fig
        self.ax_viga = ax_viga
        self.ax_v = ax_v
        self.ax_m = ax_m
        self.canvas = canvas
        self._configurar_eixos_base()

    def _configurar_eixos_base(self):
        """Remove bordas superiores e direitas para design mais limpo"""
        for ax in (self.ax_v, self.ax_m):
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

    def renderizar_empty_state(self):
        for ax in (self.ax_viga, self.ax_v, self.ax_m):
            ax.clear()
            ax.axis('off')
        self.ax_viga.text(0.5, 0.5, "Configure a geometria e adicione as cargas\npara visualizar os diagramas da viga.", 
                          ha='center', va='center', fontsize=12, color='#7f8c8d', style='italic')
        self.canvas.draw()

    def renderizar_esquema(self, L, tipo_apoio, xa, xb, cargas):
        self.ax_viga.clear()
        self.ax_viga.set_title("Diagrama de Corpo Livre", fontweight='bold', color="#2c3e50")
        self.ax_viga.set_xlim(-0.5, L + 0.5)
        self.ax_viga.set_ylim(-2.5, 2.5)
        self.ax_viga.axis('off')

        self.ax_viga.plot([0, L], [0, 0], color='#34495e', linewidth=8, zorder=2)

        # APOIOS
        if tipo_apoio == 'engaste':
            rect = patches.Rectangle((xa - 0.2, -0.6), 0.4, 1.2, linewidth=1, edgecolor='black', facecolor='#95a5a6', hatch='///')
            self.ax_viga.add_patch(rect)
        else:
            pino = patches.Polygon([[xa, 0], [xa - 0.2, -0.4], [xa + 0.2, -0.4]], closed=True, color='#2980b9', zorder=3)
            self.ax_viga.add_patch(pino)
            self.ax_viga.plot([xa - 0.3, xa + 0.3], [-0.4, -0.4], 'k-', lw=2)
            rolete = patches.Polygon([[xb, 0], [xb - 0.2, -0.3], [xb + 0.2, -0.3]], closed=True, color='#2980b9', zorder=3)
            self.ax_viga.add_patch(rolete)
            self.ax_viga.plot([xb - 0.2, xb + 0.2], [-0.4, -0.4], 'k-', lw=2)
            self.ax_viga.plot(xb - 0.1, -0.35, 'ko', markersize=4)
            self.ax_viga.plot(xb + 0.1, -0.35, 'ko', markersize=4)

        # CARGAS
        for c in cargas:
            if c["tipo"] == "pontual":
                cor = '#e74c3c' if c["val"] < 0 else '#27ae60'
                y_text = 1.5 if c["val"] < 0 else -1.5
                self.ax_viga.annotate('', xy=(c["pos"], 0), xytext=(c["pos"], y_text),
                                      arrowprops=dict(facecolor=cor, edgecolor=cor, width=2.5, headwidth=9), zorder=4)
                self.ax_viga.text(c["pos"], y_text + (0.2 if c["val"] < 0 else -0.4),
                                  f"{abs(c['val']):.1f} N", ha='center', fontweight='bold', color=cor)

            elif c["tipo"] == "momento":
                marker = r'$\circlearrowleft$' if c["val"] > 0 else r'$\circlearrowright$'
                self.ax_viga.plot(c["pos"], 0.8, marker=marker, markersize=22, color='#f39c12')
                self.ax_viga.text(c["pos"], 1.4, f"{abs(c['val']):.1f} Nm", ha='center', color='#d35400', fontweight='bold')

            elif c["tipo"] == "distrib":
                is_downward = (c["qi"] + c["qf"]) <= 0
                max_q = max(abs(c["qi"]), abs(c["qf"]))
                max_q = max_q if max_q != 0 else 1
                
                sign_y = 1 if is_downward else -1
                y_i = sign_y * (abs(c["qi"]) / max_q) * 1.2
                y_f = sign_y * (abs(c["qf"]) / max_q) * 1.2

                cor_poligono = '#e74c3c' if is_downward else '#27ae60'
                poly = patches.Polygon([[c["xi"], 0], [c["xi"], y_i], [c["xf"], y_f], [c["xf"], 0]],
                                       closed=True, color=cor_poligono, alpha=0.15, zorder=1)
                self.ax_viga.add_patch(poly)

                n_arrows = max(3, int((c["xf"] - c["xi"]) * 2))
                for x_seta in np.linspace(c["xi"], c["xf"], n_arrows):
                    t = (x_seta - c["xi"]) / (c["xf"] - c["xi"]) if c["xf"] != c["xi"] else 0
                    y_seta = y_i + t * (y_f - y_i)
                    self.ax_viga.annotate('', xy=(x_seta, 0), xytext=(x_seta, y_seta),
                                          arrowprops=dict(arrowstyle="->", color=cor_poligono, alpha=0.8, lw=1.5))

    def renderizar_diagramas(self, res):
        L = res["x"][-1]
        
        # --- CORTANTE (V) ---
        self.ax_v.clear()
        self.ax_v.axis('on')
        self._configurar_eixos_base()
        
        self.ax_v.set_title("Diagrama de Força Cortante (V)", fontweight='bold', fontsize=11, color="#2c3e50", pad=15)
        self.ax_v.set_ylabel("V [N]", fontsize=10, fontweight='bold', color="#34495e")
        self.ax_v.set_xlim(0, L)
        self.ax_v.margins(y=0.25) # Padding automático para caber os textos

        x, V = res["x"], res["V"]
        self.ax_v.plot(x, V, color='#2c3e50', linewidth=2)
        # Dual Color Fill
        self.ax_v.fill_between(x, 0, V, where=(V >= 0), color='#3498db', alpha=0.35, interpolate=True)
        self.ax_v.fill_between(x, 0, V, where=(V < 0), color='#e74c3c', alpha=0.35, interpolate=True)
        self.ax_v.axhline(0, color='black', linewidth=1.2)
        self.ax_v.grid(True, linestyle=':', alpha=0.6)

        # Anotações Inteligentes (Picos Cortante)
        v_max, v_min = res["V_max"], res["V_min"]
        if abs(v_max) > 1e-5:
            idx_max = np.argmax(V)
            self.ax_v.annotate(f"{v_max:.2f}", xy=(x[idx_max], v_max), xytext=(0, 6), textcoords='offset points', 
                               ha='center', va='bottom', fontsize=9, fontweight='bold', color='#2980b9')
        if abs(v_min) > 1e-5:
            idx_min = np.argmin(V)
            self.ax_v.annotate(f"{v_min:.2f}", xy=(x[idx_min], v_min), xytext=(0, -6), textcoords='offset points', 
                               ha='center', va='top', fontsize=9, fontweight='bold', color='#c0392b')

        # --- MOMENTO (M) ---
        self.ax_m.clear()
        self.ax_m.axis('on')
        self._configurar_eixos_base()

        self.ax_m.set_title("Diagrama de Momento Fletor (M)", fontweight='bold', fontsize=11, color="#2c3e50", pad=15)
        self.ax_m.set_ylabel("M [N.m]", fontsize=10, fontweight='bold', color="#34495e")
        self.ax_m.set_xlabel("Posição x [m]", fontweight='bold', fontsize=10)
        self.ax_m.set_xlim(0, L)
        self.ax_m.margins(y=0.25)

        M = res["M"]
        self.ax_m.plot(x, M, color='#2c3e50', linewidth=2)
        # Dual Color Fill
        self.ax_m.fill_between(x, 0, M, where=(M >= 0), color='#27ae60', alpha=0.35, interpolate=True)
        self.ax_m.fill_between(x, 0, M, where=(M < 0), color='#d35400', alpha=0.35, interpolate=True)
        self.ax_m.axhline(0, color='black', linewidth=1.2)
        self.ax_m.invert_yaxis() # Padrão Resistência dos Materiais (Positivo p/ baixo)
        self.ax_m.grid(True, linestyle=':', alpha=0.6)

        # Anotações Inteligentes (Picos Fletor invertido)
        m_max, m_min = res["M_max"], res["M_min"]
        if abs(m_max) > 1e-5:
            idx_m_max = np.argmax(M)
            # m_max é desenhado para baixo visualmente, então o texto fica embaixo (top alignment, negative y offset)
            self.ax_m.annotate(f"{m_max:.2f}", xy=(x[idx_m_max], m_max), xytext=(0, -6), textcoords='offset points', 
                               ha='center', va='top', fontsize=9, fontweight='bold', color='#27ae60')
        if abs(m_min) > 1e-5:
            idx_m_min = np.argmin(M)
            # m_min é desenhado para cima visualmente
            self.ax_m.annotate(f"{m_min:.2f}", xy=(x[idx_m_min], m_min), xytext=(0, 6), textcoords='offset points', 
                               ha='center', va='bottom', fontsize=9, fontweight='bold', color='#d35400')

        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()


# ==========================================================
# 4. JANELA DE ERRO PROFISSIONAL
# ==========================================================
class DialogoErro(tk.Toplevel):
    def __init__(self, parent, titulo, mensagem, detalhes=None):
        super().__init__(parent)
        self.title("Aviso do Sistema")
        self.configure(bg="#ffffff")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        header = tk.Frame(self, bg="#D13438", height=50)
        header.pack(fill=tk.X)
        icon_label = tk.Label(header, text="⚠", font=("Segoe UI", 24), fg="white", bg="#D13438")
        icon_label.pack(side=tk.LEFT, padx=15)
        titulo_label = tk.Label(header, text=titulo, font=("Segoe UI", 12, "bold"), fg="white", bg="#D13438")
        titulo_label.pack(side=tk.LEFT, pady=10)

        corpo = tk.Frame(self, bg="#ffffff", padx=25, pady=20)
        corpo.pack(fill=tk.BOTH, expand=True)
        msg_label = tk.Label(corpo, text=mensagem, font=("Segoe UI", 10), bg="#ffffff", wraplength=380, justify=tk.LEFT)
        msg_label.pack(anchor=tk.W)

        if detalhes:
            self.var_det = tk.BooleanVar(value=False)
            chk = ttk.Checkbutton(corpo, text="Mostrar relatório técnico", variable=self.var_det, command=self._alternar_detalhes)
            chk.pack(anchor=tk.W, pady=(10, 0))
            self.txt_det = tk.Text(corpo, height=6, font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED)
            self.txt_det.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            self.txt_det.configure(state=tk.NORMAL)
            self.txt_det.insert("1.0", detalhes)
            self.txt_det.configure(state=tk.DISABLED)
            self._alternar_detalhes()

        botoes = tk.Frame(self, bg="#f0f0f0", padx=10, pady=10)
        botoes.pack(fill=tk.X)
        ok_btn = ttk.Button(botoes, text="OK", command=self.destroy, style="Acao.TButton")
        ok_btn.pack(side=tk.RIGHT)
        ok_btn.config(cursor="hand2")

        self._centralizar(parent)

    def _centralizar(self, parent):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def _alternar_detalhes(self):
        if self.var_det.get():
            self.txt_det.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        else:
            self.txt_det.pack_forget()


# ==========================================================
# 5. APP PRINCIPAL (Controller nativo OS)
# ==========================================================
class VigaApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.theme = {
            "bg_main": "#eef2f5",
            "bg_panel": "#ffffff",
            "primary": "#005A9E",
            "danger": "#D13438",
            "text": "#333333",
            "font_title": ("Segoe UI", 11, "bold"),
            "font_body": ("Segoe UI", 10),
            "font_mono": ("Consolas", 10)
        }

        self.title("Software de Análise Estrutural")
        self.geometry("1450x850")
        self.configure(bg=self.theme["bg_main"])

        self.cargas_adicionadas = []

        self._configurar_estilos()
        self._build_ui()
        self.renderer.renderizar_empty_state()

        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _fechar(self):
        try:
            plt.close('all')
        except Exception:
            pass
        finally:
            self.quit()
            self.destroy()

    def _configurar_estilos(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure("TFrame", background=self.theme["bg_main"])
        style.configure("Panel.TFrame", background=self.theme["bg_panel"])
        style.configure("TLabelframe", background=self.theme["bg_panel"], font=self.theme["font_title"])
        style.configure("TLabelframe.Label", background=self.theme["bg_panel"], font=self.theme["font_title"], foreground=self.theme["primary"])
        style.configure("TLabel", background=self.theme["bg_panel"], font=self.theme["font_body"])

        style.configure("TButton", font=self.theme["font_body"], padding=6)
        style.configure("Acao.TButton", font=("Segoe UI", 11, "bold"), background=self.theme["primary"], foreground="white")
        style.map("Acao.TButton", background=[('active', '#0078D7')])
        style.configure("Alerta.TButton", background=self.theme["danger"], foreground="white")
        style.map("Alerta.TButton", background=[('active', '#E81123'), ('disabled', '#FADCDD')])

    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 20))

        self.frame_esq = ttk.Frame(container, width=500)
        self.frame_esq.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        self.frame_esq.pack_propagate(False)

        self.frame_dir = ttk.Frame(container)
        self.frame_dir.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_panel_geometria()
        self._build_panel_cargas()
        self._build_panel_dashboard()
        self._build_graficos()

    def _build_panel_geometria(self):
        f_geo = ttk.LabelFrame(self.frame_esq, text=" 1. Geometria da Viga ", padding=15)
        f_geo.pack(fill=tk.X, pady=(0, 15))

        linha1 = ttk.Frame(f_geo, style="Panel.TFrame")
        linha1.pack(fill=tk.X, pady=5)
        ttk.Label(linha1, text="Comprimento Total L [m]:").pack(side=tk.LEFT)
        self.entry_L = ttk.Entry(linha1, width=8, justify="center")
        self.entry_L.insert(0, "10")
        self.entry_L.pack(side=tk.RIGHT)

        ttk.Separator(f_geo, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(f_geo, text="Tipo de Apoio:").pack(anchor=tk.W)
        self.var_apoio = tk.StringVar(value="simples")

        f_radios = ttk.Frame(f_geo, style="Panel.TFrame")
        f_radios.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(f_radios, text="Bi-Apoiada", variable=self.var_apoio, value="simples", command=self._atualizar_apoios).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(f_radios, text="Engastada", variable=self.var_apoio, value="engaste", command=self._atualizar_apoios).pack(side=tk.LEFT)

        self.f_pos = ttk.Frame(f_geo, style="Panel.TFrame")
        self.f_pos.pack(fill=tk.X, pady=(5, 0))

        self.lbl_xa = ttk.Label(self.f_pos, text="Pos. Pino [m]:")
        self.lbl_xa.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entry_xa = ttk.Entry(self.f_pos, width=8, justify="center")
        self.entry_xa.insert(0, "0")
        self.entry_xa.grid(row=0, column=1, sticky=tk.E, pady=2)

        self.lbl_xb = ttk.Label(self.f_pos, text="Pos. Rolete [m]:")
        self.lbl_xb.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.entry_xb = ttk.Entry(self.f_pos, width=8, justify="center")
        self.entry_xb.insert(0, "10")
        self.entry_xb.grid(row=1, column=1, sticky=tk.E, pady=2)

        self.f_pos.columnconfigure(0, weight=1)

    def _build_panel_cargas(self):
        f_cargas = ttk.LabelFrame(self.frame_esq, text=" 2. Carregamentos ", padding=15)
        f_cargas.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.tree_cargas = ttk.Treeview(f_cargas, columns=("tipo", "valor", "posicao"), show="headings", height=4)
        self.tree_cargas.heading("tipo", text="Tipo")
        self.tree_cargas.heading("valor", text="Valor")
        self.tree_cargas.heading("posicao", text="Posição")
        self.tree_cargas.column("tipo", width=120)
        self.tree_cargas.column("valor", width=80, anchor=tk.CENTER)
        self.tree_cargas.column("posicao", width=120, anchor=tk.CENTER)
        self.tree_cargas.config(cursor="hand2")
        self.tree_cargas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tree_cargas.bind("<<TreeviewSelect>>", self._verificar_selecao)

        f_botoes = ttk.Frame(f_cargas, style="Panel.TFrame")
        f_botoes.pack(fill=tk.X, pady=(10, 0))

        btn_add = ttk.Button(f_botoes, text="➕ Nova Carga", command=self._abrir_modal)
        btn_add.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        btn_add.config(cursor="hand2")

        self.btn_rem = ttk.Button(f_botoes, text="🗑️ Remover", style="Alerta.TButton", command=self._remover_carga, state=tk.DISABLED)
        self.btn_rem.pack(side=tk.RIGHT)

    def _build_panel_dashboard(self):
        f_calc = ttk.Frame(self.frame_esq, style="TFrame")
        f_calc.pack(fill=tk.X)

        btn_calc = ttk.Button(f_calc, text="▶ CALCULAR DIAGRAMAS", style="Acao.TButton", command=self.processar)
        btn_calc.pack(fill=tk.X, pady=(0, 10), ipady=10)
        btn_calc.config(cursor="hand2")

        self.f_cards = ttk.Frame(f_calc, style="TFrame")
        self.f_cards.pack(fill=tk.X)

        self.card_r = ttk.LabelFrame(self.f_cards, text=" Reações ")
        self.card_r.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        self.lbl_res_r = ttk.Label(self.card_r, text="-", font=self.theme["font_mono"])
        self.lbl_res_r.pack(padx=5, pady=5, anchor=tk.W)

        self.card_v = ttk.LabelFrame(self.f_cards, text=" Cortante Máx (V) ")
        self.card_v.grid(row=0, column=1, padx=5, sticky="nsew")
        self.lbl_res_v = ttk.Label(self.card_v, text="-", font=("Segoe UI", 12, "bold"), foreground=self.theme["primary"])
        self.lbl_res_v.pack(padx=5, pady=10)

        self.card_m = ttk.LabelFrame(self.f_cards, text=" Fletor Máx (M) ")
        self.card_m.grid(row=0, column=2, padx=(5, 0), sticky="nsew")
        self.lbl_res_m = ttk.Label(self.card_m, text="-", font=("Segoe UI", 12, "bold"), foreground=self.theme["primary"])
        self.lbl_res_m.pack(padx=5, pady=10)

        self.f_cards.columnconfigure((0, 1, 2), weight=1)

    def _build_graficos(self):
        fig, (ax_viga, ax_v, ax_m) = plt.subplots(3, 1, figsize=(8, 8), height_ratios=[1.2, 2, 2])
        fig.patch.set_facecolor(self.theme["bg_main"])

        canvas = FigureCanvasTkAgg(fig, master=self.frame_dir)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.renderer = VigaRenderer(fig, ax_viga, ax_v, ax_m, canvas)

    def _atualizar_apoios(self):
        if self.var_apoio.get() == "engaste":
            self.lbl_xa.config(text="Pos. Engaste [m]:")
            self.lbl_xb.grid_remove()
            self.entry_xb.grid_remove()
        else:
            self.lbl_xa.config(text="Pos. Pino [m]:")
            self.lbl_xb.grid()
            self.entry_xb.grid()

    def _abrir_modal(self):
        try:
            val = self.entry_L.get()
            if not val: raise ValueError
            L = parse_float(val)
            if L <= 0: raise ValueError
            ModalNovaCarga(self, self.theme, L, self._receber_nova_carga)
        except ValueError:
            DialogoErro(self, "Geometria Inválida", "Defina um Comprimento Total (L) válido antes de adicionar cargas.")

    def _verificar_selecao(self, event):
        if self.tree_cargas.selection():
            self.btn_rem.config(state=tk.NORMAL)
            self.btn_rem.config(cursor="hand2")
        else:
            self.btn_rem.config(state=tk.DISABLED)
            self.btn_rem.config(cursor="arrow")

    def _receber_nova_carga(self, dados):
        self.cargas_adicionadas.append(dados)

        t = dados["tipo_str"]
        if dados["tipo"] == "pontual":
            self.tree_cargas.insert("", tk.END, values=(t, f"{dados['val']:.1f} N", f"x = {dados['pos']:.1f} m"))
        elif dados["tipo"] == "momento":
            self.tree_cargas.insert("", tk.END, values=(t, f"{dados['val']:.1f} N.m", f"x = {dados['pos']:.1f} m"))
        else:
            if abs(dados['qi'] - dados['qf']) < 1e-6:
                v_str = f"{dados['qi']:.1f} N/m"
            else:
                v_str = f"de {dados['qi']:.1f} a {dados['qf']:.1f} N/m"
            self.tree_cargas.insert("", tk.END, values=(t, v_str, f"x: {dados['xi']:.1f} a {dados['xf']:.1f} m"))

    def _remover_carga(self):
        sel = self.tree_cargas.selection()
        if sel:
            idx = self.tree_cargas.index(sel[0])
            self.tree_cargas.delete(sel[0])
            self.cargas_adicionadas.pop(idx)
            self._verificar_selecao(None)

            self.lbl_res_r.config(text="-")
            self.lbl_res_v.config(text="-")
            self.lbl_res_m.config(text="-")

    def processar(self):
        try:
            L = parse_float(self.entry_L.get())
            if L <= 0: raise ValueError("Comprimento da viga deve ser maior que zero.")

            t_apoio = self.var_apoio.get()
            xa = parse_float(self.entry_xa.get())
            xb = parse_float(self.entry_xb.get()) if t_apoio == 'simples' else None

            viga = VigaEngine(L)
            for c in self.cargas_adicionadas:
                if c["tipo"] == "pontual":
                    viga.adicionar_carga_pontual(c["pos"], c["val"])
                elif c["tipo"] == "momento":
                    viga.adicionar_momento(c["pos"], c["val"])
                elif c["tipo"] == "distrib":
                    viga.adicionar_carga_distribuida(c["qi"], c["qf"], c["xi"], c["xf"])

            viga.calcular_reacoes(t_apoio, xa, xb)
            res = viga.calcular_esforcos()

            t_res = ""
            for r in viga.reacoes_calculadas:
                t_res += f"{r['nome']} = {r['valor']:+.2f}\n"
            self.lbl_res_r.config(text=t_res.strip() if t_res else "-")

            self.lbl_res_v.config(text=f"Máx (+): {res['V_max']:+.2f} N\nMín (-): {res['V_min']:+.2f} N")
            self.lbl_res_m.config(text=f"Máx (+): {res['M_max']:+.2f} N.m\nMín (-): {res['M_min']:+.2f} N.m")

            self.renderer.renderizar_esquema(L, t_apoio, xa, xb, self.cargas_adicionadas)
            self.renderer.renderizar_diagramas(res)

        except Exception as e:
            DialogoErro(self, "Aviso Estrutural", str(e), traceback.format_exc())

if __name__ == "__main__":
    app = VigaApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\nAplicação encerrada com segurança.")