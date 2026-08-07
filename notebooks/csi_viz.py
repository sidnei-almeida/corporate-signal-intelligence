"""Identidade visual compartilhada pelos cadernos do Corporate Signal Intelligence.

Cada figura deste projeto atende a dois públicos ao mesmo tempo: quem lê o caderno e
quem lê o business case em LaTeX. Este módulo mantém os dois consistentes, com uma
paleta, um estilo e um caminho de exportação únicos.

**Dimensionamento para impressão.** As figuras são desenhadas na largura física em
que serão impressas (16 cm, a largura de texto do documento). Isso evita a redução
de escala que tornava os rótulos ilegíveis: uma figura de 9 polegadas reduzida para
4,6 no PDF encolhe a fonte pela metade. Desenhando no tamanho final, 10 pt continuam
10 pt na página.

A paleta categórica é validada para deficiência de visão de cores: as oito posições
superam o piso de separação para pares adjacentes (delta-E mínimo de 9,1) e o piso de
visão normal (19,6) sobre a superfície adotada. As cores são atribuídas em ordem fixa e nunca
recicladas; uma nona série vira faceta ou categoria "Outros", jamais uma cor nova.

Uso
---
    import csi_viz as viz
    viz.apply_style()
    fig, ax = plt.subplots(figsize=viz.FIG_WIDE)
    ...
    viz.save_fig(fig, "market_coverage")
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt

# --------------------------------------------------------------------------
# Paleta
# --------------------------------------------------------------------------

# Posições categóricas, em ordem de atribuição. Nunca reciclar após a oitava.
CATEGORICAL = [
    "#2a78d6",  # 1 azul
    "#eb6834",  # 2 laranja
    "#1baf7a",  # 3 água
    "#eda100",  # 4 amarelo
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 verde
    "#4a3aa7",  # 7 violeta
    "#e34948",  # 8 vermelho
]

# Gráficos de dispersão e pequenos múltiplos colocam todos os pares na tela ao mesmo
# tempo; apenas as três primeiras posições vencem os pisos nessa condição.
CATEGORICAL_ALL_PAIRS = CATEGORICAL[:3]

# Rampa de matiz única para magnitude (claro -> escuro).
SEQUENTIAL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
]

# Divergente: dois polos que se leem como opostos, com cinza neutro no meio.
DIVERGING_LOW = "#2a78d6"
DIVERGING_MID = "#f0efec"
DIVERGING_HIGH = "#d03b3b"

# Reservadas para estado, nunca para uma série.
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

# Superfície e tinta.
SURFACE = "#fcfcfb"
INK_PRIMARY = "#16161a"
INK_SECONDARY = "#4a4a52"
INK_MUTED = "#8a8a93"
GRIDLINE = "#e8e8ec"
BASELINE = "#c9c9d1"

FONT_STACK = ["Roboto", "Noto Sans", "Liberation Sans", "DejaVu Sans"]

# Tamanhos em polegadas, iguais à largura de texto do documento (16 cm = 6,3 pol).
FIG_WIDE = (6.3, 3.1)
FIG_TALL = (6.3, 4.0)
FIG_SQUARE = (6.3, 5.4)
FIG_PAIR = (6.3, 2.7)

IMAGES_DIR = Path("images/figures")


def sequential_cmap(name: str = "csi_blue"):
    """Mapa contínuo construído a partir da rampa sequencial de matiz única."""
    return mpl.colors.LinearSegmentedColormap.from_list(name, SEQUENTIAL)


def diverging_cmap(name: str = "csi_div"):
    """Mapa contínuo para magnitudes com sinal (azul <- cinza -> vermelho)."""
    return mpl.colors.LinearSegmentedColormap.from_list(
        name, [DIVERGING_LOW, DIVERGING_MID, DIVERGING_HIGH]
    )


# --------------------------------------------------------------------------
# Estilo
# --------------------------------------------------------------------------

def apply_style() -> None:
    """Instala o estilo do projeto como padrão do matplotlib.

    Marcas finas, moldura discreta, sem eixos superior e direito. A tinta fica
    nos dados; a estrutura sai do caminho.
    """
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "figure.dpi": 120,
        "savefig.facecolor": SURFACE,
        "savefig.bbox": "tight",
        "savefig.dpi": 300,
        "savefig.pad_inches": 0.02,

        "axes.facecolor": SURFACE,
        "axes.edgecolor": BASELINE,
        "axes.linewidth": 0.6,
        "axes.labelcolor": INK_SECONDARY,
        "axes.labelsize": 9,
        "axes.labelpad": 8,
        "axes.titlecolor": INK_PRIMARY,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,

        "grid.color": GRIDLINE,
        "grid.linewidth": 0.55,

        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 5,
        "ytick.major.pad": 5,

        "lines.linewidth": 1.6,
        "lines.markersize": 3.5,
        "lines.solid_capstyle": "round",
        "lines.dash_capstyle": "round",

        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.labelcolor": INK_SECONDARY,
        "legend.handlelength": 1.4,
        "legend.handletextpad": 0.5,
        "legend.columnspacing": 1.2,
        "legend.borderpad": 0.0,

        "font.family": "sans-serif",
        "font.sans-serif": FONT_STACK,
        "font.size": 9.5,
        "text.color": INK_PRIMARY,

        "figure.autolayout": False,
        "patch.linewidth": 0.0,
    })


# --------------------------------------------------------------------------
# Legibilidade de texto sobre os dados
# --------------------------------------------------------------------------

def halo(artist, width: float = 2.4, color: str = SURFACE):
    """Contorno da cor do fundo em volta do texto, para que ele sobreviva ao cruzar
    linhas, áreas preenchidas ou células coloridas.

    Sem isso, uma anotação posicionada sobre os dados fica ilegível justamente
    quando a região é densa, que é onde ela costuma precisar estar.
    """
    artist.set_path_effects([
        path_effects.Stroke(linewidth=width, foreground=color),
        path_effects.Normal(),
    ])
    return artist


def ink_on(color) -> str:
    """Escolhe tinta clara ou escura conforme a luminância do fundo.

    Um limiar fixo sobre o valor do dado erra quando o mapa de cores não é linear
    em brilho; medir a luminância real da célula não erra.
    """
    red, green, blue = mpl.colors.to_rgb(color)

    def linearise(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    luminance = (
        0.2126 * linearise(red) + 0.7152 * linearise(green) + 0.0722 * linearise(blue)
    )
    return INK_PRIMARY if luminance > 0.45 else SURFACE


def note(ax, text: str, xy, offset=(6, 0), color: str = INK_SECONDARY, **kwargs):
    """Anotação sobre os dados, sempre com contorno de proteção.

    A cor padrão é tinta secundária, e não a cor da série: texto colorido compete
    com as marcas e perde contraste contra o fundo.
    """
    annotation = ax.annotate(
        text, xy=xy, xytext=offset, textcoords="offset points",
        fontsize=kwargs.pop("fontsize", 8.5), color=color, **kwargs,
    )
    return halo(annotation)


# --------------------------------------------------------------------------
# Composição do cabeçalho
# --------------------------------------------------------------------------

def legend_above(ax, handles=None, ncols: int = 2, **kwargs):
    """Legenda em linha própria, logo acima da área do gráfico."""
    return ax.legend(
        handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0),
        bbox_transform=ax.transAxes, borderaxespad=0.3, ncols=ncols, **kwargs
    )


def title(ax, headline: str, subtitle: str | None = None, legend_rows: int = 0) -> None:
    """Empilha título e subtítulo opcional acima do gráfico.

    O subtítulo é onde a figura diz o que o leitor deve concluir; rótulos de eixo
    raramente fazem isso sozinhos. ``legend_rows`` reserva espaço para a legenda,
    que fica entre o subtítulo e a área de dados.
    """
    offset = 6 + 17 * legend_rows

    if subtitle:
        ax.annotate(
            subtitle, xy=(0, 1), xycoords="axes fraction",
            xytext=(0, offset), textcoords="offset points",
            ha="left", va="bottom", fontsize=9, color=INK_SECONDARY,
        )
        offset += 13

    ax.annotate(
        headline, xy=(0, 1), xycoords="axes fraction",
        xytext=(0, offset), textcoords="offset points",
        ha="left", va="bottom", fontsize=11, weight="bold", color=INK_PRIMARY,
    )


def hide_axis_ticks(ax, axis: str = "y") -> None:
    """Remove as marcas de um eixo cuja linha foi ocultada."""
    ax.tick_params(axis=axis, length=0)


def source_note(fig, text: str, gap: float = 0.035) -> None:
    """Linha de procedência no pé da figura.

    Posicionada abaixo do que a figura de fato desenha, medido e não presumido,
    para que rótulos rotacionados nunca fiquem por baixo dela.
    """
    fig.canvas.draw()
    bottom = fig.get_tightbbox(fig.canvas.get_renderer()).y0 / fig.get_figheight()
    fig.text(0.0, bottom - gap, text, ha="left", va="top", fontsize=7.5, color=INK_MUTED)


def label_last(ax, x, y, text: str, color: str, dx: float = 0.0) -> None:
    """Rótulo direto na ponta da linha, para que a identidade não dependa só da cor."""
    halo(ax.annotate(
        text, xy=(x, y), xytext=(5 + dx, 0), textcoords="offset points",
        va="center", ha="left", fontsize=8.5, color=color, fontweight="bold",
        annotation_clip=False,
    ))


def _protect_all_text(fig) -> None:
    """Aplica contorno a todo texto desenhado dentro das áreas de dados.

    Roda automaticamente na exportação, de modo que nenhuma anotação dependa de
    quem a escreveu ter lembrado de protegê-la. O contorno recebe a cor oposta à
    do texto: claro sob tinta escura, escuro sob tinta clara.
    """
    for axes in fig.axes:
        for text in axes.texts:
            if text.get_path_effects():
                continue
            red, green, blue = mpl.colors.to_rgb(text.get_color())
            luminancia = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            halo(text, width=2.2, color=INK_PRIMARY if luminancia > 0.7 else SURFACE)


def save_fig(fig, name: str, directory: Path | str = IMAGES_DIR) -> Path:
    """Grava a figura em PNG de alta resolução e devolve o caminho."""
    _protect_all_text(fig)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=SURFACE)
    return path
