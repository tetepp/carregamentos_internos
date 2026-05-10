# Calculadora de Carregamentos Internos em Vigas

Programa desenvolvido para a disciplina de **Resistência dos Materiais** do curso de Engenharia de Computação — Instituto Federal de Mato Grosso do Sul, Campus Três Lagoas.

Calcula e gera os diagramas de **força cortante** e **momento fletor** em vigas com carregamentos diversos.

---

## Funcionalidades

- Reações nos apoios (pino e rolete / engaste)
- Cargas pontuais concentradas
- Cargas distribuídas constantes
- Cargas distribuídas lineares (trapezoidais)
- Momentos de binário concentrados
- Cálculo numérico da força cortante e do momento fletor
- Valores máximos e mínimos de V e M
- API REST (Flask) para integração com front-end

---

## Estrutura do projeto

```
.
├── viga.py          # Lógica de cálculo (classe Viga)
├── api.py           # API Flask (opcional, para front-end)
├── requirements.txt # Dependências Python
└── README.md
```

---

## Requisitos

- Python 3.8+
- numpy
- flask
- flask-cors

Instale as dependências:

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
numpy
flask
flask-cors
```

---

## Como usar

### Modo Python direto

```python
from viga import Viga

viga = Viga(comprimento=10)

# Reações nos apoios
viga.adicionar_reacao(pos=0, valor=50)
viga.adicionar_reacao(pos=10, valor=50)

# Carga pontual
viga.adicionar_carga_pontual(pos=5, valor=-100)

# Carga distribuída constante
viga.adicionar_carga_distribuida_constante(
    intensidade=-20,
    inicio=0,
    fim=10
)

# Carga distribuída linear
viga.adicionar_carga_distribuida_linear(
    q_inicial=0,
    q_final=-30,
    inicio=2,
    fim=8
)

# Momento de binário concentrado
viga.adicionar_momento(pos=3, valor=40)

# Calcular
resultado = viga.calcular(dx=0.01)

print(resultado["forca_cortante_max"])
print(resultado["momento_fletor_min"])
```

---

### Modo API (para front-end)

Inicie o servidor:

```bash
python api.py
```

O servidor sobe em `http://localhost:5000`.

**Endpoint:** `POST /calcular`

**Corpo da requisição (JSON):**

```json
{
  "comprimento": 10,
  "reacoes": [
    { "pos": 0, "valor": 50 },
    { "pos": 10, "valor": 50 }
  ],
  "cargas_pontuais": [
    { "pos": 5, "valor": -100 }
  ],
  "cargas_distribuidas": [
    {
      "tipo": "constante",
      "q": -20,
      "inicio": 0,
      "fim": 10
    },
    {
      "tipo": "linear",
      "q_inicial": 0,
      "q_final": -30,
      "inicio": 2,
      "fim": 8
    }
  ],
  "momentos": [
    { "pos": 3, "valor": 40 }
  ]
}
```

**Resposta (JSON):**

```json
{
  "x": [0.0, 0.01, 0.02, "..."],
  "forca_cortante": [50.0, 49.8, "..."],
  "momento_fletor": [0.0, 0.5, "..."],
  "forca_cortante_max": 50.0,
  "forca_cortante_min": -50.0,
  "momento_fletor_max": 125.0,
  "momento_fletor_min": 0.0
}
```

**Exemplo com JavaScript (fetch):**

```javascript
const dados = {
  comprimento: 10,
  reacoes: [{ pos: 0, valor: 50 }, { pos: 10, valor: 50 }],
  cargas_pontuais: [{ pos: 5, valor: -100 }],
  cargas_distribuidas: [],
  momentos: []
};

const res = await fetch("http://localhost:5000/calcular", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(dados)
});

const resultado = await res.json();
console.log(resultado.forca_cortante_max);
console.log(resultado.momento_fletor);
```

---

## Convenção de sinais

| Grandeza | Positivo | Negativo |
|---|---|---|
| Reação / carga pontual | Para cima (↑) | Para baixo (↓) |
| Carga distribuída (`q`) | Para cima (↑) | Para baixo (↓) |
| Momento de binário | Anti-horário | Horário |

---

## Detalhes do cálculo

### Força cortante

Calculada pelo **método das seções**: para cada ponto x ao longo da viga, soma-se todas as forças à esquerda da seção:

```
V(x) = ΣReações(pos ≤ x) + ΣCargas pontuais(pos ≤ x) + ∫cargas distribuídas de 0 até x
```

Para cargas distribuídas lineares, a integral é calculada pela **fórmula do trapézio** (resultado exato):

```
área = s × (q_inicial + q(s)) / 2
```

onde `s` é o comprimento coberto até o ponto x e `q(s)` é a intensidade nesse ponto.

### Momento fletor

Calculado por **integração numérica** da força cortante, usando a relação:

```
dM/dx = V  →  M(x) = M(x - dx) + V(x) × dx
```

Momentos de binário concentrados são aplicados diretamente como descontinuidade no diagrama M.

---

## Parâmetros da classe Viga

### `Viga(comprimento)`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `comprimento` | `float` | Comprimento total da viga (m) |

### `adicionar_reacao(pos, valor)`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `pos` | `float` | Posição da reação (m) |
| `valor` | `float` | Intensidade da reação (N ou kN) |

### `adicionar_carga_pontual(pos, valor)`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `pos` | `float` | Posição da carga (m) |
| `valor` | `float` | Intensidade (positivo = ↑, negativo = ↓) |

### `adicionar_carga_distribuida_constante(intensidade, inicio, fim)`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `intensidade` | `float` | Valor constante da carga (N/m) |
| `inicio` | `float` | Posição de início (m) |
| `fim` | `float` | Posição de fim (m) |

### `adicionar_carga_distribuida_linear(q_inicial, q_final, inicio, fim)`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `q_inicial` | `float` | Intensidade no início (N/m) |
| `q_final` | `float` | Intensidade no fim (N/m) |
| `inicio` | `float` | Posição de início (m) |
| `fim` | `float` | Posição de fim (m) |

### `adicionar_momento(pos, valor)`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `pos` | `float` | Posição do momento (m) |
| `valor` | `float` | Intensidade (N·m) |

### `calcular(dx=0.01)`

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `dx` | `float` | Passo de discretização (m). Menor = mais preciso e mais lento |

**Retorno:** dicionário com as chaves:

| Chave | Tipo | Descrição |
|---|---|---|
| `x` | `list[float]` | Posições ao longo da viga |
| `forca_cortante` | `list[float]` | V em cada ponto de x |
| `momento_fletor` | `list[float]` | M em cada ponto de x |
| `forca_cortante_max` | `float` | Valor máximo de V |
| `forca_cortante_min` | `float` | Valor mínimo de V |
| `momento_fletor_max` | `float` | Valor máximo de M |
| `momento_fletor_min` | `float` | Valor mínimo de M |

---

## Disciplina

**Resistência dos Materiais — 2026**  
Instituto Federal de Mato Grosso do Sul — Campus Três Lagoas  
Professor: Carlos Vinicius Xavier Bessa  
Curso: Engenharia de Computação
