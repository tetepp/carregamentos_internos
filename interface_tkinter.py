import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import traceback
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# ══════════════════════════════════════════════════════════════════════════════
# PALETA DE CORES - Tema Rosa Feminino
# ══════════════════════════════════════════════════════════════════════════════
CORES = {
    "bg_main":      "#fff1f7",   # fundo principal rosinha claro
    "bg_sidebar":   "#f8d7e8",   # sidebar rosa pastel
    "bg_panel":     "#ffe4ef",   # painéis
    "bg_canvas":    "#fff7fb",   # fundo dos gráficos
    "bg_topbar":    "#f9c5d5",

    "border":       "#e7a8c2",

    "primary":      "#ec4899",   # rosa principal
    "primary_hover":"#db2777",

    "success":      "#d946ef",   # lilás vibrante
    "danger":       "#fb7185",   # rosa avermelhado
    "warning":      "#f9a8d4",   # rosa suave

    "text_pri":     "#4a044e",   # roxo escuro elegante
    "text_sec":     "#7e2253",
    "text_muted":   "#b06a8d",

    "sidebar_btn_bg":  "#fbcfe8",
    "sidebar_btn_act": "#ec4899",
    "sidebar_sect": "#9d174d",

    "carga_pontual": "#fb7185",
    "carga_momento": "#c084fc",
    "carga_distrib": "#f472b6",
}

def _get_screen_scale() -> float:
    """Retorna fator de escala baseado na resolução da tela (1.0 para HD, 0.85 para menor)."""
    try:
        import tkinter as _tk
        _r = _tk.Tk()
        _r.withdraw()
        w = _r.winfo_screenwidth()
        _r.destroy()
        if w >= 1920:
            return 1.0
        elif w >= 1280:
            return 0.88
        else:
            return 0.78
    except Exception:
        return 0.88

_SCALE = _get_screen_scale()

def _fs(size: int) -> int:
    """Escala um tamanho de fonte."""
    return max(7, round(size * _SCALE))

def _px(size: int) -> int:
    """Escala um tamanho de pixel."""
    return max(1, round(size * _SCALE))

FONT_TITLE  = ("Segoe UI", _fs(10), "bold")
FONT_BODY   = ("Segoe UI", _fs(9))
FONT_SMALL  = ("Segoe UI", _fs(8))
FONT_MONO_B = ("Consolas", _fs(10), "bold")
FONT_HEADING = ("Segoe UI", _fs(11), "bold")

# ══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
def parse_float(val_str: str) -> float:
    """Trata a entrada do utilizador permitindo o uso de vírgula decimal."""
    try:
        return float(str(val_str).replace(',', '.'))
    except ValueError:
        raise ValueError("Formato numérico inválido.")

def clean_zero(val: float) -> float:
    """Evita a exibição de '-0.00' por imprecisão de ponto flutuante."""
    return 0.0 if abs(val) < 1e-9 else val

def separador(parent, pady=6):
    """Cria um separador visual."""
    tk.Frame(parent, height=1, bg=CORES["border"]).pack(
        fill=tk.X, padx=10, pady=pady
    )

# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTES DE UI REUTILIZÁVEIS
# ══════════════════════════════════════════════════════════════════════════════
class SidebarButton(tk.Frame):
    """Botão estilizado para a barra lateral."""
    def __init__(self, parent, text, icon="•", command=None):
        super().__init__(parent, bg=CORES["bg_sidebar"], cursor="hand2")
        self.command = command
        self.active = False
        
        self.label = tk.Label(
            self, text=f"  {icon}  {text}",
            bg=CORES["bg_sidebar"], fg=CORES["text_sec"],
            font=FONT_BODY, anchor="w", padx=_px(5), pady=_px(5)
        )
        self.label.pack(fill=tk.X)
        
        for w in (self, self.label):
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)
            w.bind("<Button-1>", self.on_click)
    
    def on_enter(self, _):
        if not self.active:
            self.label.config(bg=CORES["sidebar_btn_bg"], fg=CORES["text_pri"])
    
    def on_leave(self, _):
        if not self.active:
            self.label.config(bg=CORES["bg_sidebar"], fg=CORES["text_sec"])
    
    def on_click(self, _):
        if self.command:
            self.command()
    
    def set_active(self, active):
        self.active = active
        if active:
            self.label.config(
                bg=CORES["sidebar_btn_act"], fg="#93c5fd",
                font=("Segoe UI", 9, "bold")
            )
        else:
            self.label.config(
                bg=CORES["bg_sidebar"], fg=CORES["text_sec"],
                font=FONT_BODY
            )

class DarkButton(tk.Button):
    """Botão estilizado para o tema escuro."""
    def __init__(self, parent, text, bg=None, fg=None, command=None):
        super().__init__(
            parent, text=text,
            bg=bg or CORES["primary"], fg=fg or "white",
            activebackground=CORES["primary_hover"], activeforeground="white",
            relief=tk.FLAT, bd=0, cursor="hand2",
            font=FONT_BODY, padx=_px(8), pady=_px(5), command=command
        )

class DarkEntry(tk.Entry):
    """Entry estilizada para o tema escuro."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=CORES["bg_canvas"], fg=CORES["text_pri"],
            insertbackground=CORES["text_pri"],
            font=FONT_BODY, justify="center",
            relief=tk.FLAT, bd=0,
            highlightthickness=1, highlightbackground=CORES["border"],
            highlightcolor=CORES["primary"],
            **kwargs
        )

class DarkCombobox(ttk.Combobox):
    """Combobox estilizada."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, font=FONT_BODY, state="readonly", **kwargs)

# ══════════════════════════════════════════════════════════════════════════════
# MOTOR FÍSICO (Back-end)
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class CargaPontual:
    pos: float
    valor: float

@dataclass
class MomentoConcentrado:
    pos: float
    valor: float

@dataclass
class CargaDistribuida:
    q_inicial: float
    q_final: float
    inicio: float
    fim: float

@dataclass
class Reacao:
    tipo: str  # 'forca' ou 'momento'
    pos: float
    valor: float
    nome: str

