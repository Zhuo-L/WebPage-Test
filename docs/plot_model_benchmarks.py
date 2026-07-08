#!/usr/bin/env python3
"""
Generate benchmark comparison figures from results.xlsx.

Edit the configuration block below to change model inclusion, layout, colors,
or output names. Scores, providers, and parameter sizes are read from Excel at
runtime, so updating results.xlsx and rerunning this script refreshes the plots.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import textwrap
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", "/tmp/plot_model_benchmarks_mplconfig")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.offsetbox import AnnotationBbox, DrawingArea, OffsetImage
from matplotlib.patches import Circle, PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, MaxNLocator
from PIL import Image


# =============================================================================
# User-editable configuration
# =============================================================================

EXCEL_PATH = ROOT / "results.xlsx"
LOGO_DIR = ROOT / "logos"

LAYOUT_MODE = "4x2"
OURS_MODEL_DISPLAY_NAME = "ExoMind (Ours)"  # Ours 在 2x4、avg 单图、柱状图和图例中的显示名称

DATASET_LAYOUTS = {
    "4x2": [
        ["hle", "frontier_research"],
        ["cmt", "critpt"],
        ["amobench", "imo_answer"],
        ["hipho", "frontier_olympiad"],
    ],
    "2x4": [
        ["hle", "critpt", "frontier_research", "cmt"],
        ["frontier_olympiad", "hipho", "amobench", "imo_answer"],
    ],
    "2x2": [
        ["hle", "critpt"],
        ["frontier_olympiad", "hipho"],
    ],
}

DATASET_META = {
    "hle": {"column": "HLE", "label": "HLE w/ tools", "domain": "Scientific Research Evaluation"},
    "critpt": {"column": "CritPt", "label": "CritPt", "domain": "Scientific Research Evaluation"},
    "frontier_research": {
        "column": "FrontierScience-Research",
        "label": "FrontierScience-Research",
        "domain": "Scientific Research Evaluation",
    },
    "cmt": {"column": "CMT", "label": "CMT-Benchmark", "domain": "Scientific Research Evaluation"},
    "frontier_olympiad": {
        "column": "FrontierScience-Olympiad",
        "label": "FrontierScience-Olympiad",
        "domain": "Scientific Reasoning Evaluation",
    },
    "hipho": {"column": "HiPhO", "label": "HiPhO", "domain": "Scientific Reasoning Evaluation"},
    "amobench": {"column": "AMOBench", "label": "AMO-Bench", "domain": "Scientific Reasoning Evaluation"},
    "imo_answer": {"column": "IMO-AnswerBench", "label": "IMO-AnswerBench", "domain": "Scientific Reasoning Evaluation"},
    "avg": {"column": "Avg", "label": "Average Performance", "domain": "Average Performance"},
}

#
CLOSED_SOURCE_MODELS = [
    "GPT-5.5 (xhigh)",
    "Gemini-3.1-Pro-Preview",
    "Gemini-3.5-Flash-Thinking",
    "Claude-Opus-4.8-Thinking",
    "Qwen3.7-Max",
]

OPEN_SOURCE_MODELS = [
    "DeepSeek-V4-Pro (Max)",
    "DeepSeek-V4-Flash (Max)",
    "Kimi-K2.6",
    "GLM-5.2",
    "MiniMax-M3",
    "Qwen3.5-397B-A17B",
    "Qwen3.5-122B-A10B",
    "Qwen3.5-35B-A3B",
    "Gemma-4-31B",
    "Intern-S2-Preview",
]

OUTPUT_CONFIG = {
    "draw_bar_plot": False,
    "draw_bubble_grid_plot": False,
    "draw_bubble_avg_plot": True,
    "show_bubble_legend": False,
    "save_pdf": True,
    "bar_png": "model_benchmark_bars.png",
    "bubble_png": "model_benchmark_bubbles.png",
    "bubble_avg_png": "model_benchmark_bubbles_avg.png",
    "dpi": 600,
    "figsize": (18, 24.0),
    "avg_figsize": (12.0, 6.0),
    "show_bar_y_axis": False,
}

# 画布边距和行列间距。top/hspace 控制两个 domain 和子图区域的前后间距。
FIGURE_LAYOUT_CONFIG = {
    "left": 0.045,
    "right": 0.988,
    "top": 0.785,
    "wspace": 0.34,
    "hspace": 0.66,
    "bar_bottom": 0.18,
    "bubble_bottom": 0.15,
    "avg_left": 0.16,
    "avg_right": 0.96,
    "avg_top": 0.88,
    "avg_bottom": 0.18,
}

# 圆圈图自定义参数
BUBBLE_TEXT_CONFIG = {
    "model_name_fontsize": 12.5,  # 圆圈旁模型名称字号
    "x_tick_fontsize": 18,  # x 轴 tick 字号
    "x_label_fontsize": 18,  # x 轴名称 "Total Parameters" 字号
    "x_label_bold": False,  # x 轴名称是否加粗；False 表示 normal
    "x_label_pad": 14,  # x 轴名称和 x 轴 tick 之间的上下间距
    "x_label_text": "Model Size (Billions of Parameters)",  # x 轴名称
    "y_tick_fontsize": 18,  # y 轴 tick 字号
    "y_label_fontsize": 18,  # 默认 y 轴名称字号；可被 Y_AXIS_CONFIG 的 ylabel_fontsize 覆盖
    "y_label_bold": False,  # y 轴名称是否加粗；False 表示 normal
    "dataset_name_fontsize": 22,  # 子图下方数据集名称字号
    "x_label_to_dataset_name_gap": 0.25,  # x 轴名称和数据集名称之间的上下间距
    "subplot_wspace": 0.2,  # 圆圈 8 图同一行两张子图之间的左右间距
    "subplot_hspace": 0.1,  # 圆圈 8 图相邻两行子图之间的上下间距
    "figure_top": 0.93,  # 圆圈 8 图子图区域顶部位置；去掉顶部图例后可调大
    "figure_bottom": 0.07,  # 圆圈 8 图子图区域底部位置
    "domain_title_fontsize": 24,  # Scientific Research / Scientific Reasoning 字号
    "domain_title_gap_above": 0.01,  # domain 标题上方距离；第一个相对图顶，第二个相对上方 2x2 图块下方文字
    "domain_title_gap_below": 0.015,  # domain 标题下方到对应 2x2 子图块的距离
    "axis_frame_enabled": True,  # 2x4 圆圈图所有子图是否使用封闭式坐标轴边框
    "axis_frame_color": "#000000",  # 2x4 圆圈图坐标轴边框颜色
    "axis_frame_linewidth": 1.2,  # 2x4 圆圈图坐标轴边框粗细
}

# Average Performance 单图自定义参数，独立于 2x4 圆圈图。
AVG_BUBBLE_TEXT_CONFIG = {
    "title_fontsize": 18,  # avg 单图标题字号
    "subtitle_fontsize": 11, # avg 单图副标题字号
    "model_name_fontsize": 12,  # avg 单图圆圈旁模型名称字号
    "x_tick_fontsize": 14,  # avg 单图 x 轴 tick label 字号
    "x_label_fontsize": 15,  # avg 单图 x 轴名称 "Total Parameters" 字号
    "x_label_bold": True,  # avg 单图 x 轴名称是否加粗；False 表示 normal
    "x_label_pad": 12,  # avg 单图 x 轴名称和 x 轴 tick 之间的上下间距
    "x_label_text": "Model Size (Billions of Parameters)",  # avg 单图 x 轴名称
    "y_tick_fontsize": 14,  # avg 单图 y 轴 tick label 字号
    "y_label_fontsize": 15,  # avg 单图 y 轴名称 "Average Score" 字号
    "y_label_bold": True,  # avg 单图 y 轴名称是否加粗；False 表示 normal
    "axis_frame_enabled": True,  # avg 单图是否使用封闭式坐标轴边框
    "axis_frame_color": "#000000",  # avg 单图坐标轴边框颜色
    "axis_frame_linewidth": 1.2,  # avg 单图坐标轴边框粗细
}

# Average Performance 单图红色箭头自定义参数，独立于 2x4 圆圈图。
AVG_GAIN_ARROW_CONFIG = {
    "enabled": True,
    "show_gain_arrow": True,  # avg 单图是否显示从 baseline 到 Ours 的竖向涨幅箭头
    "show_efficiency_arrow": False,  # avg 单图是否显示从 9T 到 Ours 附近的水平效率箭头
    "show_frontier_efficiency_arrow": True,  # avg 单图是否显示从高分 9T 模型到 Ours 附近的斜向效率箭头
    "baseline_model": "Qwen3.5-35B-A3B",
    "x_offset": 0,  # avg 单图竖向涨幅箭头 x 轴位置偏移
    "cap_width": 0,  # avg 单图竖向涨幅箭头上下短横线宽度
    "linewidth": 2.0,  # avg 单图红色箭头线条粗细
    "arrow_mutation_scale": 19,  # avg 单图红色箭头头部大小
    "color": None,  # None 表示使用 Ours 红色
    "zorder": 9,
    "clip_on": False,
    "gain_arrow_head_y_offset_ratio": -0.02,  # avg 单图竖向箭头末端相对 Ours 分数中心的 y 方向偏移，占 y 轴范围比例
    "gain_text_enabled": True,  # avg 单图是否显示 Gains +{improvement} 文字
    "gain_text_template": "Gains +{improvement:.1f}",  # avg 单图竖向涨幅文字模板
    "gain_text_x_offset": 0.025,  # avg 单图竖向涨幅文字相对箭头的 x 轴偏移，使用 x 轴数据单位
    "gain_text_y_offset_ratio": 0.015,  # avg 单图竖向涨幅文字相对箭头中点的 y 轴偏移，占 y 轴范围比例
    "gain_text_fontsize": 13,  # avg 单图竖向涨幅文字字号
    "efficiency_source_params_b": 9000.0,  # avg 单图水平效率箭头起点参数量
    "efficiency_target_x": None,  # avg 单图水平/斜向效率箭头终点 x 位置；None 时使用下面的相对偏移
    "efficiency_target_x_offset_ratio": 0.015,  # avg 单图效率箭头终点相对 Ours 五角星中心的 x 轴范围偏移比例
    "efficiency_target_x_offset": 0.08,  # avg 单图未设置 efficiency_target_x_offset_ratio 时，相对 Ours 的 x 轴数据单位偏移
    "efficiency_y_offset": 0.0,  # avg 单图水平/斜向效率箭头终点 y 轴偏移
    "efficiency_cap_height_ratio": 0,  # avg 单图水平箭头两端竖向短横线高度，占 y 轴范围比例
    "frontier_efficiency_source_models": ["GPT-5.5 (xhigh)"],  # avg 单图斜向效率箭头起点候选模型，自动选分数更高者
    "frontier_efficiency_text_enabled": True,  # avg 单图是否显示斜向效率箭头文字
    "frontier_efficiency_text": "Efficiency ~277×",  # avg 单图斜向效率箭头上方文字
    "frontier_efficiency_text_fontsize": 13,  # avg 单图斜向效率箭头文字字号
    "frontier_efficiency_text_y_offset_ratio": 0.015,  # avg 单图斜向效率文字默认 y 偏移；若 ARROW_TEXT_POSITIONS 已设置则不会生效
}


LABEL_EDITOR_CONFIG = {
    "grid_canvas": (520, 360),  # 2x4 交互式调参里每个子图的 SVG 画布尺寸
    "grid_margins": {"left": 58, "right": 22, "top": 24, "bottom": 54},  # 2x4 交互式调参 SVG 边距
    "grid_circle_radius_scale": 1 / 4.2,  # 2x4 交互式调参圆圈半径缩放
    "grid_star_font_scale": 1.27,  # 2x4 交互式调参五角星字号缩放
    "avg_canvas": None,  # avg 单图交互式调参 SVG 尺寸；None 表示根据 avg_figsize 自动计算
    "avg_canvas_pixels_per_inch": 120,  # avg 单图交互式调参画布每英寸像素数，用于对齐实际单图比例和圆圈大小
    "avg_margins": None,  # avg 单图交互式调参 SVG 边距；None 表示根据 avg_left/right/top/bottom 自动计算
    "avg_circle_radius_scale": None,  # avg 单图圆圈半径缩放；None 表示按 Matplotlib scatter 点单位自动换算
    "avg_star_font_scale": None,  # avg 单图五角星字号缩放；None 表示按 Matplotlib scatter 点单位自动换算
}


# 2x4 圆圈图：从 baseline 模型到 Ours 的涨幅箭头示意。
GAIN_ARROW_CONFIG = {
    "enabled": True,
    "show_gain_arrow": True,  # 是否显示从 baseline 到 Ours 的竖向涨幅箭头
    "show_efficiency_arrow": False,  # 是否显示从 9T 到 Ours 附近的水平效率箭头
    "show_frontier_efficiency_arrow": True,  # 是否显示从高分 9T 模型到 Ours 附近的斜向效率箭头
    "baseline_model": "Qwen3.5-35B-A3B",
    "x_offset": 0, # x轴位置
    "cap_width": 0, # 短横线宽度, 0.05
    "linewidth": 2.0, # 箭头线条粗细
    "arrow_mutation_scale": 19, # 箭头头部大小
    "color": None,
    "zorder": 9,
    "clip_on": False,
    "gain_arrow_head_y_offset_ratio": -0.02,  # 竖向箭头末端相对 Ours 分数中心的 y 方向偏移，占当前子图 y 轴范围比例
    "gain_text_enabled": True,  # 是否显示 Gains +{improvement} 文字
    "gain_text_template": "Gains +{improvement:.1f}",  # 竖向涨幅文字模板
    "gain_text_x_offset": 0.025,  # 竖向涨幅文字相对箭头的 x 轴偏移，使用 x 轴数据单位
    "gain_text_y_offset_ratio": 0.015,  # 竖向涨幅文字相对箭头中点的 y 轴偏移，占当前子图 y 轴范围比例
    "gain_text_fontsize": 13.5,  # 竖向涨幅文字字号
    "efficiency_source_params_b": 9000.0,
    "efficiency_target_x": 0.20,  # 水平箭头终点 x 位置，放在 35B/Ours 右侧以避免重叠
    "efficiency_target_x_offset_ratio": None,  # efficiency_target_x=None 时，箭头终点相对 Ours 的 x 轴范围偏移比例
    "efficiency_target_x_offset": 0.08,  # 未设置 efficiency_target_x_offset_ratio 时，相对 Ours 的 x 轴数据单位偏移
    "efficiency_y_offset": 0.0,
    "efficiency_cap_height_ratio": 0,  # 水平箭头两端竖向短横线高度，占当前子图 y 轴范围的比例
    "frontier_efficiency_source_models": ["GPT-5.5 (xhigh)"], # "Gemini-3.1-Pro-Preview"],  # 斜向效率箭头起点候选模型，自动选分数更高者
    "frontier_efficiency_text_enabled": True,  # 是否显示斜向效率箭头文字
    "frontier_efficiency_text": "Efficiency ~277×",  # 斜向效率箭头上方文字
    "frontier_efficiency_text_fontsize": 13.5,  # 斜向效率箭头文字字号
    "frontier_efficiency_text_y_offset_ratio": 0.015,  # 斜向效率文字默认 y 偏移；若 ARROW_TEXT_POSITIONS 已设置则不会生效
}

# 圆圈图 x 轴显示范围。30B tick 在 0.1，10T tick 在 2.1；这里左右各留 0.1 空间。
BUBBLE_X_AXIS_CONFIG = {
    "xmin": 0.0,
    "xmax": 2.2,
}

# 是否显示模型文字和模型名称的箭头、箭头样式、文字背景等。
BUBBLE_LABEL_CONFIG = {
    "show_model_labels": True,
    "wrap_width": 18,
    "fontweight": "bold",
    "text_color": "#12161C",
    "text_background_alpha": 0.80,
    "arrow_color": "#8C96A3",
    "arrow_linewidth": 0.5,
    "arrow_alpha": 0.65,
    "arrow_shrink_a": 0,
    "arrow_shrink_b": 3,
}

# 圆圈图点旁模型名称配置。只影响圆圈图标注，不影响顶部图例。
BUBBLE_LABEL_NAME_OVERRIDES = {
    # "DeepSeek-V4-Pro (Max)": "DeepSeek-V4-Pro",
    # "DeepSeek-V4-Flash (Max)": "DeepSeek-V4-Flash",
    # "Gemini-3.1-Pro-Preview": "Gemini-3.1-Pro",
    # "Gemini-3.5-Flash-Thinking": "Gemini-3.5-Flash",
    # "Claude-Opus-4.8-Thinking": "Claude-Opus-4.8",
}

# 圆圈图每个数据集子图的模型名称中心位置，单位为当前子图 x/y 轴范围的百分比。
# 例如 (1, 2) 表示文字中心相对圆圈中心向右偏移 x 轴范围的 1%、向上偏移 y 轴范围的 2%。
# key 使用 dataset id；内层 key 使用 Excel 模型名，Ours 使用 "Ours"。
# 未配置的模型会继续使用自动避让位置。
BUBBLE_LABEL_POSITIONS = {
    "hle": {
        "Ours": (5.54, 10.77),
        "GPT-5.5 (xhigh)": (-5.53, 16.23),
        "Gemini-3.1-Pro-Preview": (-9.93, -21.13),
        "Gemini-3.5-Flash-Thinking": (-5.33, -21.49),
        "Claude-Opus-4.8-Thinking": (-22.06, 6.50),
        "Qwen3.7-Max": (-15.20, 5.28),
        "DeepSeek-V4-Pro (Max)": (-20.14, -13.14),
        "DeepSeek-V4-Flash (Max)": (0.20, -25.52),
        "Kimi-K2.6": (-11.00, -12.60),
        "GLM-5.2": (-11.70, 8.50),
        "Qwen3.5-397B-A17B": (7.80, -24.66),
        "Qwen3.5-122B-A10B": (-5.23, -17.92),
        "Qwen3.5-35B-A3B": (6.37, -9.51),
        "Gemma-4-31B": (9.69, 7.27),
        "Intern-S2-Preview": (6.84, -12.84),
    },
    "frontier_research": {
        "Ours": (17.61, 3.24),
        "GPT-5.5 (xhigh)": (-6.63, 19.36),
        "Gemini-3.1-Pro-Preview": (-9.52, -7.90),
        "Gemini-3.5-Flash-Thinking": (-18.30, 22.75),
        "Claude-Opus-4.8-Thinking": (-22.19, 14.99),
        "Qwen3.7-Max": (-0.40, -4.45),
        "DeepSeek-V4-Pro (Max)": (1.18, -1.63),
        "DeepSeek-V4-Flash (Max)": (-11.44, 11.90),
        "Kimi-K2.6": (-15.60, 10.36),
        "GLM-5.2": (-9.44, 8.08),
        "MiniMax-M3": (-7.21, 20.34),
        "Qwen3.5-397B-A17B": (18.13, -0.87),
        "Qwen3.5-122B-A10B": (-1.41, -3.40),
        "Qwen3.5-35B-A3B": (7.60, 8.14),
        "Gemma-4-31B": (5.35, 14.26),
        "Intern-S2-Preview": (14.51, 6.54),
    },
    "cmt": {
        "Ours": (17.09, 3.41),
        "GPT-5.5 (xhigh)": (-7.17, 24.73),
        "Gemini-3.1-Pro-Preview": (-10.46, 18.03),
        "Gemini-3.5-Flash-Thinking": (-4.98, -20.80),
        "Claude-Opus-4.8-Thinking": (-28.49, 11.63),
        "Qwen3.7-Max": (-5.53, 9.13),
        "DeepSeek-V4-Pro (Max)": (7.10, -22.14),
        "DeepSeek-V4-Flash (Max)": (-7.00, 18.92),
        "Kimi-K2.6": (-17.81, 6.38),
        "GLM-5.2": (-0.01, -12.98),
        "MiniMax-M3": (-1.18, -11.85),
        "Qwen3.5-397B-A17B": (-15.48, -10.48),
        "Qwen3.5-122B-A10B": (-6.65, 14.90),
        "Qwen3.5-35B-A3B": (6.86, 9.31),
        "Gemma-4-31B": (5.60, -8.16),
        "Intern-S2-Preview": (18.76, -0.08),
    },
    "critpt": {
        "Ours": (6.10, 9.41),
        "GPT-5.5 (xhigh)": (-17.50, 3.82),
        "Gemini-3.1-Pro-Preview": (-24.44, 0.70),
        "Gemini-3.5-Flash-Thinking": (-23.39, 10.27),
        "Claude-Opus-4.8-Thinking": (-2.56, 11.83),
        "Qwen3.7-Max": (-14.90, 0.37),
        "DeepSeek-V4-Pro (Max)": (13.24, -14.67),
        "DeepSeek-V4-Flash (Max)": (-0.02, 12.97),
        "Kimi-K2.6": (-10.69, 7.76),
        "GLM-5.2": (-14.24, 0.29),
        "MiniMax-M3": (13.74, 0.15),
        "Qwen3.5-397B-A17B": (18.44, -1.94),
        "Qwen3.5-122B-A10B": (-1.92, 8.90),
        "Qwen3.5-35B-A3B": (8.43, 20.27),
        "Gemma-4-31B": (5.23, 23.85),
        "Intern-S2-Preview": (14.27, 17.85),
    },
    "amobench": {
        "Ours": (21.76, 0.99),
        "GPT-5.5 (xhigh)": (-6.98, 13.01),
        "Gemini-3.1-Pro-Preview": (-10.77, -22.17),
        "Gemini-3.5-Flash-Thinking": (-5.92, -17.71),
        "Claude-Opus-4.8-Thinking": (-0.04, 10.00),
        "Qwen3.7-Max": (-1.23, 10.57),
        "DeepSeek-V4-Pro (Max)": (-20.22, 3.17),
        "DeepSeek-V4-Flash (Max)": (-4.98, -11.80),
        "Kimi-K2.6": (-13.25, 3.42),
        "GLM-5.2": (7.74, -10.45),
        "Qwen3.5-397B-A17B": (-20.02, -4.55),
        "Qwen3.5-122B-A10B": (18.22, -3.28),
        "Qwen3.5-35B-A3B": (6.82, -7.60),
        "Gemma-4-31B": (13.69, -0.70),
        "MiniMax-M3": (6.38, -11.75),
        "Intern-S2-Preview": (13.17, -12.19),
    },
    "imo_answer": {
        "Ours": (15.34, 3.58),
        "GPT-5.5 (xhigh)": (-6.82, -17.36),
        "Gemini-3.1-Pro-Preview": (-10.35, 12.64),
        "Gemini-3.5-Flash-Thinking": (-5.63, -1.78),
        "Claude-Opus-4.8-Thinking": (-25.78, -5.52),
        "Qwen3.7-Max": (-11.47, 10.89),
        "DeepSeek-V4-Pro (Max)": (-15.71, -35.84),
        "DeepSeek-V4-Flash (Max)": (-17.20, -0.77),
        "Kimi-K2.6": (-0.48, -22.30),
        "GLM-5.2": (-10.13, -13.86),
        "Qwen3.5-397B-A17B": (15.67, -10.64),
        "Qwen3.5-122B-A10B": (0.03, -10.78),
        "Qwen3.5-35B-A3B": (6.71, -10.63),
        "Gemma-4-31B": (6.14, 8.23),
        "MiniMax-M3": (-12.13, -6.87),
        "Intern-S2-Preview": (16.39, -0.73),
    },
    "hipho": {
        "Ours": (26.05, -1.81),
        "GPT-5.5 (xhigh)": (-6.12, -17.74),
        "Gemini-3.1-Pro-Preview": (-9.90, 21.90),
        "Gemini-3.5-Flash-Thinking": (-26.97, 1.21),
        "Claude-Opus-4.8-Thinking": (10.67, 14.54),
        "Qwen3.7-Max": (4.03, -20.98),
        "DeepSeek-V4-Pro (Max)": (11.76, -14.25),
        "DeepSeek-V4-Flash (Max)": (0.02, -10.46),
        "Kimi-K2.6": (-12.71, 6.26),
        "GLM-5.2": (10.23, -21.32),
        "MiniMax-M3": (-0.02, -11.28),
        "Qwen3.5-397B-A17B": (0.00, 16.49),
        "Qwen3.5-122B-A10B": (-1.29, 16.23),
        "Qwen3.5-35B-A3B": (7.02, -10.48),
        "Gemma-4-31B": (5.74, -10.43),
        "Intern-S2-Preview": (15.95, 0.31),
    },
    "frontier_olympiad": {
        "Ours": (6.94, 9.73),
        "GPT-5.5 (xhigh)": (-6.81, 20.91),
        "Gemini-3.1-Pro-Preview": (-13.05, 16.90),
        "Gemini-3.5-Flash-Thinking": (-7.23, -22.02),
        "Claude-Opus-4.8-Thinking": (-17.78, -13.76),
        "Qwen3.7-Max": (-15.25, 4.00),
        "DeepSeek-V4-Pro (Max)": (6.88, -31.55),
        "DeepSeek-V4-Flash (Max)": (-14.36, -11.11),
        "Kimi-K2.6": (-19.69, -16.39),
        "GLM-5.2": (-12.05, -0.79),
        "MiniMax-M3": (-13.30, -2.40),
        "Qwen3.5-397B-A17B": (19.01, -6.79),
        "Qwen3.5-122B-A10B": (-2.02, -9.53),
        "Qwen3.5-35B-A3B": (17.95, 3.81),
        "Gemma-4-31B": (5.48, 8.64),
        "Intern-S2-Preview": (6.58, -9.38),
    },
    "avg": {
        "Ours": (12.32, 2.72),
        "GPT-5.5 (xhigh)": (-3.34, 18.12),
        "Gemini-3.1-Pro-Preview": (-7.09, 20.81),
        "Gemini-3.5-Flash-Thinking": (-0.28, -14.13),
        "Claude-Opus-4.8-Thinking": (-16.89, 1.30),
        "Qwen3.7-Max": (-10.19, 3.28),
        "DeepSeek-V4-Pro (Max)": (-1.28, -15.93),
        "DeepSeek-V4-Flash (Max)": (-13.17, 0.12),
        "Kimi-K2.6": (6.28, 8.53),
        "GLM-5.2": (-2.49, -9.77),
        "MiniMax-M3": (9.57, -1.85),
        "Qwen3.5-397B-A17B": (-1.98, 7.89),
        "Qwen3.5-122B-A10B": (0.00, -7.68),
        "Qwen3.5-35B-A3B": (11.18, 2.90),
        "Gemma-4-31B": (9.94, -1.59),
        "Intern-S2-Preview": (10.37, 8.23),
    },
}

ARROW_TEXT_POSITIONS = {
    "hle": {
        "gain": (10.75, -1.19),
        "frontier_efficiency": (-21.14, 2.57),
    },
    "frontier_research": {
        "gain": (9.29, 8.46),
        "frontier_efficiency": (10.25, 4.00),
    },
    "cmt": {
        "gain": (9.36, 11.89),
        "frontier_efficiency": (5.50, 6.91),
    },
    "critpt": {
        "gain": (9.29, 2.92),
        "frontier_efficiency": (0.00, 3.34),
    },
    "amobench": {
        "gain": (9.19, 14.19),
        "frontier_efficiency": (0.78, 4.23),
    },
    "imo_answer": {
        "gain": (9.33, 9.90),
        "frontier_efficiency": (-10.25, 10.35),
    },
    "hipho": {
        "gain": (9.38, 8.97),
        "frontier_efficiency": (0.25, 7.60),
    },
    "frontier_olympiad": {
        "gain": (9.48, 8.41),
        "frontier_efficiency": (0.25, 6.35),
    },
    "avg": {
        "gain": (7.68, 6.66),
        "frontier_efficiency": (-0.69, 8.28),
    },
}


# 图例字体大小、logo 缩放倍数、fallback/svg logo 尺寸、Ours 星标大小、图例布局。
LEGEND_CONFIG = {
    "axes": [0.035, 0.815, 0.94, 0.17],
    "items_per_row": 6,
    "row_y": [0.72, 0.32],
    "x_start": 0.06,
    "x_end": 0.88,
    "icon_x_offset": 0.034,
    "logo_zoom": 0.112,
    "svg_logo_size": 37,
    "fallback_logo_size": 37,
    "font_size": 18,
    "text_color": "#15181D",
    "closed_fontweight": "bold",
    "default_fontweight": "normal",
}

# Ours 五角星大小。Matplotlib scatter 的 s 是面积单位。
MARKER_CONFIG = {
    "legend_ours_star_size": 560,
    "bar_ours_star_size": 190,
    "bubble_ours_star_size": 560,
}

# 圆圈图 marker 超出坐标轴边界时的显示方式。
BUBBLE_CLIP_CONFIG = {
    "clip_markers": False,
}

# 圆圈图面积大小配置。半径分段线性变化，scatter 的 s 使用 radius ** 2。
BUBBLE_SIZE_CONFIG = {
    "min_params_b": 30.0,
    "mid_params_b": 1000.0,
    "max_params_b": 7000.0,
    "min_radius": 20.0,
    "mid_radius": 36.0,
    "max_radius": 50.0,
}

# 每个数据集的 y 轴范围和 ytick。设为 None 时自动计算。
Y_AXIS_CONFIG = {
    "hle": {"ylim": [25,65], "yticks": [30,40,50,60], "ylabel": "Accuracy", "ylabel_fontsize": None},
    "critpt": {"ylim": [0,30], "yticks": [0,10,20,30], "ylabel": "Accuracy", "ylabel_fontsize": None},
    "frontier_research": {"ylim": [0,75], "yticks": [0,25,50,75], "ylabel": "Accuracy", "ylabel_fontsize": None},
    "cmt": {"ylim": [0,90], "yticks": [0,30,60,90], "ylabel": "Accuracy", "ylabel_fontsize": None},
    "frontier_olympiad": {"ylim": [50,90], "yticks": [50,65,80,95], "ylabel": "Accuracy", "ylabel_fontsize": None},
    "hipho": {"ylim": [30,50], "yticks": [30,35,40,45,50], "ylabel": "Average Score", "ylabel_fontsize": None},
    "amobench": {"ylim": [35,80], "yticks": [35,50,65,80], "ylabel": "Accuracy", "ylabel_fontsize": None},
    "imo_answer": {"ylim": [65,95], "yticks": [65,75,85,95], "ylabel": "Accuracy", "ylabel_fontsize": None},
    "avg": {"ylim": [30,70], "yticks": [30,40,50,60,70], "ylabel": "Average Score", "ylabel_fontsize": None},
}

def rgb(r: int, g: int, b: int) -> tuple[float, float, float]:
    return (r / 255, g / 255, b / 255)


OURS_COLOR = rgb(227, 26, 28)
KLEIN_BLUE = "#002FA7"

PROVIDER_COLORS = {
    "Ours": OURS_COLOR,
    "OpenAI": rgb(12, 169, 130),
    "Google": rgb(250, 188, 5),
    "Claude": rgb(238, 130, 47),
    "DeepSeek": rgb(79, 106, 239),
    "Qwen": rgb(171, 104, 230),
    "Kimi": rgb(105, 174, 255),
    "GLM": rgb(175, 175, 175),
    "MiniMax": rgb(240, 51, 101),
    "Gemma": rgb(250, 188, 5),
    "Shanghai AI Lab": rgb(89, 89, 89),
}

# 图例模型顺序的唯一配置入口
SERIES_LEGEND = [
    {"label": "GPT-5.5 (xhigh)", "provider": "OpenAI", "logo": "logo_gpt.png", "kind": "closed"},
    {"label": "Gemini-3.1-Pro-Preview", "provider": "Google", "logo": "logo_gemini.svg", "kind": "closed"},
    {"label": "Gemini-3.5-Flash-Thinking", "provider": "Google", "logo": "logo_gemini.svg", "kind": "closed"},
    {"label": "Claude-Opus-4.8-Thinking", "provider": "Claude", "logo": "logo_claude.png", "kind": "closed"},
    {"label": "Qwen3.7-Max", "provider": "Qwen", "logo": "logo_qwen.png", "kind": "closed"},
    {"label": "DeepSeek-V4 Series", "provider": "DeepSeek", "logo": "logo_deepseek.png"},
    {"label": "Kimi-K2.6", "provider": "Kimi", "logo": "logo_kimi.png"},
    {"label": "GLM-5.2", "provider": "GLM", "logo": "logo_glm.png"},
    {"label": "MiniMax-M3", "provider": "MiniMax", "logo": "logo_minimax.png", "fallback_text": "MM"},
    {"label": "Qwen3.5 Series", "provider": "Qwen", "logo": "logo_qwen.png"},
    {"label": "Gemma-4-31B", "provider": "Gemma", "logo": "logo_gemma.png", "fallback_text": "G"},
    {"label": "Intern-S2-Preview", "provider": "Shanghai AI Lab", "logo": "logo_ailab.png", "fallback_text": "G"},
    {"label": OURS_MODEL_DISPLAY_NAME, "provider": "Ours", "logo": "logo_ailab.png", "kind": "ours"},
]


# =============================================================================
# Data model and Excel parsing
# =============================================================================


@dataclass
class ModelRecord:
    raw_name: str
    display_name: str
    provider: str
    size_b: float | None
    closed_source: bool
    is_ours: bool
    scores: dict[str, float | None]
    logo: str


def parse_xlsx_rows(path: Path) -> list[list[str]]:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    def col_idx(cell_ref: str) -> int:
        letters = "".join(ch for ch in cell_ref if ch.isalpha())
        n = 0
        for ch in letters:
            n = n * 26 + ord(ch.upper()) - 64
        return n - 1

    with zipfile.ZipFile(path) as zf:
        shared = []
        shared_xml = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in shared_xml.findall("a:si", ns):
            shared.append("".join((t.text or "") for t in si.findall(".//a:t", ns)))

        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//a:sheetData/a:row", ns):
            values = []
            for cell in row.findall("a:c", ns):
                idx = col_idx(cell.attrib["r"])
                while len(values) <= idx:
                    values.append("")
                value = cell.find("a:v", ns)
                if value is None:
                    cell_value = ""
                elif cell.attrib.get("t") == "s":
                    cell_value = shared[int(value.text)]
                else:
                    cell_value = value.text or ""
                values[idx] = str(cell_value).strip()
            rows.append(values)

    if not rows:
        raise ValueError(f"No rows found in {path}")
    max_len = max(len(row) for row in rows)
    return [row + [""] * (max_len - len(row)) for row in rows]


def parse_score(value: str) -> float | None:
    text = str(value).strip()
    if not text or text in {"-", "—", "nan", "NaN"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def parse_size_b(value: str) -> float | None:
    text = str(value).strip().upper().replace(" ", "")
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)([BT])", text)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2)
    return number * 1000 if unit == "T" else number


def logo_for_provider(provider: str) -> str:
    return {
        "Ours": "logo_ailab.png",
        "OpenAI": "logo_gpt.png",
        "Google": "logo_gemini.svg",
        "Claude": "logo_claude.png",
        "DeepSeek": "logo_deepseek.png",
        "Qwen": "logo_qwen.png",
        "Kimi": "logo_kimi.png",
        "GLM": "logo_glm.png",
        "MiniMax": "logo_minimax.png",
        "Shanghai AI Lab": "logo_ailab.png",
    }.get(provider, "")


def load_excel_records(path: Path) -> list[ModelRecord]:
    rows = parse_xlsx_rows(path)
    header = rows[0]
    column_idx = {name: idx for idx, name in enumerate(header)}
    size_idx = column_idx.get("Size")
    provider_idx = column_idx.get("Provider")
    if size_idx is None or provider_idx is None:
        raise ValueError("results.xlsx must contain Size and Provider columns")

    records: list[ModelRecord] = []
    for row in rows[1:]:
        raw_name = row[0].strip()
        if not raw_name or raw_name.lower().startswith("open-sourced"):
            continue
        provider = row[provider_idx].strip()
        if not provider:
            continue
        is_ours = provider == "Ours"
        closed_source = raw_name in CLOSED_SOURCE_MODELS
        scores = {}
        for dataset_id, meta in DATASET_META.items():
            idx = column_idx.get(meta["column"])
            scores[dataset_id] = parse_score(row[idx]) if idx is not None and idx < len(row) else None
        records.append(
            ModelRecord(
                raw_name=raw_name,
                display_name=OURS_MODEL_DISPLAY_NAME if is_ours else raw_name,
                provider=provider,
                size_b=parse_size_b(row[size_idx]),
                closed_source=closed_source,
                is_ours=is_ours,
                scores=scores,
                logo=logo_for_provider(provider),
            )
        )
    return records


def selected_records(records: list[ModelRecord]) -> list[ModelRecord]:
    by_name = {record.raw_name: record for record in records}
    closed = [by_name[name] for name in CLOSED_SOURCE_MODELS if name in by_name]
    open_models = [by_name[name] for name in OPEN_SOURCE_MODELS if name in by_name]
    ours = [record for record in records if record.is_ours]
    missing = [name for name in CLOSED_SOURCE_MODELS + OPEN_SOURCE_MODELS if name not in by_name]
    if missing:
        print("Warning: missing models in results.xlsx:", ", ".join(missing))
    return ours + closed + open_models


# =============================================================================
# Plot helpers
# =============================================================================

LOGO_CACHE: dict[str, np.ndarray | None] = {}


def resample_filter():
    return getattr(getattr(Image, "Resampling", Image), "LANCZOS")


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.edgecolor": "#D8DCE2",
            "axes.linewidth": 0.8,
            "xtick.color": "#3B3F46",
            "ytick.color": "#3B3F46",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )


def provider_color(provider: str) -> tuple[float, float, float]:
    return PROVIDER_COLORS.get(provider, rgb(138, 144, 153))


def crop_logo(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba)
    alpha = arr[..., 3]
    rgb = arr[..., :3]
    non_white = np.any(rgb < 245, axis=2)
    mask = (alpha > 8) & non_white
    if not mask.any():
        mask = alpha > 8
    if not mask.any():
        return rgba
    ys, xs = np.where(mask)
    pad = 6
    left = max(xs.min() - pad, 0)
    right = min(xs.max() + pad + 1, rgba.width)
    top = max(ys.min() - pad, 0)
    bottom = min(ys.max() + pad + 1, rgba.height)
    return rgba.crop((left, top, right, bottom))


def normalize_logo(image: Image.Image, canvas_size: int = 180, padding: int = 18) -> Image.Image:
    image = image.convert("RGBA")
    max_side = max(1, canvas_size - padding * 2)
    scale = min(max_side / image.width, max_side / image.height)
    new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    resized = image.resize(new_size, resample_filter())
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
    offset = ((canvas_size - new_size[0]) // 2, (canvas_size - new_size[1]) // 2)
    canvas.alpha_composite(resized, offset)
    return canvas


def svg_primary_color(path: Path, default: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return default
    match = re.search(r'fill="(#[0-9A-Fa-f]{6})"', text)
    return match.group(1) if match else default


def svg_logo_box(path: Path, size: int, default_color: str) -> DrawingArea:
    color = svg_primary_color(path, default_color)
    box = DrawingArea(size, size, 0, 0)
    scale = size / 24.0
    points = [
        (12.0, 1.2),
        (14.55, 8.1),
        (22.8, 12.0),
        (14.55, 15.9),
        (12.0, 22.8),
        (9.45, 15.9),
        (1.2, 12.0),
        (9.45, 8.1),
        (12.0, 1.2),
    ]
    vertices = [(x * scale, y * scale) for x, y in points]
    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(vertices) - 2) + [MplPath.CLOSEPOLY]
    box.add_artist(PathPatch(MplPath(vertices, codes), fc=color, ec="white", lw=max(0.8, size * 0.045), joinstyle="round"))
    return box


def load_logo(filename: str) -> np.ndarray | None:
    if not filename:
        return None
    if filename in LOGO_CACHE:
        return LOGO_CACHE[filename]
    path = LOGO_DIR / filename
    if not path.exists() or path.suffix.lower() == ".svg":
        LOGO_CACHE[filename] = None
        return None
    try:
        LOGO_CACHE[filename] = np.asarray(normalize_logo(crop_logo(Image.open(path))))
    except Exception:
        LOGO_CACHE[filename] = None
    return LOGO_CACHE[filename]


def fallback_logo_box(text: str, face: str, size: int = 26) -> DrawingArea:
    box = DrawingArea(size, size, 0, 0)
    box.add_artist(Circle((size / 2, size / 2), size * 0.46, fc=face, ec="white", lw=1.0))
    box.add_artist(Text(size / 2, size / 2, text[:3], color="white", ha="center", va="center", fontsize=max(7, size * 0.28), fontweight="bold"))
    return box


def logo_artist(filename: str, provider: str, fallback_text: str, zoom: float = 0.08, fallback_size: int = 24):
    path = LOGO_DIR / filename if filename else Path("")
    if filename and path.suffix.lower() == ".svg" and path.exists():
        return svg_logo_box(path, fallback_size, provider_color(provider))
    img = load_logo(filename)
    if img is not None:
        return OffsetImage(img, zoom=zoom, resample=True)
    return fallback_logo_box(fallback_text, provider_color(provider), fallback_size)


def add_logo(ax, filename: str, provider: str, fallback_text: str, xy, xycoords="data", zoom: float = 0.08, fallback_size: int = 24, zorder: int = 10):
    ab = AnnotationBbox(
        logo_artist(filename, provider, fallback_text, zoom=zoom, fallback_size=fallback_size),
        xy,
        xycoords=xycoords,
        frameon=False,
        box_alignment=(0.5, 0.5),
        pad=0,
        zorder=zorder,
    )
    ax.add_artist(ab)
    return ab


def save_figure(fig, png_path: Path) -> Path:
    fig.savefig(png_path, dpi=OUTPUT_CONFIG["dpi"], bbox_inches="tight", pad_inches=0.18)
    if OUTPUT_CONFIG.get("save_pdf", True):
        fig.savefig(png_path.with_suffix(".pdf"), dpi=OUTPUT_CONFIG["dpi"], bbox_inches="tight", pad_inches=0.18)
    return png_path


def current_layout() -> list[list[str]]:
    if LAYOUT_MODE not in DATASET_LAYOUTS:
        raise ValueError(f"Unknown LAYOUT_MODE={LAYOUT_MODE!r}. Choose one of {sorted(DATASET_LAYOUTS)}.")
    return DATASET_LAYOUTS[LAYOUT_MODE]


def position_dataset_ids() -> list[str]:
    dataset_ids = [dataset for row in current_layout() for dataset in row]
    if "avg" in DATASET_META and "avg" not in dataset_ids:
        dataset_ids.append("avg")
    return dataset_ids


def selected_dataset_grid() -> tuple[list[list[dict]], int, int]:
    layout = current_layout()
    rows = len(layout)
    cols = max(len(row) for row in layout)
    grid = []
    for row in layout:
        grid.append([{**DATASET_META[dataset_id], "id": dataset_id} for dataset_id in row])
    return grid, rows, cols


def grouped_domain_layout_enabled(rows: int, cols: int, text_config: dict | None) -> bool:
    return LAYOUT_MODE == "4x2" and rows == 4 and cols == 2 and text_config is not None


def grouped_domain_subplot_grid(rows: int, cols: int, text_config: dict):
    fig = plt.figure(figsize=OUTPUT_CONFIG["figsize"])
    left = FIGURE_LAYOUT_CONFIG["left"]
    right = FIGURE_LAYOUT_CONFIG["right"]
    top = text_config.get("figure_top", FIGURE_LAYOUT_CONFIG["top"])
    bottom = text_config.get("figure_bottom", FIGURE_LAYOUT_CONFIG["bubble_bottom"])
    wspace = text_config.get("subplot_wspace", FIGURE_LAYOUT_CONFIG["wspace"])
    hspace = text_config.get("subplot_hspace", FIGURE_LAYOUT_CONFIG["hspace"])
    title_gap_above = text_config.get("domain_title_gap_above", 0.02)
    title_gap_below = text_config.get("domain_title_gap_below", 0.02)
    fig_height_in = OUTPUT_CONFIG["figsize"][1]
    title_height = text_config.get("domain_title_fontsize", 22) * 1.28 / 72.0 / fig_height_in
    dataset_label_height = text_config.get("dataset_name_fontsize", 16) * 1.25 / 72.0 / fig_height_in
    label_gap_ratio = text_config.get("x_label_to_dataset_name_gap", 0.0)

    total_width = right - left
    ax_width = total_width / (cols + (cols - 1) * wspace)
    col_gap = ax_width * wspace
    total_height = top - bottom
    row_gap_count = 2  # one gap inside each 2x2 domain block
    fixed_height = 2 * (title_gap_above + title_height + title_gap_below) + rows * dataset_label_height
    row_height = (total_height - fixed_height) / (rows * (1.0 + label_gap_ratio) + row_gap_count * hspace)
    if row_height <= 0:
        raise ValueError("domain title gaps and label reserve are too large for the current 4x2 bubble figure height")
    row_gap = row_height * hspace
    row_label_reserve = row_height * label_gap_ratio + dataset_label_height

    axes = np.empty((rows, cols), dtype=object)
    cursor = top
    for row_idx in range(rows):
        if row_idx in {0, 2}:
            cursor -= title_gap_above + title_height + title_gap_below
        else:
            cursor -= row_gap
        y0 = cursor - row_height
        for col_idx in range(cols):
            x0 = left + col_idx * (ax_width + col_gap)
            axes[row_idx, col_idx] = fig.add_axes([x0, y0, ax_width, row_height])
        cursor = y0 - row_label_reserve
    return fig, axes


def subplot_grid(rows: int, cols: int, bottom: float = 0.11, text_config: dict | None = None):
    use_grouped_layout = grouped_domain_layout_enabled(rows, cols, text_config)
    text_config = text_config or {}
    if use_grouped_layout:
        return grouped_domain_subplot_grid(rows, cols, text_config)
    fig, axes = plt.subplots(rows, cols, figsize=OUTPUT_CONFIG["figsize"], squeeze=False)
    fig.subplots_adjust(
        left=FIGURE_LAYOUT_CONFIG["left"],
        right=FIGURE_LAYOUT_CONFIG["right"],
        bottom=text_config.get("figure_bottom", bottom),
        top=text_config.get("figure_top", FIGURE_LAYOUT_CONFIG["top"]),
        wspace=text_config.get("subplot_wspace", FIGURE_LAYOUT_CONFIG["wspace"]),
        hspace=text_config.get("subplot_hspace", FIGURE_LAYOUT_CONFIG["hspace"]),
    )
    return fig, axes


def add_domain_titles(fig, axes, dataset_grid: list[list[dict]], text_config: dict | None = None) -> None:
    text_config = text_config or {}
    grouped_layout = grouped_domain_layout_enabled(len(dataset_grid), max(len(row) for row in dataset_grid), text_config)
    for row_idx, row in enumerate(dataset_grid):
        if row_idx > 0 and row[0]["domain"] == dataset_grid[row_idx - 1][0]["domain"]:
            continue
        left = axes[row_idx, 0].get_position()
        right = axes[row_idx, len(row) - 1].get_position()
        x = (left.x0 + right.x1) / 2
        if grouped_layout:
            y = left.y1 + text_config.get("domain_title_gap_below", 0.02)
        else:
            y = left.y1 + text_config.get("domain_title_y_offset", text_config.get("domain_title_gap_below", 0.032))
        fig.text(
            x,
            y,
            row[0]["domain"],
            ha="center",
            va="bottom",
            fontsize=text_config.get("domain_title_fontsize", 22),
            fontweight="bold",
            color="#050505",
        )


def score_values(records: list[ModelRecord], dataset_id: str) -> list[float]:
    return [score for record in records if (score := record.scores.get(dataset_id)) is not None]


def axis_ylim(scores: list[float]) -> tuple[float, float]:
    if not scores:
        return 0, 100
    lo = min(scores)
    hi = max(scores)
    pad = max(5.0, (hi - lo) * 0.14)
    return max(0.0, lo - pad), min(100.0, hi + pad)


def configured_y_axis(dataset_id: str, scores: list[float]) -> tuple[tuple[float, float], list[float] | None, str | None, float | None]:
    config = Y_AXIS_CONFIG.get(dataset_id) or {}
    configured_ylim = config.get("ylim")
    configured_yticks = config.get("yticks")
    ylim = tuple(configured_ylim) if configured_ylim is not None else axis_ylim(scores)
    yticks = list(configured_yticks) if configured_yticks is not None else None
    ylabel = config.get("ylabel")
    ylabel_fontsize = config.get("ylabel_fontsize")
    return ylim, yticks, ylabel, ylabel_fontsize


def label_fontweight(text_config: dict, key: str, default: bool = True) -> str:
    return "bold" if text_config.get(key, default) else "normal"


def style_axis(
    ax,
    dataset: dict,
    scores: list[float],
    ylabel: bool,
    show_y_axis: bool = True,
    text_config: dict | None = None,
) -> tuple[float, float]:
    text_config = text_config or {}
    (ymin, ymax), yticks, configured_ylabel, configured_ylabel_fontsize = configured_y_axis(dataset["id"], scores)
    ax.set_ylim(ymin, ymax)
    if yticks is None:
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    else:
        ax.set_yticks(yticks)
    ax.grid(axis="y", color="#E6EAF0", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#D8DCE2")
    ax.spines["bottom"].set_color("#D8DCE2")
    ax.tick_params(axis="x", labelsize=text_config.get("x_tick_fontsize", 8.5), length=0)
    ax.tick_params(axis="y", labelsize=text_config.get("y_tick_fontsize", 8.5), length=0)
    if not show_y_axis:
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", left=False, labelleft=False)
    ylabel_text = configured_ylabel if configured_ylabel is not None else text_config.get("y_label_text", "Score")
    ylabel_fontsize = configured_ylabel_fontsize if configured_ylabel_fontsize is not None else text_config.get("y_label_fontsize", plt.rcParams["font.size"])
    ax.set_ylabel(
        ylabel_text if ylabel and show_y_axis else "",
        fontweight=label_fontweight(text_config, "y_label_bold"),
        fontsize=ylabel_fontsize,
        color="#22262C",
    )
    ax.set_xlabel(
        dataset["label"],
        fontweight=label_fontweight(text_config, "x_label_bold"),
        labelpad=text_config.get("dataset_label_pad", 12),
        fontsize=text_config.get("dataset_label_fontsize", 12.5),
        color="#111111",
    )
    return ymin, ymax


def apply_axis_frame(ax, text_config: dict) -> None:
    if not text_config.get("axis_frame_enabled", False):
        return
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(text_config.get("axis_frame_color", "#000000"))
        spine.set_linewidth(text_config.get("axis_frame_linewidth", 1.2))


def apply_avg_axis_frame(ax) -> None:
    apply_axis_frame(ax, AVG_BUBBLE_TEXT_CONFIG)


def format_params(params_b: float) -> str:
    if params_b >= 1000:
        value = params_b / 1000
        return f"{value:.0f}T" if math.isclose(value, round(value)) else f"{value:.1f}T"
    return f"{int(round(params_b))}B"


def param_axis_position(params_b: float) -> float:
    """Piecewise-linear parameter axis through fixed tick coordinates."""
    params = float(params_b)
    if params < 30.0:
        return 0.2
    tick_params = [30.0, 100.0, 500.0, 1000.0, 10000.0]
    tick_positions = [0.1, 0.6, 1.1, 1.6, 2.1]
    if params <= tick_params[0]:
        return tick_positions[0]
    if params >= tick_params[-1]:
        return tick_positions[-1]
    for left_param, right_param, left_pos, right_pos in zip(tick_params, tick_params[1:], tick_positions, tick_positions[1:]):
        if left_param <= params <= right_param:
            fraction = (params - left_param) / (right_param - left_param)
            return left_pos + fraction * (right_pos - left_pos)
    return tick_positions[-1]


def bubble_area(params_b: float) -> float:
    # Matplotlib scatter size is area; keep the user-facing config in radius.
    cfg = BUBBLE_SIZE_CONFIG
    params = min(max(float(params_b), cfg["min_params_b"]), cfg["max_params_b"])
    if params <= cfg["mid_params_b"]:
        t = (params - cfg["min_params_b"]) / (cfg["mid_params_b"] - cfg["min_params_b"])
        radius = cfg["min_radius"] + t * (cfg["mid_radius"] - cfg["min_radius"])
    else:
        t = (params - cfg["mid_params_b"]) / (cfg["max_params_b"] - cfg["mid_params_b"])
        radius = cfg["mid_radius"] + t * (cfg["max_radius"] - cfg["mid_radius"])
    return radius * radius


def x_position(record: ModelRecord, closed_index: int | None = None) -> float:
    if record.size_b is None:
        return param_axis_position(30.0)
    return param_axis_position(record.size_b)


def closed_source_index(records: list[ModelRecord]) -> dict[str, int]:
    closed = [record for record in records if record.closed_source]
    return {record.raw_name: idx for idx, record in enumerate(closed)}


def label_model_key(record: ModelRecord) -> str:
    return "Ours" if record.is_ours else record.raw_name


def label_offsets(index: int) -> tuple[float, float]:
    offsets = [(4.5, 5.5), (4.5, -5.5), (-8.5, 5.5), (-8.5, -5.5), (6.5, 8.0), (-10.5, 8.0), (6.5, -8.0), (-10.5, -8.0)]
    return offsets[index % len(offsets)]


def record_label_offset(record: ModelRecord, index: int, score: float) -> tuple[float, float]:
    if record.is_ours:
        return 6.0, 7.5
    if record.closed_source:
        return -10.0, 8.0 if "Gemini" in record.raw_name else -8.0
    if record.provider == "Shanghai AI Lab":
        return -13.0, 8.0 if score >= 15 else -8.0
    if record.provider == "Qwen":
        return -13.0, 7.0 if index % 2 == 0 else -8.0
    if record.provider == "DeepSeek":
        return (8.0, 8.0) if "Pro" in record.raw_name else (-14.0, 7.0)
    if record.provider == "Kimi":
        return 8.0, -8.0
    if record.provider == "GLM":
        return 7.0, 7.0
    if record.provider == "MiniMax":
        return -14.0, -8.0
    if "Gemma" in record.raw_name:
        return -13.0, 7.5
    return label_offsets(index)


def bubble_label_name(record: ModelRecord) -> str:
    key = label_model_key(record)
    if key in BUBBLE_LABEL_NAME_OVERRIDES:
        return BUBBLE_LABEL_NAME_OVERRIDES[key]
    if record.is_ours:
        return OURS_MODEL_DISPLAY_NAME
    return record.raw_name


def full_label(text: str) -> str:
    if text == OURS_MODEL_DISPLAY_NAME:
        return text
    return "\n".join(textwrap.wrap(text, width=BUBBLE_LABEL_CONFIG["wrap_width"], break_long_words=False, break_on_hyphens=False))


def configured_label_offset(dataset_id: str, record: ModelRecord) -> tuple[float, float] | None:
    dataset_positions = BUBBLE_LABEL_POSITIONS.get(dataset_id, {})
    value = dataset_positions.get(label_model_key(record))
    if value is None:
        return None
    if len(value) != 2:
        raise ValueError(f"BUBBLE_LABEL_POSITIONS[{dataset_id!r}][{label_model_key(record)!r}] must contain exactly two values")
    return float(value[0]), float(value[1])


def annotation_candidates(record: ModelRecord, index: int, score: float, x: float) -> list[tuple[float, float]]:
    base = record_label_offset(record, index, score)
    dy_values = [6, -6, 10, -10, 14, -14, 18, -18, 22, -22]
    if record.is_ours:
        return [base, (6.5, 8), (8, 12), (-8, 10)]
    if x < 0.08:
        candidates = [(7, dy) for dy in dy_values] + [(16, dy) for dy in dy_values[:8]] + [(-7, dy) for dy in dy_values[:6]]
    elif x > 0.78:
        candidates = [(-7, dy) for dy in dy_values] + [(-16, dy) for dy in dy_values[:8]] + [(7, dy) for dy in dy_values[:5]]
    else:
        candidates = [(7, dy) for dy in dy_values[:8]] + [(-7, dy) for dy in dy_values[:8]]
    return [base] + [candidate for candidate in candidates if candidate != base]


def label_center_from_offset(ax, x: float, y: float, x_offset_pct: float, y_offset_pct: float) -> tuple[float, float]:
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    return x + (xmax - xmin) * x_offset_pct / 100.0, y + (ymax - ymin) * y_offset_pct / 100.0


def choose_label_offsets(ax, label_specs: list[dict]) -> dict[int, tuple[float, float]]:
    occupied: list[tuple[float, float, float, float]] = []
    chosen: dict[int, tuple[float, float]] = {}
    point_to_px = ax.figure.dpi / 72.0

    for spec in sorted(label_specs, key=lambda item: (not item["record"].is_ours, item["x"], -item["score"])):
        lines = spec["label"].splitlines() or [spec["label"]]
        max_chars = max(len(line) for line in lines)
        width_px = max(28.0, min(118.0, max_chars * spec["fontsize"] * 0.54 * point_to_px))
        height_px = max(14.0, len(lines) * spec["fontsize"] * 1.25 * point_to_px)

        candidates = [spec["custom_offset"]] if spec.get("custom_offset") is not None else annotation_candidates(spec["record"], spec["index"], spec["score"], spec["x"])
        picked = candidates[0]
        for x_offset_pct, y_offset_pct in candidates:
            label_x, label_y = label_center_from_offset(ax, spec["x"], spec["score"], x_offset_pct, y_offset_pct)
            tx, ty = ax.transData.transform((label_x, label_y))
            rect = (tx - width_px / 2 - 2, ty - height_px / 2 - 2, tx + width_px / 2 + 2, ty + height_px / 2 + 2)
            if not any(rect[0] < other[2] and rect[2] > other[0] and rect[1] < other[3] and rect[3] > other[1] for other in occupied):
                picked = (x_offset_pct, y_offset_pct)
                occupied.append(rect)
                break
        else:
            label_x, label_y = label_center_from_offset(ax, spec["x"], spec["score"], picked[0], picked[1])
            tx, ty = ax.transData.transform((label_x, label_y))
            occupied.append((tx - width_px / 2 - 2, ty - height_px / 2 - 2, tx + width_px / 2 + 2, ty + height_px / 2 + 2))
        chosen[spec["index"]] = picked
    return chosen


def add_top_legend(fig) -> None:
    cfg = LEGEND_CONFIG
    legend_ax = fig.add_axes(cfg["axes"])
    legend_ax.axis("off")
    legend_ax.set_xlim(0, 1)
    legend_ax.set_ylim(0, 1)

    positions = []
    items_per_row = cfg["items_per_row"]
    for start in range(0, len(SERIES_LEGEND), items_per_row):
        row_idx = start // items_per_row
        row_items = SERIES_LEGEND[start : start + items_per_row]
        y = cfg["row_y"][row_idx] if row_idx < len(cfg["row_y"]) else cfg["row_y"][-1]
        if len(row_items) == 1:
            xs = [(cfg["x_start"] + cfg["x_end"]) / 2]
        else:
            xs = np.linspace(cfg["x_start"], cfg["x_end"], len(row_items))
        positions.extend((x, y) for x in xs)

    for (x, y), item in zip(positions, SERIES_LEGEND):
        icon_x = x - cfg["icon_x_offset"]
        if item.get("kind") == "ours":
            legend_ax.scatter(
                [icon_x],
                [y],
                marker="*",
                s=MARKER_CONFIG["legend_ours_star_size"],
                color=OURS_COLOR,
                transform=legend_ax.transAxes,
                zorder=4,
            )
        else:
            logo_file = item.get("logo", "")
            logo_size = cfg["svg_logo_size"] if logo_file.lower().endswith(".svg") else cfg["fallback_logo_size"]
            add_logo(
                legend_ax,
                logo_file,
                item["provider"],
                item.get("fallback_text", item["label"][:2]),
                (icon_x, y),
                xycoords="axes fraction",
                zoom=cfg["logo_zoom"],
                fallback_size=logo_size,
            )
        legend_ax.text(
            x,
            y,
            item["label"],
            transform=legend_ax.transAxes,
            ha="left",
            va="center",
            fontsize=cfg["font_size"],
            fontweight=cfg["closed_fontweight"] if item.get("kind") in {"closed", "ours"} else cfg["default_fontweight"],
            color=cfg["text_color"],
        )


def plot_bar_panel(ax, dataset: dict, records: list[ModelRecord], show_ylabel: bool = False) -> None:
    panel_records = [record for record in records if record.scores.get(dataset["id"]) is not None]
    scores = [record.scores[dataset["id"]] for record in panel_records]
    ymin, ymax = style_axis(ax, dataset, scores, show_ylabel, show_y_axis=OUTPUT_CONFIG["show_bar_y_axis"])
    span = ymax - ymin
    x = np.arange(len(panel_records))
    colors = [
        to_rgba(OURS_COLOR if record.is_ours else provider_color(record.provider), 1.0 if record.is_ours else 0.72)
        for record in panel_records
    ]
    bars = ax.bar(x, scores, width=0.72, color=colors, edgecolor="none", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [record.display_name for record in panel_records],
        rotation=58,
        ha="right",
        va="top",
        rotation_mode="anchor",
        fontsize=5.5,
        fontweight="bold",
    )
    ax.tick_params(axis="x", length=0, pad=2)
    ax.set_xlim(-0.65, len(panel_records) - 0.35)
    for record, score, bar in zip(panel_records, scores, bars):
        if record.is_ours:
            ax.scatter(
                [bar.get_x() + bar.get_width() / 2],
                [max(ymin + span * 0.04, score - span * 0.05)],
                marker="*",
                s=MARKER_CONFIG["bar_ours_star_size"],
                color=OURS_COLOR,
                zorder=5,
            )
        else:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                max(ymin + span * 0.04, score - span * 0.055),
                provider_abbrev(record.provider),
                ha="center",
                va="center",
                fontsize=7.2,
                fontweight="bold",
                color="white",
                bbox=dict(boxstyle="round,pad=0.22", fc=provider_color(record.provider), ec="none", alpha=0.95),
                zorder=5,
            )
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            min(score + span * 0.018, ymax - span * 0.025),
            f"{score:g}",
            ha="center",
            va="bottom",
            fontsize=7.6,
            fontweight="bold" if record.is_ours else "normal",
            color=OURS_COLOR if record.is_ours else "#4C525C",
            zorder=6,
        )


def provider_abbrev(provider: str) -> str:
    return {
        "Shanghai AI Lab": "P1",
        "DeepSeek": "DS",
        "MiniMax": "MM",
        "OpenAI": "GPT",
        "Google": "G",
        "Claude": "CLA",
    }.get(provider, provider[:2].upper())


def y_range(ax) -> float:
    ymin, ymax = ax.get_ylim()
    return abs(ymax - ymin)


def x_range(ax) -> float:
    xmin, xmax = ax.get_xlim()
    return abs(xmax - xmin)


def configured_arrow_text_offset(dataset_id: str, text_key: str, fallback: tuple[float, float]) -> tuple[float, float]:
    value = ARROW_TEXT_POSITIONS.get(dataset_id, {}).get(text_key)
    if value is None:
        return fallback
    if len(value) != 2:
        raise ValueError(f"ARROW_TEXT_POSITIONS[{dataset_id!r}][{text_key!r}] must contain exactly two values")
    return float(value[0]), float(value[1])


def arrow_text_center_from_offset(ax, anchor_x: float, anchor_y: float, x_offset_pct: float, y_offset_pct: float) -> tuple[float, float]:
    return label_center_from_offset(ax, anchor_x, anchor_y, x_offset_pct, y_offset_pct)


def efficiency_target_point(points: dict[str, tuple[float, float]], gain_config: dict | None = None) -> tuple[float, float] | None:
    cfg = gain_config or GAIN_ARROW_CONFIG
    if "Ours" not in points:
        return None
    ours_x, ours_y = points["Ours"]
    target_x = cfg.get("efficiency_target_x")
    if target_x is None:
        x_offset_ratio = cfg.get("efficiency_target_x_offset_ratio")
        if x_offset_ratio is not None:
            x_span = BUBBLE_X_AXIS_CONFIG["xmax"] - BUBBLE_X_AXIS_CONFIG["xmin"]
            target_x = ours_x + x_span * float(x_offset_ratio)
        else:
            target_x = ours_x + cfg.get("efficiency_target_x_offset", 0.0)
    return target_x, ours_y + cfg.get("efficiency_y_offset", 0.0)


def annotate_arrow(ax, xy: tuple[float, float], xytext: tuple[float, float], color, gain_config: dict | None = None) -> None:
    cfg = gain_config or GAIN_ARROW_CONFIG
    annotation = ax.annotate(
        "",
        xy=xy,
        xytext=xytext,
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=cfg["linewidth"],
            mutation_scale=cfg["arrow_mutation_scale"],
            shrinkA=0,
            shrinkB=0,
        ),
        annotation_clip=cfg["clip_on"],
        zorder=cfg["zorder"],
    )
    if annotation.arrow_patch is not None:
        annotation.arrow_patch.set_clip_on(cfg["clip_on"])


def add_gain_arrow(
    ax,
    points: dict[str, tuple[float, float]],
    dataset_id: str,
    text_config: dict | None = None,
    gain_config: dict | None = None,
) -> None:
    text_config = text_config or {}
    cfg = gain_config or GAIN_ARROW_CONFIG
    if not cfg["enabled"] or not cfg["show_gain_arrow"] or "Ours" not in points or cfg["baseline_model"] not in points:
        return

    ours_x, ours_y = points["Ours"]
    _, baseline_y = points[cfg["baseline_model"]]
    arrow_x = ours_x + cfg["x_offset"]
    head_y = ours_y + y_range(ax) * cfg["gain_arrow_head_y_offset_ratio"]
    half_cap = cfg["cap_width"] / 2
    color = cfg["color"] or OURS_COLOR

    ax.plot(
        [arrow_x - half_cap, arrow_x + half_cap],
        [baseline_y, baseline_y],
        color=color,
        lw=cfg["linewidth"],
        solid_capstyle="round",
        clip_on=cfg["clip_on"],
        zorder=cfg["zorder"],
    )
    ax.plot(
        [arrow_x - half_cap, arrow_x + half_cap],
        [head_y, head_y],
        color=color,
        lw=cfg["linewidth"],
        solid_capstyle="round",
        clip_on=cfg["clip_on"],
        zorder=cfg["zorder"],
    )
    annotate_arrow(ax, (arrow_x, head_y), (arrow_x, baseline_y), color, gain_config=cfg)
    if cfg["gain_text_enabled"]:
        improvement = ours_y - baseline_y
        anchor_x = arrow_x
        anchor_y = (baseline_y + head_y) / 2
        fallback = (
            cfg["gain_text_x_offset"] / x_range(ax) * 100 if x_range(ax) else 0.0,
            cfg["gain_text_y_offset_ratio"] * 100,
        )
        text_offset = configured_arrow_text_offset(dataset_id, "gain", fallback)
        text_x, text_y = arrow_text_center_from_offset(ax, anchor_x, anchor_y, text_offset[0], text_offset[1])
        ax.text(
            text_x,
            text_y,
            cfg["gain_text_template"].format(improvement=improvement),
            color=color,
            fontsize=text_config.get("gain_text_fontsize", cfg["gain_text_fontsize"]),
            fontweight="bold",
            ha="center",
            va="center",
            clip_on=cfg["clip_on"],
            zorder=cfg["zorder"] + 1,
        )


def add_efficiency_arrow(ax, points: dict[str, tuple[float, float]], gain_config: dict | None = None) -> None:
    cfg = gain_config or GAIN_ARROW_CONFIG
    if not cfg["enabled"] or not cfg["show_efficiency_arrow"] or "Ours" not in points:
        return

    target = efficiency_target_point(points, gain_config=cfg)
    if target is None:
        return
    target_x, arrow_y = target
    source_x = param_axis_position(cfg["efficiency_source_params_b"])
    half_cap = y_range(ax) * cfg["efficiency_cap_height_ratio"] / 2
    color = cfg["color"] or OURS_COLOR

    ax.plot(
        [source_x, source_x],
        [arrow_y - half_cap, arrow_y + half_cap],
        color=color,
        lw=cfg["linewidth"],
        solid_capstyle="round",
        clip_on=cfg["clip_on"],
        zorder=cfg["zorder"],
    )
    ax.plot(
        [target_x, target_x],
        [arrow_y - half_cap, arrow_y + half_cap],
        color=color,
        lw=cfg["linewidth"],
        solid_capstyle="round",
        clip_on=cfg["clip_on"],
        zorder=cfg["zorder"],
    )
    annotate_arrow(ax, (target_x, arrow_y), (source_x, arrow_y), color, gain_config=cfg)


def add_frontier_efficiency_arrow(
    ax,
    points: dict[str, tuple[float, float]],
    dataset_id: str,
    text_config: dict | None = None,
    gain_config: dict | None = None,
) -> None:
    text_config = text_config or {}
    cfg = gain_config or GAIN_ARROW_CONFIG
    if not cfg["enabled"] or not cfg["show_frontier_efficiency_arrow"]:
        return
    target = efficiency_target_point(points, gain_config=cfg)
    if target is None:
        return
    candidates = [(model, points[model]) for model in cfg["frontier_efficiency_source_models"] if model in points]
    if not candidates:
        return

    _, (source_x, source_y) = max(candidates, key=lambda item: item[1][1])
    target_x, target_y = target
    color = cfg["color"] or OURS_COLOR
    annotate_arrow(ax, (target_x, target_y), (source_x, source_y), color, gain_config=cfg)

    if cfg["frontier_efficiency_text_enabled"]:
        anchor_x = (source_x + target_x) / 2
        anchor_y = (source_y + target_y) / 2
        text_offset = configured_arrow_text_offset(
            dataset_id,
            "frontier_efficiency",
            (0.0, cfg.get("frontier_efficiency_text_y_offset_ratio", 0.015) * 100),
        )
        text_x, text_y = arrow_text_center_from_offset(ax, anchor_x, anchor_y, text_offset[0], text_offset[1])
        ax.text(
            text_x,
            text_y,
            cfg["frontier_efficiency_text"],
            color=color,
            fontsize=text_config.get(
                "frontier_efficiency_text_fontsize",
                text_config.get("efficiency_text_fontsize", cfg["frontier_efficiency_text_fontsize"]),
            ),
            fontweight="bold",
            ha="center",
            va="center",
            clip_on=cfg["clip_on"],
            zorder=cfg["zorder"] + 1,
        )


def plot_bubble_panel(
    ax,
    dataset: dict,
    records: list[ModelRecord],
    show_ylabel: bool = False,
    show_xlabel: bool = False,
    show_dataset_name: bool = True,
    text_config: dict | None = None,
    gain_config: dict | None = None,
) -> None:
    text_config = text_config or BUBBLE_TEXT_CONFIG
    gain_config = gain_config or GAIN_ARROW_CONFIG
    panel_records = [record for record in records if record.scores.get(dataset["id"]) is not None]
    scores = [record.scores[dataset["id"]] for record in panel_records]
    ymin, ymax = style_axis(ax, dataset, scores, show_ylabel, show_y_axis=True, text_config=text_config)
    apply_axis_frame(ax, text_config)
    axis_ticks = [30, 100, 500, 1000, 10000]
    ax.set_xlim(BUBBLE_X_AXIS_CONFIG["xmin"], BUBBLE_X_AXIS_CONFIG["xmax"])
    ax.xaxis.set_major_locator(FixedLocator([param_axis_position(tick) for tick in axis_ticks]))
    ax.set_xticklabels([format_params(tick) for tick in axis_ticks])
    ax.tick_params(axis="x", labelsize=text_config["x_tick_fontsize"])
    ax.set_xlabel(
        text_config["x_label_text"],
        fontweight=label_fontweight(text_config, "x_label_bold"),
        labelpad=text_config["x_label_pad"],
        fontsize=text_config["x_label_fontsize"],
        color="#22262C",
    )
    if show_dataset_name:
        ax.text(
            0.5,
            -text_config["x_label_to_dataset_name_gap"],
            dataset["label"],
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=text_config["dataset_name_fontsize"],
            fontweight="bold",
            color="#111111",
        )
    ax.grid(axis="x", which="major", color="#E9EDF3", linewidth=0.9)

    closed_idx = closed_source_index(records)
    label_specs = []
    points: dict[str, tuple[float, float]] = {}
    for idx, record in enumerate(panel_records):
        score = record.scores[dataset["id"]]
        x = x_position(record, closed_idx.get(record.raw_name))
        point_key = "Ours" if record.is_ours else record.raw_name
        points[point_key] = (x, score)
        if record.is_ours:
            ax.scatter(
                [x],
                [score],
                marker="*",
                s=MARKER_CONFIG["bubble_ours_star_size"],
                color=OURS_COLOR,
                clip_on=BUBBLE_CLIP_CONFIG["clip_markers"],
                zorder=8,
            )
        else:
            params = record.size_b or 30
            ax.scatter(
                [x],
                [score],
                s=bubble_area(params),
                color=provider_color(record.provider),
                alpha=0.66,
                edgecolors="none",
                clip_on=BUBBLE_CLIP_CONFIG["clip_markers"],
                zorder=4,
            )
        label = full_label(bubble_label_name(record))
        fontsize = text_config["model_name_fontsize"]
        label_specs.append(
            {
                "index": idx,
                "record": record,
                "score": score,
                "x": x,
                "label": label,
                "fontsize": fontsize,
                "custom_offset": configured_label_offset(dataset["id"], record),
            }
        )

    add_gain_arrow(ax, points, dataset["id"], text_config=text_config, gain_config=gain_config)
    add_efficiency_arrow(ax, points, gain_config=gain_config)
    add_frontier_efficiency_arrow(ax, points, dataset["id"], text_config=text_config, gain_config=gain_config)

    if not BUBBLE_LABEL_CONFIG["show_model_labels"]:
        return

    offsets = choose_label_offsets(ax, label_specs)
    for spec in label_specs:
        x_offset_pct, y_offset_pct = offsets[spec["index"]]
        label_x, label_y = label_center_from_offset(ax, spec["x"], spec["score"], x_offset_pct, y_offset_pct)
        ax.annotate(
            spec["label"],
            xy=(spec["x"], spec["score"]),
            xytext=(label_x, label_y),
            textcoords="data",
            ha="center",
            va="center",
            fontsize=spec["fontsize"],
            fontweight=BUBBLE_LABEL_CONFIG["fontweight"],
            color=BUBBLE_LABEL_CONFIG["text_color"],
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=BUBBLE_LABEL_CONFIG["text_background_alpha"]),
            arrowprops=dict(
                arrowstyle="-",
                color=BUBBLE_LABEL_CONFIG["arrow_color"],
                lw=BUBBLE_LABEL_CONFIG["arrow_linewidth"],
                alpha=BUBBLE_LABEL_CONFIG["arrow_alpha"],
                shrinkA=BUBBLE_LABEL_CONFIG["arrow_shrink_a"],
                shrinkB=BUBBLE_LABEL_CONFIG["arrow_shrink_b"],
            ),
            zorder=10,
        )


def plot_bars(records: list[ModelRecord]) -> Path:
    dataset_grid, rows, cols = selected_dataset_grid()
    fig, axes = subplot_grid(rows, cols, bottom=FIGURE_LAYOUT_CONFIG["bar_bottom"])
    add_top_legend(fig)
    add_domain_titles(fig, axes, dataset_grid)
    for row_idx, row in enumerate(dataset_grid):
        for col_idx, dataset in enumerate(row):
            plot_bar_panel(axes[row_idx, col_idx], dataset, records, show_ylabel=(col_idx == 0))
    out = ROOT / OUTPUT_CONFIG["bar_png"]
    save_figure(fig, out)
    plt.close(fig)
    return out


def plot_bubbles(records: list[ModelRecord]) -> Path:
    dataset_grid, rows, cols = selected_dataset_grid()
    fig, axes = subplot_grid(rows, cols, bottom=FIGURE_LAYOUT_CONFIG["bubble_bottom"], text_config=BUBBLE_TEXT_CONFIG)
    if OUTPUT_CONFIG.get("show_bubble_legend", False):
        add_top_legend(fig)
    add_domain_titles(fig, axes, dataset_grid, text_config=BUBBLE_TEXT_CONFIG)
    for row_idx, row in enumerate(dataset_grid):
        for col_idx, dataset in enumerate(row):
            plot_bubble_panel(
                axes[row_idx, col_idx],
                dataset,
                records,
                show_ylabel=True,
                show_xlabel=(row_idx == rows - 1),
            )
    out = ROOT / OUTPUT_CONFIG["bubble_png"]
    save_figure(fig, out)
    plt.close(fig)
    return out


def plot_avg_bubble(records: list[ModelRecord]) -> Path:
    dataset = {**DATASET_META["avg"], "id": "avg"}
    fig, ax = plt.subplots(1, 1, figsize=OUTPUT_CONFIG["avg_figsize"])
    fig.subplots_adjust(
        left=FIGURE_LAYOUT_CONFIG["avg_left"],
        right=FIGURE_LAYOUT_CONFIG["avg_right"],
        top=FIGURE_LAYOUT_CONFIG["avg_top"],
        bottom=FIGURE_LAYOUT_CONFIG["avg_bottom"],
    )
    plot_bubble_panel(
        ax,
        dataset,
        records,
        show_ylabel=True,
        show_xlabel=True,
        show_dataset_name=False,
        text_config=AVG_BUBBLE_TEXT_CONFIG,
        gain_config=AVG_GAIN_ARROW_CONFIG,
    )
    apply_avg_axis_frame(ax)
    ax.set_title(
        "Scientific Intelligence Evaluation",
        fontsize=AVG_BUBBLE_TEXT_CONFIG["title_fontsize"],
        fontweight="bold",
        color="#050505",
        pad=14, #30,
    )

    # ✅ 副标题（更小字号）
    # fig.text(
    #     0.55,
    #     0.92,  # 位置可微调（越大越靠上）
    #     "(HLE w/ tools, CritPt, CMT-Benchmark, FrontierScience-Research, "
    #     "FrontierScience-Olympiad, HiPhO, AMOBench, IMO-AnswerBench)",
    #     ha="center",
    #     va="center",
    #     fontsize=AVG_BUBBLE_TEXT_CONFIG["subtitle_fontsize"],
    #     color="#555555",
    # )

    out = ROOT / OUTPUT_CONFIG["bubble_avg_png"]
    save_figure(fig, out)
    plt.close(fig)
    return out


def color_to_hex(color) -> str:
    r, g, b, _ = to_rgba(color)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def label_editor_view_settings(view: str) -> dict:
    cfg = LABEL_EDITOR_CONFIG
    if view == "avg":
        pixels_per_inch = float(cfg["avg_canvas_pixels_per_inch"])
        configured_canvas = cfg.get("avg_canvas")
        if configured_canvas is None:
            fig_w, fig_h = OUTPUT_CONFIG["avg_figsize"]
            canvas_width = fig_w * pixels_per_inch
            canvas_height = fig_h * pixels_per_inch
        else:
            canvas_width, canvas_height = configured_canvas
        configured_margins = cfg.get("avg_margins")
        if configured_margins is None:
            margins = {
                "left": canvas_width * FIGURE_LAYOUT_CONFIG["avg_left"],
                "right": canvas_width * (1.0 - FIGURE_LAYOUT_CONFIG["avg_right"]),
                "top": canvas_height * (1.0 - FIGURE_LAYOUT_CONFIG["avg_top"]),
                "bottom": canvas_height * FIGURE_LAYOUT_CONFIG["avg_bottom"],
            }
        else:
            margins = configured_margins
        circle_radius_scale = cfg["avg_circle_radius_scale"]
        if circle_radius_scale is None:
            circle_radius_scale = pixels_per_inch / 144.0
        star_font_scale = cfg["avg_star_font_scale"]
        if star_font_scale is None:
            star_font_scale = pixels_per_inch / 72.0
    else:
        canvas_width, canvas_height = cfg["grid_canvas"]
        margins = cfg["grid_margins"]
        circle_radius_scale = cfg["grid_circle_radius_scale"]
        star_font_scale = cfg["grid_star_font_scale"]

    return {
        "canvas": {"width": round(float(canvas_width), 2), "height": round(float(canvas_height), 2)},
        "margins": {key: round(float(value), 2) for key, value in margins.items()},
        "marker": {
            "circleRadiusScale": float(circle_radius_scale),
            "starFontScale": float(star_font_scale),
        },
    }


def build_label_editor_payload(records: list[ModelRecord], view: str = "grid") -> dict:
    if view not in {"grid", "avg"}:
        raise ValueError("label editor view must be either 'grid' or 'avg'")
    dataset_grid, rows, cols = selected_dataset_grid()
    closed_idx = closed_source_index(records)
    view_settings = label_editor_view_settings(view)

    def build_panel(dataset: dict, row_idx: int, col_idx: int) -> dict:
        cfg = AVG_GAIN_ARROW_CONFIG if dataset["id"] == "avg" else GAIN_ARROW_CONFIG
        panel_records = [record for record in records if record.scores.get(dataset["id"]) is not None]
        scores = [record.scores[dataset["id"]] for record in panel_records]
        (ymin, ymax), yticks, _, _ = configured_y_axis(dataset["id"], scores)
        points = []
        point_map: dict[str, tuple[float, float]] = {}
        for idx, record in enumerate(panel_records):
            score = record.scores[dataset["id"]]
            x = x_position(record, closed_idx.get(record.raw_name))
            key = label_model_key(record)
            point_map[key] = (x, score)
            offset = configured_label_offset(dataset["id"], record)
            if offset is None:
                offset = record_label_offset(record, idx, score)
            marker = "star" if record.is_ours else "circle"
            size = MARKER_CONFIG["bubble_ours_star_size"] if record.is_ours else bubble_area(record.size_b or 30)
            points.append(
                {
                    "key": key,
                    "label": full_label(bubble_label_name(record)),
                    "x": x,
                    "y": score,
                    "offset": [round(float(offset[0]), 2), round(float(offset[1]), 2)],
                    "color": color_to_hex(OURS_COLOR if record.is_ours else provider_color(record.provider)),
                    "marker": marker,
                    "size": size,
                }
            )

        arrow_texts = []
        x_min, x_max = BUBBLE_X_AXIS_CONFIG["xmin"], BUBBLE_X_AXIS_CONFIG["xmax"]
        x_span = abs(x_max - x_min)
        y_span = abs(ymax - ymin)
        if cfg["enabled"] and cfg["show_gain_arrow"] and cfg["gain_text_enabled"] and "Ours" in point_map and cfg["baseline_model"] in point_map:
            ours_x, ours_y = point_map["Ours"]
            _, baseline_y = point_map[cfg["baseline_model"]]
            head_y = ours_y + y_span * cfg["gain_arrow_head_y_offset_ratio"]
            anchor_x = ours_x + cfg["x_offset"]
            anchor_y = (baseline_y + head_y) / 2
            gain_fallback = (
                cfg["gain_text_x_offset"] / x_span * 100 if x_span else 0.0,
                cfg["gain_text_y_offset_ratio"] * 100,
            )
            gain_offset = configured_arrow_text_offset(dataset["id"], "gain", gain_fallback)
            arrow_texts.append(
                {
                    "key": "gain",
                    "label": cfg["gain_text_template"].format(improvement=ours_y - baseline_y),
                    "anchorX": anchor_x,
                    "anchorY": anchor_y,
                    "offset": [round(float(gain_offset[0]), 2), round(float(gain_offset[1]), 2)],
                    "color": color_to_hex(cfg["color"] or OURS_COLOR),
                }
            )
        if cfg["enabled"] and cfg["show_frontier_efficiency_arrow"] and cfg["frontier_efficiency_text_enabled"] and "Ours" in point_map:
            candidates = [(model, point_map[model]) for model in cfg["frontier_efficiency_source_models"] if model in point_map]
            if candidates:
                _, (source_x, source_y) = max(candidates, key=lambda item: item[1][1])
                target = efficiency_target_point(point_map, gain_config=cfg)
                if target is not None:
                    target_x, target_y = target
                    frontier_offset = configured_arrow_text_offset(
                        dataset["id"],
                        "frontier_efficiency",
                        (0.0, cfg.get("frontier_efficiency_text_y_offset_ratio", 0.015) * 100),
                    )
                    arrow_texts.append(
                        {
                            "key": "frontier_efficiency",
                            "label": cfg["frontier_efficiency_text"],
                            "anchorX": (source_x + target_x) / 2,
                            "anchorY": (source_y + target_y) / 2,
                            "offset": [round(float(frontier_offset[0]), 2), round(float(frontier_offset[1]), 2)],
                            "color": color_to_hex(cfg["color"] or OURS_COLOR),
                        }
                    )

        return {
            "id": dataset["id"],
            "label": dataset["label"],
            "domain": dataset["domain"],
            "row": row_idx,
            "col": col_idx,
            "xlim": [BUBBLE_X_AXIS_CONFIG["xmin"], BUBBLE_X_AXIS_CONFIG["xmax"]],
            "xticks": [{"value": tick, "x": param_axis_position(tick), "label": format_params(tick)} for tick in [30, 100, 500, 1000, 10000]],
            "ylim": [ymin, ymax],
            "yticks": yticks,
            "points": points,
            "arrowTexts": arrow_texts,
        }

    panels = []
    if view == "avg":
        panels.append(build_panel({**DATASET_META["avg"], "id": "avg"}, 0, 0))
        output_rows, output_cols = 1, 1
    else:
        for row_idx, row in enumerate(dataset_grid):
            for col_idx, dataset in enumerate(row):
                panels.append(build_panel(dataset, row_idx, col_idx))
        output_rows, output_cols = rows, cols
    return {
        "view": view,
        "rows": output_rows,
        "cols": output_cols,
        "canvas": view_settings["canvas"],
        "margins": view_settings["margins"],
        "marker": view_settings["marker"],
        "positionUnit": "axis_percent",
        "positions": BUBBLE_LABEL_POSITIONS,
        "arrowTextPositions": ARROW_TEXT_POSITIONS,
        "panels": panels,
    }


def format_positions_py(
    positions: dict[str, dict[str, list[float] | tuple[float, float]]],
    arrow_text_positions: dict[str, dict[str, list[float] | tuple[float, float]]] | None = None,
) -> str:
    lines = ["BUBBLE_LABEL_POSITIONS = {"]
    for dataset_id in position_dataset_ids():
        lines.append(f'    "{dataset_id}": {{')
        for model_key, offset in positions.get(dataset_id, {}).items():
            dx, dy = round(float(offset[0]), 2), round(float(offset[1]), 2)
            lines.append(f'        "{model_key}": ({dx:.2f}, {dy:.2f}),')
        lines.append("    },")
    lines.append("}")
    lines.append("")
    if arrow_text_positions is not None:
        lines.append("ARROW_TEXT_POSITIONS = {")
        for dataset_id in position_dataset_ids():
            lines.append(f'    "{dataset_id}": {{')
            for text_key, offset in arrow_text_positions.get(dataset_id, {}).items():
                dx, dy = round(float(offset[0]), 2), round(float(offset[1]), 2)
                lines.append(f'        "{text_key}": ({dx:.2f}, {dy:.2f}),')
            lines.append("    },")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


LABEL_EDITOR_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Bubble Label Position Editor</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; color: #15181d; background: #f6f7f9; }
    header { position: sticky; top: 0; z-index: 5; display: flex; gap: 16px; align-items: center; padding: 12px 18px; background: white; border-bottom: 1px solid #d8dce2; }
    button { font: inherit; font-weight: 700; padding: 8px 14px; border: 0; border-radius: 6px; background: #0ca982; color: white; cursor: pointer; }
    #status { color: #4c525c; font-size: 13px; }
    #grid { padding: 18px; display: grid; gap: 18px; }
    .panel { background: white; border: 1px solid #d8dce2; border-radius: 8px; overflow: hidden; }
    .panel-title { padding: 10px 12px 0; font-weight: 800; font-size: 16px; }
    svg { display: block; width: 100%; height: 360px; user-select: none; }
    .grid-line { stroke: #e9edf3; stroke-width: 1; }
    .axis { stroke: #d8dce2; stroke-width: 1; }
    .tick-label { fill: #3b3f46; font-size: 11px; font-weight: 700; }
    .label { cursor: move; font-size: 11px; font-weight: 800; fill: #12161c; paint-order: stroke; stroke: white; stroke-width: 3px; stroke-linejoin: round; }
    .arrow-text { cursor: move; font-size: 11px; font-weight: 900; fill: #e31a1c; paint-order: stroke; stroke: white; stroke-width: 3px; stroke-linejoin: round; }
    .leader { stroke: #8c96a3; stroke-width: 1; opacity: .75; }
    .arrow-text-leader { stroke: #e31a1c; stroke-width: 1; opacity: .45; stroke-dasharray: 4 3; }
  </style>
</head>
<body>
  <header>
    <button id="save">Save positions</button>
    <span id="status">Drag labels, then save axis-percent positions. Output: bubble_label_positions.generated.py</span>
  </header>
  <main id="grid"></main>
  <script>
    let W = 520, H = 360;
    let M = {left: 58, right: 22, top: 24, bottom: 54};
    let markerConfig = {circleRadiusScale: 1 / 4.2, starFontScale: 1.27};
    let payload, positions, arrowTextPositions, drag = null;

    function sx(panel, x) {
      return M.left + (x - panel.xlim[0]) / (panel.xlim[1] - panel.xlim[0]) * (W - M.left - M.right);
    }
    function sy(panel, y) {
      return H - M.bottom - (y - panel.ylim[0]) / (panel.ylim[1] - panel.ylim[0]) * (H - M.top - M.bottom);
    }
    function markerRadius(point) {
      return Math.sqrt(point.size) * markerConfig.circleRadiusScale;
    }
    function starFontSize(point) {
      return Math.sqrt(point.size) * markerConfig.starFontScale;
    }
    function offsetXY(panel, anchorX, anchorY, off) {
      const labelX = anchorX + (panel.xlim[1] - panel.xlim[0]) * off[0] / 100;
      const labelY = anchorY + (panel.ylim[1] - panel.ylim[0]) * off[1] / 100;
      return {x: sx(panel, labelX), y: sy(panel, labelY)};
    }
    function labelXY(panel, point) {
      const off = positions[panel.id][point.key] || point.offset;
      return offsetXY(panel, point.x, point.y, off);
    }
    function arrowTextXY(panel, item) {
      const off = arrowTextPositions[panel.id][item.key] || item.offset;
      return offsetXY(panel, item.anchorX, item.anchorY, off);
    }
    function svgEl(name, attrs = {}) {
      const el = document.createElementNS("http://www.w3.org/2000/svg", name);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
      return el;
    }
    function textLines(text) {
      return String(text).split("\n");
    }
    function drawPanel(panel) {
      const div = document.createElement("section");
      div.className = "panel";
      div.innerHTML = `<div class="panel-title">${panel.label}</div>`;
      const svg = svgEl("svg", {viewBox: `0 0 ${W} ${H}`});
      svg.style.height = `${H}px`;
      div.appendChild(svg);

      panel.xticks.forEach(t => {
        const x = sx(panel, t.x);
        svg.appendChild(svgEl("line", {class: "grid-line", x1: x, y1: M.top, x2: x, y2: H - M.bottom}));
        const txt = svgEl("text", {class: "tick-label", x, y: H - 26, "text-anchor": "middle"});
        txt.textContent = t.label;
        svg.appendChild(txt);
      });
      (panel.yticks || []).forEach(t => {
        const y = sy(panel, t);
        svg.appendChild(svgEl("line", {class: "grid-line", x1: M.left, y1: y, x2: W - M.right, y2: y}));
        const txt = svgEl("text", {class: "tick-label", x: M.left - 8, y: y + 4, "text-anchor": "end"});
        txt.textContent = t;
        svg.appendChild(txt);
      });
      svg.appendChild(svgEl("line", {class: "axis", x1: M.left, y1: M.top, x2: M.left, y2: H - M.bottom}));
      svg.appendChild(svgEl("line", {class: "axis", x1: M.left, y1: H - M.bottom, x2: W - M.right, y2: H - M.bottom}));

      panel.points.forEach(point => {
        const cx = sx(panel, point.x), cy = sy(panel, point.y);
        if (point.marker === "star") {
          const fontSize = starFontSize(point);
          const star = svgEl("text", {x: cx, y: cy + fontSize * 0.28, "text-anchor": "middle", fill: point.color, "font-size": fontSize, "font-weight": 900});
          star.textContent = "★";
          svg.appendChild(star);
        } else {
          svg.appendChild(svgEl("circle", {cx, cy, r: markerRadius(point), fill: point.color, opacity: .66}));
        }
      });

      panel.points.forEach(point => {
        const cx = sx(panel, point.x), cy = sy(panel, point.y);
        const pos = labelXY(panel, point);
        const line = svgEl("line", {class: "leader", x1: cx, y1: cy, x2: pos.x, y2: pos.y});
        svg.appendChild(line);
        const g = svgEl("g", {"data-panel": panel.id, "data-key": point.key, transform: `translate(${pos.x},${pos.y})`});
        const text = svgEl("text", {class: "label", "text-anchor": "middle"});
        textLines(point.label).forEach((lineText, i) => {
          const tspan = svgEl("tspan", {x: 0, dy: i === 0 ? 0 : 13});
          tspan.textContent = lineText;
          text.appendChild(tspan);
        });
        g.appendChild(text);
        g.addEventListener("pointerdown", event => {
          drag = {type: "model", panel, key: point.key, startX: event.clientX, startY: event.clientY, startOffset: [...positions[panel.id][point.key]]};
          g.setPointerCapture(event.pointerId);
        });
        svg.appendChild(g);
      });
      (panel.arrowTexts || []).forEach(item => {
        const cx = sx(panel, item.anchorX), cy = sy(panel, item.anchorY);
        const pos = arrowTextXY(panel, item);
        svg.appendChild(svgEl("line", {class: "arrow-text-leader", x1: cx, y1: cy, x2: pos.x, y2: pos.y}));
        const g = svgEl("g", {"data-panel": panel.id, "data-key": item.key, transform: `translate(${pos.x},${pos.y})`});
        const text = svgEl("text", {class: "arrow-text", "text-anchor": "middle"});
        text.textContent = item.label;
        g.appendChild(text);
        g.addEventListener("pointerdown", event => {
          drag = {type: "arrowText", panel, key: item.key, startX: event.clientX, startY: event.clientY, startOffset: [...arrowTextPositions[panel.id][item.key]]};
          g.setPointerCapture(event.pointerId);
        });
        svg.appendChild(g);
      });
      return div;
    }
    function redraw() {
      const grid = document.getElementById("grid");
      const minColumnWidth = payload.view === "avg" ? Math.min(W, 1100) : 360;
      grid.style.gridTemplateColumns = `repeat(${payload.cols}, minmax(${minColumnWidth}px, 1fr))`;
      grid.innerHTML = "";
      payload.panels.forEach(panel => grid.appendChild(drawPanel(panel)));
    }
    document.addEventListener("pointermove", event => {
      if (!drag) return;
      const plotWidth = W - M.left - M.right;
      const plotHeight = H - M.top - M.bottom;
      const dx = (event.clientX - drag.startX) / plotWidth * 100;
      const dy = -(event.clientY - drag.startY) / plotHeight * 100;
      const targetPositions = drag.type === "arrowText" ? arrowTextPositions : positions;
      targetPositions[drag.panel.id][drag.key] = [
        Number((drag.startOffset[0] + dx).toFixed(2)),
        Number((drag.startOffset[1] + dy).toFixed(2))
      ];
      redraw();
    });
    document.addEventListener("pointerup", () => { drag = null; });
    document.getElementById("save").addEventListener("click", async () => {
      const res = await fetch("/save", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({positions, arrowTextPositions})});
      const data = await res.json();
      document.getElementById("status").textContent = data.ok ? `Saved ${data.path}` : `Save failed: ${data.error}`;
    });
    fetch("/data.json").then(r => r.json()).then(data => {
      payload = data;
      W = Number(data.canvas?.width || W);
      H = Number(data.canvas?.height || H);
      M = Object.assign({}, M, data.margins || {});
      markerConfig = Object.assign({}, markerConfig, data.marker || {});
      positions = JSON.parse(JSON.stringify(data.positions));
      arrowTextPositions = JSON.parse(JSON.stringify(data.arrowTextPositions || {}));
      for (const panel of payload.panels) {
        positions[panel.id] = positions[panel.id] || {};
        for (const point of panel.points) {
          positions[panel.id][point.key] = positions[panel.id][point.key] || point.offset;
        }
        arrowTextPositions[panel.id] = arrowTextPositions[panel.id] || {};
        for (const item of panel.arrowTexts || []) {
          arrowTextPositions[panel.id][item.key] = arrowTextPositions[panel.id][item.key] || item.offset;
        }
      }
      redraw();
    });
  </script>
</body>
</html>
"""


