"""Gera um gráfico SVG das contribuições no GitHub nos últimos 31 dias."""

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

DIAS = 31
LARGURA, ALTURA = 1200, 420
MARGEM = {"topo": 80, "direita": 40, "baixo": 60, "esquerda": 70}

FUNDO = "#0D1117"
TEXTO = "#C9D1D9"
GRADE = "#21262D"
DESTAQUE = "#E4A24F"
PONTO = "#F5C27A"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def buscar_contribuicoes(login, token):
    hoje = datetime.now(timezone.utc).date()
    inicio = hoje - timedelta(days=DIAS - 1)
    corpo = json.dumps({
        "query": QUERY,
        "variables": {
            "login": login,
            "from": f"{inicio}T00:00:00Z",
            "to": f"{hoje}T23:59:59Z",
        },
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        dados = json.load(resp)
    if "errors" in dados:
        sys.exit(f"Erro na API do GitHub: {dados['errors']}")

    semanas = dados["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    por_dia = {
        d["date"]: d["contributionCount"]
        for semana in semanas
        for d in semana["contributionDays"]
    }
    return [
        (inicio + timedelta(days=i), por_dia.get(str(inicio + timedelta(days=i)), 0))
        for i in range(DIAS)
    ]


def gerar_svg(dias):
    area_l = LARGURA - MARGEM["esquerda"] - MARGEM["direita"]
    area_a = ALTURA - MARGEM["topo"] - MARGEM["baixo"]
    base = MARGEM["topo"] + area_a

    maximo = max(c for _, c in dias)
    passo = max(1, -(-maximo // 4))  # 4 linhas de grade, arredondado para cima
    topo_escala = passo * 4

    def x(i):
        return MARGEM["esquerda"] + i * area_l / (len(dias) - 1)

    def y(valor):
        return base - valor * area_a / topo_escala

    pontos = [(x(i), y(c)) for i, (_, c) in enumerate(dias)]
    linha = " ".join(f"{px:.1f},{py:.1f}" for px, py in pontos)
    area = f"{pontos[0][0]:.1f},{base} {linha} {pontos[-1][0]:.1f},{base}"

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LARGURA} {ALTURA}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
        "<defs>",
        '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0" stop-color="{DESTAQUE}" stop-opacity="0.45"/>',
        f'<stop offset="1" stop-color="{DESTAQUE}" stop-opacity="0.02"/>',
        "</linearGradient>",
        "</defs>",
        f'<rect width="{LARGURA}" height="{ALTURA}" rx="8" fill="{FUNDO}"/>',
        f'<text x="{LARGURA / 2}" y="45" text-anchor="middle" font-size="24" '
        f'font-weight="600" fill="{DESTAQUE}">Contribuições nos últimos {DIAS} dias</text>',
    ]

    for n in range(5):
        valor = passo * n
        py = y(valor)
        partes.append(
            f'<line x1="{MARGEM["esquerda"]}" y1="{py:.1f}" x2="{LARGURA - MARGEM["direita"]}" '
            f'y2="{py:.1f}" stroke="{GRADE}" stroke-width="1"/>'
        )
        partes.append(
            f'<text x="{MARGEM["esquerda"] - 14}" y="{py + 5:.1f}" text-anchor="end" '
            f'font-size="14" fill="{TEXTO}">{valor}</text>'
        )

    for i, (dia, _) in enumerate(dias):
        if i % 2 == 0 or i == len(dias) - 1:
            partes.append(
                f'<text x="{x(i):.1f}" y="{base + 28}" text-anchor="middle" '
                f'font-size="13" fill="{TEXTO}">{dia.day}</text>'
            )

    partes.append(f'<polygon points="{area}" fill="url(#area)"/>')
    partes.append(
        f'<polyline points="{linha}" fill="none" stroke="{DESTAQUE}" stroke-width="3" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
    )
    for (px, py), (dia, c) in zip(pontos, dias):
        partes.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{PONTO}" stroke="{FUNDO}" '
            f'stroke-width="2"><title>{dia:%d/%m}: {c}</title></circle>'
        )

    partes.append(
        f'<text x="{LARGURA - MARGEM["direita"]}" y="{ALTURA - 12}" text-anchor="end" '
        f'font-size="12" fill="{TEXTO}" opacity="0.6">'
        f'Atualizado em {date.today():%d/%m/%Y}</text>'
    )
    partes.append("</svg>")
    return "\n".join(partes)


def main():
    login = os.environ["GITHUB_USER"]
    token = os.environ["GITHUB_TOKEN"]
    saida = sys.argv[1] if len(sys.argv) > 1 else "dist/activity-graph.svg"

    os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        f.write(gerar_svg(buscar_contribuicoes(login, token)))
    print(f"Gráfico salvo em {saida}")


if __name__ == "__main__":
    main()