class VigaEngine:
    """Motor de cálculo estrutural."""
    
    def __init__(self, comprimento: float):
        self.L = comprimento
        self.cargas_pontuais: List[CargaPontual] = []
        self.cargas_distribuidas: List[CargaDistribuida] = []
        self.momentos: List[MomentoConcentrado] = []
        self.reacoes_calculadas: List[Reacao] = []
    
    def adicionar_carga_pontual(self, pos: float, valor: float):
        self.cargas_pontuais.append(CargaPontual(pos, valor))
    
    def adicionar_carga_distribuida(self, q_ini: float, q_fim: float, inicio: float, fim: float):
        self.cargas_distribuidas.append(CargaDistribuida(q_ini, q_fim, inicio, fim))
    
    def adicionar_momento(self, pos: float, valor: float):
        self.momentos.append(MomentoConcentrado(pos, valor))
    
    def calcular_reacoes(self, tipo_apoio: str, x_a: float, x_b: Optional[float] = None):
        soma_Fy = 0.0
        soma_M_A = 0.0
        
        for p in self.cargas_pontuais:
            soma_Fy += p.valor
            soma_M_A += p.valor * (p.pos - x_a)
        
        for c in self.cargas_distribuidas:
            L_c = c.fim - c.inicio
            if L_c <= 0:
                continue
            
            F_ret = c.q_inicial * L_c
            x_ret = c.inicio + L_c / 2.0
            
            F_tri = (c.q_final - c.q_inicial) * L_c / 2.0
            x_tri = c.inicio + (2.0 / 3.0) * L_c
            
            F_eq = F_ret + F_tri
            if abs(F_eq) > 1e-9:
                x_eq = (F_ret * x_ret + F_tri * x_tri) / F_eq
                soma_Fy += F_eq
                soma_M_A += F_eq * (x_eq - x_a)
        
        for m in self.momentos:
            soma_M_A += m.valor
        
        self.reacoes_calculadas = []
        
        if tipo_apoio == 'engaste':
            Ry = -soma_Fy
            M_eng = -soma_M_A
            self.reacoes_calculadas.append(
                Reacao("forca", x_a, clean_zero(Ry), "Ry")
            )
            self.reacoes_calculadas.append(
                Reacao("momento", x_a, clean_zero(M_eng), "M_eng")
            )
        else:
            if abs(x_b - x_a) < 1e-6:
                raise ValueError("Os apoios não podem coincidir na mesma posição.")
            
            Rb = -soma_M_A / (x_b - x_a)
            Ra = -soma_Fy - Rb
            self.reacoes_calculadas.append(
                Reacao("forca", x_a, clean_zero(Ra), "Ra")
            )
            self.reacoes_calculadas.append(
                Reacao("forca", x_b, clean_zero(Rb), "Rb")
            )
    
    def _get_shear_at(self, x: float) -> float:
        v = 0.0
        for r in self.reacoes_calculadas:
            if x >= r.pos - 1e-9:
                v += r.valor
        for p in self.cargas_pontuais:
            if x >= p.pos - 1e-9:
                v += p.valor
        for c in self.cargas_distribuidas:
            if x > c.inicio + 1e-9:
                limite = min(x, c.fim)
                s = limite - c.inicio
                if s > 0:
                    L_total = c.fim - c.inicio
                    t = s / L_total if L_total > 0 else 1
                    q_s = c.q_inicial + t * (c.q_final - c.q_inicial)
                    v += s * (c.q_inicial + q_s) / 2.0
        return v
    
    def calcular_esforcos(self, dx: float = 0.01) -> Dict[str, Any]:
        pontos = [0.0, self.L]
        for p in self.cargas_pontuais:
            pontos.append(p.pos)
        for m in self.momentos:
            pontos.append(m.pos)
        for c in self.cargas_distribuidas:
            pontos.extend([c.inicio, c.fim])
        for r in self.reacoes_calculadas:
            pontos.append(r.pos)
        
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
            if abs(mc.pos) < 1e-6:
                m0 -= mc.valor
        for r in self.reacoes_calculadas:
            if r.tipo == "momento" and abs(r.pos) < 1e-6:
                m0 -= r.valor
        momento[0] = m0
        
        for i in range(1, len(xs)):
            delta_x = xs[i] - xs[i - 1]
            x_mid = (xs[i - 1] + xs[i]) / 2.0
            v_mid = self._get_shear_at(x_mid)
            m = momento[i - 1] + (v_mid * delta_x)
            
            x0, x1 = xs[i - 1], xs[i]
            for mc in self.momentos:
                if x0 + 1e-6 < mc.pos <= x1 + 1e-6:
                    m -= mc.valor
            for r in self.reacoes_calculadas:
                if r.tipo == "momento" and x0 + 1e-6 < r.pos <= x1 + 1e-6:
                    m -= r.valor
            
            momento[i] = m
        
        return {
            "x": xs,
            "V": cortante,
            "M": momento,
            "V_max": clean_zero(np.max(cortante)),
            "V_min": clean_zero(np.min(cortante)),
            "M_max": clean_zero(np.max(momento)),
            "M_min": clean_zero(np.min(momento))
        }
    
    def limpar(self):
        """Limpa todas as cargas e reações."""
        self.cargas_pontuais.clear()
        self.cargas_distribuidas.clear()
        self.momentos.clear()
        self.reacoes_calculadas.clear()