def run_label_editor(records: list[ModelRecord], port: int, view: str = "grid") -> None:
    payload = build_label_editor_payload(records, view=view)
    output = ROOT / "bubble_label_positions.generated.py"

    class LabelEditorHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/data.json":
                self._send(200, "application/json", json.dumps(payload).encode("utf-8"))
            else:
                self._send(200, "text/html; charset=utf-8", LABEL_EDITOR_HTML.encode("utf-8"))

        def do_POST(self):
            if self.path != "/save":
                self._send(404, "application/json", b'{"ok": false, "error": "not found"}')
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                output.write_text(format_positions_py(body["positions"], body.get("arrowTextPositions")), encoding="utf-8")
                response = {"ok": True, "path": str(output)}
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            self._send(200, "application/json", json.dumps(response).encode("utf-8"))

    server = HTTPServer(("127.0.0.1", port), LabelEditorHandler)
    print(f"Label editor ({view}): http://127.0.0.1:{port}")
    print(f"Save output: {output}")
    server.serve_forever()


def main() -> None:
    setup_style()
    records = selected_records(load_excel_records(EXCEL_PATH))
    if not records:
        raise RuntimeError("No selected records found. Check results.xlsx and model lists.")
    paths = []
    if OUTPUT_CONFIG["draw_bar_plot"]:
        paths.append(plot_bars(records))
    if OUTPUT_CONFIG["draw_bubble_grid_plot"]:
        paths.append(plot_bubbles(records))
    if OUTPUT_CONFIG["draw_bubble_avg_plot"]:
        paths.append(plot_avg_bubble(records))
    if not paths:
        raise RuntimeError("At least one of draw_bar_plot, draw_bubble_grid_plot, or draw_bubble_avg_plot must be True.")
    for path in paths:
        print(path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label-editor", action="store_true", help="start browser label-position editor instead of writing PNGs")
    parser.add_argument("--label-editor-view", choices=["grid", "avg"], default="grid", help="choose 2x4 grid or Average Performance single-panel editor")
    parser.add_argument("--port", type=int, default=8765, help="port for --label-editor")
    args = parser.parse_args()
    if args.label_editor:
        setup_style()
        editor_records = selected_records(load_excel_records(EXCEL_PATH))
        run_label_editor(editor_records, args.port, view=args.label_editor_view)
    else:
        main()