# ══════════════════════════════════════════════════════════════════════════════
# RENDERIZADOR DE GRÁFICOS (Adaptado para tema escuro)
# ══════════════════════════════════════════════════════════════════════════════
class VigaRenderer:
    """Renderiza os diagramas de corpo livre, cortante e momento."""
    
    def __init__(self, fig, ax_viga, ax_v, ax_m, canvas):
        self.fig = fig
        self.ax_viga = ax_viga
        self.ax_v = ax_v
        self.ax_m = ax_m
        self.canvas = canvas
        
        # Aplicar tema escuro
        self.fig.patch.set_facecolor(CORES["bg_canvas"])
        for ax in (self.ax_viga, self.ax_v, self.ax_m):
            ax.set_facecolor(CORES["bg_canvas"])
            ax.tick_params(colors=CORES["text_sec"])
            ax.xaxis.label.set_color(CORES["text_sec"])
            ax.yaxis.label.set_color(CORES["text_sec"])
            for spine in ax.spines.values():
                spine.set_color(CORES["border"])
        
        self._configurar_eixos_base()
        self.renderizar_empty_state()
    
    def _configurar_eixos_base(self):
        for ax in (self.ax_v, self.ax_m):
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
    
    def renderizar_empty_state(self):
        for ax in (self.ax_viga, self.ax_v, self.ax_m):
            ax.clear()
            ax.axis('off')
            ax.set_facecolor(CORES["bg_canvas"])
        
        self.ax_viga.text(
            0.5, 0.5,
            "Configure a geometria e adicione as cargas\npara visualizar os diagramas da viga.",
            ha='center', va='center', fontsize=_fs(10),
            color=CORES["text_muted"], style='italic'
        )
        self.canvas.draw()
    
    def renderizar_esquema(self, L, tipo_apoio, xa, xb, cargas):
        self.ax_viga.clear()
        self.ax_viga.set_facecolor(CORES["bg_canvas"])
        self.ax_viga.set_title(
            "Diagrama de Corpo Livre",
            fontweight='bold', color=CORES["text_pri"], pad=_px(8), fontsize=_fs(10)
        )
        self.ax_viga.set_xlim(-0.5, L + 0.5)
        self.ax_viga.set_ylim(-2.2, 2.5)
        self.ax_viga.axis('off')
        
        # Viga
        self.ax_viga.plot([0, L], [0, 0], color='#64748b', linewidth=8, zorder=2)
        
        # Apoios
        if tipo_apoio == 'engaste':
            rect = patches.Rectangle(
                (xa - 0.2, -0.6), 0.4, 1.2,
                linewidth=1, edgecolor=CORES["text_sec"],
                facecolor='#475569', hatch='///'
            )
            self.ax_viga.add_patch(rect)
        else:
            # Pino (roxo)
            pino = patches.Polygon(
                [[xa, 0], [xa - 0.2, -0.4], [xa + 0.2, -0.4]],
                closed=True, color='#9333ea', zorder=3
            )
            self.ax_viga.add_patch(pino)
            self.ax_viga.plot(
                [xa - 0.3, xa + 0.3], [-0.4, -0.4],
                color=CORES["text_sec"], lw=2
            )
            
            # Rolete (círculo vermelho)
            rolete_circle = patches.Circle(
                (xb, -0.2), 0.2,
                linewidth=1.5, edgecolor='#dc2626',
                facecolor='#ef4444', zorder=3
            )
            self.ax_viga.add_patch(rolete_circle)
            self.ax_viga.plot(
                [xb - 0.25, xb + 0.25], [-0.42, -0.42],
                color=CORES["text_sec"], lw=2
            )
        
        # Régua abaixo da viga
        self.ax_viga.set_xlim(-0.5, L + 0.5)
        ruler_y = -1.2
        self.ax_viga.plot([0, L], [ruler_y, ruler_y], color=CORES["border"], lw=1.5, zorder=5)
        # Extremidades da régua
        self.ax_viga.plot([0, 0], [ruler_y - 0.1, ruler_y + 0.1], color=CORES["border"], lw=1.5, zorder=5)
        self.ax_viga.plot([L, L], [ruler_y - 0.1, ruler_y + 0.1], color=CORES["border"], lw=1.5, zorder=5)
        # Marcações intermediárias
        num_marks = min(10, max(5, int(L)))
        step = L / num_marks
        for i in range(num_marks + 1):
            xr = i * step
            is_major = (i % max(1, num_marks // 5) == 0) or (i == num_marks)
            tick_h = 0.12 if is_major else 0.06
            self.ax_viga.plot([xr, xr], [ruler_y - tick_h, ruler_y + tick_h],
                              color=CORES["border"], lw=1.2, zorder=5)
            if is_major:
                self.ax_viga.text(xr, ruler_y - 0.28, f"{xr:.1f}m",
                                  ha='center', va='top', fontsize=_fs(7),
                                  color=CORES["text_muted"], zorder=5)
        # Label comprimento total
        self.ax_viga.text(L / 2, ruler_y - 0.52, f"L = {L:.1f} m",
                          ha='center', va='top', fontsize=_fs(8),
                          fontweight='bold', color=CORES["text_sec"], zorder=5)
        for c in cargas:
            if c.get("tipo") == "pontual":
                cor = CORES["carga_pontual"] if c["val"] < 0 else CORES["success"]
                y_text = 1.5 if c["val"] < 0 else -1.5
                self.ax_viga.annotate(
                    '', xy=(c["pos"], 0), xytext=(c["pos"], y_text),
                    arrowprops=dict(facecolor=cor, edgecolor=cor, width=2.5, headwidth=9),
                    zorder=4
                )
                self.ax_viga.text(
                    c["pos"],
                    y_text + (0.2 if c["val"] < 0 else -0.4),
                    f"{abs(c['val']):.1f} N",
                    ha='center', fontweight='bold', color=cor
                )
            
            elif c.get("tipo") == "momento":
                marker = r'$\circlearrowleft$' if c["val"] > 0 else r'$\circlearrowright$'
                self.ax_viga.plot(
                    c["pos"], 0.8, marker=marker,
                    markersize=22, color=CORES["carga_momento"]
                )
                self.ax_viga.text(
                    c["pos"], 1.4, f"{abs(c['val']):.1f} Nm",
                    ha='center', color=CORES["carga_momento"], fontweight='bold'
                )
            
            elif c.get("tipo") == "distrib":
                qi, qf = c["qi"], c["qf"]
                xi, xf = c["xi"], c["xf"]
                is_downward = (qi + qf) <= 0
                max_q = max(abs(qi), abs(qf))
                max_q = max_q if max_q != 0 else 1
                
                sign_y = 1 if is_downward else -1
                y_i = sign_y * (abs(qi) / max_q) * 1.2
                y_f = sign_y * (abs(qf) / max_q) * 1.2
                
                cor_poligono = CORES["carga_pontual"] if is_downward else CORES["success"]
                poly = patches.Polygon(
                    [[xi, 0], [xi, y_i], [xf, y_f], [xf, 0]],
                    closed=True, color=cor_poligono, alpha=0.2, zorder=1
                )
                self.ax_viga.add_patch(poly)
                
                n_arrows = max(3, int((xf - xi) * 2))
                for x_seta in np.linspace(xi, xf, n_arrows):
                    t = (x_seta - xi) / (xf - xi) if xf != xi else 0
                    y_seta = y_i + t * (y_f - y_i)
                    self.ax_viga.annotate(
                        '', xy=(x_seta, 0), xytext=(x_seta, y_seta),
                        arrowprops=dict(
                            arrowstyle="->", color=cor_poligono,
                            alpha=0.7, lw=1.5
                        )
                    )
    
    def renderizar_diagramas(self, res, L):
        x, V, M = res["x"], res["V"], res["M"]
        
        # --- Cortante ---
        self.ax_v.clear()
        self.ax_v.set_facecolor(CORES["bg_canvas"])
        self.ax_v.axis('on')
        self._configurar_eixos_base()
        
        self.ax_v.set_title(
            "Diagrama de Força Cortante (V)",
            fontweight='bold', fontsize=_fs(10), color=CORES["text_pri"], pad=_px(10)
        )
        self.ax_v.set_ylabel("V [N]", fontsize=_fs(9), fontweight='bold', color=CORES["text_sec"])
        self.ax_v.set_xlim(0, L)
        self.ax_v.margins(y=0.25)
        
        self.ax_v.plot(x, V, color=CORES["text_pri"], linewidth=2)
        self.ax_v.fill_between(x, 0, V, where=(V >= 0), color='#3b82f6', alpha=0.3, interpolate=True)
        self.ax_v.fill_between(x, 0, V, where=(V < 0), color=CORES["danger"], alpha=0.3, interpolate=True)
        self.ax_v.axhline(0, color=CORES["border"], linewidth=1.2)
        self.ax_v.grid(True, linestyle=':', alpha=0.4, color=CORES["border"])
        self.ax_v.tick_params(colors=CORES["text_sec"])
        
        v_max, v_min = res["V_max"], res["V_min"]
        if abs(v_max) > 1e-5:
            idx_max = np.argmax(V)
            self.ax_v.annotate(
                f"{v_max:.2f}", xy=(x[idx_max], v_max),
                xytext=(0, 5), textcoords='offset points',
                ha='center', va='bottom', fontsize=_fs(8),
                fontweight='bold', color='#93c5fd'
            )
        if abs(v_min) > 1e-5:
            idx_min = np.argmin(V)
            self.ax_v.annotate(
                f"{v_min:.2f}", xy=(x[idx_min], v_min),
                xytext=(0, -5), textcoords='offset points',
                ha='center', va='top', fontsize=_fs(8),
                fontweight='bold', color='#fca5a5'
            )
        
        # --- Momento ---
        self.ax_m.clear()
        self.ax_m.set_facecolor(CORES["bg_canvas"])
        self.ax_m.axis('on')
        self._configurar_eixos_base()
        
        self.ax_m.set_title(
            "Diagrama de Momento Fletor (M)",
            fontweight='bold', fontsize=_fs(10), color=CORES["text_pri"], pad=_px(10)
        )
        self.ax_m.set_ylabel("M [N.m]", fontsize=_fs(9), fontweight='bold', color=CORES["text_sec"])
        self.ax_m.set_xlabel("Posição x [m]", fontweight='bold', fontsize=_fs(9), color=CORES["text_sec"])
        self.ax_m.set_xlim(0, L)
        self.ax_m.margins(y=0.25)
        
        self.ax_m.plot(x, M, color=CORES["text_pri"], linewidth=2)
        self.ax_m.fill_between(x, 0, M, where=(M >= 0), color=CORES["success"], alpha=0.3, interpolate=True)
        self.ax_m.fill_between(x, 0, M, where=(M < 0), color='#f97316', alpha=0.3, interpolate=True)
        self.ax_m.axhline(0, color=CORES["border"], linewidth=1.2)
        self.ax_m.invert_yaxis()
        self.ax_m.grid(True, linestyle=':', alpha=0.4, color=CORES["border"])
        self.ax_m.tick_params(colors=CORES["text_sec"])
        
        m_max, m_min = res["M_max"], res["M_min"]
        if abs(m_max) > 1e-5:
            idx_m_max = np.argmax(M)
            self.ax_m.annotate(
                f"{m_max:.2f}", xy=(x[idx_m_max], m_max),
                xytext=(0, -6), textcoords='offset points',
                ha='center', va='top', fontsize=_fs(8),
                fontweight='bold', color='#86efac'
            )
        if abs(m_min) > 1e-5:
            idx_m_min = np.argmin(M)
            self.ax_m.annotate(
                f"{m_min:.2f}", xy=(x[idx_m_min], m_min),
                xytext=(0, 6), textcoords='offset points',
                ha='center', va='bottom', fontsize=_fs(8),
                fontweight='bold', color='#fdba74'
            )
        
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

# ══════════════════════════════════════════════════════════════════════════════
# MODAL DE NOVA CARGA (Adaptado para tema escuro)
# ══════════════════════════════════════════════════════════════════════════════
class ModalNovaCarga(tk.Toplevel):
    """Janela modal para adicionar cargas."""
    
    def __init__(self, parent, L_max, callback_salvar, tipo_default="Pontual (Força)"):
        super().__init__(parent)
        self.L_max = L_max
        self.callback = callback_salvar
        self._tipo_default = tipo_default
        
        self.title("Adicionar Nova Carga")
        modal_w, modal_h = _px(420), _px(380)
        self.geometry(f"{modal_w}x{modal_h}")
        self.configure(bg=CORES["bg_panel"])
        
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        
        self._build_ui()
        self._centralizar_no_parent(parent)
    
    def _centralizar_no_parent(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")
    
    def _build_ui(self):
        # Título
        header = tk.Frame(self, bg=CORES["bg_sidebar"])
        header.pack(fill=tk.X)
        tk.Label(
            header, text="⚡ Configuração de Carga",
            bg=CORES["bg_sidebar"], fg=CORES["primary"],
            font=FONT_HEADING, padx=_px(16), pady=_px(9)
        ).pack(anchor=tk.W)
        
        f_main = tk.Frame(self, bg=CORES["bg_panel"], padx=_px(20), pady=_px(15))
        f_main.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            f_main, text="Tipo de carregamento:",
            bg=CORES["bg_panel"], fg=CORES["text_sec"],
            font=FONT_BODY
        ).pack(anchor=tk.W, pady=(0, 8))
        
        self.var_tipo = tk.StringVar(value=self._tipo_default)
        cb = DarkCombobox(
            f_main, textvariable=self.var_tipo,
            values=[
                "Pontual (Força)",
                "Momento Concentrado",
                "Distribuída Constante",
                "Distribuída Linear"
            ]
        )
        cb.pack(fill=tk.X, pady=(0, 15))
        
        self.f_inputs = tk.Frame(f_main, bg=CORES["bg_panel"])
        self.f_inputs.pack(fill=tk.BOTH, expand=True)
        
        self.var_tipo.trace_add("write", self._atualizar_campos)
        self._atualizar_campos()
        
        # Botões
        f_botoes = tk.Frame(f_main, bg=CORES["bg_panel"])
        f_botoes.pack(fill=tk.X, pady=(20, 0))
        
        btn_cancelar = DarkButton(
            f_botoes, text="Cancelar",
            bg=CORES["bg_sidebar"], fg=CORES["text_sec"],
            command=self.destroy
        )
        btn_cancelar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        btn_salvar = DarkButton(
            f_botoes, text="✔ Confirmar",
            bg=CORES["success"], command=self._validar_e_salvar
        )
        btn_salvar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
    
    def _criar_entry(self, parent):
        entry = DarkEntry(parent)
        return entry
    
    def _atualizar_campos(self, *args):
        for w in self.f_inputs.winfo_children():
            w.destroy()
        
        tipo = self.var_tipo.get()
        
        if tipo in ["Pontual (Força)", "Momento Concentrado"]:
            lbl_u = "N" if tipo == "Pontual (Força)" else "N.m"
            instrucao = "[- p/ Baixo]" if tipo == "Pontual (Força)" else "[- p/ Horário]"
            
            tk.Label(self.f_inputs, text=f"Intensidade ({lbl_u})\n{instrucao}:",
                     bg=CORES["bg_panel"], fg=CORES["text_sec"], justify=tk.LEFT,
                     font=FONT_SMALL).grid(row=0, column=0, sticky=tk.W, pady=8)
            ent_val = self._criar_entry(self.f_inputs)
            ent_val.grid(row=0, column=1, sticky="ew", pady=8, padx=(10, 0))
            
            tk.Label(self.f_inputs, text="Posição x [m]:",
                     bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_SMALL
                     ).grid(row=1, column=0, sticky=tk.W, pady=8)
            ent_pos = self._criar_entry(self.f_inputs)
            ent_pos.grid(row=1, column=1, sticky="ew", pady=8, padx=(10, 0))
            
            self.f_inputs.entries = {"val": ent_val, "pos": ent_pos}
            self.f_inputs.columnconfigure(1, weight=1)
        
        else:
            tk.Label(self.f_inputs, text="Intens. Início [N/m]\n[- p/ Baixo]:",
                     bg=CORES["bg_panel"], fg=CORES["text_sec"], justify=tk.LEFT,
                     font=FONT_SMALL).grid(row=0, column=0, sticky=tk.W, pady=5)
            ent_qi = self._criar_entry(self.f_inputs)
            ent_qi.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))
            
            ent_qf = None
            if tipo == "Distribuída Linear":
                tk.Label(self.f_inputs, text="Intens. Final [N/m]:",
                         bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_SMALL
                         ).grid(row=1, column=0, sticky=tk.W, pady=5)
                ent_qf = self._criar_entry(self.f_inputs)
                ent_qf.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))
            
            r_offset = 2 if tipo == "Distribuída Linear" else 1
            
            tk.Label(self.f_inputs, text="Posição Inicial x [m]:",
                     bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_SMALL
                     ).grid(row=r_offset, column=0, sticky=tk.W, pady=5)
            ent_xi = self._criar_entry(self.f_inputs)
            ent_xi.grid(row=r_offset, column=1, sticky="ew", pady=5, padx=(10, 0))
            
            tk.Label(self.f_inputs, text="Posição Final x [m]:",
                     bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_SMALL
                     ).grid(row=r_offset + 1, column=0, sticky=tk.W, pady=5)
            ent_xf = self._criar_entry(self.f_inputs)
            ent_xf.grid(row=r_offset + 1, column=1, sticky="ew", pady=5, padx=(10, 0))
            
            self.f_inputs.entries = {
                "qi": ent_qi, "qf": ent_qf, "xi": ent_xi, "xf": ent_xf
            }
            self.f_inputs.columnconfigure(1, weight=1)
    
    def _validar_e_salvar(self):
        tipo = self.var_tipo.get()
        try:
            dados = {"tipo_str": tipo}
            
            if tipo in ["Pontual (Força)", "Momento Concentrado"]:
                pos = parse_float(self.f_inputs.entries["pos"].get())
                if not (0 <= pos <= self.L_max):
                    raise ValueError(f"Posição fora da viga (0 a {self.L_max} m)")
                
                dados.update({
                    "tipo": "pontual" if tipo == "Pontual (Força)" else "momento",
                    "val": parse_float(self.f_inputs.entries["val"].get()),
                    "pos": pos
                })
            else:
                qi = parse_float(self.f_inputs.entries["qi"].get())
                qf = parse_float(
                    self.f_inputs.entries["qf"].get()
                ) if tipo == "Distribuída Linear" else qi
                xi = parse_float(self.f_inputs.entries["xi"].get())
                xf = parse_float(self.f_inputs.entries["xf"].get())
                
                if not (0 <= xi < xf <= self.L_max):
                    raise ValueError(f"Intervalo de x inválido (limites 0 a {self.L_max} m).")
                
                dados.update({
                    "tipo": "distrib", "qi": qi, "qf": qf, "xi": xi, "xf": xf
                })
            
            self.callback(dados)
            self.destroy()
        
        except ValueError as e:
            msg = str(e) if "Posição" in str(e) or "Intervalo" in str(e) else \
                  "Insira apenas números (use vírgula ou ponto)."
            DialogoErro(self, "Dados Inválidos", msg)

# ══════════════════════════════════════════════════════════════════════════════
# DIÁLOGO DE ERRO (Adaptado)
# ══════════════════════════════════════════════════════════════════════════════
class DialogoErro(tk.Toplevel):
    def __init__(self, parent, titulo, mensagem, detalhes=None):
        super().__init__(parent)
        self.title("Aviso do Sistema")
        self.configure(bg=CORES["bg_panel"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Header
        header = tk.Frame(self, bg=CORES["danger"], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header, text="⚠", font=("Segoe UI", 24),
            fg="white", bg=CORES["danger"]
        ).pack(side=tk.LEFT, padx=15)
        tk.Label(
            header, text=titulo,
            font=("Segoe UI", 12, "bold"),
            fg="white", bg=CORES["danger"]
        ).pack(side=tk.LEFT, pady=10)
        
        corpo = tk.Frame(self, bg=CORES["bg_panel"], padx=25, pady=20)
        corpo.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            corpo, text=mensagem, font=FONT_BODY,
            bg=CORES["bg_panel"], fg=CORES["text_pri"],
            wraplength=380, justify=tk.LEFT
        ).pack(anchor=tk.W)
        
        if detalhes:
            self.var_det = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                corpo, text="Mostrar relatório técnico",
                variable=self.var_det, command=self._alternar_detalhes
            ).pack(anchor=tk.W, pady=(10, 0))
            
            self.txt_det = tk.Text(
                corpo, height=6, font=("Consolas", 9),
                wrap=tk.WORD, bg=CORES["bg_canvas"],
                fg=CORES["text_sec"]
            )
            self.txt_det.insert("1.0", detalhes)
            self.txt_det.config(state=tk.DISABLED)
            self._alternar_detalhes()
        
        botoes = tk.Frame(self, bg=CORES["bg_sidebar"], padx=10, pady=10)
        botoes.pack(fill=tk.X)
        DarkButton(botoes, text="OK", command=self.destroy).pack(side=tk.RIGHT)
        
        self._centralizar(parent)
    
    def _centralizar(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")
    
    def _alternar_detalhes(self):
        if self.var_det.get():
            self.txt_det.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        else:
            self.txt_det.pack_forget()

# ══════════════════════════════════════════════════════════════════════════════
# APLICAÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class VigaApp(tk.Tk):
    """Aplicação principal de análise estrutural."""
    
    def __init__(self):
        super().__init__()
        
        self.title("⬡ Análise Estrutural - Viga")

        # Detectar resolução e adaptar janela
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        if sw >= 1920:
            win_w, win_h = 1450, 850
            self.minsize(1200, 680)
        elif sw >= 1280:
            win_w, win_h = min(1280, sw - 40), min(720, sh - 60)
            self.minsize(900, 580)
        else:
            win_w, win_h = min(1100, sw - 20), min(660, sh - 40)
            self.minsize(800, 520)

        # Centralizar janela na tela
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.configure(bg=CORES["bg_main"])
        
        # Estado da aplicação
        self.cargas_adicionadas: List[Dict] = []
        self.comprimento_viga = 10.0
        self.tipo_apoio = "simples"
        self.pos_apoio_a = 0.0
        self.pos_apoio_b = 10.0
        self.resultados = None
        
        # Inicializar referências (serão preenchidas depois)
        self.sidebar_buttons = {}
        self.result_labels = {}
        self.panel_body = None
        self.panel_title = None
        self.config_panel = None
        self.tree_cargas = None
        self.status_label = None
        
        # Construir UI
        self._build_ui()
        
        # Protocolo de fechamento
        self.protocol("WM_DELETE_WINDOW", self._fechar)
    
    def _fechar(self):
        try:
            plt.close('all')
        except Exception:
            pass
        finally:
            self.quit()
            self.destroy()
    
    # ══════════════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DA UI
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        # Topbar
        self._build_topbar()
        
        # Corpo principal
        corpo = tk.Frame(self, bg=CORES["bg_main"])
        corpo.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar
        self._build_sidebar(corpo)
        
        # Área central
        self._build_central_area(corpo)
        
        # Ativar primeira aba APÓS tudo estar construído
        self._activate_sidebar_tab("geometria")
    
    def _build_topbar(self):
        topbar = tk.Frame(self, bg=CORES["bg_topbar"], height=_px(40))
        topbar.pack(fill=tk.X)
        topbar.pack_propagate(False)
        
        tk.Label(
            topbar, text="  ⬡  Análise Estrutural",
            bg=CORES["bg_topbar"], fg=CORES["primary"],
            font=("Segoe UI", _fs(10), "bold")
        ).pack(side=tk.LEFT, padx=(_px(10), _px(20)))
        
        self.status_label = tk.Label(
            topbar, text="Pronto",
            bg=CORES["bg_topbar"], fg=CORES["text_muted"],
            font=FONT_SMALL
        )
        self.status_label.pack(side=tk.LEFT, padx=_px(10))
        
        DarkButton(
            topbar, text="🗑 Limpar Tudo",
            bg=CORES["bg_sidebar"], fg=CORES["text_sec"],
            command=self._limpar_tudo
        ).pack(side=tk.RIGHT, padx=_px(10), pady=_px(5))
        
        DarkButton(
            topbar, text="▶ Resolver",
            bg=CORES["success"], command=self.processar
        ).pack(side=tk.RIGHT, padx=_px(3), pady=_px(5))
    
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=CORES["bg_sidebar"], width=_px(195))
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        def section(text):
            tk.Label(
                sidebar, text=text.upper(),
                bg=CORES["bg_sidebar"], fg=CORES["sidebar_sect"],
                font=("Segoe UI", _fs(7), "bold"), anchor="w"
            ).pack(fill=tk.X, padx=_px(10), pady=(_px(8), 0))
        
        def add_button(key, icon, text):
            btn = SidebarButton(
                sidebar, text=text, icon=icon,
                command=lambda k=key: self._activate_sidebar_tab(k)
            )
            btn.pack(fill=tk.X, padx=6)
            self.sidebar_buttons[key] = btn
        
        section("Modelo")
        add_button("geometria", "⬛", "Geometria")
        add_button("apoios", "▽", "Apoios")
        
        separador(sidebar)
        
        section("Cargas")
        add_button("pontuais", "↓", "Cargas Pontuais")
        add_button("momentos", "↺", "Momentos")
        add_button("distribuidas", "≡", "Dist. Distribuídas")
        
        tk.Frame(sidebar, bg=CORES["bg_sidebar"]).pack(
            fill=tk.BOTH, expand=True
        )
        
        separador(sidebar)
        
        tk.Label(
            sidebar, text="v0.8.9 - Alpha",
            bg=CORES["bg_sidebar"], fg=CORES["text_muted"],
            font=("Segoe UI", _fs(7))
        ).pack(pady=_px(5))
    
    def _activate_sidebar_tab(self, key):
        """Ativa uma aba da sidebar e renderiza o painel correspondente."""
        # Verificar se o panel_body já existe
        if not hasattr(self, 'panel_body') or self.panel_body is None:
            return
        
        for k, btn in self.sidebar_buttons.items():
            btn.set_active(k == key)
        
        self._render_panel(key)
    
    def _build_central_area(self, parent):
        centro = tk.Frame(parent, bg=CORES["bg_main"])
        centro.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        split = tk.Frame(centro, bg=CORES["bg_main"])
        split.pack(fill=tk.BOTH, expand=True)
        
        # Área dos gráficos
        self.canvas_area = tk.Frame(split, bg=CORES["bg_canvas"])
        self.canvas_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Inicializar matplotlib com tamanho proporcional à tela
        fig_w = 10 * _SCALE
        fig_h = max(5.5, 8 * _SCALE)
        self.fig, (self.ax_viga, self.ax_v, self.ax_m) = plt.subplots(
            3, 1, figsize=(fig_w, fig_h),
            height_ratios=[1.2, 2, 2],
            facecolor=CORES["bg_canvas"]
        )
        
        # Ajustar espaçamento entre subplots
        self.fig.subplots_adjust(hspace=0.45, top=0.95, bottom=0.07, left=0.10, right=0.97)
        
        self.fig_canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_area)
        self.fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.renderer = VigaRenderer(
            self.fig, self.ax_viga, self.ax_v, self.ax_m, self.fig_canvas
        )
        
        # Painel de configuração (à direita) — largura responsiva
        config_w = _px(270)
        self.config_panel = tk.Frame(
            split, bg=CORES["bg_panel"], width=config_w,
            highlightthickness=1, highlightbackground=CORES["border"]
        )
        self.config_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_panel.pack_propagate(False)
        
        # Título do painel
        self.panel_title = tk.Label(
            self.config_panel, text="Geometria da Viga",
            bg=CORES["bg_sidebar"], fg=CORES["text_pri"],
            font=FONT_TITLE, anchor="w", padx=12, pady=10
        )
        self.panel_title.pack(fill=tk.X)
        tk.Frame(self.config_panel, height=1, bg=CORES["border"]).pack(fill=tk.X)
        
        # Corpo do painel (onde o conteúdo muda)
        self.panel_body = tk.Frame(self.config_panel, bg=CORES["bg_panel"])
        self.panel_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        
        # Barra inferior de resultados
        self._build_bottom_bar(centro)
    
    def _build_bottom_bar(self, parent):
        """Constroi a barra inferior com os resultados."""
        bottom = tk.Frame(
            parent, bg=CORES["bg_sidebar"],
            highlightthickness=1, highlightbackground=CORES["border"]
        )
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Cartões de resultado - CORRIGIDO: usar chaves consistentes
        chaves = ["pessoa1", "pessoa2", "pessoa3", "pessoa4"]  # sem acentos para consistência
        
        for titulo, chave in zip(["ANDRÉ FELLIPE MEIRA ALVES", "ESTER PANZINI PACHECO", "GABRIEL ALMEIDA DELLA CROCE", "GUSTAVO HENRIQUE PEREIRA FERREIRA"], chaves):
            frame = tk.Frame(
                bottom, bg=CORES["bg_panel"],
                highlightthickness=1, highlightbackground=CORES["border"],
                padx=_px(10), pady=_px(4)
            )
            frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=_px(4), pady=_px(4))
            
            tk.Label(
                frame, text=titulo, bg=CORES["bg_panel"],
                fg=CORES["sidebar_sect"], font=("Segoe UI", _fs(7), "bold")
            ).pack(anchor="w")
            
            lbl = tk.Label(
                frame, text="---", bg=CORES["bg_panel"],
                fg=CORES["text_pri"], font=FONT_MONO_B,
                justify=tk.LEFT
            )
            lbl.pack(anchor="w")
            
            self.result_labels[chave] = lbl  # Usar chave sem acento
    
    # ══════════════════════════════════════════════════════════════════════════
    # RENDERIZAÇÃO DO PAINEL DE CONFIGURAÇÃO
    # ══════════════════════════════════════════════════════════════════════════
    def _render_panel(self, tab_key):
        """Renderiza o conteúdo do painel direito conforme a aba selecionada."""
        if self.panel_body is None:
            return
        
        # Limpar painel
        for w in self.panel_body.winfo_children():
            w.destroy()
        
        if tab_key == "geometria":
            self.panel_title.config(text="Geometria da Viga")
            self._render_geometria_panel()
        elif tab_key == "apoios":
            self.panel_title.config(text="Configuração dos Apoios")
            self._render_apoios_panel()
        else:
            self.panel_title.config(text="Adicionar Carregamento")
            self._render_cargas_panel(tab_key)
    
    def _render_geometria_panel(self):
        self.panel_body.columnconfigure(1, weight=1)
        
        tk.Label(
            self.panel_body, text="Comprimento Total L [m]:",
            bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_BODY
        ).grid(row=0, column=0, sticky="w", pady=5)
        
        self.entry_L = DarkEntry(self.panel_body, width=12)
        self.entry_L.insert(0, str(self.comprimento_viga))
        self.entry_L.grid(row=0, column=1, sticky="ew", pady=5, padx=(8, 0))
        
        tk.Label(
            self.panel_body, text="\nDefina o comprimento total da viga\nem metros.",
            bg=CORES["bg_panel"], fg=CORES["text_muted"], font=FONT_SMALL,
            justify=tk.LEFT
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        
        DarkButton(
            self.panel_body, text="Aplicar Geometria",
            bg=CORES["primary"],
            command=self._aplicar_geometria
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(20, 0), ipady=4)
    
    def _render_apoios_panel(self):
        self.panel_body.columnconfigure(1, weight=1)
        
        tk.Label(
            self.panel_body, text="Tipo de Apoio:",
            bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_BODY
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        
        self.var_apoio_tipo = tk.StringVar(value=self.tipo_apoio)
        
        for idx, (text, val) in enumerate([
            ("Bi-Apoiada (Pino + Rolete)", "simples"),
            ("Engastada", "engaste")
        ]):
            rb = tk.Radiobutton(
                self.panel_body, text=text, variable=self.var_apoio_tipo,
                value=val, bg=CORES["bg_panel"], fg=CORES["text_sec"],
                selectcolor=CORES["bg_sidebar"],
                activebackground=CORES["bg_panel"],
                activeforeground=CORES["text_pri"],
                font=FONT_BODY, command=self._atualizar_apoios
            )
            rb.grid(row=idx + 1, column=0, columnspan=2, sticky="w", pady=3)
        
        # Frame para posições dos apoios
        self.apoios_frame = tk.Frame(self.panel_body, bg=CORES["bg_panel"])
        self.apoios_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        self.apoios_frame.columnconfigure(1, weight=1)
        
        self._atualizar_apoios()
        
        DarkButton(
            self.panel_body, text="Aplicar Apoios",
            bg=CORES["primary"],
            command=self._aplicar_apoios
        ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(15, 0), ipady=4)
    
    def _atualizar_apoios(self):
        """Atualiza os campos de posição dos apoios conforme o tipo."""
        if not hasattr(self, 'apoios_frame'):
            return
        
        for w in self.apoios_frame.winfo_children():
            w.destroy()
        
        tipo = self.var_apoio_tipo.get()
        
        if tipo == "engaste":
            tk.Label(
                self.apoios_frame, text="Pos. Engaste [m]:",
                bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_BODY
            ).grid(row=0, column=0, sticky="w", pady=5)
            
            self.entry_apoio_a = DarkEntry(self.apoios_frame, width=12)
            self.entry_apoio_a.insert(0, str(self.pos_apoio_a))
            self.entry_apoio_a.grid(row=0, column=1, sticky="ew", pady=5, padx=(8, 0))
        
        else:
            tk.Label(
                self.apoios_frame, text="Pos. Pino [m]:",
                bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_BODY
            ).grid(row=0, column=0, sticky="w", pady=5)
            
            self.entry_apoio_a = DarkEntry(self.apoios_frame, width=12)
            self.entry_apoio_a.insert(0, str(self.pos_apoio_a))
            self.entry_apoio_a.grid(row=0, column=1, sticky="ew", pady=5, padx=(8, 0))
            
            tk.Label(
                self.apoios_frame, text="Pos. Rolete [m]:",
                bg=CORES["bg_panel"], fg=CORES["text_sec"], font=FONT_BODY
            ).grid(row=1, column=0, sticky="w", pady=5)
            
            self.entry_apoio_b = DarkEntry(self.apoios_frame, width=12)
            self.entry_apoio_b.insert(0, str(self.pos_apoio_b))
            self.entry_apoio_b.grid(row=1, column=1, sticky="ew", pady=5, padx=(8, 0))
    
    def _render_cargas_panel(self, tipo_carga):
        """Renderiza o painel de cargas para o tipo selecionado."""
        self.panel_body.columnconfigure(0, weight=1)
        
        # Mapear tipo de aba para tipo de carga
        tipo_map = {
            "pontuais": ("pontual", "Cargas Pontuais", "Pontual (Força)"),
            "momentos": ("momento", "Momentos Concentrados", "Momento Concentrado"),
            "distribuidas": ("distrib", "Cargas Distribuídas", "Distribuída Constante"),
        }
        
        if tipo_carga in tipo_map:
            tipo_filtro, titulo, tipo_modal_default = tipo_map[tipo_carga]
            
            tk.Label(
                self.panel_body, text=titulo,
                bg=CORES["bg_panel"], fg=CORES["text_pri"],
                font=FONT_HEADING
            ).pack(anchor="w", pady=(0, 10))
            
            # Lista de cargas
            lista_frame = tk.Frame(self.panel_body, bg=CORES["bg_canvas"])
            lista_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Colunas específicas por tipo
            if tipo_filtro == "pontual":
                colunas = ("pos", "val")
                headings = [("pos", "Pos. (m)", 80), ("val", "Valor (N)", 110)]
            elif tipo_filtro == "momento":
                colunas = ("pos", "val")
                headings = [("pos", "Pos. (m)", 80), ("val", "Valor (N.m)", 110)]
            else:
                colunas = ("xi", "xf", "qi", "qf")
                headings = [("xi", "x ini", 50), ("xf", "x fim", 50),
                            ("qi", "q ini", 55), ("qf", "q fim", 55)]
            
            self.tree_cargas = ttk.Treeview(
                lista_frame, columns=colunas,
                show="headings", height=6
            )
            for col, head, w in headings:
                self.tree_cargas.heading(col, text=head)
                self.tree_cargas.column(col, width=w, anchor="center")
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(
                lista_frame, orient="vertical",
                command=self.tree_cargas.yview
            )
            self.tree_cargas.configure(yscrollcommand=scrollbar.set)
            
            self.tree_cargas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Preencher com cargas existentes do tipo filtrado
            self._tree_tipo_atual = tipo_filtro
            for i, c in enumerate(self.cargas_adicionadas):
                if c["tipo"] == tipo_filtro:
                    self._adicionar_item_tree_tipado(c, i, tipo_filtro)
            
            # Botões
            btn_frame = tk.Frame(self.panel_body, bg=CORES["bg_panel"])
            btn_frame.pack(fill=tk.X, pady=(0, 5))
            
            DarkButton(
                btn_frame, text="➕ Adicionar",
                bg=CORES["primary"],
                command=lambda t=tipo_modal_default: self._abrir_modal_carga_tipo(t)
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            DarkButton(
                btn_frame, text="🗑 Remover",
                bg=CORES["danger"],
                command=self._remover_carga_selecionada
            ).pack(side=tk.RIGHT)
    
    def _adicionar_item_tree_tipado(self, carga, idx, tipo_filtro):
        """Adiciona uma carga à treeview com colunas específicas do tipo."""
        if not self.tree_cargas:
            return
        if tipo_filtro == "pontual":
            values = (f"{carga['pos']:.2f}", f"{carga['val']:.2f}")
        elif tipo_filtro == "momento":
            values = (f"{carga['pos']:.2f}", f"{carga['val']:.2f}")
        else:
            qf = carga.get('qf', carga.get('qi', 0))
            values = (f"{carga['xi']:.2f}", f"{carga['xf']:.2f}",
                      f"{carga['qi']:.2f}", f"{qf:.2f}")
        self.tree_cargas.insert("", tk.END, iid=str(idx), values=values)
    
    def _adicionar_item_tree(self, carga, idx):
        """Adiciona uma carga à treeview (compatibilidade)."""
        tipo_filtro = carga.get("tipo", "pontual")
        self._adicionar_item_tree_tipado(carga, idx, tipo_filtro)
    
    def _abrir_modal_carga_tipo(self, tipo_default):
        """Abre o modal para adicionar uma carga com tipo pré-selecionado."""
        if self.comprimento_viga <= 0:
            DialogoErro(
                self, "Geometria Necessária",
                "Defina o comprimento da viga antes de adicionar cargas."
            )
            return
        ModalNovaCarga(self, self.comprimento_viga, self._receber_nova_carga, tipo_default)
    
    # ══════════════════════════════════════════════════════════════════════════
    # AÇÕES DO USUÁRIO
    # ══════════════════════════════════════════════════════════════════════════
    def _aplicar_geometria(self):
        """Aplica a geometria da viga."""
        try:
            L = parse_float(self.entry_L.get())
            if L <= 0:
                raise ValueError("Comprimento deve ser maior que zero.")
            
            self.comprimento_viga = L
            
            # Atualizar posições dos apoios se necessário
            if self.pos_apoio_a > L:
                self.pos_apoio_a = 0.0
            if self.pos_apoio_b > L:
                self.pos_apoio_b = L
            
            # Remover cargas fora da viga
            self.cargas_adicionadas = [
                c for c in self.cargas_adicionadas
                if self._carga_dentro_da_viga(c)
            ]
            
            # Atualizar a visualização
            self._renderizar_esquema()
            
            # Recarregar painel atual para refletir mudanças
            for key, btn in self.sidebar_buttons.items():
                if btn.active:
                    self._render_panel(key)
                    break

            self.processar()
            
            if self.status_label:
                self.status_label.config(text=f"✅ Geometria aplicada: L={L:.1f}m")
            
        except ValueError as e:
            DialogoErro(self, "Geometria Inválida", str(e))
    
    def _carga_dentro_da_viga(self, carga):
        """Verifica se uma carga está dentro dos limites da viga."""
        if carga["tipo"] in ["pontual", "momento"]:
            return 0 <= carga["pos"] <= self.comprimento_viga
        else:
            return (0 <= carga["xi"] <= self.comprimento_viga and
                    0 < carga["xf"] <= self.comprimento_viga)
    
    def _aplicar_apoios(self):
        """Aplica a configuração de apoios."""
        try:
            tipo = self.var_apoio_tipo.get()
            pos_a = parse_float(self.entry_apoio_a.get())
            
            if not (0 <= pos_a <= self.comprimento_viga):
                raise ValueError(f"Posição do apoio fora da viga (0 a {self.comprimento_viga} m)")
            
            if tipo == "simples":
                pos_b = parse_float(self.entry_apoio_b.get())
                if not (0 <= pos_b <= self.comprimento_viga):
                    raise ValueError(f"Posição do rolete fora da viga (0 a {self.comprimento_viga} m)")
                if abs(pos_a - pos_b) < 1e-6:
                    raise ValueError("Os apoios não podem estar na mesma posição.")
                self.pos_apoio_b = pos_b
            
            self.tipo_apoio = tipo
            self.pos_apoio_a = pos_a
            
            self._renderizar_esquema()

            self.processar()

            if self.status_label:
                self.status_label.config(
                    text=f"✅ Apoios configurados: {tipo} (xA={pos_a:.1f}m)"
                )
            
        except ValueError as e:
            DialogoErro(self, "Apoio Inválido", str(e))
    
    def _abrir_modal_carga(self):
        """Abre o modal para adicionar uma nova carga."""
        if self.comprimento_viga <= 0:
            DialogoErro(
                self, "Geometria Necessária",
                "Defina o comprimento da viga antes de adicionar cargas."
            )
            return
        
        ModalNovaCarga(self, self.comprimento_viga, self._receber_nova_carga)
    
    def _receber_nova_carga(self, dados):
        """Recebe os dados de uma nova carga."""
        self.cargas_adicionadas.append(dados)
        
        if self.status_label:
            self.status_label.config(text=f"✅ Carga adicionada: {dados['tipo_str']}")
        
        # Recarregar painel atual para mostrar a nova carga
        for key, btn in self.sidebar_buttons.items():
            if btn.active:
                self._render_panel(key)
                break
        
        self._renderizar_esquema()
        self.processar()
    
    def _remover_carga_selecionada(self):
        """Remove a carga selecionada na treeview."""
        if self.tree_cargas is None:
            return
        
        selecionado = self.tree_cargas.selection()
        if selecionado:
            idx = int(selecionado[0])
            if 0 <= idx < len(self.cargas_adicionadas):
                self.cargas_adicionadas.pop(idx)
                
                # Recarregar a aba atual
                for key, btn in self.sidebar_buttons.items():
                    if btn.active:
                        self._render_panel(key)
                        break
                
                self._renderizar_esquema()
                self.processar()
                if self.status_label:
                    self.status_label.config(text="🗑 Carga removida")
    
    def _limpar_tudo(self):
        """Limpa todos os dados e resultados."""
        self.cargas_adicionadas.clear()
        self.resultados = None
        
        # Limpar labels de resultado
        for chave in ["reações", "cortante", "momento"]:
            if chave in self.result_labels and self.result_labels[chave]:
                self.result_labels[chave].config(text="---")
        
        self.renderer.renderizar_empty_state()
        
        # Recarregar painel atual
        for key, btn in self.sidebar_buttons.items():
            if btn.active:
                self._render_panel(key)
                break
        
        if self.status_label:
            self.status_label.config(text="🗑 Todos os dados foram limpos")
    
    def _renderizar_esquema(self):
        """Renderiza o diagrama de corpo livre com as cargas atuais."""
        if self.comprimento_viga > 0 and hasattr(self, 'renderer'):
            self.renderer.renderizar_esquema(
                self.comprimento_viga,
                self.tipo_apoio,
                self.pos_apoio_a,
                self.pos_apoio_b if self.tipo_apoio == "simples" else None,
                self.cargas_adicionadas
            )
    
    def processar(self):
        """Executa o cálculo estrutural completo."""
        try:
            if self.comprimento_viga <= 0:
                raise ValueError("Defina o comprimento da viga primeiro.")
            
            # Validar apoios
            if self.tipo_apoio == "simples":
                if abs(self.pos_apoio_a - self.pos_apoio_b) < 1e-6:
                    raise ValueError("Apoios não podem coincidir.")
            
            # Criar engine
            viga = VigaEngine(self.comprimento_viga)
            
            for c in self.cargas_adicionadas:
                if c["tipo"] == "pontual":
                    viga.adicionar_carga_pontual(c["pos"], c["val"])
                elif c["tipo"] == "momento":
                    viga.adicionar_momento(c["pos"], c["val"])
                elif c["tipo"] == "distrib":
                    viga.adicionar_carga_distribuida(
                        c["qi"], c["qf"], c["xi"], c["xf"]
                    )
            
            # Calcular
            xb = self.pos_apoio_b if self.tipo_apoio == "simples" else None
            viga.calcular_reacoes(self.tipo_apoio, self.pos_apoio_a, xb)
            self.resultados = viga.calcular_esforcos()
            
            # Atualizar labels de resultado - CORRIGIDO: usar chaves sem acento
            if self.resultados and self.result_labels:
                # Reações
                reacoes_text = ""
                for r in viga.reacoes_calculadas:
                    reacoes_text += f"{r.nome} = {r.valor:+.2f}\n"
                
                if "reações" in self.result_labels and self.result_labels["reações"]:
                    self.result_labels["reações"].config(
                        text=reacoes_text.strip() if reacoes_text else "Sem reações"
                    )
                
                # Cortante
                if "cortante" in self.result_labels and self.result_labels["cortante"]:
                    self.result_labels["cortante"].config(
                        text=f"Máx (+): {self.resultados['V_max']:+.2f} N\n"
                             f"Mín (-): {self.resultados['V_min']:+.2f} N"
                    )
                
                # Momento
                if "momento" in self.result_labels and self.result_labels["momento"]:
                    self.result_labels["momento"].config(
                        text=f"Máx (+): {self.resultados['M_max']:+.2f} N.m\n"
                             f"Mín (-): {self.resultados['M_min']:+.2f} N.m"
                    )
            
            # Renderizar gráficos
            self.renderer.renderizar_esquema(
                self.comprimento_viga,
                self.tipo_apoio,
                self.pos_apoio_a,
                self.pos_apoio_b if self.tipo_apoio == "simples" else None,
                self.cargas_adicionadas
            )
            
            self.renderer.renderizar_diagramas(
                self.resultados,
                self.comprimento_viga
            )
            
            if self.status_label:
                self.status_label.config(text="✅ Cálculo concluído com sucesso!")
            
        except Exception as e:
            DialogoErro(
                self, "Erro no Cálculo",
                str(e),
                traceback.format_exc()
            )
            if self.status_label:
                self.status_label.config(text="❌ Erro no cálculo")

# ══════════════════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = VigaApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\nAplicação encerrada com segurança.")
